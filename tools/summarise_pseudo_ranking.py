#!/usr/bin/env python3
"""Apply docs/24's pre-registered decision rule to the two-yardstick matrix.

The rule, fixed in `docs/24_pseudo_label_validation.md` before any cell was computed:

    For each segment and seed, let truth pick the step with the highest F1 against the
    withheld annotation, and let pseudo pick the step with the highest F1 against the
    pseudo-labels. The penalty is what truth says you lost by taking pseudo's pick.

    penalty > 0.03 in BOTH seeds  -> "they disagree"
    selections match, or penalty < 0.03  -> "they agree"
    anything else                        -> "not captured" (no spinning a split result)

0.03 is this project's noise floor, established in July by evaluating one configuration
four times. The verdict is refused on an incomplete matrix, because a rule applied to
whichever cells happen to have finished is not the rule that was registered.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = REPO / "runs" / "ink9um_scorecard" / "pseudo_rank_matrix.csv"
NOISE = 0.03
EXPECTED_STEPS = ["002500", "005000", "010000"]
EXPECTED_SEEDS = [42, 43]
EXPECTED_SEGMENTS = ["pherc1667-w013", "pherc1667-w023", "pherc1667-w028",
                     "pherc1667-w029", "pherc1667-w031"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    parser.add_argument("--out", type=Path,
                        default=REPO / "runs" / "ink9um_scorecard" / "pseudo_rank_summary.json")
    parser.add_argument("--allow-partial", action="store_true",
                        help="describe what is there without rendering the verdict")
    args = parser.parse_args(argv)

    with args.matrix.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    cell: dict[tuple, dict] = defaultdict(dict)
    for r in rows:
        key = (int(r["seed"]), r["segment"], r["step"])
        cell[key][r["yardstick"]] = {"f1": float(r["best_f1"]),
                                     "threshold": int(r["best_threshold"])}

    want = {(s, g, t) for s in EXPECTED_SEEDS for g in EXPECTED_SEGMENTS
            for t in EXPECTED_STEPS}
    complete = {k for k, v in cell.items() if {"truth", "pseudo"} <= v.keys()}
    missing = sorted(want - complete)

    per_segment = []
    for segment in EXPECTED_SEGMENTS:
        entry: dict = {"segment": segment, "seeds": {}}
        for seed in EXPECTED_SEEDS:
            steps = [t for t in EXPECTED_STEPS if (seed, segment, t) in complete]
            if len(steps) < len(EXPECTED_STEPS):
                entry["seeds"][str(seed)] = {"incomplete": True, "have": steps}
                continue
            truth = {t: cell[(seed, segment, t)]["truth"] for t in steps}
            pseudo = {t: cell[(seed, segment, t)]["pseudo"] for t in steps}
            truth_pick = max(steps, key=lambda t: truth[t]["f1"])
            pseudo_pick = max(steps, key=lambda t: pseudo[t]["f1"])
            penalty = truth[truth_pick]["f1"] - truth[pseudo_pick]["f1"]
            entry["seeds"][str(seed)] = {
                "truth_pick": truth_pick, "pseudo_pick": pseudo_pick,
                "same_pick": truth_pick == pseudo_pick,
                "penalty_in_truth_f1": round(penalty, 4),
                "truth_f1_by_step": {t: truth[t]["f1"] for t in steps},
                "pseudo_f1_by_step": {t: pseudo[t]["f1"] for t in steps},
                # not part of the rule; recorded because it is what an operator would set
                "threshold_gap": {t: pseudo[t]["threshold"] - truth[t]["threshold"]
                                  for t in steps},
            }
        both = [v for v in entry["seeds"].values() if "penalty_in_truth_f1" in v]
        if len(both) == len(EXPECTED_SEEDS):
            if all(v["penalty_in_truth_f1"] > NOISE for v in both):
                entry["verdict"] = "disagree"
            elif all(v["same_pick"] or v["penalty_in_truth_f1"] < NOISE for v in both):
                entry["verdict"] = "agree"
            else:
                entry["verdict"] = "not captured"
        per_segment.append(entry)

    summary = {
        "rule": "docs/24: penalty > 0.03 in both seeds -> disagree; matching picks or "
                "penalty < 0.03 -> agree; otherwise not captured",
        "noise_floor": NOISE,
        "cells_complete": len(complete), "cells_expected": len(want),
        "missing_cells": [f"s{s}_{g}_{t}" for s, g, t in missing],
        "per_segment": per_segment,
    }
    verdicts = [e.get("verdict") for e in per_segment if e.get("verdict")]
    if missing and not args.allow_partial:
        summary["verdict"] = None
        summary["verdict_withheld_because"] = (
            f"{len(missing)} of {len(want)} cells are missing; the registered rule is over the "
            "whole matrix, and applying it to whichever cells finished is a different rule")
    else:
        summary["verdict_by_segment"] = verdicts
        summary["segments_disagreeing"] = verdicts.count("disagree")
        summary["segments_agreeing"] = verdicts.count("agree")
        summary["segments_not_captured"] = verdicts.count("not captured")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"cells {len(complete)}/{len(want)}")
    for e in per_segment:
        print(f"  {e['segment']:16s} {e.get('verdict', '(incomplete)')}")
        for seed, v in e["seeds"].items():
            if "penalty_in_truth_f1" in v:
                print(f"    s{seed}: truth picks {v['truth_pick']}, pseudo picks "
                      f"{v['pseudo_pick']}, penalty {v['penalty_in_truth_f1']:+.4f}")
    if summary.get("verdict_withheld_because"):
        print(f"VERDICT WITHHELD: {summary['verdict_withheld_because']}")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
