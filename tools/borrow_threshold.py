#!/usr/bin/env python3
"""borrow_threshold.py -- pick an ink threshold for a scroll nobody has labelled, by borrowing
the optimum the same model reaches on scrolls you can score (docs/27).

docs/27 tested this twice, pre-registered: on leave-one-scroll-out models over three scrolls
(322 cells) and on the 14 released ink_9um checkpoints over three scrolls they never saw
(70 predictions). Borrowing the same model's F1-optimal threshold from other scrolls lost
0.003-0.016 F1 (mean per scroll) against each scroll's own optimum; binarizing at 128 lost
0.056-0.145 on the first set. What transfers is a model's own threshold, not a number: the two sets wanted 84-92
and 98-141. So calibrate with the model you will run, and re-calibrate after fine-tuning.

docs/29 (a third test, dense-label checkpoints) found the value rule failing on one of three scrolls
(0.062 lost) while the quantile rule held on all three; the quantile rule has passed every test so far.
Read the borrowing check `calibrate` prints, and prefer ``apply --rule quantile`` for an unfamiliar model.

Step 1, ``calibrate``: run the model on segments you have ink labels for -- ideally from more
than one scroll -- and give it each (prediction, ink labels, supervision mask) triple. It
records each cell's F1-optimal threshold and writes their median (``value`` rule, R1 in
docs/27) and the median fraction of the sheet those thresholds mark (``quantile`` rule, R3).
With two or more scrolls it also runs the docs/27 check on your own cells: each scroll is
scored with a threshold borrowed from the others, so you see what borrowing costs for this
model before you rely on it.

Step 2, ``apply``: binarize a prediction of the unlabelled scroll at the calibrated threshold.

    python tools/borrow_threshold.py calibrate --out calib.json \\
        --cell PHerc0841 preds/0841-w00.tif labels/0841-w00_inklabels.zarr labels/0841-w00_supervision_mask.zarr \\
        --cell PHerc0009B preds/0009b.tif labels/0009b_inklabels.zarr labels/0009b_supervision_mask.zarr
    python tools/borrow_threshold.py apply preds/unlabelled.tif --calibration calib.json --out ink_mask.tif

Inputs: predictions are 2-D TIFFs as written by ``koine_machines.inference.infer`` (uint8; other
dtypes are clipped to 0-255). Labels and masks may be label Zarrs in the ink-detection layout
(``<segment>_inklabels.zarr`` with array ``0``; a 3-D array is read at its middle slice) or 2-D
TIFF/PNG images; any non-zero pixel counts. Without a supervision mask, the whole image is scored.
A pixel is ink when ``score >= threshold``, as in tools/eval_validation.py.

The ``quantile`` rule also reads the sheet: pass ``--sheet`` (a surface-volume Zarr, read at its
middle layer, or a mask image) to both steps, or it falls back to prediction > 0, as in docs/27.

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

NOISE_FLOOR = 0.03  # same-config spread of F1 measured in docs/09


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #
def read_prediction(path: Path) -> np.ndarray:
    import tifffile

    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        if len(page.shape) != 2:
            sys.exit(f"error: {path}: expected a 2-D prediction, got shape={page.shape}")
        prediction = page.asarray()
    if prediction.dtype != np.uint8:
        prediction = np.clip(prediction, 0, 255).astype(np.uint8)
    return prediction


def read_mask(path: Path) -> np.ndarray:
    """A 2-D boolean plane from a label/volume Zarr (array ``0``, middle slice) or an image."""
    if path.is_dir() or path.suffix == ".zarr":
        import zarr

        node = zarr.open(str(path), mode="r")
        array = node["0"] if hasattr(node, "array_keys") else node
        plane = np.asarray(array[array.shape[0] // 2]) if array.ndim == 3 else np.asarray(array)
    elif path.suffix.lower() in (".tif", ".tiff"):
        import tifffile

        plane = tifffile.imread(path)
    else:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = None
        plane = np.asarray(Image.open(path))
    if plane.ndim == 3:  # RGB(A) image
        plane = plane[..., :3].max(axis=-1)
    if plane.ndim != 2:
        sys.exit(f"error: {path}: expected a 2-D mask, got shape={plane.shape}")
    return plane > 0


def check_shape(name: Path, mask: np.ndarray, shape: tuple) -> None:
    if mask.shape != shape:
        sys.exit(f"error: {name} has shape {mask.shape}, the prediction has {shape}")


def sheet_histogram(prediction: np.ndarray, sheet_path: Path | None) -> tuple[np.ndarray, str]:
    if sheet_path is None:
        return np.bincount(prediction[prediction > 0], minlength=256), "prediction > 0"
    sheet = read_mask(sheet_path)
    check_shape(sheet_path, sheet, prediction.shape)
    return np.bincount(prediction[sheet], minlength=256), str(sheet_path)


# --------------------------------------------------------------------------- #
# Rules (identical to tools/score_label_free_threshold.py)
# --------------------------------------------------------------------------- #
def f1_curve(pos: np.ndarray, neg: np.ndarray) -> np.ndarray:
    """F1 at every threshold t (positive = score >= t)."""
    tp = pos[::-1].cumsum()[::-1].astype(float)
    fp = neg[::-1].cumsum()[::-1].astype(float)
    total = float(pos.sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        precision = np.where(tp + fp > 0, tp / (tp + fp), 0.0)
        recall = tp / max(total, 1.0)
        return np.where(precision + recall > 0, 2 * precision * recall / (precision + recall), 0.0)


def fraction_at_or_above(hist: np.ndarray) -> np.ndarray:
    return hist[::-1].cumsum()[::-1] / max(float(hist.sum()), 1.0)


def round_half_up(value: float) -> int:
    return int(np.floor(value + 0.5))


def value_threshold(cells: list[dict]) -> int:
    return round_half_up(float(np.median([c["oracle_threshold"] for c in cells])))


def quantile_q(cells: list[dict]) -> float:
    return float(np.median([c["sheet_fraction_at_oracle"] for c in cells]))


def quantile_threshold(sheet_hist: np.ndarray, q: float) -> int:
    """Lowest threshold at which at most a fraction q of the sheet is marked."""
    frac = fraction_at_or_above(sheet_hist)
    return int(np.argmax(frac <= q)) if (frac <= q).any() else 255


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def read_cells(args) -> list[dict]:
    specs = []
    for item in args.cell or []:
        if len(item) not in (3, 4):
            sys.exit("error: --cell takes SCROLL PREDICTION INKLABELS [SUPERVISION]")
        specs.append({"scroll": item[0], "prediction": item[1], "inklabels": item[2],
                      "supervision": item[3] if len(item) == 4 else ""})
    if args.cells_csv:
        with open(args.cells_csv, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                specs.append({k: (row.get(k) or "").strip()
                              for k in ("scroll", "prediction", "inklabels", "supervision", "sheet")})
    if not specs:
        sys.exit("error: give at least one --cell or --cells-csv")
    return specs


def calibrate(args) -> None:
    cells = []
    for spec in read_cells(args):
        pred_path = Path(spec["prediction"])
        prediction = read_prediction(pred_path)
        ink = read_mask(Path(spec["inklabels"]))
        check_shape(Path(spec["inklabels"]), ink, prediction.shape)
        if spec.get("supervision"):
            supervised = read_mask(Path(spec["supervision"]))
            check_shape(Path(spec["supervision"]), supervised, prediction.shape)
        else:
            supervised = np.ones(prediction.shape, bool)
        ink &= supervised
        if not ink.any():
            sys.exit(f"error: {pred_path}: no ink pixels inside the supervision mask")
        pos = np.bincount(prediction[ink], minlength=256)
        neg = np.bincount(prediction[supervised & ~ink], minlength=256)
        sheet_spec = spec.get("sheet") or args.sheet
        sheet_hist, sheet_source = sheet_histogram(prediction, Path(sheet_spec) if sheet_spec else None)
        curve = f1_curve(pos, neg)
        oracle = int(np.argmax(curve))
        cells.append({"scroll": spec["scroll"], "prediction": str(pred_path),
                      "oracle_threshold": oracle, "oracle_f1": float(curve.max()),
                      "f1_at_128": float(curve[128]),
                      "sheet_fraction_at_oracle": float(fraction_at_or_above(sheet_hist)[oracle]),
                      "sheet": sheet_source, "_curve": curve, "_sheet_hist": sheet_hist})
        print(f"{spec['scroll']:>14}  {pred_path.name}: optimum {oracle} (F1 {curve.max():.3f}; "
              f"at 128: {curve[128]:.3f})", flush=True)

    result = {
        "method": "docs/27: borrow the same model's F1-optimal threshold from scorable scrolls",
        "model": args.model or "",
        "value_threshold": value_threshold(cells),
        "quantile_q": quantile_q(cells),
        "cells": [{k: v for k, v in c.items() if not k.startswith("_")} for c in cells],
    }

    scrolls = sorted({c["scroll"] for c in cells})
    if len(scrolls) >= 2:
        check = {}
        for scroll in scrolls:
            own = [c for c in cells if c["scroll"] == scroll]
            donors = [c for c in cells if c["scroll"] != scroll]
            t_value, q = value_threshold(donors), quantile_q(donors)
            regret = {"value": [], "quantile": [], "128": []}
            for c in own:
                curve = c["_curve"]
                t_quant = quantile_threshold(c["_sheet_hist"], q)
                regret["value"].append(curve.max() - curve[t_value])
                regret["quantile"].append(curve.max() - curve[t_quant])
                regret["128"].append(curve.max() - curve[128])
            check[scroll] = {"cells": len(own), "borrowed_value_threshold": t_value,
                             **{f"mean_regret_{k}": float(np.mean(v)) for k, v in regret.items()}}
        result["leave_one_scroll_out_check"] = check
        print("\nborrowing check (each scroll scored with the other scrolls' threshold):")
        print(f"{'scroll':>14} {'cells':>5} {'borrowed':>8} {'value':>7} {'quantile':>8} {'128':>7}")
        for scroll, row in check.items():
            print(f"{scroll:>14} {row['cells']:>5} {row['borrowed_value_threshold']:>8} "
                  f"{row['mean_regret_value']:>7.3f} {row['mean_regret_quantile']:>8.3f} "
                  f"{row['mean_regret_128']:>7.3f}")
        worst = max(row["mean_regret_value"] for row in check.values())
        if worst >= NOISE_FLOOR:
            print(f"warning: borrowing the value costs {worst:.3f} F1 on at least one of your scrolls "
                  f"(noise floor {NOISE_FLOOR}); do not trust it on a new scroll without more data.")
        result["leave_one_scroll_out_ok"] = bool(worst < NOISE_FLOOR)
    else:
        print("\nnote: all cells come from one scroll, so the borrowing check cannot run. docs/27 "
              "borrows from other scrolls; add a second scroll if you can.")
        result["leave_one_scroll_out_check"] = None

    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\nvalue threshold {result['value_threshold']}, quantile q {result['quantile_q']:.4f} "
          f"-> wrote {args.out}")


def apply(args) -> None:
    calibration = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    prediction = read_prediction(Path(args.prediction))
    sheet_hist, sheet_source = sheet_histogram(prediction, Path(args.sheet) if args.sheet else None)
    if args.rule == "value":
        threshold = int(calibration["value_threshold"])
    else:
        threshold = quantile_threshold(sheet_hist, float(calibration["quantile_q"]))
    marked = float(fraction_at_or_above(sheet_hist)[threshold])
    report = {"prediction": args.prediction, "rule": args.rule, "threshold": threshold,
              "sheet": sheet_source, "sheet_fraction_marked": marked}
    if args.out:
        import tifffile

        tifffile.imwrite(args.out, np.where(prediction >= threshold, 255, 0).astype(np.uint8),
                         compression="zlib")
        report["out"] = args.out
    print(json.dumps(report, indent=1))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("calibrate", help="optimum per labelled cell, their median, and the borrowing check")
    p.add_argument("--cell", nargs="+", action="append", metavar="ARG",
                   help="SCROLL PREDICTION INKLABELS [SUPERVISION]; repeat per labelled segment")
    p.add_argument("--cells-csv", help="CSV with columns scroll,prediction,inklabels[,supervision][,sheet]")
    p.add_argument("--sheet", help="sheet mask used for every cell without its own (quantile rule only)")
    p.add_argument("--model", help="free-text note of the checkpoint, stored in the output")
    p.add_argument("--out", required=True, help="calibration JSON to write")
    p = sub.add_parser("apply", help="binarize a prediction at the calibrated threshold")
    p.add_argument("prediction")
    p.add_argument("--calibration", required=True)
    p.add_argument("--rule", choices=("value", "quantile"), default="value",
                   help="value (default; R1 in docs/27) or quantile (R3)")
    p.add_argument("--sheet", help="sheet mask of this prediction (quantile rule; default prediction > 0)")
    p.add_argument("--out", help="write the binary mask (0/255 uint8 TIFF) here")
    args = parser.parse_args(argv)
    {"calibrate": calibrate, "apply": apply}[args.cmd](args)


if __name__ == "__main__":
    main()
