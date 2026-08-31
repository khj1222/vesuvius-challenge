#!/usr/bin/env python
"""Apply the pre-registered decision rule of docs/20 to the annotation-targeting matrix.

The `density` arm is not re-run: it is the published `keep0250` arm of the label-efficiency
matrix, read from the same CSV it was published in, at the same step. The three new arms come
from `annotarget_matrix.csv`.

The rule, fixed before the arms ran:

    spread = highest arm mean - lowest arm mean, over the seven segments the base never saw
    spread < 0.03  -> at this budget the choice of regions does not change the result
    spread >= 0.03 -> report the ordering; claim an acquisition effect only if
                      disagree-max beats disagree-min in BOTH seeds by at least 0.03

Usage
-----
    python tools/summarise_annotation_targeting.py
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics

REPO = Path(__file__).resolve().parent.parent
SCORECARD = REPO / "runs" / "ink9um_scorecard"
NEW_MATRIX = SCORECARD / "annotarget_matrix.csv"
PUBLISHED = SCORECARD / "labelbudget_matrix.csv"
CANDIDATES = SCORECARD / "annotation_candidates.json"
OUT = SCORECARD / "annotarget_summary.json"

STEP = "002500"
NOISE = 0.03
ARM_LABEL = {
    "keep0250": "density",
    "disagreemax": "disagree-max",
    "disagreemin": "disagree-min",
    "randomsel": "random",
}


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--allow-partial", action="store_true",
                        help="Summarise what exists instead of refusing an incomplete matrix.")
    args = parser.parse_args(argv)

    rows = [r for r in read(NEW_MATRIX) if r["step"] == STEP]
    rows += [r for r in read(PUBLISHED) if r["step"] == STEP and r["arm"] == "keep0250"]

    cells: dict[tuple[str, str], dict[str, float]] = {}
    for row in rows:
        cells.setdefault((ARM_LABEL.get(row["arm"], row["arm"]), row["seed"]), {})[row["segment"]] = float(row["best_f1"])

    segments = sorted({segment for values in cells.values() for segment in values})
    arms = sorted({arm for arm, _ in cells}, key=lambda a: list(ARM_LABEL.values()).index(a)
                  if a in ARM_LABEL.values() else 99)

    incomplete = [(arm, seed, len(values)) for (arm, seed), values in sorted(cells.items())
                  if len(values) != len(segments)]
    if incomplete and not args.allow_partial:
        print("matrix is incomplete; not applying the rule:")
        for arm, seed, count in incomplete:
            print(f"  {arm} seed {seed}: {count}/{len(segments)} segments")
        return 1

    report: dict[str, object] = {
        "step": STEP,
        "segments": segments,
        "noise_floor": NOISE,
        "per_arm": {},
        "per_segment": {},
    }
    if CANDIDATES.exists():
        candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
        report["selection"] = {
            name: {k: choice[k] for k in ("groups", "keep", "ink_density", "mean_disagreement")}
            for name, choice in candidates["selection"].items()
        }

    means: dict[str, float] = {}
    for arm in arms:
        per_seed = {}
        for seed in ("42", "43"):
            values = cells.get((arm, seed))
            if values:
                per_seed[seed] = round(statistics.fmean(values.values()), 4)
        arm_mean = round(statistics.fmean(per_seed.values()), 4) if per_seed else None
        means[arm] = arm_mean
        report["per_arm"][arm] = {
            "per_seed_mean": per_seed,
            "mean": arm_mean,
            "seed_abs_diff": (round(abs(per_seed["42"] - per_seed["43"]), 4)
                              if len(per_seed) == 2 else None),
        }

    for segment in segments:
        report["per_segment"][segment] = {
            arm: round(statistics.fmean([cells[(arm, s)][segment] for s in ("42", "43")
                                         if (arm, s) in cells and segment in cells[(arm, s)]]), 4)
            for arm in arms
            if any((arm, s) in cells and segment in cells[(arm, s)] for s in ("42", "43"))
        }

    # how often each arm is the best on a segment, and the two confounds named in docs/20
    wins = {arm: 0 for arm in arms}
    for segment, values in report["per_segment"].items():
        wins[max(values, key=values.get)] += 1
    report["segment_wins"] = wins

    facts = dict(report.get("selection", {}))
    facts.setdefault("density", {"keep": 0.2072, "ink_density": 0.2462, "mean_disagreement": None})
    report["arm_facts"] = {
        arm: {
            "keep": facts.get(arm, {}).get("keep"),
            "ink_density": facts.get(arm, {}).get("ink_density"),
            "mean_disagreement": facts.get(arm, {}).get("mean_disagreement"),
            "mean_f1": means[arm],
        }
        for arm in arms
    }
    ordered_by_f1 = [a for a, _ in sorted(means.items(), key=lambda kv: -(kv[1] or 0))]
    with_keep = [a for a in arms if report["arm_facts"][a]["keep"]]
    with_density = [a for a in arms if report["arm_facts"][a]["ink_density"]]
    report["confound_checks"] = {
        "ordered_by_f1": ordered_by_f1,
        "ordered_by_keep": sorted(with_keep, key=lambda a: -report["arm_facts"][a]["keep"]),
        "ordered_by_ink_density": sorted(with_density,
                                         key=lambda a: -report["arm_facts"][a]["ink_density"]),
        "most_annotation_arm": max(with_keep, key=lambda a: report["arm_facts"][a]["keep"]),
        "best_arm": ordered_by_f1[0],
    }

    ranked = sorted((m for m in means.values() if m is not None))
    spread = round(ranked[-1] - ranked[0], 4) if len(ranked) > 1 else None
    report["spread"] = spread
    report["ordering"] = [a for a, _ in sorted(means.items(), key=lambda kv: -(kv[1] or 0))]

    # the acquisition test, both seeds, as pre-registered
    per_seed_gap = {}
    for seed in ("42", "43"):
        high = cells.get(("disagree-max", seed))
        low = cells.get(("disagree-min", seed))
        if high and low:
            per_seed_gap[seed] = round(statistics.fmean(high.values()) - statistics.fmean(low.values()), 4)
    report["disagree_max_minus_min_per_seed"] = per_seed_gap
    acquisition = (len(per_seed_gap) == 2 and all(g >= NOISE for g in per_seed_gap.values()))
    report["acquisition_effect_claimed"] = acquisition

    if spread is None:
        verdict = "not enough arms to judge"
    elif spread < NOISE:
        verdict = ("At this budget the choice of regions does not change the result: the four "
                   f"arms span {spread:.4f} F1, inside the {NOISE} noise floor.")
    elif acquisition:
        verdict = (f"The choice matters (spread {spread:.4f}) and the ranking captures it: "
                   f"disagree-max beats disagree-min in both seeds "
                   f"({per_seed_gap['42']:+.4f}, {per_seed_gap['43']:+.4f}).")
    else:
        verdict = (f"The choice matters (spread {spread:.4f}) but our ranking does not capture "
                   f"it: the disagree-max minus disagree-min gap is {per_seed_gap}, which does "
                   f"not clear {NOISE} in both seeds.")
    report["verdict"] = verdict

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(f"step {STEP}, {len(segments)} segments, noise floor {NOISE}\n")
    print(f"{'arm':14s} {'seed 42':>8s} {'seed 43':>8s} {'mean':>8s} {'|Δseed|':>8s}")
    for arm in arms:
        entry = report["per_arm"][arm]
        per_seed = entry["per_seed_mean"]
        print(f"{arm:14s} {per_seed.get('42', float('nan')):8.4f} "
              f"{per_seed.get('43', float('nan')):8.4f} "
              f"{entry['mean']:8.4f} {entry['seed_abs_diff'] or float('nan'):8.4f}")
    print()
    print(f"{'arm':14s} {'keep':>8s} {'density':>8s} {'disagree':>9s} {'mean F1':>8s} {'wins':>5s}")
    for arm in arms:
        facts_row = report["arm_facts"][arm]
        print(f"{arm:14s} {facts_row['keep'] or float('nan'):8.4f} "
              f"{facts_row['ink_density'] or float('nan'):8.4f} "
              f"{facts_row['mean_disagreement'] or float('nan'):9.4f} "
              f"{facts_row['mean_f1']:8.4f} {report['segment_wins'][arm]:5d}")
    print(f"\nspread {spread}   ordering {report['ordering']}")
    print(f"disagree-max minus disagree-min per seed: {per_seed_gap}")
    print(f"\nVERDICT: {verdict}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
