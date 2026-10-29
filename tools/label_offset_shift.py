#!/usr/bin/env python3
"""label_offset_shift.py -- docs/33 Stage 1: does a 9 um model draw ink displaced from where the labels put it?

For each model and open-label segment, AUC(d) = AUC over supervised pixels of label(y, x) against
prediction(y + dy, x + dx) for integer d in [-12, 12]^2 (256-bin histogram AUC). The shift s is the argmax,
refined per axis by a parabola. The judged quantity is the shift relative to ink_9um seed43, per segment.

    python tools/label_offset_shift.py infer    # Reader V3 and v2 on the five segments (same command as docs/29)
    python tools/label_offset_shift.py check    # method check: known shift recovered, histogram AUC vs sklearn
    python tools/label_offset_shift.py run      # the measurement and the docs/33 verdict

Pre-registration: docs/33 (commit e1e4af2). License: MIT.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parent.parent
VOLUMES = ROOT / "data/ink_9um/surface-volumes/openlabels9"
LABELS = ROOT / "data/ink_9um/labels/openlabels9/_npy"
CLEAN = ROOT / "data/ink_9um/models_ext/clean"
ENV_PROJECT = ROOT / "external/villa/ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")
PRED_DIRS = ROOT / "runs/ink9um_openlabels"
NEW_PREDS = PRED_DIRS / "preds_docs33"
OUT = ROOT / "runs/label_offset"

SEGMENTS = ("pherc0841-w00", "pherc0841-ag144", "pherc0841-ag174", "pherc0009b-ag055", "pherc0500p2-s1")
MODELS = {  # name -> prediction path pattern
    "ink9um_s43": PRED_DIRS / "preds" / "{seg}_s43_075000.tif",
    "ink9um_s42": PRED_DIRS / "preds" / "{seg}_s42_075000.tif",
    "reader_v3": NEW_PREDS / "{seg}_reader_v3.tif",
    "reader_v2": NEW_PREDS / "{seg}_reader_v2.tif",
    "klavis_all7": PRED_DIRS / "preds_otherrecipes" / "{seg}_K_all7_75k.tif",
    "klavis_control": PRED_DIRS / "preds_otherrecipes" / "{seg}_K_control_75k.tif",
    "nieuwlaar_native": PRED_DIRS / "preds_otherrecipes" / "{seg}_N_native_16k.tif",
}
NEW_CKPTS = {"reader_v3": "klavis_reader-v3.pth", "reader_v2": "klavis_reader-v2.pth"}
R = 12


def infer(_args=None) -> None:
    NEW_PREDS.mkdir(parents=True, exist_ok=True)
    for model, ckpt in NEW_CKPTS.items():
        for seg in SEGMENTS:
            out = Path(str(MODELS[model]).format(seg=seg))
            if out.exists():
                continue
            cmd = ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", "-m",
                   "koine_machines.inference.infer", str(VOLUMES / f"{seg}.zarr"), str(CLEAN / ckpt), str(out),
                   "--overlap", "0.5", "--blend-mode", "hann", "--batch-size", "4", "--no-compile"]
            t0 = time.time()
            for _ in range(3):
                proc = subprocess.run(cmd, cwd=RUN_TREE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                if proc.returncode == 0 and out.exists():
                    break
                time.sleep(30)
            print(f"{seg} {model}: exit {proc.returncode} in {(time.time() - t0) / 60:.1f} min", flush=True)
            if not out.exists():
                sys.exit(f"error: no prediction for {seg} {model}\n{proc.stderr[-2000:]}")


def load(seg: str, model: str):
    pred = tifffile.imread(str(MODELS[model]).format(seg=seg))
    ink = np.load(LABELS / f"{seg}_inklabels.npy") > 0
    sup = np.load(LABELS / f"{seg}_supervision.npy") > 0
    assert pred.dtype == np.uint8 and pred.shape == ink.shape == sup.shape, (seg, model, pred.dtype, pred.shape)
    return pred, ink, sup


def hist_auc(p: np.ndarray, pos: np.ndarray) -> float:
    hp = np.bincount(p[pos], minlength=256).astype(np.float64)
    hn = np.bincount(p[~pos], minlength=256).astype(np.float64)
    above = np.cumsum(hp[::-1])[::-1] - hp  # positives strictly above each bin
    return float((hn * (above + 0.5 * hp)).sum() / (hp.sum() * hn.sum()))


def auc_at(pred, ink, sup, dy: int, dx: int) -> float:
    H, W = ink.shape
    y0, y1 = max(0, -dy), H - max(0, dy)
    x0, x1 = max(0, -dx), W - max(0, dx)
    m = sup[y0:y1, x0:x1]
    p = pred[y0 + dy:y1 + dy, x0 + dx:x1 + dx][m]
    return hist_auc(p, ink[y0:y1, x0:x1][m])


def parabola(a_m, a_0, a_p) -> float:
    den = a_m - 2 * a_0 + a_p
    return 0.0 if den == 0 else 0.5 * (a_m - a_p) / den


def shift_of(pred, ink, sup) -> dict:
    grid = np.full((2 * R + 1, 2 * R + 1), np.nan)
    for i, dy in enumerate(range(-R, R + 1)):
        for j, dx in enumerate(range(-R, R + 1)):
            grid[i, j] = auc_at(pred, ink, sup, dy, dx)
    i, j = np.unravel_index(np.nanargmax(grid), grid.shape)
    edge = i in (0, 2 * R) or j in (0, 2 * R)
    fy = 0.0 if i in (0, 2 * R) else parabola(grid[i - 1, j], grid[i, j], grid[i + 1, j])
    fx = 0.0 if j in (0, 2 * R) else parabola(grid[i, j - 1], grid[i, j], grid[i, j + 1])
    return {"s": [float(i - R + fy), float(j - R + fx)], "argmax": [int(i - R), int(j - R)], "edge": bool(edge),
            "auc0": float(grid[R, R]), "auc_max": float(grid[i, j]), "grid": grid.tolist()}


def _job(args):
    seg, model = args
    pred, ink, sup = load(seg, model)
    return seg, model, shift_of(pred, ink, sup)


def check(_args=None) -> None:
    from sklearn.metrics import roc_auc_score
    seg = SEGMENTS[0]
    pred, ink, sup = load(seg, "ink9um_s43")
    moved = np.zeros_like(pred)  # draw the same map +5 rows, -3 columns
    moved[5:, :-3] = pred[:-5, 3:]
    a, b = shift_of(pred, ink, sup), shift_of(moved, ink, sup)
    rel = [b["s"][0] - a["s"][0], b["s"][1] - a["s"][1]]
    rows = []
    for s in SEGMENTS:
        p, k, m = load(s, "ink9um_s43")
        rows.append({"segment": s, "hist_auc": hist_auc(p[m], k[m]), "sklearn_auc": float(roc_auc_score(k[m], p[m]))})
    ok_shift = abs(rel[0] - 5) <= 0.5 and abs(rel[1] + 3) <= 0.5
    ok_auc = all(abs(r["hist_auc"] - r["sklearn_auc"]) <= 0.002 for r in rows)
    res = {"known_shift": [5, -3], "recovered_relative": rel, "auc_rows": rows, "pass": bool(ok_shift and ok_auc)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "method_check.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def judge_model(rel: dict, lo: float, hi: float) -> dict:
    inside = sum(lo <= r[0] <= hi and lo <= r[1] <= hi for r in rel.values())
    still = sum(abs(r[0]) <= 2 and abs(r[1]) <= 2 for r in rel.values())
    return {"in_window": inside, "within_2": still}


def run(_args=None) -> None:
    jobs = [(s, m) for m in MODELS for s in SEGMENTS]
    res = {m: {} for m in MODELS}
    with ProcessPoolExecutor(8) as ex:
        for seg, model, r in ex.map(_job, jobs):
            res[model][seg] = r
            print(f"{model:17s} {seg:17s} s=({r['s'][0]:+.2f},{r['s'][1]:+.2f}) edge={r['edge']} "
                  f"auc0={r['auc0']:.4f} max={r['auc_max']:.4f}", flush=True)
    ref = {s: res["ink9um_s43"][s]["s"] for s in SEGMENTS}
    rel = {m: {s: [res[m][s]["s"][0] - ref[s][0], res[m][s]["s"][1] - ref[s][1]] for s in SEGMENTS} for m in MODELS}
    counts = {m: judge_model(rel[m], 4, 10) for m in MODELS}

    def verdict(m):
        if counts[m]["in_window"] >= 4 and counts["ink9um_s42"]["within_2"] >= 4:
            return "learned shift present"
        if counts[m]["within_2"] >= 4:
            return "absent"
        return "unclear"

    # post-hoc fix: one fixed vector = round(mean s43 shift over the five segments) + (7, 7)
    mean_ref = np.mean([ref[s] for s in SEGMENTS], 0)
    fix = [int(np.round(mean_ref[0])) + 7, int(np.round(mean_ref[1])) + 7]
    fixes = {}
    for m in MODELS:
        rows = {}
        for s in SEGMENTS:
            g = np.array(res[m][s]["grid"])
            if abs(fix[0]) <= R and abs(fix[1]) <= R:
                rows[s] = float(g[fix[0] + R, fix[1] + R] - g[R, R])
        vals = list(rows.values())
        fixes[m] = {"per_segment": rows, "mean": float(np.mean(vals)), "n_positive": int(sum(v > 0 for v in vals))}
    summary = {
        "relative_shift": rel, "counts": counts,
        "verdict": {"reader_v3": verdict("reader_v3"), "reader_v2": verdict("reader_v2")},
        "fix_vector": fix, "posthoc_fix": fixes,
        "posthoc_useful_reader_v3": bool(fixes["reader_v3"]["mean"] >= 0.005 and fixes["reader_v3"]["n_positive"] >= 4),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage1_grids.json").write_text(json.dumps(res))
    (OUT / "stage1_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "posthoc_fix"}, indent=1))
    print("post-hoc mean dAUC:", {m: round(f["mean"], 4) for m, f in fixes.items()})


if __name__ == "__main__":
    {"infer": infer, "check": check, "run": run}[sys.argv[1]]()
