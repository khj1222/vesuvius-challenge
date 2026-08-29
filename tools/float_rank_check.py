#!/usr/bin/env python3
"""Did the model's ranking change, or only the scale it is written on?

Every score in this project comes from a uint8 TIFF: `infer` writes
`round(255 * p)` and `eval_validation` sweeps integer thresholds. That is the
right measurement for a deliverable, and the wrong one for deciding whether an
adaptation changed what the model *knows*, because an adaptation that squashes
its output into a handful of grey levels loses discrimination in the 8-bit
representation even if it ranks every pixel exactly as before.

So this re-runs the model in float over the annotated area only, and reports
three numbers per checkpoint:

* **AUC** -- rank-only, invariant to any monotone rescaling;
* **best F1 in float** -- the ceiling a perfectly-scaled 8-bit write would reach;
* **best F1 after uint8 quantisation** -- what the pipeline actually scores.

A gap between the second and third is scale, not knowledge. Inference here is a
single non-overlapping pass rather than the blended one `infer` performs, so the
absolute numbers are not comparable to the matrices; the comparison between two
checkpoints under identical conditions is the point.

The labels are read only to score, after the forward pass.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("volume", type=Path, help="surface volume zarr")
    parser.add_argument("labels", type=Path, help="the segment's label directory")
    parser.add_argument("--segment", required=True)
    parser.add_argument("--checkpoints", nargs="+", type=Path, required=True)
    parser.add_argument("--names", nargs="+", default=None,
                        help="labels for the checkpoints in the report")
    parser.add_argument("--code-root", type=Path, default=Path("D:/vw2/ink-detection"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-blocks", type=int, default=0, help="0 = all")
    return parser.parse_args(argv)


def log(message: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


def curve_stats(probability: np.ndarray, truth: np.ndarray) -> dict:
    order = np.argsort(-probability, kind="stable")
    sorted_truth = truth[order]
    tp = np.cumsum(sorted_truth)
    fp = np.cumsum(1 - sorted_truth)
    positives = float(tp[-1])
    negatives = float(fp[-1])
    precision = tp / np.maximum(1, tp + fp)
    recall = tp / max(1.0, positives)
    f1 = 2 * precision * recall / np.maximum(1e-12, precision + recall)
    best = int(np.argmax(f1))
    # AUC from the rank sum of the positives (ties averaged).
    ranks = np.empty(probability.size, dtype=np.float64)
    ascending = np.argsort(probability, kind="stable")
    ranks[ascending] = np.arange(1, probability.size + 1, dtype=np.float64)
    values = probability[ascending]
    start = 0
    for index in range(1, values.size + 1):
        if index == values.size or values[index] != values[start]:
            if index - start > 1:
                ranks[ascending[start:index]] = (start + 1 + index) / 2.0
            start = index
    positive_ranks = ranks[truth > 0].sum()
    auc = (positive_ranks - positives * (positives + 1) / 2.0) / max(1.0, positives * negatives)
    return {
        "auc": float(auc),
        "best_f1": float(f1[best]),
        "best_precision": float(precision[best]),
        "best_recall": float(recall[best]),
        "threshold_at_best": float(probability[order][best]),
        "kept_fraction_at_best": float((best + 1) / probability.size),
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    sys.path.insert(0, str(args.code_root))
    from koine_machines.inference import infer  # noqa: E402
    import zarr  # noqa: E402

    names = args.names or [c.parent.name + "/" + c.stem for c in args.checkpoints]
    if len(names) != len(args.checkpoints):
        raise SystemExit("error: --names must match --checkpoints")

    supervision = zarr.open(
        str(args.labels / f"{args.segment}_supervision_mask.zarr"), mode="r")
    ink = zarr.open(str(args.labels / f"{args.segment}_inklabels.zarr"), mode="r")
    channel = int(dict(supervision.attrs).get("annotation_center_channel",
                                              supervision["0"].shape[0] // 2))
    log("reading the annotated area")
    supervised = np.asarray(supervision["0"][channel]) > 0
    truth_plane = np.asarray(ink["0"][channel]) > 0
    log(f"supervised pixels: {int(supervised.sum()):,}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    report = {"segment": args.segment, "volume": str(args.volume).replace("\\", "/"),
              "supervised_pixels": int(supervised.sum()), "checkpoints": {}}

    for name, checkpoint in zip(names, args.checkpoints):
        payload = infer.load_checkpoint_payload(checkpoint)
        bundle = infer.build_repo_training_model_bundle(payload, checkpoint)
        model = bundle.model.to(device).eval()
        patch = int(bundle.roi_size)

        root = infer.open_zarr_readonly(args.volume)
        array = root if isinstance(root, zarr.Array) else root["0"]
        shape = tuple(int(v) for v in array.shape)
        depth_first = int(np.argmin(shape)) == 0
        depth, height, width = shape if depth_first else (shape[2], shape[0], shape[1])
        layer_indices = np.arange(0, depth, dtype=np.int64)
        if layer_indices.size > int(bundle.in_chans):
            start = (layer_indices.size - int(bundle.in_chans)) // 2
            layer_indices = layer_indices[start:start + int(bundle.in_chans)]
        reader = infer.OmeZarrPatchReader(
            input_path=args.volume, resolution="0", depth_axis_first=depth_first,
            height=height, width=width, layer_indices=layer_indices,
            preprocessing=bundle.preprocessing)

        blocks = []
        for y0 in range(0, height, patch):
            for x0 in range(0, width, patch):
                if supervised[y0:y0 + patch, x0:x0 + patch].any():
                    blocks.append((y0, x0))
        if args.max_blocks:
            blocks = blocks[:args.max_blocks]
        dataset = infer.OmeZarrBlockDataset(
            reader=reader,
            blocks=[infer.Block(y0=y, x0=x, valid_h=min(patch, height - y),
                                valid_w=min(patch, width - x)) for y, x in blocks],
            patch_size=patch, preprocessing=bundle.preprocessing)
        loader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size,
                                             shuffle=False, num_workers=4)
        log(f"{name}: {len(blocks)} blocks over the annotated area")

        probabilities, truths = [], []
        started = time.time()
        with torch.no_grad():
            for images, metas in loader:
                logits = model(images.to(device))
                batch = torch.sigmoid(logits.float()).squeeze(1).cpu().numpy()
                for row, meta in enumerate(metas.numpy()):
                    # The block meta carries more than four fields in some
                    # revisions of infer.py; the first four are the geometry.
                    y0, x0, valid_h, valid_w = [int(v) for v in meta[:4]]
                    window = supervised[y0:y0 + valid_h, x0:x0 + valid_w]
                    if not window.any():
                        continue
                    probabilities.append(batch[row, :valid_h, :valid_w][window])
                    truths.append(truth_plane[y0:y0 + valid_h, x0:x0 + valid_w][window])
        probability = np.concatenate(probabilities)
        truth = np.concatenate(truths).astype(np.float64)
        quantised = np.round(255.0 * probability)

        entry = {
            "pixels": int(probability.size),
            "ink_fraction": float(truth.mean()),
            "minutes": (time.time() - started) / 60.0,
            "float": curve_stats(probability, truth),
            "uint8": curve_stats(quantised, truth),
            "distribution": {
                "min": float(probability.min()), "max": float(probability.max()),
                "percentiles": {str(p): float(np.percentile(probability, p))
                                for p in (1, 25, 50, 75, 99)},
                "distinct_uint8_levels": int(np.unique(quantised).size),
                "interquartile_uint8_levels":
                    int(np.percentile(quantised, 75) - np.percentile(quantised, 25) + 1),
            },
        }
        report["checkpoints"][name] = entry
        log(f"{name}: AUC {entry['float']['auc']:.4f}  best F1 float "
            f"{entry['float']['best_f1']:.4f}  uint8 {entry['uint8']['best_f1']:.4f}  "
            f"(p25-p75 = {entry['distribution']['percentiles']['25']:.3f}-"
            f"{entry['distribution']['percentiles']['75']:.3f})")

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        log(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
