#!/usr/bin/env python3
"""score_label_free_threshold.py -- the docs/27 run: can an unseen scroll's threshold be
chosen without its labels?

Pass 1 (``collect``) reads every saved leave-one-scroll-out prediction once and keeps four
256-bin histograms per cell:

* ``pos``/``neg`` -- annotated ink / non-ink pixels inside the supervision mask, each pixel
  counted once (the numbers the rules are judged on);
* ``pos_legacy``/``neg_legacy`` -- the same populations counted the way
  ``eval_validation.py`` counts them (per region bounding box, so overlapping boxes count a
  pixel twice), used only to check that the committed matrices reproduce;
* ``sheet`` -- every pixel of the rendered sheet (middle layer of the surface volume > 0),
  the only population a label-free rule may read.

Pass 2 (``score``) applies the pre-registered rules R0-R3 and writes regret per cell and the
per-scroll summary. Nothing in pass 2 touches a TIFF, so the rules can be audited from the
histogram file alone.

    uv run --project external/villa/ink-detection --no-sync python tools/score_label_free_threshold.py collect
    python tools/score_label_free_threshold.py score

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

PRED_DIR = Path(r"Z:\아카이브\vesuvius-runs\ink9um_scorecard\preds")
LABEL_DIR = ROOT / "data/ink_9um/labels/aligned-scrollprizeorg-21slices"
VOLUME_DIR = ROOT / "data/ink_9um/surface-volumes/aligned9"
OUT_DIR = ROOT / "runs/ink9um_scorecard"
HIST_FILE = OUT_DIR / "labelfree_hists.npz"
CELLS_FILE = OUT_DIR / "labelfree_cells.csv"
SUMMARY_FILE = OUT_DIR / "labelfree_summary.json"

MATRICES = {"phercparis4": "paris4_matrix", "pherc1667": "no1667_matrix", "pherc0139": "no0139_matrix"}
PRIMARY_STEPS = ("010000", "020000")
NOISE_FLOOR = 0.03


def matrix_rows() -> list[dict]:
    """LOSO rows of the three committed matrices, aligned segments only."""
    rows = []
    for scroll, name in MATRICES.items():
        text = subprocess.run(["git", "show", f"HEAD:runs/ink9um_scorecard/{name}.csv"],
                              cwd=ROOT, capture_output=True, text=True, check=True).stdout
        for row in csv.DictReader(io.StringIO(text)):
            if row["arm"] in ("loso42", "loso43") and row["segment"].startswith(scroll + "-"):
                row["scroll"] = scroll
                row["seed"] = row["arm"][-2:]
                rows.append(row)
    return rows


def prediction_path(row: dict) -> Path:
    arm = f"loso0139_{row['seed']}" if row["scroll"] == "pherc0139" else row["arm"]
    return PRED_DIR / f"{row['segment']}_{arm}_{row['step']}.tif"


def collect(args) -> None:
    import zarr
    from eval_validation import find_regions, open_pyramid, read_prediction

    rows = matrix_rows()
    by_segment: dict[str, list[dict]] = {}
    for row in rows:
        by_segment.setdefault(row["segment"], []).append(row)
    print(f"{len(rows)} cells over {len(by_segment)} segments")

    store = dict(np.load(HIST_FILE)) if HIST_FILE.exists() else {}
    for segment, seg_rows in sorted(by_segment.items()):
        todo = [r for r in seg_rows if f"{segment}|{r['seed']}|{r['step']}|sheet" not in store]
        if not todo:
            continue
        t0 = time.time()
        seg_dir = LABEL_DIR / segment
        support = open_pyramid(seg_dir, "supervision_mask")
        inklabels = open_pyramid(seg_dir, "inklabels")
        sup_full = np.asarray(support["0"][support["0"].shape[0] // 2]) > 0
        ink_full = (np.asarray(inklabels["0"][inklabels["0"].shape[0] // 2]) > 0) & sup_full
        bg_full = sup_full & ~ink_full
        volume = zarr.open(str(VOLUME_DIR / f"{segment}.zarr"), mode="r")["0"]
        sheet = np.asarray(volume[volume.shape[0] // 2]) > 0
        regions, _ = find_regions(support)
        boxes = []
        for region in regions:
            y0, y1, x0, x1 = region["bbox"]
            valid = sup_full[y0:y1, x0:x1]
            truth = ink_full[y0:y1, x0:x1]
            boxes.append((y0, y1, x0, x1, truth, valid & ~truth))
        for row in todo:
            prediction = read_prediction(prediction_path(row))
            if prediction.shape != sheet.shape:
                sys.exit(f"error: {prediction_path(row).name} {prediction.shape} != sheet {sheet.shape}")
            key = f"{segment}|{row['seed']}|{row['step']}"
            store[f"{key}|pos"] = np.bincount(prediction[ink_full], minlength=256)
            store[f"{key}|neg"] = np.bincount(prediction[bg_full], minlength=256)
            pos_l = np.zeros(256, np.int64)
            neg_l = np.zeros(256, np.int64)
            for y0, y1, x0, x1, truth, negative in boxes:
                crop = prediction[y0:y1, x0:x1]
                pos_l += np.bincount(crop[truth], minlength=256)
                neg_l += np.bincount(crop[negative], minlength=256)
            store[f"{key}|pos_legacy"] = pos_l
            store[f"{key}|neg_legacy"] = neg_l
            store[f"{key}|sheet"] = np.bincount(prediction[sheet], minlength=256)
        np.savez_compressed(HIST_FILE, **store)
        print(f"{segment}: {len(todo)} cells, sheet {int(sheet.sum()):,} px, "
              f"supervised {int(sup_full.sum()):,} px, {time.time() - t0:.0f}s", flush=True)
    print(f"wrote {HIST_FILE}")


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


def otsu(hist: np.ndarray) -> int:
    """k in 1..255 maximising between-class variance of {<k} vs {>=k}; lowest k on ties."""
    levels = np.arange(256, dtype=float)
    total = hist.sum()
    best_k, best_var = 1, -1.0
    for k in range(1, 256):
        w0, w1 = hist[:k].sum(), hist[k:].sum()
        if w0 == 0 or w1 == 0:
            continue
        m0 = (hist[:k] * levels[:k]).sum() / w0
        m1 = (hist[k:] * levels[k:]).sum() / w1
        var = (w0 / total) * (w1 / total) * (m0 - m1) ** 2
        if var > best_var:
            best_k, best_var = k, var
    return best_k


def round_half_up(value: float) -> int:
    return int(np.floor(value + 0.5))


def score(args) -> None:
    rows = matrix_rows()
    store = np.load(HIST_FILE)
    cells = []
    for row in rows:
        key = f"{row['segment']}|{row['seed']}|{row['step']}"
        pos, neg, sheet = store[f"{key}|pos"], store[f"{key}|neg"], store[f"{key}|sheet"]
        legacy = f1_curve(store[f"{key}|pos_legacy"], store[f"{key}|neg_legacy"])
        curve = f1_curve(pos, neg)
        cells.append({
            **{k: row[k] for k in ("scroll", "segment", "seed", "step")},
            "matrix_threshold": int(row["best_threshold"]), "matrix_f1": float(row["best_f1"]),
            "legacy_threshold": int(np.argmax(legacy)), "legacy_f1": float(legacy.max()),
            "curve": curve, "legacy_curve": legacy, "sheet": sheet,
            "oracle_threshold": int(np.argmax(curve)), "oracle_f1": float(curve.max()),
            "sheet_px": int(sheet.sum()),
        })

    # Reproduction check (pre-registered): threshold exact, F1 within 0.0001.
    for c in cells:
        c["reproduces"] = (c["legacy_threshold"] == c["matrix_threshold"]
                           and abs(c["legacy_f1"] - c["matrix_f1"]) <= 0.0001 + 1e-9)
    failed = [c for c in cells if not c["reproduces"]]
    used = [c for c in cells if c["reproduces"]]

    def others(c, pool):
        return [o for o in pool if o["scroll"] != c["scroll"] and o["step"] == c["step"]]

    for c in used:
        donors = others(c, used)
        r1 = round_half_up(float(np.median([o["oracle_threshold"] for o in donors])))
        q = float(np.median([fraction_at_or_above(o["sheet"])[o["oracle_threshold"]] for o in donors]))
        frac = fraction_at_or_above(c["sheet"])
        r3 = int(np.argmax(frac <= q)) if (frac <= q).any() else 255
        c["thresholds"] = {"R0": 128, "R1": r1, "R2": otsu(c["sheet"]), "R3": r3}
        c["q"] = q
        for curve_name, prefix in (("curve", ""), ("legacy_curve", "legacy_")):
            curve = c[curve_name]
            for rule, t in c["thresholds"].items():
                c[f"{prefix}regret_{rule}"] = float(curve.max() - curve[t])

    def summarise(steps, prefix=""):
        out = {}
        for rule in ("R0", "R1", "R2", "R3"):
            per = {}
            for scroll in MATRICES:
                sel = [c for c in used if c["scroll"] == scroll and c["step"] in steps]
                vals = [c[f"{prefix}regret_{rule}"] for c in sel]
                thr = [c["thresholds"][rule] for c in sel]
                per[scroll] = {"cells": len(vals), "mean_regret": float(np.mean(vals)),
                               "max_regret": float(np.max(vals)),
                               "within_noise": int(sum(v < NOISE_FLOOR for v in vals)),
                               "threshold_range": [int(min(thr)), int(max(thr))]}
            out[rule] = per
        verdict = {}
        for rule in ("R1", "R2", "R3", "R0"):
            ok = all(out[rule][s]["mean_regret"] < NOISE_FLOOR for s in MATRICES)
            beats = all(out[rule][s]["mean_regret"] < out["R0"][s]["mean_regret"] for s in MATRICES)
            n_ok = sum(out[rule][s]["mean_regret"] < NOISE_FLOOR for s in MATRICES)
            verdict[rule] = {"passes": bool(ok and beats and rule != "R0"),
                             "scrolls_under_noise": n_ok, "beats_R0_everywhere": bool(beats)}
        return out, verdict

    all_steps = sorted({c["step"] for c in used})
    primary, primary_verdict = summarise(PRIMARY_STEPS)
    primary_legacy, primary_legacy_verdict = summarise(PRIMARY_STEPS, "legacy_")
    secondary, secondary_verdict = summarise(all_steps)
    oracle = {s: {"cells": len([c for c in used if c["scroll"] == s and c["step"] in PRIMARY_STEPS]),
                  "mean_oracle_f1": float(np.mean([c["oracle_f1"] for c in used
                                                   if c["scroll"] == s and c["step"] in PRIMARY_STEPS])),
                  "oracle_threshold_range": [int(min(c["oracle_threshold"] for c in used
                                                     if c["scroll"] == s and c["step"] in PRIMARY_STEPS)),
                                             int(max(c["oracle_threshold"] for c in used
                                                     if c["scroll"] == s and c["step"] in PRIMARY_STEPS))]}
              for s in MATRICES}
    summary = {
        "preregistration": "docs/27_label_free_threshold.md (commit 1b5917e)",
        "cells_total": len(cells), "cells_reproduced": len(used),
        "reproduction_failures": [{k: c[k] for k in ("segment", "seed", "step", "matrix_threshold",
                                                     "legacy_threshold", "matrix_f1", "legacy_f1")}
                                  for c in failed],
        "sheet_px_range": [min(c["sheet_px"] for c in cells), max(c["sheet_px"] for c in cells)],
        "primary_steps": list(PRIMARY_STEPS), "oracle_primary": oracle,
        "primary": primary, "primary_verdict": primary_verdict,
        "primary_legacy_counting": primary_legacy, "primary_legacy_verdict": primary_legacy_verdict,
        "secondary_all_steps": secondary, "secondary_verdict": secondary_verdict,
    }
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with CELLS_FILE.open("w", newline="", encoding="utf-8") as fh:
        fields = ["scroll", "segment", "seed", "step", "sheet_px", "matrix_threshold", "matrix_f1",
                  "legacy_threshold", "legacy_f1", "reproduces", "oracle_threshold", "oracle_f1", "q",
                  "t_R0", "t_R1", "t_R2", "t_R3", "regret_R0", "regret_R1", "regret_R2", "regret_R3"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for c in cells:
            out = {k: c.get(k, "") for k in fields}
            for rule, t in c.get("thresholds", {}).items():
                out[f"t_{rule}"] = t
            for k in ("oracle_f1", "legacy_f1", "q") + tuple(f"regret_R{i}" for i in range(4)):
                if isinstance(out.get(k), float):
                    out[k] = f"{out[k]:.6f}"
            writer.writerow(out)
    print(json.dumps({k: summary[k] for k in ("cells_total", "cells_reproduced", "primary_verdict")},
                     indent=1))
    print(f"wrote {SUMMARY_FILE} and {CELLS_FILE}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect", help="read predictions once, store histograms")
    sub.add_parser("score", help="apply the pre-registered rules to the stored histograms")
    args = parser.parse_args(argv)
    {"collect": collect, "score": score}[args.cmd](args)


if __name__ == "__main__":
    main()
