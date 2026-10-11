#!/usr/bin/env python3
"""check_depth_perturbation.py -- feasibility check (not pre-registered): how much does a 9 um ink
read lose when the surface it was rendered on is off along the normal?

Two kinds of error on a rendered 21-slice surface volume (~9.6 um per slice):
  const k  : the whole surface shifted by k slices (what a global depth window can undo)
  wander A : a smooth, spatially varying shift with peak |shift| = A slices (correlation length
             ~2 mm), like a surface that drifts on and off the sheet; no single window undoes it
Slices are resampled with linear interpolation along z and clamped at the volume's ends, so only
small shifts (|k|, A <= 2) stay inside rendered data.

    uv run --project external/villa/ink-detection --no-sync python tools/check_depth_perturbation.py make
    python tools/check_depth_perturbation.py infer
    uv run --project external/villa/ink-detection --no-sync python tools/check_depth_perturbation.py score

License: MIT.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/ink_9um/surface-volumes/openlabels9"
LABELS = ROOT / "data/ink_9um/labels/openlabels9"
PERT = ROOT / "data/ink_9um/surface-volumes/perturbed"
PREDS = ROOT / "runs/ink9um_openlabels/preds_perturbed"
CKPT = ROOT / "data/ink_9um/models/hybrid_3d2d-seed43/step-020000.pth"
ENV_PROJECT = ROOT / "external/villa/ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")
OUT = ROOT / "runs/ink9um_scorecard/depth_perturbation.json"

SEGMENTS = ("pherc0841-w00", "pherc0009b-ag055")
VARIANTS = {"const+0": ("const", 0.0), "const+1": ("const", 1.0), "const-1": ("const", -1.0),
            "const+2": ("const", 2.0), "const-2": ("const", -2.0),
            "wander1": ("wander", 1.0), "wander2": ("wander", 2.0)}
CORR_PX = 200          # ~2 mm at ~9.6 um/px
SEED = 7


def offset_field(shape, kind, amount):
    if kind == "const":
        return np.full(shape, amount, np.float32)
    from scipy.ndimage import gaussian_filter, zoom

    rng = np.random.default_rng(SEED)
    small = (max(4, shape[0] // 25), max(4, shape[1] // 25))
    noise = gaussian_filter(rng.standard_normal(small), sigma=CORR_PX / 25)
    field = zoom(noise, (shape[0] / small[0], shape[1] / small[1]), order=1)[: shape[0], : shape[1]]
    return (field / np.abs(field).max() * amount).astype(np.float32)


def make(args) -> None:
    import zarr

    PERT.mkdir(parents=True, exist_ok=True)
    for seg in SEGMENTS:
        src = zarr.open(str(SRC / f"{seg}.zarr"), mode="r")
        vol = np.asarray(src["0"][:]).astype(np.float32)          # (21, H, W)
        depth = vol.shape[0]
        z = np.arange(depth, dtype=np.float32)[:, None, None]
        for name, (kind, amount) in VARIANTS.items():
            dst_path = PERT / f"{seg}__{name}.zarr"
            if dst_path.exists():
                continue
            d = offset_field(vol.shape[1:], kind, amount)[None]
            pos = np.clip(z + d, 0, depth - 1)
            lo = np.floor(pos).astype(np.int64)
            hi = np.minimum(lo + 1, depth - 1)
            w = pos - lo
            out = (np.take_along_axis(vol, lo, 0) * (1 - w) + np.take_along_axis(vol, hi, 0) * w)
            out = np.where(vol.max(axis=0, keepdims=True) > 0, out, 0)   # keep the render's own mask
            root = zarr.open_group(str(dst_path), mode="w")
            root.attrs.update(dict(src.attrs))
            root.create_dataset("0", data=np.rint(out).astype(np.uint8), chunks=src["0"].chunks)
            print(f"{seg} {name}: |shift| max {np.abs(d).max():.2f}, mean {np.abs(d).mean():.2f}", flush=True)


def infer(args) -> None:
    PREDS.mkdir(parents=True, exist_ok=True)
    for seg in SEGMENTS:
        for name in VARIANTS:
            out = PREDS / f"{seg}__{name}.tif"
            if out.exists():
                continue
            cmd = ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", "-m",
                   "koine_machines.inference.infer", str(PERT / f"{seg}__{name}.zarr"), str(CKPT), str(out),
                   "--overlap", "0.5", "--blend-mode", "hann", "--batch-size", "4", "--no-compile"]
            t0 = time.time()
            proc = subprocess.run(cmd, cwd=RUN_TREE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            print(f"{seg} {name}: exit {proc.returncode} in {(time.time() - t0) / 60:.1f} min", flush=True)
            if proc.returncode != 0:
                print(proc.stderr[-1500:], flush=True)


def score(args) -> None:
    import tifffile
    import zarr

    sys.path.insert(0, str(ROOT / "tools"))
    from score_label_free_threshold import f1_curve

    result = {}
    for seg in SEGMENTS:
        sup = np.asarray(zarr.open(str(LABELS / seg / f"{seg}_supervision_mask.zarr"), mode="r")["0"][0]) > 0
        ink = (np.asarray(zarr.open(str(LABELS / seg / f"{seg}_inklabels.zarr"), mode="r")["0"][0]) > 0) & sup
        bg = sup & ~ink
        for name in VARIANTS:
            p = tifffile.imread(PREDS / f"{seg}__{name}.tif")
            pos = np.bincount(p[ink], minlength=256).astype(float)
            neg = np.bincount(p[bg], minlength=256).astype(float)
            neg_below = np.concatenate([[0.0], np.cumsum(neg)[:-1]])
            auc = float((pos * (neg_below + 0.5 * neg)).sum() / (pos.sum() * neg.sum()))
            curve = f1_curve(pos, neg)
            result[f"{seg}|{name}"] = {"auc": auc, "f1_best": float(curve.max()), "f1_at_128": float(curve[128])}
            print(f"{seg:18} {name:8} AUC {auc:.4f}  best F1 {curve.max():.4f}  F1@128 {curve[128]:.4f}", flush=True)
    OUT.write_text(json.dumps({"checkpoint": str(CKPT.relative_to(ROOT)), "variants": VARIANTS,
                               "corr_px": CORR_PX, "results": result}, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    {"make": make, "infer": infer, "score": score}[sys.argv[1]](None)
