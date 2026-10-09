#!/usr/bin/env python3
"""run_other_recipes_threshold.py -- docs/29: the docs/27 label-free threshold rules on public 9 um ink
checkpoints trained with other labels (KLAVIS ink9um-dense, Nieuwlaar dense-native), on the three
open-label scrolls none of them trained on (PHerc0841, PHerc0009B, PHerc0500P2).

    python tools/run_other_recipes_threshold.py infer     # 25 predictions, resumable
    python tools/run_other_recipes_threshold.py collect   # 256-bin histograms per cell
    python tools/run_other_recipes_threshold.py score     # the pre-registered rules (docs/29)

Inputs and labels are the docs/27 replication's (tools/prepare_open_label_segments.py). The rules,
inference flags and scoring code are the replication's (tools/run_open_label_replication.py), so the
only thing that changes is the checkpoint.

Checkpoints are third-party. They are never unpickled here: data/ink_9um/models_ext/clean/ holds copies
re-saved from torch.load(weights_only=True) (KLAVIS .pth) and from safetensors (Nieuwlaar), with
sha256 of every source file in convert_report.json.

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
CLEAN = ROOT / "data/ink_9um/models_ext/clean"
PREDS = ROOT / "runs/ink9um_openlabels/preds_otherrecipes"
ENV_PROJECT = ROOT / "external/villa/ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")            # tree whose schema matches ink_9um
OUT = ROOT / "runs/ink9um_scorecard"
HIST_FILE = OUT / "otherrecipes_hists.npz"

SEGMENTS = {"pherc0841-w00": "PHerc0841", "pherc0841-ag144": "PHerc0841", "pherc0841-ag174": "PHerc0841",
            "pherc0009b-ag055": "PHerc0009B", "pherc0500p2-s1": "PHerc0500P2"}
SCROLLS = ("PHerc0841", "PHerc0009B", "PHerc0500P2")
# name -> clean checkpoint. PRIMARY = the dense-label checkpoints; CONTROL = KLAVIS's matched
# manual-label run (the released recipe, retrained), reported on its own.
MODELS = {
    "K_ex016_75k": "klavis_dense9um-w016excluded-step075000.pth",
    "K_ex016_60k": "klavis_dense9um-w016excluded-step060000-best.pth",
    "K_all7_75k": "klavis_dense9um-all7-step075000.pth",
    "N_native_16k": "nieuwlaar_dense_native_016000.pth",
    "K_control_75k": "klavis_control-manuallabels-step075000.pth",
}
PRIMARY = ("K_ex016_75k", "K_ex016_60k", "K_all7_75k", "N_native_16k")
CONTROL = ("K_control_75k",)
RULES = ("R0", "R1b", "R2", "R3")
NOISE_FLOOR = 0.03
READING_MARGIN = 0.05   # gate: mean oracle F1 must beat the trivial all-ink F1 by this much


def pred_path(seg: str, model: str) -> Path:
    return PREDS / f"{seg}_{model}.tif"


def infer(args) -> None:
    PREDS.mkdir(parents=True, exist_ok=True)
    for model, ckpt in MODELS.items():
        for seg in SEGMENTS:
            out = pred_path(seg, model)
            if out.exists():
                continue
            cmd = ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", "-m",
                   "koine_machines.inference.infer", str(VOLUMES / f"{seg}.zarr"), str(CLEAN / ckpt), str(out),
                   "--overlap", "0.5", "--blend-mode", "hann", "--batch-size", "4", "--no-compile"]
            t0 = time.time()
            for attempt in range(3):
                proc = subprocess.run(cmd, cwd=RUN_TREE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                      text=True)
                if proc.returncode == 0 and out.exists():
                    break
                print(proc.stderr[-2000:], flush=True)
                time.sleep(30)
            print(f"{seg} {model}: exit {proc.returncode} in {(time.time() - t0) / 60:.1f} min", flush=True)
            if not out.exists():
                sys.exit(f"error: no prediction for {seg} {model}")


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
        for model in MODELS:
            key = f"{seg}|{model}"
            if f"{key}|sheet" in store:
                continue
            p = read_prediction(pred_path(seg, model))
            if p.shape != sheet.shape:
                sys.exit(f"error: {seg} {model} prediction {p.shape} != {sheet.shape}")
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
        for model in MODELS:
            key = f"{seg}|{model}"
            pos, neg = store[f"{key}|pos"], store[f"{key}|neg"]
            curve = f1_curve(pos, neg)
            p = pos.sum() / (pos.sum() + neg.sum())
            cells.append({"scroll": scroll, "segment": seg, "model": model, "curve": curve,
                          "sheet": store[f"{key}|sheet"], "oracle_threshold": int(np.argmax(curve)),
                          "oracle_f1": float(curve.max()), "trivial_floor": float(2 * p / (1 + p))})
    for c in cells:
        donors = [o for o in cells if o["scroll"] != c["scroll"] and o["model"] == c["model"]]
        r1b = round_half_up(float(np.median([o["oracle_threshold"] for o in donors])))
        q = float(np.median([fraction_at_or_above(o["sheet"])[o["oracle_threshold"]] for o in donors]))
        frac = fraction_at_or_above(c["sheet"])
        r3 = int(np.argmax(frac <= q)) if (frac <= q).any() else 255
        c["thresholds"] = {"R0": 128, "R1b": r1b, "R2": otsu(c["sheet"]), "R3": r3}
        for rule, t in c["thresholds"].items():
            c[f"regret_{rule}"] = float(c["curve"].max() - c["curve"][t])

    # reading gate (fixed in advance): a model x scroll whose mean oracle F1 does not beat the trivial
    # all-ink F1 by READING_MARGIN is reported as not reading and dropped from every rule alike
    gate = {}
    for model in MODELS:
        for scroll in SCROLLS:
            sel = [c for c in cells if c["model"] == model and c["scroll"] == scroll]
            margin = float(np.mean([c["oracle_f1"] - c["trivial_floor"] for c in sel]))
            gate[f"{model}|{scroll}"] = {"margin": margin, "reading": margin >= READING_MARGIN}

    def summarise(models):
        out = {}
        for rule in RULES:
            out[rule] = {}
            for scroll in SCROLLS:
                sel = [c for c in cells if c["scroll"] == scroll and c["model"] in models
                       and gate[f"{c['model']}|{scroll}"]["reading"]]
                if not sel:
                    out[rule][scroll] = None
                    continue
                vals = [c[f"regret_{rule}"] for c in sel]
                out[rule][scroll] = {"cells": len(vals), "mean_regret": float(np.mean(vals)),
                                     "max_regret": float(np.max(vals)),
                                     "within_noise": int(sum(v < NOISE_FLOOR for v in vals)),
                                     "threshold_range": [int(min(c["thresholds"][rule] for c in sel)),
                                                         int(max(c["thresholds"][rule] for c in sel))]}
        verdict = {}
        for rule in out:
            ok = [s for s in SCROLLS if out[rule][s] is not None and out[rule][s]["mean_regret"] < NOISE_FLOOR]
            verdict[rule] = {"under_noise_on_all_three": len(ok) == 3, "scrolls_under_noise": ok}
        return out, verdict

    primary, primary_verdict = summarise(PRIMARY)
    control, control_verdict = summarise(CONTROL)
    per_model = {m: summarise((m,)) for m in MODELS}
    oracle = {m: {s: {"oracle_threshold_range": [min(c["oracle_threshold"] for c in cells
                                                     if c["model"] == m and c["scroll"] == s),
                                                 max(c["oracle_threshold"] for c in cells
                                                     if c["model"] == m and c["scroll"] == s)],
                      "mean_oracle_f1": float(np.mean([c["oracle_f1"] for c in cells
                                                       if c["model"] == m and c["scroll"] == s]))}
                  for s in SCROLLS} for m in MODELS}
    summary = {"preregistration": "docs/29_threshold_other_recipes.md (committed before inference)",
               "cells": len(cells), "reading_gate": gate, "oracle": oracle,
               "primary": primary, "primary_verdict": primary_verdict,
               "control": control, "control_verdict": control_verdict,
               "per_model": {m: {"summary": s, "verdict": v} for m, (s, v) in per_model.items()}}
    (OUT / "otherrecipes_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    fields = ["scroll", "segment", "model", "oracle_threshold", "oracle_f1", "trivial_floor"] + \
             [f"t_{r}" for r in RULES] + [f"regret_{r}" for r in RULES]
    with (OUT / "otherrecipes_cells.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for c in cells:
            row = {k: c[k] for k in fields if k in c}
            row.update({f"t_{r}": t for r, t in c["thresholds"].items()})
            for k in ("oracle_f1", "trivial_floor") + tuple(f"regret_{r}" for r in RULES):
                row[k] = f"{c[k]:.6f}"
            writer.writerow(row)
    print(json.dumps({"reading_gate": gate, "primary_verdict": primary_verdict,
                      "control_verdict": control_verdict}, indent=1))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("infer", "collect", "score"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    {"infer": infer, "collect": collect, "score": score}[args.cmd](args)


if __name__ == "__main__":
    main()
