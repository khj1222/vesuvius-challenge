#!/usr/bin/env python3
"""check_quantile_sheet.py -- does the quantile rule (R3) need the surface volume, or is
`prediction > 0` an equivalent sheet?

docs/27 and docs/29 define the sheet as the non-zero pixels of the segment's middle surface-volume
layer, with `prediction > 0` as the fallback. A villa command that only takes predictions and labels
would use the fallback, so this recomputes R3 with the fallback on the open-label data of docs/27's
replication (14 released checkpoints) and docs/29 (5 checkpoints) and compares it with the published R3.

    uv run --project external/villa/ink-detection --no-sync python tools/check_quantile_sheet.py

Run after both studies; descriptive, not pre-registered. License: MIT.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from score_label_free_threshold import f1_curve, fraction_at_or_above  # noqa: E402

LABELS = ROOT / "data/ink_9um/labels/openlabels9"
SEGMENTS = {"pherc0841-w00": "PHerc0841", "pherc0841-ag144": "PHerc0841", "pherc0841-ag174": "PHerc0841",
            "pherc0009b-ag055": "PHerc0009B", "pherc0500p2-s1": "PHerc0500P2"}
SCROLLS = ("PHerc0841", "PHerc0009B", "PHerc0500P2")
OUT = ROOT / "runs/ink9um_scorecard/quantile_sheet_check.json"


def plane(path: Path) -> np.ndarray:
    import zarr

    a = zarr.open(str(path), mode="r")["0"]
    return np.asarray(a[a.shape[0] // 2]) if a.ndim == 3 else np.asarray(a)


def study(name, models, pred_file, cells_csv, model_key):
    labels = {}
    for seg in SEGMENTS:
        sup = plane(LABELS / seg / f"{seg}_supervision_mask.zarr") > 0
        ink = (plane(LABELS / seg / f"{seg}_inklabels.zarr") > 0) & sup
        labels[seg] = (ink, sup & ~ink)
    cells = []
    for model in models:
        for seg, scroll in SEGMENTS.items():
            p = tifffile.imread(pred_file(seg, model))
            ink, bg = labels[seg]
            curve = f1_curve(np.bincount(p[ink], minlength=256), np.bincount(p[bg], minlength=256))
            cells.append({"model": model, "seg": seg, "scroll": scroll, "curve": curve,
                          "oracle": int(np.argmax(curve)), "sheet": np.bincount(p[p > 0], minlength=256)})
    for c in cells:
        donors = [o for o in cells if o["model"] == c["model"] and o["scroll"] != c["scroll"]]
        q = float(np.median([fraction_at_or_above(o["sheet"])[o["oracle"]] for o in donors]))
        frac = fraction_at_or_above(c["sheet"])
        t = int(np.argmax(frac <= q)) if (frac <= q).any() else 255
        c["regret"] = float(c["curve"].max() - c["curve"][t])
        c["t"] = t
    published = {(r[model_key], r["segment"]): r for r in csv.DictReader(open(cells_csv))}
    out = {}
    for scroll in SCROLLS:
        sel = [c for c in cells if c["scroll"] == scroll]
        pub = [float(published[(c["model"], c["seg"])]["regret_R3"]) for c in sel]
        out[scroll] = {"cells": len(sel), "R3_prediction_gt0": float(np.mean([c["regret"] for c in sel])),
                       "R3_published_volume_sheet": float(np.mean(pub)),
                       "max_cell_threshold_shift": int(max(abs(c["t"] - int(published[(c["model"], c["seg"])]["t_R3"]))
                                                           for c in sel))}
        print(f"{name:10} {scroll:12} R3 with prediction>0 {out[scroll]['R3_prediction_gt0']:.4f}  "
              f"published (volume sheet) {out[scroll]['R3_published_volume_sheet']:.4f}  "
              f"largest threshold shift {out[scroll]['max_cell_threshold_shift']}", flush=True)
    return out


def main() -> None:
    import run_other_recipes_threshold as R

    result = {}
    # docs/27 replication: 14 released checkpoints (seed x step); cells keyed by "s{seed}_{step}"
    rep_models = [f"{s}_{st}" for s in ("42", "43") for st in ("010000", "020000", "030000", "040000",
                                                               "050000", "060000", "075000")]
    rep_csv = ROOT / "runs/ink9um_scorecard/openlabels_cells.csv"
    tmp = ROOT / "runs/ink9um_scorecard/_openlabels_cells_keyed.csv"
    with open(rep_csv, newline="") as fh, open(tmp, "w", newline="") as out:
        reader = csv.DictReader(fh)
        writer = csv.DictWriter(out, fieldnames=reader.fieldnames + ["model"])
        writer.writeheader()
        for row in reader:
            row["model"] = f"{row['seed']}_{row['step']}"
            writer.writerow(row)
    result["docs27_replication_released"] = study(
        "released", rep_models,
        lambda seg, m: ROOT / f"runs/ink9um_openlabels/preds/{seg}_s{m.split('_')[0]}_{m.split('_')[1]}.tif",
        tmp, "model")
    tmp.unlink()
    result["docs29_dense_and_control"] = study("docs29", list(R.MODELS), R.pred_path,
                                               R.OUT / "otherrecipes_cells.csv", "model")
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
