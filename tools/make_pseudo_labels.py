#!/usr/bin/env python3
"""Arm C of docs/18: turn a model's own predictions into a pseudo-label tree.

Confidence-thresholded self-training is the method everyone asks about, and
docs/18 s3C predicts it fails here for a reason already measured: the
cross-scroll gap is bias, not variance, so a confident wrong prediction trains
the next model to be wrong in the same place. This builds the labels that test
that.

The rules from docs/18 s1 hold: **the target's own annotation never enters.**
The supervised area comes from the prediction and from the render's valid area,
both of which a genuinely unlabelled scroll provides. The withheld ground truth
is opened only afterwards, to score.

Output matches the corpus's own label contract -- `<seg>_inklabels.zarr` and
`<seg>_supervision_mask.zarr`, one filled channel at the reference tree's
`annotation_center_channel`, same shape, chunking and compressor -- so the
released training recipe consumes it with no code change.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import tifffile
import zarr
from numcodecs import Blosc


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prediction", type=Path, help="prediction TIFF from the base model")
    parser.add_argument("out_dir", type=Path, help="label tree root; a <segment>/ is created")
    parser.add_argument("--segment", required=True, help="segment name, e.g. phercparis4-w01")
    parser.add_argument("--volume", type=Path, required=True,
                        help="the segment's surface volume (for the valid render area)")
    parser.add_argument("--reference", type=Path, required=True,
                        help="the real label tree for this segment, read for shape and contract")
    parser.add_argument("--center", type=float, default=0.5,
                        help="the model's own decision point, in probability")
    parser.add_argument("--margin", type=float, default=0.1,
                        help="confidence margin either side of the centre")
    parser.add_argument("--probe", action="store_true",
                        help="report the prediction distribution and write nothing")
    return parser.parse_args(argv)


def log(message: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


def sheet_mask(volume: Path) -> np.ndarray:
    """The render's valid area, from the image alone: one mid-depth plane."""
    array = zarr.open(str(volume / "0") if (volume / "0").exists() else str(volume), mode="r")
    depth = int(array.shape[0])
    return np.asarray(array[depth // 2]) != 0


def reference_contract(reference: Path, segment: str) -> dict:
    labels = zarr.open(str(reference / f"{segment}_inklabels.zarr"), mode="r")
    level = labels["0"]
    attrs = dict(labels.attrs)
    return {
        "shape": tuple(int(v) for v in level.shape),
        "chunks": tuple(int(v) for v in level.chunks),
        "dtype": level.dtype,
        "channel": int(attrs.get("annotation_center_channel", level.shape[0] // 2)),
        "attrs": attrs,
    }


def write_label(path: Path, plane: np.ndarray, contract: dict, attrs: dict) -> None:
    if path.exists():
        raise SystemExit(f"error: {path} exists; refusing to overwrite")
    root = zarr.open(str(path), mode="w")
    root.attrs.update(attrs)
    array = root.create_dataset(
        "0", shape=contract["shape"], chunks=contract["chunks"], dtype="|u1",
        compressor=Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE),
        fill_value=0, overwrite=True)
    channel = contract["channel"]
    height = contract["shape"][1]
    step = max(contract["chunks"][1], 1024)
    for y0 in range(0, height, step):
        y1 = min(height, y0 + step)
        array[channel, y0:y1, :] = plane[y0:y1, :]


def main(argv=None) -> int:
    args = parse_args(argv)
    contract = reference_contract(args.reference, args.segment)
    prediction = tifffile.imread(args.prediction)
    if prediction.shape != contract["shape"][1:]:
        raise SystemExit(f"error: prediction {prediction.shape} does not match the label grid "
                         f"{contract['shape'][1:]}")
    sheet = sheet_mask(args.volume)
    if sheet.shape != prediction.shape:
        raise SystemExit(f"error: volume plane {sheet.shape} does not match the prediction "
                         f"{prediction.shape}")

    high = int(round(255 * min(1.0, args.center + args.margin)))
    low = int(round(255 * max(0.0, args.center - args.margin)))
    on_sheet = prediction[sheet]
    positive = (prediction >= high) & sheet
    negative = (prediction <= low) & sheet
    supervised = positive | negative

    stats = {
        "segment": args.segment,
        "prediction": str(args.prediction).replace("\\", "/"),
        "sheet_pixels": int(sheet.sum()),
        "prediction_min_on_sheet": int(on_sheet.min()),
        "prediction_max_on_sheet": int(on_sheet.max()),
        "prediction_percentiles_on_sheet": {str(p): int(np.percentile(on_sheet, p))
                                            for p in (1, 5, 25, 50, 75, 95, 99)},
        "center": args.center, "margin": args.margin,
        "high_threshold": high, "low_threshold": low,
        "positive_pixels": int(positive.sum()),
        "negative_pixels": int(negative.sum()),
        "supervised_pixels": int(supervised.sum()),
        "positive_share_of_supervised": float(positive.sum() / max(1, supervised.sum())),
        "supervised_share_of_sheet": float(supervised.sum() / max(1, sheet.sum())),
    }
    log(json.dumps({k: stats[k] for k in (
        "segment", "sheet_pixels", "prediction_min_on_sheet", "prediction_max_on_sheet",
        "positive_pixels", "negative_pixels", "positive_share_of_supervised",
        "supervised_share_of_sheet")}))
    if args.probe:
        print(json.dumps(stats, indent=2))
        return 0

    out = args.out_dir / args.segment
    out.mkdir(parents=True, exist_ok=True)
    shared = {
        "case": args.segment,
        "format": "pseudo-label-from-prediction-v1",
        "derived_from": stats["prediction"],
        "rule": (f"positive: p >= {args.center + args.margin:.2f}; "
                 f"negative: p <= {args.center - args.margin:.2f}; "
                 "middle discarded; restricted to the render's valid area"),
        "annotation_center_channel": contract["channel"],
        "output_channels": contract["shape"][0],
        "no_target_annotation_used": True,
        "reference_tree": str(args.reference).replace("\\", "/"),
        "stats": stats,
    }
    write_label(out / f"{args.segment}_inklabels.zarr",
                positive.astype(np.uint8), contract, shared)
    write_label(out / f"{args.segment}_supervision_mask.zarr",
                supervised.astype(np.uint8), contract, shared)
    (out / f"{args.segment}_pseudo_labels.json").write_text(
        json.dumps(shared, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
