#!/usr/bin/env python3
"""depth_contrast.py -- where along z is the ink visible in the raw CT, no model involved.

Companion to ``depth_profile.py``, which asks a trained model where it takes its
ink evidence. That answer is useful but circular: the model was trained on
labels that were copied down every z layer, so its depth preference is partly a
statement about its own training data.

This tool asks the volume instead. For every z layer of the surface volume it
averages the normalized CT intensity over ink-labeled pixels and over the
labeled background inside the same supervision mask, and reports the difference.
No network, no checkpoint, no learned prior -- just: at which depth do the
pixels a human called ink actually look different from the ones next to them?

If the two profiles agree on a depth, the model-based answer stands on
something physical. If they disagree, the model-based answer is about the model.

Normalization is the pipeline's own per-patch ``normalize_robust`` (median/MAD),
so blocks with different overall brightness are comparable and the per-z means
measure contrast within a patch rather than absolute density.

Two statistics, because the first one alone is misleading:

* the **difference of means**, which is easy to read but moves with anything that
  shifts a whole column (the sampled volume leaving the sheet, for instance), and
* the **AUC** -- the chance that a random ink pixel is brighter than a random
  background pixel at that depth. 0.5 is "indistinguishable". It compares the two
  populations directly, so a drift common to both does not move it.

Outputs (under SEGMENT_DIR/depth_contrast by default):
    depth_contrast.json   per-z means, difference and AUC, overall and per region
    depth_contrast.csv    one row per z layer
    depth_contrast.png    the profiles, their difference, and the AUC per region

Usage
-----
    uv run --project external/villa/ink-detection python tools/depth_contrast.py \
        data/ink-dataset/phercparis4/w00_20231016151002

    ... --mask validation_mask --limit-blocks 40

Dependencies: numpy, zarr, scipy, Pillow -- all in the ink-detection uv
environment. No torch, no GPU.

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- #
# Segment IO  (kept local: the tools in this folder are self-contained)
# --------------------------------------------------------------------------- #
def open_pyramid(segment_dir: Path, kind: str):
    import zarr

    suffix = f"_{kind}" if kind else ""
    path = segment_dir / f"{segment_dir.name}{suffix}.zarr"
    if not path.exists():
        sys.exit(f"error: missing {path}")
    return zarr.open(str(path), mode="r")


def coarse_plane(group, *, level: int = 3) -> np.ndarray:
    array = group[str(level)]
    return np.asarray(array[array.shape[0] // 2]) > 0


def region_boxes(group, *, level: int = 3) -> list[dict]:
    """Full-resolution boxes of the connected annotated areas."""
    from scipy import ndimage

    plane = coarse_plane(group, level=level)
    if not plane.any():
        sys.exit(f"error: mask is empty at level {level}")

    full = group["0"]
    scale_y = full.shape[1] / plane.shape[0]
    scale_x = full.shape[2] / plane.shape[1]

    labels, _ = ndimage.label(plane)
    regions = []
    for index, box in enumerate(ndimage.find_objects(labels), start=1):
        y0 = max(0, int(np.floor(box[0].start * scale_y)) - 1)
        y1 = min(int(full.shape[1]), int(np.ceil(box[0].stop * scale_y)) + 1)
        x0 = max(0, int(np.floor(box[1].start * scale_x)) - 1)
        x1 = min(int(full.shape[2]), int(np.ceil(box[1].stop * scale_x)) + 1)
        regions.append({"region": index, "bbox": (y0, y1, x0, x1)})
    return regions


# --------------------------------------------------------------------------- #
# Separation
# --------------------------------------------------------------------------- #
HISTOGRAM_BINS = 256
HISTOGRAM_RANGE = (-4.0, 4.0)


def quantize(values: np.ndarray) -> np.ndarray:
    """Bin normalized intensities so a whole population fits in a histogram.

    Robust normalization puts the bulk of a patch inside a few MAD units; the
    range is clipped rather than widened so that the tails cannot smear the
    resolution of the part that matters.
    """
    low, high = HISTOGRAM_RANGE
    scaled = (values - low) * (HISTOGRAM_BINS / (high - low))
    return np.clip(scaled, 0, HISTOGRAM_BINS - 1).astype(np.int32, copy=False)


def auc_from_histograms(positive: np.ndarray, negative: np.ndarray) -> float:
    """P(random positive > random negative), ties counted as half.

    Same trick eval_validation.py uses for its threshold sweep: with the two
    populations already binned, the whole curve is one cumulative pass instead
    of a pairwise comparison over tens of millions of pixels.
    """
    positive_total = float(positive.sum())
    negative_total = float(negative.sum())
    if positive_total == 0 or negative_total == 0:
        return float("nan")
    negative_below = np.concatenate([[0.0], np.cumsum(negative[:-1], dtype=np.float64)])
    wins = float((positive * (negative_below + 0.5 * negative)).sum())
    return wins / (positive_total * negative_total)


def auc_curve(positive: np.ndarray, negative: np.ndarray) -> np.ndarray:
    return np.array([auc_from_histograms(positive[z], negative[z]) for z in range(positive.shape[0])])


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def draw_profiles(path: Path, ink: np.ndarray, background: np.ndarray, auc: np.ndarray,
                  region_contrast: list[tuple[int, np.ndarray]],
                  region_auc: list[tuple[int, np.ndarray]]) -> None:
    """The two profiles, their difference, and the separation that survives drift."""
    from PIL import Image, ImageDraw

    width, height = 980, 1010
    left, right, top, gap, bottom = 78, 26, 44, 66, 52
    panel_h = (height - top - 2 * gap - bottom) // 3
    plot_w = width - left - right

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    def panel(panel_top: int, title: str, series: list[tuple[str, np.ndarray, tuple[int, int, int], int]],
              reference: float | None = None):
        values = np.concatenate([values for _, values, _, _ in series])
        values = values[np.isfinite(values)]
        y_max, y_min = float(values.max()), float(values.min())
        if reference is not None:
            y_max, y_min = max(y_max, reference), min(y_min, reference)
        pad = max(1e-6, (y_max - y_min) * 0.12)
        y_max, y_min = y_max + pad, y_min - pad
        y_span = y_max - y_min

        draw.rectangle([left, panel_top, left + plot_w, panel_top + panel_h], outline=(200, 200, 200))
        draw.text((left, panel_top - 22), title, fill=(40, 40, 40))
        for tick in range(5):
            value = y_min + y_span * tick / 4
            y_pixel = panel_top + panel_h - int(panel_h * (value - y_min) / y_span)
            draw.line([left, y_pixel, left + plot_w, y_pixel], fill=(236, 236, 236))
            draw.text((8, y_pixel - 6), f"{value:+.3f}", fill=(90, 90, 90))
        marker = 0.0 if reference is None else reference
        if y_min < marker < y_max:
            marker_pixel = panel_top + panel_h - int(panel_h * (marker - y_min) / y_span)
            draw.line([left, marker_pixel, left + plot_w, marker_pixel], fill=(150, 150, 150))
        for tick in range(0, len(ink) + 1, 8):
            x_pixel = left + int(plot_w * tick / max(1, len(ink) - 1))
            draw.line([x_pixel, panel_top, x_pixel, panel_top + panel_h], fill=(245, 245, 245))
            draw.text((x_pixel - 6, panel_top + panel_h + 8), f"{tick}", fill=(90, 90, 90))

        legend_x = left + 12
        for label, values, color, line_width in series:
            points = []
            for index, value in enumerate(values):
                if not np.isfinite(value):
                    continue
                x_pixel = left + int(plot_w * index / max(1, len(values) - 1))
                y_pixel = panel_top + panel_h - int(panel_h * (float(value) - y_min) / y_span)
                points.append((x_pixel, y_pixel))
            if len(points) > 1:
                draw.line(points, fill=color, width=line_width)
            if label:
                draw.rectangle([legend_x, panel_top + 10, legend_x + 14, panel_top + 20], fill=color)
                draw.text((legend_x + 20, panel_top + 8), label, fill=(60, 60, 60))
                legend_x += 24 + 8 * len(label)

    panel(top, "mean normalized CT intensity per z layer", [
        ("ink", ink, (200, 60, 55), 2),
        ("background", background, (70, 110, 200), 2),
    ])
    contrast_series = [("", values, (205, 205, 205), 1) for _, values in region_contrast]
    contrast_series.append(("ink - background", ink - background, (30, 30, 30), 2))
    panel(top + panel_h + gap, "ink minus background (gray = one annotated region)", contrast_series)

    auc_series = [("", values, (205, 205, 205), 1) for _, values in region_auc]
    auc_series.append(("AUC", auc, (30, 30, 30), 2))
    panel(top + 2 * (panel_h + gap),
          "AUC: P(random ink pixel brighter than random background pixel); 0.5 = indistinguishable",
          auc_series, reference=0.5)

    draw.text((left, height - 26), "z layer (0 = first layer of the surface volume)", fill=(60, 60, 60))
    image.save(path)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure per-z CT contrast between ink and background pixels. No model.",
    )
    parser.add_argument("segment_dir", type=Path, help="Segment folder (volume + label pyramids)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output folder. Default: SEGMENT_DIR/depth_contrast")
    parser.add_argument("--mask", default="supervision_mask",
                        choices=("supervision_mask", "validation_mask"),
                        help="Which mask defines the measured area. Default: supervision_mask")
    parser.add_argument("--block", type=int, default=256, help="Block size in pixels. Default: 256")
    parser.add_argument("--limit-blocks", type=int, default=None, help="Measure only the first N blocks.")
    parser.add_argument("--min-ink-pixels", type=int, default=1,
                        help="Skip blocks with fewer labeled ink pixels. Default: 1")
    parser.add_argument("--raw", action="store_true",
                        help="Skip robust normalization and average raw uint8 intensity instead.")
    args = parser.parse_args(argv)

    from tqdm.auto import tqdm
    from vesuvius.image_proc.intensity.normalization import normalize_robust

    from koine_machines.inference.infer import iter_blocks

    segment_dir = args.segment_dir.resolve()
    if not segment_dir.is_dir():
        sys.exit(f"error: not a directory: {segment_dir}")
    out_dir = args.out_dir or (segment_dir / "depth_contrast")
    out_dir.mkdir(parents=True, exist_ok=True)

    volume = open_pyramid(segment_dir, "")["0"]
    inklabels = open_pyramid(segment_dir, "inklabels")
    mask_group = open_pyramid(segment_dir, args.mask)
    mask_array = mask_group["0"]
    ink_array = inklabels["0"]

    depth, height, width = (int(v) for v in volume.shape)
    label_z = int(ink_array.shape[0] // 2)

    coarse = coarse_plane(mask_group)
    scale_y = max(1, int(round(height / coarse.shape[0])))
    scale_x = max(1, int(round(width / coarse.shape[1])))
    blocks = iter_blocks((height, width), args.block, args.block, coarse, (scale_y, scale_x))
    if args.limit_blocks is not None:
        blocks = blocks[: int(args.limit_blocks)]
    if not blocks:
        sys.exit("error: the mask selected no blocks")

    regions = region_boxes(mask_group)

    print(f"segment      : {segment_dir.name}")
    print(f"volume       : ({depth}, {height}, {width})")
    print(f"mask         : {args.mask}  ({len(regions)} region(s))")
    print(f"blocks       : {len(blocks)} of {args.block}x{args.block}")
    print(f"intensity    : {'raw uint8' if args.raw else 'robust-normalized per block'}")

    ink_sum = np.zeros(depth, dtype=np.float64)
    background_sum = np.zeros(depth, dtype=np.float64)
    ink_count = background_count = 0
    ink_histogram = np.zeros((depth, HISTOGRAM_BINS), dtype=np.int64)
    background_histogram = np.zeros((depth, HISTOGRAM_BINS), dtype=np.int64)
    region_sums = {
        region["region"]: [np.zeros(depth), np.zeros(depth), 0, 0] for region in regions
    }
    region_histograms = {
        region["region"]: [np.zeros((depth, HISTOGRAM_BINS), dtype=np.int64),
                           np.zeros((depth, HISTOGRAM_BINS), dtype=np.int64)]
        for region in regions
    }
    skipped = 0

    z_offsets = (np.arange(depth, dtype=np.int32) * HISTOGRAM_BINS)[:, None]

    def add_histogram(target: np.ndarray, values: np.ndarray) -> None:
        """values: [z, n] intensities for one pixel population, one z per row.

        Binned in a single pass by offsetting each row into its own slice of a
        flat histogram -- 65 separate bincounts per block per population is the
        difference between a minute and ten.
        """
        if values.shape[1] == 0:
            return
        flat = (quantize(values) + z_offsets).ravel()
        counts = np.bincount(flat, minlength=depth * HISTOGRAM_BINS)
        target += counts.reshape(depth, HISTOGRAM_BINS)

    for block in tqdm(blocks, desc="Contrast", unit="block"):
        y0, x0 = int(block.y0), int(block.x0)
        valid_h, valid_w = int(block.valid_h), int(block.valid_w)

        scored = np.asarray(mask_array[label_z, y0:y0 + valid_h, x0:x0 + valid_w]) > 0
        truth = (np.asarray(ink_array[label_z, y0:y0 + valid_h, x0:x0 + valid_w]) > 0) & scored
        if int(truth.sum()) < int(args.min_ink_pixels):
            skipped += 1
            continue
        background = scored & ~truth

        patch = np.asarray(volume[:, y0:y0 + valid_h, x0:x0 + valid_w], dtype=np.float32)
        if not args.raw:
            patch = normalize_robust(patch)
            binnable = patch
        else:
            # Put raw uint8 on the same axis the histogram bins expect.
            binnable = patch * (8.0 / 255.0) - 4.0

        ink_values = patch[:, truth]
        background_values = patch[:, background]
        ink_sum += ink_values.sum(axis=1)
        background_sum += background_values.sum(axis=1)
        ink_count += int(truth.sum())
        background_count += int(background.sum())
        add_histogram(ink_histogram, binnable[:, truth])
        add_histogram(background_histogram, binnable[:, background])

        for region in regions:
            ry0, ry1, rx0, rx1 = region["bbox"]
            if ry1 <= y0 or ry0 >= y0 + valid_h or rx1 <= x0 or rx0 >= x0 + valid_w:
                continue
            box = np.zeros((valid_h, valid_w), dtype=bool)
            box[max(0, ry0 - y0):max(0, ry1 - y0), max(0, rx0 - x0):max(0, rx1 - x0)] = True
            region_ink = box & truth
            region_background = box & background
            entry = region_sums[region["region"]]
            histograms = region_histograms[region["region"]]
            if region_ink.any():
                entry[0] += patch[:, region_ink].sum(axis=1)
                entry[2] += int(region_ink.sum())
                add_histogram(histograms[0], binnable[:, region_ink])
            if region_background.any():
                entry[1] += patch[:, region_background].sum(axis=1)
                entry[3] += int(region_background.sum())
                add_histogram(histograms[1], binnable[:, region_background])

    if ink_count == 0:
        sys.exit("error: no ink pixels inside the measured blocks")

    ink_mean = ink_sum / ink_count
    background_mean = background_sum / max(1, background_count)
    contrast = ink_mean - background_mean
    auc = auc_curve(ink_histogram, background_histogram)

    print(f"\nmeasured px  : {ink_count + background_count:,} (ink {ink_count:,}) "
          f"over {len(blocks) - skipped} block(s), {skipped} skipped for lack of ink")
    peak = int(np.argmax(np.abs(contrast)))
    auc_peak = int(np.nanargmax(np.abs(auc - 0.5)))
    print(f"peak contrast: z {peak}  ({contrast[peak]:+.4f})")
    print(f"peak AUC     : z {auc_peak}  ({auc[auc_peak]:.4f})   "
          f"range {np.nanmin(auc):.4f} .. {np.nanmax(auc):.4f}")

    print("\nper z layer (every 4th):")
    print(f"  {'z':>3}  {'ink':>9}  {'background':>11}  {'ink-bg':>9}  {'AUC':>7}")
    for z in range(0, depth, 4):
        print(f"  {z:>3}  {ink_mean[z]:>+9.4f}  {background_mean[z]:>+11.4f}  "
              f"{contrast[z]:>+9.4f}  {auc[z]:>7.4f}")

    region_report = []
    region_contrast = []
    region_auc = []
    print("\nper region (where the two populations differ most):")
    # ASCII only in console output: the default Windows console codepage mangles
    # anything else.
    print(f"  {'region':>6}  {'ink px':>9}  {'peak z':>7}  {'peak diff':>9}  {'AUC z':>6}  {'AUC':>7}")
    for region in regions:
        ink_totals, background_totals, region_ink_count, region_background_count = region_sums[region["region"]]
        if region_ink_count == 0 or region_background_count == 0:
            continue
        region_curve = ink_totals / region_ink_count - background_totals / region_background_count
        region_peak = int(np.argmax(np.abs(region_curve)))
        region_auc_curve = auc_curve(*region_histograms[region["region"]])
        region_auc_peak = int(np.nanargmax(np.abs(region_auc_curve - 0.5)))
        print(f"  {region['region']:>6}  {region_ink_count:>9,}  {region_peak:>7}  "
              f"{region_curve[region_peak]:>+9.4f}  {region_auc_peak:>6}  "
              f"{region_auc_curve[region_auc_peak]:>7.4f}")
        region_report.append({
            "region": region["region"],
            "ink_pixels": region_ink_count,
            "background_pixels": region_background_count,
            "peak_z": region_peak,
            "peak_contrast": round(float(region_curve[region_peak]), 6),
            "peak_auc_z": region_auc_peak,
            "peak_auc": round(float(region_auc_curve[region_auc_peak]), 6),
            "contrast": [round(float(v), 6) for v in region_curve],
            "auc": [round(float(v), 6) for v in region_auc_curve],
        })
        region_contrast.append((region["region"], region_curve))
        region_auc.append((region["region"], region_auc_curve))

    if region_report:
        peaks = [entry["peak_z"] for entry in region_report]
        auc_peaks = [entry["peak_auc_z"] for entry in region_report]
        strengths = [abs(entry["peak_auc"] - 0.5) for entry in region_report]
        print(f"\n  peak-diff z across regions: min {min(peaks)}  median {int(np.median(peaks))}  max {max(peaks)}")
        print(f"  peak-AUC z across regions: min {min(auc_peaks)}  median {int(np.median(auc_peaks))}  "
              f"max {max(auc_peaks)}")
        print(f"  |AUC - 0.5| at those peaks: min {min(strengths):.4f}  "
              f"median {float(np.median(strengths)):.4f}  max {max(strengths):.4f}")

    report = {
        "segment": segment_dir.name,
        "mask": args.mask,
        "blocks": len(blocks),
        "blocks_measured": len(blocks) - skipped,
        "normalization": "raw" if args.raw else "normalize_robust per block",
        "ink_pixels": ink_count,
        "background_pixels": background_count,
        "peak_z": peak,
        "peak_auc_z": auc_peak,
        "ink_mean": [round(float(v), 6) for v in ink_mean],
        "background_mean": [round(float(v), 6) for v in background_mean],
        "contrast": [round(float(v), 6) for v in contrast],
        "auc": [round(float(v), 6) for v in auc],
        "regions": region_report,
    }
    json_path = out_dir / "depth_contrast.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    csv_path = out_dir / "depth_contrast.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["z", "ink_mean", "background_mean", "contrast", "auc"])
        for z in range(depth):
            writer.writerow([z, f"{ink_mean[z]:.6f}", f"{background_mean[z]:.6f}",
                             f"{contrast[z]:.6f}", f"{auc[z]:.6f}"])

    png_path = out_dir / "depth_contrast.png"
    draw_profiles(png_path, ink_mean, background_mean, auc, region_contrast, region_auc)

    print(f"\nreport  -> {json_path}")
    print(f"csv     -> {csv_path}")
    print(f"plot    -> {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
