"""Apply the docs/25 v2 gate to every scouting score file and print the scorecard.

Gate (docs/25 section 9): on the seed42-vs-seed43 step-20,000 pair, whole-sheet top-decile
IoU >= 0.229 AND window IoU >= 0.405, evaluated on the target's responsive orientation (the
orientation with the higher whole-sheet IoU; if the two orientations are within 0.03 the
target is "indifferent" = no signal). Collapse guard: released-checkpoint median <= 75 and
low-third share >= 0.80 on the responsive orientation demotes.

Usage: python tools/summarise_scouting.py [--out runs/scouting/scorecard.json]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

SCORES = Path("runs/scouting/scores")
GATE_SHEET = 0.229
GATE_WINDOW = 0.405
INDIFFERENT = 0.03


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("runs/scouting/scorecard.json"))
    args = ap.parse_args()

    by_target: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in sorted(SCORES.glob("*__seed42_020000.json")):
        d = json.loads(f.read_text())
        name = d["name"]
        if "__" not in name:
            continue  # pre-v2 files (references/controls without an orientation tag)
        target, variant = name.rsplit("__", 1)
        by_target[target][variant] = d

    rows = []
    for target, variants in sorted(by_target.items()):
        if "flipnormals" not in variants:
            continue
        fn = variants["flipnormals"]
        zf = variants.get("zflip")
        c2_fn = fn["C2_top_decile_iou_sheet"]
        c2_zf = zf["C2_top_decile_iou_sheet"] if zf else None
        if zf and abs(c2_fn - c2_zf) < INDIFFERENT:
            orientation = "indifferent"
            best = fn if c2_fn >= c2_zf else zf
        else:
            orientation = "flipnormals" if (zf is None or c2_fn >= c2_zf) else "zflip"
            best = fn if orientation == "flipnormals" else zf
        g = best["guards"][best["primary"]]
        collapsed = g["median"] <= 75 and best["C3_thirds"]["low"] >= 0.80
        gate = (best["C2_top_decile_iou_sheet"] >= GATE_SHEET
                and best["C2_top_decile_iou_window"] >= GATE_WINDOW)
        candidate = gate and orientation != "indifferent" and not collapsed
        rows.append({
            "target": target,
            "orientation": orientation,
            "c2_sheet_flipnormals": round(c2_fn, 3),
            "c2_sheet_zflip": round(c2_zf, 3) if c2_zf is not None else None,
            "c2_sheet_best": round(best["C2_top_decile_iou_sheet"], 3),
            "c2_window_best": round(best["C2_top_decile_iou_window"], 3),
            "gt128_share": round(g["gt128_share"], 3),
            "median": g["median"],
            "low_third": round(best["C3_thirds"]["low"], 3),
            "ckpt_ratio": round(best["guard_gt128_ratio_max_over_min"] or 0, 2),
            "sheet_share": round(best["sheet_share_of_canvas"], 3),
            "collapsed": collapsed,
            "gate": gate,
            "candidate": candidate,
        })

    print(f"{'target':62} {'orient':12} {'C2 fn':>6} {'C2 zf':>6} {'C2win':>6} {'>128':>6} {'med':>4} {'low3':>5} {'ratio':>5} gate cand")
    for r in rows:
        zf = f"{r['c2_sheet_zflip']:6.3f}" if r["c2_sheet_zflip"] is not None else "     -"
        print(f"{r['target'][:62]:62} {r['orientation']:12} {r['c2_sheet_flipnormals']:6.3f} {zf} "
              f"{r['c2_window_best']:6.3f} {r['gt128_share']:6.3f} {r['median']:4d} {r['low_third']:5.3f} "
              f"{r['ckpt_ratio']:5.2f} {'PASS' if r['gate'] else 'fail'} {'YES' if r['candidate'] else 'no'}"
              f"{'  COLLAPSED' if r['collapsed'] else ''}")
    n = len(rows)
    print(f"\n{n} targets scored, {sum(r['gate'] for r in rows)} pass the C2 gate, "
          f"{sum(r['candidate'] for r in rows)} candidates, "
          f"{sum(r['orientation'] == 'indifferent' for r in rows)} orientation-indifferent, "
          f"{sum(r['collapsed'] for r in rows)} collapsed")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"gate": {"sheet": GATE_SHEET, "window": GATE_WINDOW,
                                             "indifferent": INDIFFERENT}, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
