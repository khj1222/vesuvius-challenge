#!/usr/bin/env python3
"""check_otherrecipes.py -- checks on docs/29, run after its results.

    python tools/check_otherrecipes.py control-infer   # positive control predictions (GPU)
    python tools/check_otherrecipes.py control-score   # reproduce KLAVIS's published validation numbers
    python tools/check_otherrecipes.py direct          # recompute F1 from the TIFFs, not the histograms
    python tools/check_otherrecipes.py tensors         # converted checkpoints == their sources

Positive control: KLAVIS's card publishes balanced accuracy at 0.5 and AUC inside the three ink_9um
`_validation_mask` regions for two of the checkpoints used here; his `step9_eval.py` (DomRusso2/ink9um-dense)
scores AUC by Mann-Whitney over the masked pixels of the middle label plane. If the converted checkpoints
and this inference path reproduce those numbers, the docs/29 predictions are what those models produce.

License: MIT.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import run_other_recipes_threshold as R  # noqa: E402

ALIGNED_VOL = ROOT / "data/ink_9um/surface-volumes/aligned9"
ALIGNED_LAB = ROOT / "data/ink_9um/labels/aligned-scrollprizeorg-21slices"
CTRL_PREDS = ROOT / "runs/ink9um_openlabels/preds_otherrecipes_control"
OUT = ROOT / "runs/ink9um_scorecard/otherrecipes_checks.json"

# KLAVIS's published numbers (HF card domenicor046/ink9um-dense, results/step9_results.jsonl)
PUBLISHED = {
    ("K_ex016_75k", "pherc0814-46527"): (0.8329, 0.9298),
    ("K_ex016_75k", "pherc0139-w016"): (0.7496, 0.9070),
    ("K_ex016_75k", "pherc1667-w029"): (0.7882, 0.8853),
    ("K_control_75k", "pherc0139-w016"): (0.7016, 0.8707),
    ("K_control_75k", "pherc0814-46527"): (0.7539, 0.8323),
    ("K_control_75k", "pherc1667-w029"): (0.7814, 0.8945),
}


def control_infer(args) -> None:
    CTRL_PREDS.mkdir(parents=True, exist_ok=True)
    for (model, seg) in PUBLISHED:
        out = CTRL_PREDS / f"{seg}_{model}.tif"
        if out.exists():
            continue
        cmd = ["uv", "run", "--project", str(R.ENV_PROJECT), "--no-sync", "python", "-m",
               "koine_machines.inference.infer", str(ALIGNED_VOL / f"{seg}.zarr"), str(R.CLEAN / R.MODELS[model]),
               str(out), "--overlap", "0.5", "--blend-mode", "hann", "--batch-size", "4", "--no-compile"]
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=R.RUN_TREE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        print(f"{seg} {model}: exit {proc.returncode} in {(time.time() - t0) / 60:.1f} min", flush=True)
        if proc.returncode != 0:
            print(proc.stderr[-2000:], flush=True)


def _plane(path: Path) -> np.ndarray:
    import zarr

    node = zarr.open(str(path), mode="r")
    arr = node["0"] if hasattr(node, "array_keys") else node
    return np.asarray(arr[arr.shape[0] // 2]) if arr.ndim == 3 else np.asarray(arr)


def _auc(scores: np.ndarray, truth: np.ndarray) -> float:
    """Tie-aware Mann-Whitney AUC from 256-bin counts (scores are uint8)."""
    pos = np.bincount(scores[truth], minlength=256).astype(np.float64)
    neg = np.bincount(scores[~truth], minlength=256).astype(np.float64)
    neg_below = np.concatenate([[0.0], np.cumsum(neg)[:-1]])
    return float((pos * (neg_below + 0.5 * neg)).sum() / (pos.sum() * neg.sum()))


def control_score(args) -> None:
    import tifffile

    rows = {}
    for (model, seg), (ba_pub, auc_pub) in PUBLISHED.items():
        pred_file = CTRL_PREDS / f"{seg}_{model}.tif"
        if not pred_file.exists():
            continue
        p = tifffile.imread(pred_file)
        gt = _plane(ALIGNED_LAB / seg / f"{seg}_inklabels.zarr") > 0
        valid = _plane(ALIGNED_LAB / seg / f"{seg}_validation_mask.zarr") > 0
        pv, gv = p[valid], gt[valid]
        marked = pv >= 128
        ba = 0.5 * (np.mean(marked[gv]) + np.mean(~marked[~gv]))
        auc = _auc(pv, gv)
        rows[f"{model}|{seg}"] = {"ba_at_128": float(ba), "auc": auc, "published_ba": ba_pub, "published_auc": auc_pub,
                                  "d_ba": float(ba - ba_pub), "d_auc": float(auc - auc_pub)}
        print(f"{model:14} {seg:16} BA {ba:.4f} (published {ba_pub:.4f}, {ba - ba_pub:+.4f})  "
              f"AUC {auc:.4f} (published {auc_pub:.4f}, {auc - auc_pub:+.4f})", flush=True)
    _save("positive_control", rows)


def direct(args) -> None:
    """F1 at the oracle, 128 and R1b thresholds, counted pixel by pixel from each TIFF."""
    import tifffile

    cells = {(r["segment"], r["model"]): r for r in csv.DictReader(open(R.OUT / "otherrecipes_cells.csv"))}
    worst = 0.0
    rows = {}
    for seg in R.SEGMENTS:
        sup = _plane(R.LABELS / seg / f"{seg}_supervision_mask.zarr") > 0
        ink = (_plane(R.LABELS / seg / f"{seg}_inklabels.zarr") > 0) & sup
        bg = sup & ~ink
        for model in R.MODELS:
            p = tifffile.imread(R.pred_path(seg, model))
            row = cells[(seg, model)]
            out = {}
            for name, t in (("oracle", int(row["oracle_threshold"])), ("R0", 128), ("R1b", int(row["t_R1b"]))):
                m = p >= t
                tp, fp, fn = int((m & ink).sum()), int((m & bg).sum()), int((~m & ink).sum())
                out[name] = 2 * tp / (2 * tp + fp + fn)
            d = max(abs(out["oracle"] - float(row["oracle_f1"])),
                    abs((out["oracle"] - out["R0"]) - float(row["regret_R0"])),
                    abs((out["oracle"] - out["R1b"]) - float(row["regret_R1b"])))
            worst = max(worst, d)
            rows[f"{seg}|{model}"] = {**out, "max_abs_diff_vs_csv": d}
    print(f"25 cells recounted from the TIFFs; largest difference from otherrecipes_cells.csv: {worst:.2e}")
    _save("direct_recount", {"cells": rows, "max_abs_diff": worst})


def tensors(args) -> None:
    import torch
    from safetensors.torch import load_file

    rows = {}
    src = R.ROOT / "data/ink_9um/models_ext"
    pairs = [(src / "klavis_dense" / f"{m[len('klavis_'):]}", R.CLEAN / m) for m in R.MODELS.values() if m.startswith("klavis_")]
    for a, b in pairs:
        ma = torch.load(a, map_location="cpu", weights_only=True)["model"]
        mb = torch.load(b, map_location="cpu", weights_only=True)["model"]
        rows[b.name] = bool(set(ma) == set(mb) and all(torch.equal(ma[k], mb[k]) for k in ma))
    na = load_file(str(src / "nieuwlaar_dense_native/weights/dense_native_016000.safetensors"))
    nb = torch.load(R.CLEAN / R.MODELS["N_native_16k"], map_location="cpu", weights_only=True)["model"]
    rows[R.MODELS["N_native_16k"]] = bool(set(na) == set(nb) and all(torch.equal(na[k], nb[k]) for k in na))
    for k, v in rows.items():
        print(f"{k}: identical to source {v}")
    _save("tensor_identity", rows)


def _save(key, value) -> None:
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data[key] = value
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    {"control-infer": control_infer, "control-score": control_score, "direct": direct,
     "tensors": tensors}[sys.argv[1]](None)
