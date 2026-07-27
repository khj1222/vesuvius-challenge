#!/usr/bin/env python3
"""depth_profile.py -- where along z does a 2.5D ink model take its evidence?

Ink labels in this dataset are drawn in 2D and stored with no depth: of the 65
z layers of `<segment>_inklabels.zarr`, exactly one -- the middle -- is
populated. Depth is manufactured downstream, by projecting that plane along the
surface normal with a constant thickness (villa issue #192). A model trained
this way can score well while keying on surface texture rather than on ink, and
nothing in the pipeline currently says which it is doing.

This tool asks the trained model directly, on the annotated area only, with two
complementary perturbations of the input volume:

* **occlusion** -- blank a band of z slices and measure how far the ink response
  falls. A band that matters is one the model cannot do without (*necessity*).
* **window** -- blank everything *except* a band, and measure what response
  survives. A band that carries the evidence can stand alone (*sufficiency*).

Both are reported for ink-labeled pixels and, as a control, for the labeled
background inside the same supervision mask. A depth band that is specific to
ink moves the two curves apart; a band that merely disturbs image statistics
moves them together, which is exactly the confound this prototype exists to
catch.

Blanking is done *after* the per-patch robust normalization, filling with 0.0 --
which is the patch median in that space, so a blanked slice carries no signal
either way and no information about what it replaced.

Per pixel the tool also records which window scores highest, giving a depth map
of the ink evidence: the input to a real 3D label. `--depth-map` renders it.

Outputs (under CHECKPOINT_DIR/depth_profile by default):
    depth_profile.json        full report, including a per-region breakdown
    depth_profile.csv         one row per variant
    depth_curve.png           occlusion + window curves, ink vs background
    depth_map_window.png      per-region montage: best window per ink pixel
    depth_map_occlusion.png   per-region montage: band each ink pixel needs most

Read the two curves against each other, not in isolation. Blanking 56 of 64
slices shifts the input far off the training distribution, so a window's
*absolute* logit is not comparable to the baseline; the ink-minus-background
separation within one variant is.

Usage
-----
    uv run --project external/villa/ink-detection python tools/depth_profile.py \
        data/ink-dataset/phercparis4/w00_20231016151002 \
        external/villa/ink-detection/runs/ink_holdout_20k/ckpt_020000.pth

    ... --limit-blocks 8            # smoke test, a few blocks only
    ... --mask validation_mask      # profile the held-out regions instead

Reading, normalization and layer selection are imported from
``koine_machines.inference.infer`` rather than reimplemented, so the volume the
model sees here is the volume it sees at inference time.

Dependencies: numpy, torch, zarr, scipy, Pillow -- all present in the
ink-detection uv environment.

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
# Segment IO
# --------------------------------------------------------------------------- #
def open_pyramid(segment_dir: Path, kind: str):
    import zarr

    suffix = f"_{kind}" if kind else ""
    path = segment_dir / f"{segment_dir.name}{suffix}.zarr"
    if not path.exists():
        sys.exit(f"error: missing {path}")
    return zarr.open(str(path), mode="r")


def labeled_plane_index(group) -> int:
    """Index of the one z slice the 2D annotation lives on.

    Measured on the published segment: of 65 planes only the middle one is
    populated, in both the ink labels and the supervision mask.
    """
    return int(group["0"].shape[0] // 2)


def coarse_plane(group, *, level: int = 3) -> tuple[np.ndarray, int]:
    """Middle z slice of a label pyramid at a downsampled level, as bool."""
    array = group[str(level)]
    return np.asarray(array[array.shape[0] // 2]) > 0, level


def region_boxes(group, *, level: int = 3) -> list[dict]:
    """Full-resolution boxes of the connected annotated areas.

    The segment carries a handful of separately annotated letters rather than
    one continuous ribbon, and a depth profile averaged over all of them would
    hide the very thing worth checking: whether the ink sits at a consistent
    depth from one annotation to the next.
    """
    from scipy import ndimage

    plane, _ = coarse_plane(group, level=level)
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
# Variants
# --------------------------------------------------------------------------- #
def build_variants(
    depth: int,
    *,
    occlude_width: int,
    window_width: int,
    window_stride: int,
) -> list[dict]:
    """Baseline first, then every occlusion band, then every keep-only window.

    Each variant carries the z indices to blank, so the runner never has to know
    what a variant means.
    """
    variants: list[dict] = [
        {"name": "baseline", "kind": "baseline", "z0": 0, "z1": depth, "blank": np.zeros(0, dtype=np.int64)}
    ]

    for z0 in range(0, depth, max(1, occlude_width)):
        z1 = min(depth, z0 + occlude_width)
        variants.append({
            "name": f"occlude_{z0:02d}_{z1:02d}",
            "kind": "occlude",
            "z0": z0,
            "z1": z1,
            "blank": np.arange(z0, z1, dtype=np.int64),
        })

    starts = list(range(0, max(1, depth - window_width + 1), max(1, window_stride)))
    if starts and starts[-1] != depth - window_width:
        starts.append(depth - window_width)
    for z0 in starts:
        z1 = min(depth, z0 + window_width)
        keep = np.zeros(depth, dtype=bool)
        keep[z0:z1] = True
        variants.append({
            "name": f"window_{z0:02d}_{z1:02d}",
            "kind": "window",
            "z0": z0,
            "z1": z1,
            "blank": np.nonzero(~keep)[0].astype(np.int64),
        })
    return variants


# --------------------------------------------------------------------------- #
# Accumulation
# --------------------------------------------------------------------------- #
class ResponseAccumulator:
    """Sums of model response over a pixel population, per variant."""

    def __init__(self, n_variants: int):
        self.logit_sum = np.zeros(n_variants, dtype=np.float64)
        self.prob_sum = np.zeros(n_variants, dtype=np.float64)
        self.count = 0

    def add(self, logit_sums: np.ndarray, prob_sums: np.ndarray, count: int) -> None:
        self.logit_sum += logit_sums
        self.prob_sum += prob_sums
        self.count += int(count)

    def means(self) -> tuple[np.ndarray, np.ndarray]:
        denominator = max(1, self.count)
        return self.logit_sum / denominator, self.prob_sum / denominator


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def depth_ramp(fraction: float) -> tuple[int, int, int]:
    """Blue (shallow) -> green -> red (deep). Hand-rolled: no matplotlib here."""
    fraction = float(np.clip(fraction, 0.0, 1.0))
    if fraction < 0.5:
        t = fraction / 0.5
        return (int(40 + 20 * t), int(70 + 150 * t), int(220 - 100 * t))
    t = (fraction - 0.5) / 0.5
    return (int(60 + 175 * t), int(220 - 130 * t), int(120 - 80 * t))


def draw_curves(path: Path, variants: list[dict], rows: dict, depth: int) -> None:
    """Two stacked panels: occlusion drop and window response, ink vs background."""
    from PIL import Image, ImageDraw

    width, height = 980, 720
    left, right, top, gap, bottom = 78, 26, 44, 74, 52
    panel_h = (height - top - gap - bottom) // 2
    plot_w = width - left - right

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    panels = [
        ("occlude", "occlusion: drop in mean logit when the band is blanked", top),
        ("window", "window: mean logit with only the band kept", top + panel_h + gap),
    ]
    colors = {"ink": (200, 60, 55), "background": (70, 110, 200)}

    for kind, title, panel_top in panels:
        selected = [v for v in variants if v["kind"] == kind]
        if not selected:
            continue
        series = {
            population: [rows[kind][population][v["name"]] for v in selected]
            for population in ("ink", "background")
        }
        values = [value for population in series.values() for value in population]
        y_max = max(values) if values else 1.0
        y_min = min(values) if values else 0.0
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
        if y_min < 0.0 < y_max:
            zero_pixel = panel_top + panel_h - int(panel_h * (0.0 - y_min) / y_span)
            draw.line([left, zero_pixel, left + plot_w, zero_pixel], fill=(150, 150, 150))

        for tick in range(0, depth + 1, 8):
            x_pixel = left + int(plot_w * tick / depth)
            draw.line([x_pixel, panel_top, x_pixel, panel_top + panel_h], fill=(245, 245, 245))
            draw.text((x_pixel - 6, panel_top + panel_h + 8), f"{tick}", fill=(90, 90, 90))

        for index, (population, color) in enumerate(colors.items()):
            points = []
            for variant, value in zip(selected, series[population]):
                center = 0.5 * (variant["z0"] + variant["z1"])
                x_pixel = left + int(plot_w * center / depth)
                y_pixel = panel_top + panel_h - int(panel_h * (value - y_min) / y_span)
                points.append((x_pixel, y_pixel))
            if len(points) > 1:
                draw.line(points, fill=color, width=2)
            for point in points:
                draw.ellipse([point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3], fill=color)
            draw.rectangle([left + 12 + index * 130, panel_top + 10, left + 26 + index * 130, panel_top + 20],
                           fill=color)
            draw.text((left + 32 + index * 130, panel_top + 8), population, fill=(60, 60, 60))

    draw.text((left, height - 26), "z layer (0 = first layer of the surface volume)", fill=(60, 60, 60))
    image.save(path)


def draw_depth_map(path: Path, tiles: list[dict], *, depth: int, downsample: int, key: str) -> None:
    """Montage of per-region depth maps: hue = z, ink pixels only.

    The regions sit tens of thousands of pixels apart, so drawing them in place
    would be a mostly empty canvas; the montage puts the letters side by side
    (same reasoning as eval_validation.py's preview).
    """
    from PIL import Image, ImageDraw

    if not tiles:
        return
    step = max(1, downsample)
    rendered = []
    for tile in tiles:
        centers = tile[key][::step, ::step]
        ink = tile["ink"][::step, ::step]
        canvas = np.zeros((*centers.shape, 3), dtype=np.uint8)
        canvas[tile["scored"][::step, ::step]] = (30, 30, 30)
        ys, xs = np.nonzero(ink)
        for y, x in zip(ys, xs):
            canvas[y, x] = depth_ramp(centers[y, x] / max(1.0, float(depth)))
        rendered.append((tile["region"], canvas))

    height = max(canvas.shape[0] for _, canvas in rendered) + 18
    width = sum(canvas.shape[1] for _, canvas in rendered) + 12 * (len(rendered) - 1)
    montage = np.zeros((height, width, 3), dtype=np.uint8)
    x_offset = 0
    labels = []
    for region, canvas in rendered:
        y_offset = (height - 18 - canvas.shape[0]) // 2
        montage[y_offset:y_offset + canvas.shape[0], x_offset:x_offset + canvas.shape[1]] = canvas
        labels.append((x_offset + 2, height - 15, str(region)))
        x_offset += canvas.shape[1] + 12

    image = Image.fromarray(montage)
    draw = ImageDraw.Draw(image)
    for x, y, text in labels:
        draw.text((x, y), text, fill=(160, 160, 160))
    image.save(path)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Profile where along z a trained 2.5D ink model takes its evidence.",
    )
    parser.add_argument("segment_dir", type=Path, help="Segment folder (volume + label pyramids)")
    parser.add_argument("checkpoint", type=Path, help="Training checkpoint (ckpt_*.pth)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output folder. Default: CHECKPOINT_DIR/depth_profile")
    parser.add_argument("--mask", default="supervision_mask",
                        choices=("supervision_mask", "validation_mask"),
                        help="Which mask defines the profiled area. Default: supervision_mask")
    parser.add_argument("--occlude-width", type=int, default=4, help="Occlusion band thickness. Default: 4")
    parser.add_argument("--window-width", type=int, default=8, help="Keep-only window thickness. Default: 8")
    parser.add_argument("--window-stride", type=int, default=4, help="Window stride. Default: 4")
    parser.add_argument("--batch-size", type=int, default=4, help="Variants per forward pass. Default: 4")
    parser.add_argument("--limit-blocks", type=int, default=None, help="Profile only the first N blocks.")
    parser.add_argument("--min-ink-pixels", type=int, default=1,
                        help="Skip blocks with fewer labeled ink pixels than this. Blocks with no ink "
                             "add nothing to the ink curve, and keeping the background control on the "
                             "same blocks as the ink makes the two curves paired. Default: 1")
    parser.add_argument("--depth-map-downsample", type=int, default=4,
                        help="Downsample for the depth-map montage. Default: 4")
    parser.add_argument("--no-depth-map", dest="depth_map", action="store_false",
                        help="Skip the per-pixel depth map.")
    parser.add_argument("--device", default=None, help="Torch device. Default: cuda when available.")
    args = parser.parse_args(argv)

    import torch
    from tqdm.auto import tqdm
    from vesuvius.image_proc.intensity.normalization import normalize_robust

    from koine_machines.inference.infer import (
        OmeZarrPatchReader,
        build_repo_training_model_bundle,
        iter_blocks,
        load_checkpoint_payload,
    )

    segment_dir = args.segment_dir.resolve()
    if not segment_dir.is_dir():
        sys.exit(f"error: not a directory: {segment_dir}")
    if not args.checkpoint.exists():
        sys.exit(f"error: no such checkpoint: {args.checkpoint}")

    out_dir = args.out_dir or (args.checkpoint.parent / "depth_profile")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- model ----------------------------------------------------------- #
    payload = load_checkpoint_payload(args.checkpoint)
    bundle = build_repo_training_model_bundle(payload, args.checkpoint)
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model = bundle.model.to(device).eval()
    patch_size = int(bundle.roi_size)
    depth = int(bundle.in_chans)

    # ---- volume + labels -------------------------------------------------- #
    volume = open_pyramid(segment_dir, "")
    inklabels = open_pyramid(segment_dir, "inklabels")
    mask_group = open_pyramid(segment_dir, args.mask)

    volume_shape = tuple(int(v) for v in volume["0"].shape)
    volume_depth, height, width = volume_shape

    # infer.py centers the model's z window inside the volume; match it exactly,
    # otherwise the profile is of a volume the model was never fed.
    layer_indices = np.arange(0, volume_depth, dtype=np.int64)
    if layer_indices.size > depth:
        offset = (layer_indices.size - depth) // 2
        layer_indices = layer_indices[offset:offset + depth]

    reader = OmeZarrPatchReader(
        input_path=segment_dir / f"{segment_dir.name}.zarr",
        resolution="0",
        depth_axis_first=True,
        height=height,
        width=width,
        layer_indices=layer_indices,
        preprocessing=bundle.preprocessing,
    )

    coarse, level = coarse_plane(mask_group)
    scale_y = max(1, int(round(height / coarse.shape[0])))
    scale_x = max(1, int(round(width / coarse.shape[1])))
    blocks = iter_blocks((height, width), patch_size, patch_size, coarse, (scale_y, scale_x))
    if args.limit_blocks is not None:
        blocks = blocks[: int(args.limit_blocks)]
    if not blocks:
        sys.exit("error: the mask selected no blocks")

    regions = region_boxes(mask_group)
    variants = build_variants(
        depth,
        occlude_width=args.occlude_width,
        window_width=args.window_width,
        window_stride=args.window_stride,
    )
    window_variants = [index for index, v in enumerate(variants) if v["kind"] == "window"]
    window_centers = np.array(
        [0.5 * (variants[index]["z0"] + variants[index]["z1"]) for index in window_variants],
        dtype=np.float32,
    )
    occlude_variants = [index for index, v in enumerate(variants) if v["kind"] == "occlude"]
    occlude_centers = np.array(
        [0.5 * (variants[index]["z0"] + variants[index]["z1"]) for index in occlude_variants],
        dtype=np.float32,
    )

    print(f"segment      : {segment_dir.name}")
    print(f"checkpoint   : {args.checkpoint.name}")
    print(f"volume       : {volume_shape}  z window {int(layer_indices[0])}..{int(layer_indices[-1])}")
    print(f"mask         : {args.mask}  ({len(regions)} region(s), level {level})")
    print(f"blocks       : {len(blocks)} of {patch_size}x{patch_size}")
    print(f"variants     : {len(variants)}  "
          f"(1 baseline + {sum(v['kind'] == 'occlude' for v in variants)} occlusions "
          f"+ {len(window_variants)} windows)")
    print(f"device       : {device}")

    blank_indices = [torch.from_numpy(v["blank"]).to(device) for v in variants]

    ink_accumulator = ResponseAccumulator(len(variants))
    background_accumulator = ResponseAccumulator(len(variants))
    region_accumulators = {
        region["region"]: (ResponseAccumulator(len(variants)), ResponseAccumulator(len(variants)))
        for region in regions
    }
    region_depth_hist = {region["region"]: np.zeros(len(window_variants), dtype=np.int64) for region in regions}
    region_occlusion_hist = {
        region["region"]: np.zeros(len(occlude_variants), dtype=np.int64) for region in regions
    }
    depth_tiles: dict[int, dict] = {}
    skipped_blocks = 0

    ink_array = inklabels["0"]
    mask_array = mask_group["0"]
    label_z = labeled_plane_index(inklabels)

    with torch.inference_mode():
        for block in tqdm(blocks, desc="Profile", unit="block"):
            y0, x0 = int(block.y0), int(block.x0)
            valid_h, valid_w = int(block.valid_h), int(block.valid_w)

            scored = np.zeros((patch_size, patch_size), dtype=bool)
            truth = np.zeros((patch_size, patch_size), dtype=bool)
            scored[:valid_h, :valid_w] = np.asarray(
                mask_array[label_z, y0:y0 + valid_h, x0:x0 + valid_w]) > 0
            truth[:valid_h, :valid_w] = np.asarray(
                ink_array[label_z, y0:y0 + valid_h, x0:x0 + valid_w]) > 0
            truth &= scored
            background = scored & ~truth
            if int(truth.sum()) < int(args.min_ink_pixels):
                skipped_blocks += 1
                continue

            patch = reader.read(y0, x0, patch_size, patch_size)
            patch = np.ascontiguousarray(np.moveaxis(patch, -1, 0))
            patch = normalize_robust(patch)
            patch_t = torch.from_numpy(np.ascontiguousarray(patch, dtype=np.float32)).to(device)

            ink_t = torch.from_numpy(truth).to(device)
            background_t = torch.from_numpy(background).to(device)
            region_masks = {}
            for region in regions:
                ry0, ry1, rx0, rx1 = region["bbox"]
                if ry1 <= y0 or ry0 >= y0 + valid_h or rx1 <= x0 or rx0 >= x0 + valid_w:
                    continue
                box = np.zeros((patch_size, patch_size), dtype=bool)
                box[max(0, ry0 - y0):max(0, ry1 - y0), max(0, rx0 - x0):max(0, rx1 - x0)] = True
                region_ink = torch.from_numpy(box & truth).to(device)
                region_background = torch.from_numpy(box & background).to(device)
                if int(region_ink.sum()) or int(region_background.sum()):
                    region_masks[region["region"]] = (region_ink, region_background, box)

            logits_all = torch.empty((len(variants), patch_size, patch_size), dtype=torch.float32, device=device)
            for start in range(0, len(variants), max(1, args.batch_size)):
                chunk = range(start, min(len(variants), start + max(1, args.batch_size)))
                batch = patch_t.unsqueeze(0).repeat(len(chunk), 1, 1, 1).clone()
                for row, index in enumerate(chunk):
                    if blank_indices[index].numel():
                        batch[row, blank_indices[index]] = 0.0
                with torch.autocast(device_type=device.type, dtype=torch.float16,
                                    enabled=device.type == "cuda"):
                    logits = model(batch.unsqueeze(1))
                logits = logits.float()[:, 0]
                if logits.shape[-2:] != (patch_size, patch_size):
                    logits = torch.nn.functional.interpolate(
                        logits.unsqueeze(1), size=(patch_size, patch_size),
                        mode="bilinear", align_corners=False).squeeze(1)
                logits_all[start:start + logits.shape[0]] = logits

            probs_all = torch.sigmoid(logits_all)

            def population_sums(mask_t):
                count = int(mask_t.sum())
                if count == 0:
                    return None
                selected = mask_t.unsqueeze(0)
                logit_sums = (logits_all * selected).sum(dim=(1, 2)).cpu().numpy().astype(np.float64)
                prob_sums = (probs_all * selected).sum(dim=(1, 2)).cpu().numpy().astype(np.float64)
                return logit_sums, prob_sums, count

            for accumulator, mask_t in ((ink_accumulator, ink_t), (background_accumulator, background_t)):
                sums = population_sums(mask_t)
                if sums is not None:
                    accumulator.add(*sums)

            # Two per-pixel readings of the same forward passes:
            #   window   -- which band alone gives this pixel its highest ink score
            #   occluded -- which band, when blanked, costs this pixel the most
            # The second is the better-founded one: it is measured against the
            # pixel's own unperturbed logit, so it does not ride on the overall
            # shift that blanking 56 of 64 slices introduces.
            best = torch.argmax(probs_all[window_variants], dim=0).cpu().numpy()
            centers = window_centers[best]
            sensitivity = logits_all[0].unsqueeze(0) - logits_all[occlude_variants]
            most_needed = torch.argmax(sensitivity, dim=0).cpu().numpy()
            needed_centers = occlude_centers[most_needed]

            for region_id, (region_ink, region_background, box) in region_masks.items():
                ink_sums = population_sums(region_ink)
                background_sums = population_sums(region_background)
                if ink_sums is not None:
                    region_accumulators[region_id][0].add(*ink_sums)
                    region_ink_pixels = box & truth
                    region_depth_hist[region_id] += np.bincount(
                        best[region_ink_pixels], minlength=len(window_variants))
                    region_occlusion_hist[region_id] += np.bincount(
                        most_needed[region_ink_pixels], minlength=len(occlude_variants))
                if background_sums is not None:
                    region_accumulators[region_id][1].add(*background_sums)

            if args.depth_map:
                for region in regions:
                    if region["region"] not in region_masks:
                        continue
                    ry0, ry1, rx0, rx1 = region["bbox"]
                    tile = depth_tiles.get(region["region"])
                    if tile is None:
                        tile = {
                            "region": region["region"],
                            "bbox": region["bbox"],
                            "centers": np.zeros((ry1 - ry0, rx1 - rx0), dtype=np.float32),
                            "occluded": np.zeros((ry1 - ry0, rx1 - rx0), dtype=np.float32),
                            "ink": np.zeros((ry1 - ry0, rx1 - rx0), dtype=bool),
                            "scored": np.zeros((ry1 - ry0, rx1 - rx0), dtype=bool),
                        }
                        depth_tiles[region["region"]] = tile
                    ty0 = max(ry0, y0) - ry0
                    tx0 = max(rx0, x0) - rx0
                    ty1 = min(ry1, y0 + valid_h) - ry0
                    tx1 = min(rx1, x0 + valid_w) - rx0
                    by0 = max(ry0, y0) - y0
                    bx0 = max(rx0, x0) - x0
                    by1 = by0 + (ty1 - ty0)
                    bx1 = bx0 + (tx1 - tx0)
                    if ty1 <= ty0 or tx1 <= tx0:
                        continue
                    tile["centers"][ty0:ty1, tx0:tx1] = centers[by0:by1, bx0:bx1]
                    tile["occluded"][ty0:ty1, tx0:tx1] = needed_centers[by0:by1, bx0:bx1]
                    tile["ink"][ty0:ty1, tx0:tx1] = truth[by0:by1, bx0:bx1]
                    tile["scored"][ty0:ty1, tx0:tx1] = scored[by0:by1, bx0:bx1]

    if ink_accumulator.count == 0:
        sys.exit("error: no ink pixels inside the profiled blocks")

    ink_logit, ink_prob = ink_accumulator.means()
    background_logit, background_prob = background_accumulator.means()
    baseline_ink = float(ink_logit[0])
    baseline_background = float(background_logit[0])

    print(f"\nscored px    : {ink_accumulator.count + background_accumulator.count:,} "
          f"(ink {ink_accumulator.count:,})  over {len(blocks) - skipped_blocks} block(s), "
          f"{skipped_blocks} skipped for lack of ink")
    print(f"baseline     : ink logit {baseline_ink:+.4f} (p={ink_prob[0]:.4f})   "
          f"background logit {baseline_background:+.4f} (p={background_prob[0]:.4f})")

    # ---- report ----------------------------------------------------------- #
    rows = []
    curve_rows = {"occlude": {"ink": {}, "background": {}}, "window": {"ink": {}, "background": {}}}
    for index, variant in enumerate(variants):
        ink_delta = float(ink_logit[index] - baseline_ink)
        background_delta = float(background_logit[index] - baseline_background)
        row = {
            "variant": variant["name"],
            "kind": variant["kind"],
            "z0": variant["z0"],
            "z1": variant["z1"],
            "ink_logit": round(float(ink_logit[index]), 6),
            "ink_prob": round(float(ink_prob[index]), 6),
            "background_logit": round(float(background_logit[index]), 6),
            "background_prob": round(float(background_prob[index]), 6),
            "ink_delta": round(ink_delta, 6),
            "background_delta": round(background_delta, 6),
            "specificity": round(ink_delta - background_delta, 6),
        }
        rows.append(row)
        if variant["kind"] == "occlude":
            curve_rows["occlude"]["ink"][variant["name"]] = ink_delta
            curve_rows["occlude"]["background"][variant["name"]] = background_delta
        elif variant["kind"] == "window":
            curve_rows["window"]["ink"][variant["name"]] = float(ink_logit[index])
            curve_rows["window"]["background"][variant["name"]] = float(background_logit[index])

    occlusions = [row for row in rows if row["kind"] == "occlude"]
    windows = [row for row in rows if row["kind"] == "window"]

    print("\nocclusion (blank the band; negative delta = the model needed it):")
    print(f"  {'band':>9}  {'ink d-logit':>11}  {'bg d-logit':>11}  {'ink-bg':>8}")
    for row in occlusions:
        print(f"  {row['z0']:>3}-{row['z1']:<5}  {row['ink_delta']:>+11.4f}  "
              f"{row['background_delta']:>+11.4f}  {row['specificity']:>+8.4f}")

    print("\nwindow (keep only the band; higher ink logit = the band suffices):")
    print(f"  {'band':>9}  {'ink logit':>11}  {'bg logit':>11}  {'ink-bg':>8}")
    for row in windows:
        print(f"  {row['z0']:>3}-{row['z1']:<5}  {row['ink_logit']:>+11.4f}  "
              f"{row['background_logit']:>+11.4f}  "
              f"{row['ink_logit'] - row['background_logit']:>+8.4f}")

    if occlusions:
        peak = min(occlusions, key=lambda row: row["specificity"])
        print(f"\nmost ink-specific occlusion band: z {peak['z0']}-{peak['z1']} "
              f"(ink {peak['ink_delta']:+.4f} vs background {peak['background_delta']:+.4f})")
    if windows:
        best_window = max(windows, key=lambda row: row["ink_logit"] - row["background_logit"])
        print(f"most ink-specific window        : z {best_window['z0']}-{best_window['z1']} "
              f"(separation {best_window['ink_logit'] - best_window['background_logit']:+.4f})")

    def quartiles(histogram: np.ndarray, centers: np.ndarray) -> tuple[float, float, float]:
        total = int(histogram.sum())
        if not total:
            return float("nan"), float("nan"), float("nan")
        cumulative = np.cumsum(histogram) / total
        pick = lambda q: float(centers[min(len(centers) - 1, int(np.searchsorted(cumulative, q)))])
        return pick(0.5), pick(0.25), pick(0.75)

    region_report = []
    print("\nper region (window = best band alone, occl = band each ink pixel needs most):")
    print(f"  {'region':>6}  {'ink px':>9}  {'best window':>12}  {'window z':>17}  {'occl z':>17}")
    for region in regions:
        region_id = region["region"]
        ink_acc, background_acc = region_accumulators[region_id]
        if ink_acc.count == 0:
            continue
        region_ink_logit, _ = ink_acc.means()
        region_background_logit, _ = background_acc.means()
        separation = region_ink_logit[window_variants] - (
            region_background_logit[window_variants] if background_acc.count else 0.0)
        best_index = int(np.argmax(region_ink_logit[window_variants]))
        best_variant = variants[window_variants[best_index]]

        histogram = region_depth_hist[region_id]
        occlusion_histogram = region_occlusion_hist[region_id]
        median_z, q1, q3 = quartiles(histogram, window_centers)
        occlusion_median, occlusion_q1, occlusion_q3 = quartiles(occlusion_histogram, occlude_centers)

        window_label = f"{best_variant['z0']}-{best_variant['z1']}"
        print(f"  {region_id:>6}  {ink_acc.count:>9,}  {window_label:>12}  "
              f"{median_z:>6.1f} ({q1:>4.1f}-{q3:<4.1f})  "
              f"{occlusion_median:>6.1f} ({occlusion_q1:>4.1f}-{occlusion_q3:<4.1f})")
        region_report.append({
            "region": region_id,
            "bbox": list(region["bbox"]),
            "ink_pixels": ink_acc.count,
            "background_pixels": background_acc.count,
            "best_window": [best_variant["z0"], best_variant["z1"]],
            "best_window_separation": round(float(separation[best_index]), 6),
            "depth_median": median_z,
            "depth_q1": q1,
            "depth_q3": q3,
            "occlusion_depth_median": occlusion_median,
            "occlusion_depth_q1": occlusion_q1,
            "occlusion_depth_q3": occlusion_q3,
            "window_ink_logit": [round(float(v), 6) for v in region_ink_logit[window_variants]],
            "depth_histogram": [int(v) for v in histogram],
            "occlusion_depth_histogram": [int(v) for v in occlusion_histogram],
        })

    report = {
        "segment": segment_dir.name,
        "checkpoint": str(args.checkpoint),
        "mask": args.mask,
        "blocks": len(blocks),
        "blocks_profiled": len(blocks) - skipped_blocks,
        "min_ink_pixels": args.min_ink_pixels,
        "patch_size": patch_size,
        "z_window": [int(layer_indices[0]), int(layer_indices[-1]) + 1],
        "fill": "0.0 after robust normalization (the patch median)",
        "occlude_width": args.occlude_width,
        "window_width": args.window_width,
        "window_stride": args.window_stride,
        "ink_pixels": ink_accumulator.count,
        "background_pixels": background_accumulator.count,
        "baseline": {
            "ink_logit": round(baseline_ink, 6),
            "ink_prob": round(float(ink_prob[0]), 6),
            "background_logit": round(baseline_background, 6),
            "background_prob": round(float(background_prob[0]), 6),
        },
        "window_centers": [float(v) for v in window_centers],
        "occlusion_centers": [float(v) for v in occlude_centers],
        "variants": rows,
        "regions": region_report,
    }

    json_path = out_dir / "depth_profile.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    csv_path = out_dir / "depth_profile.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    curve_path = out_dir / "depth_curve.png"
    draw_curves(curve_path, variants, curve_rows, depth)

    print(f"\nreport  -> {json_path}")
    print(f"csv     -> {csv_path}")
    print(f"curves  -> {curve_path}")

    if args.depth_map and depth_tiles:
        tiles = [depth_tiles[key] for key in sorted(depth_tiles)]
        for key, filename in (("centers", "depth_map_window.png"),
                              ("occluded", "depth_map_occlusion.png")):
            map_path = out_dir / filename
            draw_depth_map(map_path, tiles, depth=depth,
                           downsample=args.depth_map_downsample, key=key)
            print(f"map     -> {map_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
