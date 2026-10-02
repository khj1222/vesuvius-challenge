#!/usr/bin/env python3
"""run_open_label_replication.py -- the docs/27 replication: the 14 released ink_9um checkpoints on
the three scrolls they never saw, judged by the open-data labels.

    python tools/run_open_label_replication.py infer     # 70 predictions, resumable
    python tools/run_open_label_replication.py collect   # 256-bin histograms per cell
    python tools/run_open_label_replication.py score     # the pre-registered rules (docs/27, commit 72c7679)

Inputs come from tools/prepare_open_label_segments.py. Scoring reuses the regret, Otsu and quantile
code of tools/score_label_free_threshold.py so the two studies apply the rules identically.

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from score_label_free_threshold import f1_curve, fraction_at_or_above, otsu, round_half_up  # noqa: E402

VOLUMES = ROOT / "data/ink_9um/surface-volumes/openlabels9"
LABELS = ROOT / "data/ink_9um/labels/openlabels9"
MODELS = ROOT / "data/ink_9um/models"
PREDS = ROOT / "runs/ink9um_openlabels/preds"
ENV_PROJECT = ROOT / "external/villa/ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")            # tree whose schema matches ink_9um
OUT = ROOT / "runs/ink9um_scorecard"
HIST_FILE = OUT / "openlabels_hists.npz"

SEGMENTS = {"pherc0841-w00": "PHerc0841", "pherc0841-ag144": "PHerc0841", "pherc0841-ag174": "PHerc0841",
            "pherc0009b-ag055": "PHerc0009B", "pherc0500p2-s1": "PHerc0500P2"}
SCROLLS = ("PHerc0841", "PHerc0009B", "PHerc0500P2")
SEEDS = ("42", "43")
STEPS = ("010000", "020000", "030000", "040000", "050000", "060000", "075000")
PRIMARY_STEPS = ("010000", "020000")
R1A = 87          # docs/27: median oracle threshold of its 92 primary cells, 86.5 rounded half up
NOISE_FLOOR = 0.03


def pred_path(seg: str, seed: str, step: str) -> Path:
    return PREDS / f"{seg}_s{seed}_{step}.tif"


def infer(args) -> None:
    PREDS.mkdir(parents=True, exist_ok=True)
    jobs = [(st, sd, sg) for st in STEPS for sd in SEEDS for sg in SEGMENTS]   # primary steps first
    for step, seed, seg in jobs:
        out = pred_path(seg, seed, step)
        if out.exists():
            continue
        ckpt = MODELS / f"hybrid_3d2d-seed{seed}" / f"step-{step}.pth"
        cmd = ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", "-m",
               "koine_machines.inference.infer", str(VOLUMES / f"{seg}.zarr"), str(ckpt), str(out),
               "--overlap", "0.5", "--blend-mode", "hann", "--batch-size", "4", "--no-compile"]
        t0 = time.time()
        for attempt in range(3):
            code = subprocess.run(cmd, cwd=RUN_TREE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  text=True).returncode
            if code == 0 and out.exists():
                break
            time.sleep(30)
        print(f"{seg} s{seed} {step}: exit {code} in {(time.time() - t0) / 60:.1f} min", flush=True)
        if not out.exists():
            sys.exit(f"error: no prediction for {seg} s{seed} {step}")


def collect(args) -> None:
    import zarr
    from eval_validation import read_prediction

    store = dict(np.load(HIST_FILE)) if HIST_FILE.exists() else {}
    for seg in SEGMENTS:
        sup = np.asarray(zarr.open(str(LABELS / seg / f"{seg}_supervision_mask.zarr"), mode="r")["0"][0]) > 0
        ink = (np.asarray(zarr.open(str(LABELS / seg / f"{seg}_inklabels.zarr"), mode="r")["0"][0]) > 0) & sup
        bg = sup & ~ink
        vol = zarr.open(str(VOLUMES / f"{seg}.zarr"), mode="r")["0"]
        sheet = np.asarray(vol[vol.shape[0] // 2]) > 0
        for seed in SEEDS:
            for step in STEPS:
                key = f"{seg}|{seed}|{step}"
                if f"{key}|sheet" in store:
                    continue
                p = read_prediction(pred_path(seg, seed, step))
                if p.shape != sheet.shape:
                    sys.exit(f"error: {seg} prediction {p.shape} != {sheet.shape}")
                store[f"{key}|pos"] = np.bincount(p[ink], minlength=256)
                store[f"{key}|neg"] = np.bincount(p[bg], minlength=256)
                store[f"{key}|sheet"] = np.bincount(p[sheet], minlength=256)
        np.savez_compressed(HIST_FILE, **store)
        print(f"{seg}: sheet {int(sheet.sum()):,} px, supervised {int(sup.sum()):,}, ink {int(ink.sum()):,}",
              flush=True)


def score(args) -> None:
    store = np.load(HIST_FILE)
    cells = []
    for seg, scroll in SEGMENTS.items():
        for seed in SEEDS:
            for step in STEPS:
                key = f"{seg}|{seed}|{step}"
                curve = f1_curve(store[f"{key}|pos"], store[f"{key}|neg"])
                pos = store[f"{key}|pos"]
                p = pos.sum() / (pos.sum() + store[f"{key}|neg"].sum())
                cells.append({"scroll": scroll, "segment": seg, "seed": seed, "step": step, "curve": curve,
                              "sheet": store[f"{key}|sheet"], "oracle_threshold": int(np.argmax(curve)),
                              "oracle_f1": float(curve.max()), "trivial_floor": float(2 * p / (1 + p))})
    for c in cells:
        donors = [o for o in cells if o["scroll"] != c["scroll"] and o["seed"] == c["seed"]
                  and o["step"] == c["step"]]
        r1b = round_half_up(float(np.median([o["oracle_threshold"] for o in donors])))
        q = float(np.median([fraction_at_or_above(o["sheet"])[o["oracle_threshold"]] for o in donors]))
        frac = fraction_at_or_above(c["sheet"])
        r3 = int(np.argmax(frac <= q)) if (frac <= q).any() else 255
        c["thresholds"] = {"R0": 128, "R1a": R1A, "R1b": r1b, "R2": otsu(c["sheet"]), "R3": r3}
        for rule, t in c["thresholds"].items():
            c[f"regret_{rule}"] = float(c["curve"].max() - c["curve"][t])

    def summarise(steps):
        out = {}
        for rule in ("R0", "R1a", "R1b", "R2", "R3"):
            out[rule] = {}
            for scroll in SCROLLS:
                sel = [c for c in cells if c["scroll"] == scroll and c["step"] in steps]
                vals = [c[f"regret_{rule}"] for c in sel]
                out[rule][scroll] = {"cells": len(vals), "mean_regret": float(np.mean(vals)),
                                     "max_regret": float(np.max(vals)),
                                     "within_noise": int(sum(v < NOISE_FLOOR for v in vals)),
                                     "threshold_range": [int(min(c["thresholds"][rule] for c in sel)),
                                                         int(max(c["thresholds"][rule] for c in sel))]}
        verdict = {}
        for rule in out:
            under = [s for s in SCROLLS if out[rule][s]["mean_regret"] < NOISE_FLOOR]
            beats = [s for s in SCROLLS if out[rule][s]["mean_regret"] < out["R0"][s]["mean_regret"]]
            verdict[rule] = {"passes": rule != "R0" and len(under) == 3 and len(beats) == 3,
                             "scrolls_under_noise_and_beating_R0": sorted(set(under) & set(beats))}
        return out, verdict

    primary, primary_verdict = summarise(PRIMARY_STEPS)
    secondary, secondary_verdict = summarise(STEPS)
    oracle = {s: {"mean_oracle_f1": float(np.mean([c["oracle_f1"] for c in cells
                                                   if c["scroll"] == s and c["step"] in PRIMARY_STEPS])),
                  "mean_trivial_floor": float(np.mean([c["trivial_floor"] for c in cells
                                                       if c["scroll"] == s and c["step"] in PRIMARY_STEPS])),
                  "oracle_threshold_range": [min(c["oracle_threshold"] for c in cells
                                                 if c["scroll"] == s and c["step"] in PRIMARY_STEPS),
                                             max(c["oracle_threshold"] for c in cells
                                                 if c["scroll"] == s and c["step"] in PRIMARY_STEPS)]}
              for s in SCROLLS}
    summary = {"preregistration": "docs/27_label_free_threshold.md, replication section (commit 72c7679)",
               "cells": len(cells), "oracle_primary": oracle, "primary": primary,
               "primary_verdict": primary_verdict, "secondary_all_steps": secondary,
               "secondary_verdict": secondary_verdict}
    (OUT / "openlabels_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    fields = ["scroll", "segment", "seed", "step", "oracle_threshold", "oracle_f1", "trivial_floor"] + \
             [f"t_{r}" for r in ("R0", "R1a", "R1b", "R2", "R3")] + \
             [f"regret_{r}" for r in ("R0", "R1a", "R1b", "R2", "R3")]
    with (OUT / "openlabels_cells.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for c in cells:
            row = {k: c[k] for k in fields if k in c}
            row.update({f"t_{r}": t for r, t in c["thresholds"].items()})
            for k in ("oracle_f1", "trivial_floor") + tuple(f"regret_{r}" for r in ("R0", "R1a", "R1b", "R2", "R3")):
                row[k] = f"{c[k]:.6f}"
            writer.writerow(row)
    print(json.dumps({"oracle_primary": oracle, "primary_verdict": primary_verdict}, indent=1))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("infer", "collect", "score"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    {"infer": infer, "collect": collect, "score": score}[args.cmd](args)


if __name__ == "__main__":
    main()
