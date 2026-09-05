#!/usr/bin/env python3
"""eval_validation.py -- score an ink prediction against the held-out regions.

Companion to ``make_validation_mask.py``. That tool holds out whole annotated
regions of a segment; this one measures a prediction inside them, so "did this
change help?" gets a number instead of an opinion.

What it reports
---------------
* A **threshold sweep** over the prediction's full uint8 range, computed from
  256-bin histograms of the positive/negative populations, so precision/recall/
  F1/IoU at *every* threshold costs one pass over the pixels rather than 256.
* Confusion metrics at the chosen threshold (default: the F1-optimal one),
  including the balanced accuracy ``train.py`` logs during training.
* **DRD** (Distance Reciprocal Distortion) and **pseudo-F-measure**, the two
  document-binarization metrics that ship in
  ``koine_machines/evaluation/metrics/`` but that nothing in the pipeline
  currently calls, because the tutorial produces no validation set to call them
  on. They are computed with the repo's own classes, not a reimplementation.
* A **per-region breakdown**. A segment carries only a handful of annotated
  regions (15 on ``w00_20231016151002``), so a held-out set is a handful of
  letters and a single average hides which of them the model actually failed.
  The two image metrics are also computed per region: both normalize per image,
  so running them across a sparse full-segment canvas would be meaningless.

Only pixels inside the validation mask are scored -- it is already the
intersection of the held-out regions with the supervision mask, so unlabeled
voxels never enter the counts.

Usage
-----
    python tools/eval_validation.py PRED.tif SEGMENT_DIR
    python tools/eval_validation.py PRED.tif SEGMENT_DIR --threshold 128 --json out.json
    python tools/eval_validation.py PRED.tif SEGMENT_DIR --preview scored.png

Producing a prediction for just the held-out regions is much cheaper than a full
segment inference -- ``infer`` skips blocks outside ``--mask-path``:

    uv run --project external/villa/ink-detection python -m koine_machines.inference.infer \
        SEG/SEG.zarr runs/ink_holdout_20k/ckpt_020000.pth preds/val_020000.tif \
        --mask-path SEG/SEG_validation_mask.tif --no-compile --batch-size 4

Dependencies: numpy, scipy, zarr, tifffile, opencv with ximgproc (pFM), Pillow
(--preview). All present in the ink-detection uv environment; ``--project``
borrows it without changing the working directory:

    uv run --project external/villa/ink-detection python tools/eval_validation.py ...

License: MIT.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- #
# Segment IO
# --------------------------------------------------------------------------- #
def open_pyramid(segment_dir: Path, kind: str):
    import zarr

    path = segment_dir / f"{segment_dir.name}_{kind}.zarr"
    if not path.exists():
        sys.exit(
            f"error: missing {path}\n"
            "       run tools/make_validation_mask.py first, then "
            "koine_machines.preprocessing.create_label_zarrs"
        )
    return zarr.open(str(path), mode="r")


def find_regions(validation_group, *, level: int = 3) -> tuple[list[dict], int]:
    """Locate each held-out region, in full-resolution pixel boxes.

    Region finding only needs a coarse plane, but not every label set ships a
    pyramid -- the ink_9um aligned labels are single-level -- so fall back to
    the coarsest level that exists.
    """
    from scipy import ndimage

    available = sorted(int(key) for key in validation_group.array_keys())
    if not available:
        sys.exit("error: the mask pyramid has no arrays")
    level = min(level, max(available))
    coarse = validation_group[str(level)]
    plane = np.asarray(coarse[coarse.shape[0] // 2]) > 0
    if not plane.any():
        sys.exit(f"error: validation mask is empty at level {level}")

    full = validation_group["0"]
    scale_y = full.shape[1] / coarse.shape[1]
    scale_x = full.shape[2] / coarse.shape[2]

    labels, count = ndimage.label(plane)
    regions = []
    for index, box in enumerate(ndimage.find_objects(labels), start=1):
        y0 = max(0, int(np.floor(box[0].start * scale_y)) - 1)
        y1 = min(int(full.shape[1]), int(np.ceil(box[0].stop * scale_y)) + 1)
        x0 = max(0, int(np.floor(box[1].start * scale_x)) - 1)
        x1 = min(int(full.shape[2]), int(np.ceil(box[1].stop * scale_x)) + 1)
        regions.append({"region": index, "bbox": (y0, y1, x0, x1)})
    return regions, count


def read_plane(group, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """Read the labeled z-slice of a label pyramid over ``bbox`` as bool."""
    array = group["0"]
    y0, y1, x0, x1 = bbox
    return np.asarray(array[array.shape[0] // 2, y0:y1, x0:x1]) > 0


def read_prediction(path: Path) -> np.ndarray:
    """Load the prediction TIFF.

    Read with a plain full decode: tifffile's ``aszarr`` path needs zarr>=3 and
    the ink-detection environment pins zarr 2.x (same constraint as ink_viz.py).
    """
    import tifffile

    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        if len(page.shape) != 2:
            sys.exit(f"error: expected a 2-D prediction, got shape={page.shape}")
        prediction = page.asarray()
    if prediction.dtype != np.uint8:
        prediction = np.clip(prediction, 0, 255).astype(np.uint8)
    return prediction


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def sweep_from_histograms(positive_hist: np.ndarray, negative_hist: np.ndarray) -> dict:
    """Precision/recall/F1/IoU at every uint8 threshold.

    A pixel counts as predicted-positive when ``score >= threshold``, matching
    how the prediction TIFF is normally binarized for display.
    """
    tp = np.cumsum(positive_hist[::-1])[::-1].astype(np.float64)
    fp = np.cumsum(negative_hist[::-1])[::-1].astype(np.float64)
    total_positive = float(positive_hist.sum())
    total_negative = float(negative_hist.sum())
    fn = total_positive - tp
    tn = total_negative - fp

    with np.errstate(divide="ignore", invalid="ignore"):
        precision = np.where(tp + fp > 0, tp / (tp + fp), 0.0)
        recall = np.where(total_positive > 0, tp / max(total_positive, 1.0), 0.0)
        f1 = np.where(precision + recall > 0, 2 * precision * recall / (precision + recall), 0.0)
        iou = np.where(tp + fp + fn > 0, tp / (tp + fp + fn), 0.0)
        specificity = np.where(total_negative > 0, tn / max(total_negative, 1.0), 0.0)

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1, "iou": iou,
        "balanced_accuracy": 0.5 * (recall + specificity),
    }


def metrics_at(sweep: dict, threshold: int) -> dict:
    index = int(np.clip(threshold, 0, 255))
    return {
        "threshold": index,
        "tp": int(sweep["tp"][index]), "fp": int(sweep["fp"][index]),
        "fn": int(sweep["fn"][index]), "tn": int(sweep["tn"][index]),
        "precision": float(sweep["precision"][index]),
        "recall": float(sweep["recall"][index]),
        "f1": float(sweep["f1"][index]),
        "iou": float(sweep["iou"][index]),
        "balanced_accuracy": float(sweep["balanced_accuracy"][index]),
    }


def image_metrics(pred_bin: np.ndarray, gt_bin: np.ndarray) -> dict:
    """DRD + pseudo-F-measure using the pipeline's own metric classes."""
    results: dict[str, object] = {}
    try:
        from koine_machines.evaluation.metrics.drd import DRD

        results["drd"] = float(DRD().compute_binary(pred_bin, gt_bin))
    except Exception as exc:  # noqa: BLE001 - report, don't abort the whole run
        results["drd_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from koine_machines.evaluation.metrics.pfm_weighted import PFMWeighted

        results["pseudo_fmeasure"] = float(PFMWeighted().compute_binary(pred_bin, gt_bin))
    except Exception as exc:  # noqa: BLE001
        results["pseudo_fmeasure_error"] = f"{type(exc).__name__}: {exc}"
    return results


# --------------------------------------------------------------------------- #
# Preview
# --------------------------------------------------------------------------- #
def render_tile(pred_bin, gt_bin, valid, *, downsample: int) -> np.ndarray:
    """Green = hit, red = false positive, blue = miss, gray = scored background."""
    step = max(1, downsample)
    pred = pred_bin[::step, ::step]
    truth = gt_bin[::step, ::step]
    scored = valid[::step, ::step]

    tile = np.zeros((*pred.shape, 3), dtype=np.uint8)
    tile[scored] = (35, 35, 35)
    tile[scored & truth & pred] = (60, 190, 90)
    tile[scored & ~truth & pred] = (215, 70, 60)
    tile[scored & truth & ~pred] = (60, 110, 220)
    return tile


def montage(tiles: list[np.ndarray], *, gap: int = 12) -> np.ndarray:
    """Lay the region tiles side by side.

    The held-out regions are scattered across tens of thousands of pixels, so
    drawing them at their true positions yields a mostly-empty canvas. A
    montage puts the letters -- the part anyone actually inspects -- next to
    each other.
    """
    if not tiles:
        return np.zeros((1, 1, 3), dtype=np.uint8)
    height = max(tile.shape[0] for tile in tiles)
    width = sum(tile.shape[1] for tile in tiles) + gap * (len(tiles) - 1)
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = 0
    for tile in tiles:
        y = (height - tile.shape[0]) // 2
        canvas[y:y + tile.shape[0], x:x + tile.shape[1]] = tile
        x += tile.shape[1] + gap
    return canvas


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Score an ink prediction TIFF inside a segment's held-out regions.",
    )
    parser.add_argument("prediction", type=Path, help="Prediction TIFF from koine_machines.inference.infer")
    parser.add_argument("segment_dir", type=Path, help="Segment folder holding the label pyramids")
    parser.add_argument("--threshold", type=int, default=None,
                        help="Score at this uint8 threshold. Default: the F1-optimal one.")
    parser.add_argument("--json", type=Path, default=None, help="Write the full report as JSON.")
    parser.add_argument("--preview", type=Path, default=None, help="Write a hit/miss preview PNG.")
    parser.add_argument("--preview-downsample", type=int, default=8, help="Preview downsample. Default: 8")
    parser.add_argument("--no-image-metrics", dest="image_metrics", action="store_false",
                        help="Skip DRD / pseudo-F-measure (they are the slow part).")
    parser.add_argument("--label", default=None, help="Free-form tag stored in the JSON report.")
    parser.add_argument("--no-regions", dest="per_region", action="store_false",
                        help="Skip the per-region breakdown. The headline numbers come "
                             "from the first pass and do not change; this drops only the "
                             "second pass, which costs one threshold sweep per connected "
                             "component and is pathological on a thinned mask -- a "
                             "pseudo-label tree can have tens of thousands of components "
                             "where an annotation has eight.")
    parser.add_argument("--region-kind", default="validation_mask",
                        choices=("validation_mask", "supervision_mask"),
                        help="Which mask pyramid delimits the scored regions. Use "
                             "supervision_mask when the whole segment was held out of "
                             "training and every annotated pixel is fair game.")
    args = parser.parse_args(argv)

    segment_dir = args.segment_dir.resolve()
    if not segment_dir.is_dir():
        sys.exit(f"error: not a directory: {segment_dir}")
    if not args.prediction.exists():
        sys.exit(f"error: no such prediction: {args.prediction}")

    validation = open_pyramid(segment_dir, args.region_kind)
    inklabels = open_pyramid(segment_dir, "inklabels")
    regions, count = find_regions(validation)

    print(f"segment      : {segment_dir.name}")
    print(f"prediction   : {args.prediction.name}")
    print(f"scored region: {count} region(s) from {args.region_kind}")

    prediction = read_prediction(args.prediction)

    # First pass: per-region pixel populations -> a single global sweep.
    positive_hist = np.zeros(256, dtype=np.int64)
    negative_hist = np.zeros(256, dtype=np.int64)
    for region in regions:
        bbox = region["bbox"]
        valid = read_plane(validation, bbox)
        truth = read_plane(inklabels, bbox) & valid
        y0, y1, x0, x1 = bbox
        crop = prediction[y0:y1, x0:x1]
        if crop.shape != valid.shape:
            sys.exit(f"error: prediction crop {crop.shape} != mask {valid.shape} -- "
                     "is this prediction from the same segment?")
        positive_hist += np.bincount(crop[truth], minlength=256)
        negative_hist += np.bincount(crop[valid & ~truth], minlength=256)
        region["scored"] = int(valid.sum())
        region["ink"] = int(truth.sum())

    scored_px = int(sum(region["scored"] for region in regions))
    ink_px = int(sum(region["ink"] for region in regions))
    if scored_px == 0:
        sys.exit("error: no scored pixels -- the validation mask is empty")
    print(f"scored px    : {scored_px:,}  (ink {ink_px:,} = {100.0 * ink_px / scored_px:.2f}%)")
    if positive_hist[1:].sum() + negative_hist[1:].sum() == 0:
        print("warning: the prediction is entirely zero inside the held-out regions")

    sweep = sweep_from_histograms(positive_hist, negative_hist)
    best_index = int(np.argmax(sweep["f1"]))
    threshold = best_index if args.threshold is None else int(args.threshold)
    chosen = metrics_at(sweep, threshold)
    best = metrics_at(sweep, best_index)

    print(f"\nbest F1      : {best['f1']:.4f} @ threshold {best['threshold']}"
          f"  (precision {best['precision']:.4f}, recall {best['recall']:.4f})")
    if threshold != best_index:
        print(f"at threshold {threshold}: F1 {chosen['f1']:.4f} "
              f"(precision {chosen['precision']:.4f}, recall {chosen['recall']:.4f})")
    print(f"IoU          : {chosen['iou']:.4f}")
    print(f"balanced acc : {chosen['balanced_accuracy']:.4f}")
    print(f"counts       : tp {chosen['tp']:,}  fp {chosen['fp']:,}  "
          f"fn {chosen['fn']:,}  tn {chosen['tn']:,}")

    # Second pass: per-region metrics at the chosen threshold (+ image metrics).
    tiles: list[np.ndarray] = []

    if not args.per_region:
        print(f"\nper region: skipped (--no-regions); {len(regions):,} components")
        regions = []

    print(f"\nper region (threshold {threshold}):")
    header = f"  {'region':>6}  {'px':>10}  {'ink%':>6}  {'F1':>7}  {'prec':>6}  {'rec':>6}"
    if args.image_metrics:
        header += f"  {'DRD':>9}  {'pFM':>6}"
    print(header)
    for region in regions:
        bbox = region["bbox"]
        valid = read_plane(validation, bbox)
        truth = read_plane(inklabels, bbox) & valid
        y0, y1, x0, x1 = bbox
        crop = prediction[y0:y1, x0:x1]

        region_sweep = sweep_from_histograms(
            np.bincount(crop[truth], minlength=256),
            np.bincount(crop[valid & ~truth], minlength=256),
        )
        region_metrics = metrics_at(region_sweep, threshold)
        pred_bin = (crop >= threshold) & valid
        gt_bin = truth

        line = (f"  {region['region']:>6}  {region['scored']:>10,}  "
                f"{100.0 * region['ink'] / max(1, region['scored']):>5.1f}%  "
                f"{region_metrics['f1']:>7.4f}  {region_metrics['precision']:>6.4f}  "
                f"{region_metrics['recall']:>6.4f}")
        if args.image_metrics:
            extra = image_metrics(pred_bin, gt_bin)
            region_metrics.update(extra)
            drd = extra.get("drd")
            pfm = extra.get("pseudo_fmeasure")
            line += f"  {drd:>9.3f}" if isinstance(drd, float) else f"  {'n/a':>9}"
            line += f"  {pfm:>6.4f}" if isinstance(pfm, float) else f"  {'n/a':>6}"
        print(line)
        region["metrics"] = region_metrics

        if args.preview:
            tiles.append(render_tile(pred_bin, gt_bin, valid,
                                     downsample=args.preview_downsample))

    if args.image_metrics:
        drds = [r["metrics"]["drd"] for r in regions if isinstance(r["metrics"].get("drd"), float)]
        pfms = [r["metrics"]["pseudo_fmeasure"] for r in regions
                if isinstance(r["metrics"].get("pseudo_fmeasure"), float)]
        f1s = [r["metrics"]["f1"] for r in regions]
        print(f"\n  region F1 spread: min {min(f1s):.4f}  median {float(np.median(f1s)):.4f}  "
              f"max {max(f1s):.4f}")
        if drds:
            print(f"  mean DRD {float(np.mean(drds)):.3f}   mean pFM {float(np.mean(pfms)):.4f}")

    report = {
        "prediction": str(args.prediction),
        "segment": segment_dir.name,
        "label": args.label,
        "held_out_regions": count,
        "scored_pixels": scored_px,
        "ink_pixels": ink_px,
        "ink_fraction": ink_px / scored_px,
        "best_f1": best,
        "at_threshold": chosen,
        "regions": [
            {"region": r["region"], "bbox": list(r["bbox"]), "scored": r["scored"],
             "ink": r["ink"], **r["metrics"]}
            for r in regions
        ],
        "sweep": {
            "threshold": list(range(0, 256, 8)),
            "f1": [round(float(v), 6) for v in sweep["f1"][::8]],
            "precision": [round(float(v), 6) for v in sweep["precision"][::8]],
            "recall": [round(float(v), 6) for v in sweep["recall"][::8]],
        },
    }

    if args.preview:
        from PIL import Image

        Image.fromarray(montage(tiles)).save(args.preview)
        print(f"\npreview -> {args.preview}")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"report  -> {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
