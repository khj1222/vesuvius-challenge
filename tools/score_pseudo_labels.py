#!/usr/bin/env python3
"""Stage 1 of docs/24: score a pseudo-label tree against the withheld annotations.

The open-problems page reports a cross-scroll improvement as a validation Dice computed on
pseudo-labels. This measures the object such a score is computed against: how well the
pseudo-labels themselves agree with the annotations that were withheld from training.

Support matters and is reported rather than assumed. Pseudo-labels only have an opinion where
the base model was confident inside the valid render area; annotations only exist inside the
annotated regions. Agreement is computed **on the intersection of the two supervision masks**,
and the size and positive rate of that intersection are reported beside it, because agreement
over a differently shaped support is a different quantity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import zarr


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pseudo_root", type=Path, help="pseudo-label tree, e.g. .../pseudo1667D_s42")
    p.add_argument("truth_root", type=Path, help="annotation tree, e.g. .../aligned-...-21slices")
    p.add_argument("--out", type=Path, required=True, help="JSON to write")
    p.add_argument("--level", default="0", help="pyramid level to read (default 0)")
    return p.parse_args(argv)


def _open(path: Path, level: str) -> np.ndarray | None:
    if not path.exists():
        return None
    store = zarr.open(str(path), mode="r")
    node = store[level] if level in store else store
    arr = np.asarray(node)
    # (C, H, W) label volumes carry one filled channel; reduce to the 2D plane.
    while arr.ndim > 2:
        arr = arr.max(axis=0)
    return arr


def score_segment(pseudo_dir: Path, truth_dir: Path, segment: str, level: str) -> dict | None:
    pl = _open(pseudo_dir / f"{segment}_inklabels.zarr", level)
    pm = _open(pseudo_dir / f"{segment}_supervision_mask.zarr", level)
    tl = _open(truth_dir / f"{segment}_inklabels.zarr", level)
    tm = _open(truth_dir / f"{segment}_supervision_mask.zarr", level)
    if any(a is None for a in (pl, pm, tl, tm)):
        return None
    if not (pl.shape == pm.shape == tl.shape == tm.shape):
        return {"segment": segment, "error": "shape mismatch",
                "shapes": [list(a.shape) for a in (pl, pm, tl, tm)]}

    pseudo_sup = pm > 0
    truth_sup = tm > 0
    both = pseudo_sup & truth_sup
    n_both = int(both.sum())
    out = {
        "segment": segment,
        "pixels_pseudo_supervised": int(pseudo_sup.sum()),
        "pixels_truth_supervised": int(truth_sup.sum()),
        "pixels_compared": n_both,
        # how much of the annotated area the pseudo-labels have any opinion about
        "coverage_of_annotation": (float(n_both / truth_sup.sum())
                                   if truth_sup.sum() else None),
    }
    if n_both == 0:
        out["error"] = "no overlapping supervision"
        return out

    p = (pl > 0)[both]
    t = (tl > 0)[both]
    tp = int(np.count_nonzero(p & t))
    fp = int(np.count_nonzero(p & ~t))
    fn = int(np.count_nonzero(~p & t))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    out.update({
        "positive_rate_pseudo": float(p.mean()),
        "positive_rate_truth": float(t.mean()),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        # the score a trivial all-positive classifier would get on this support,
        # which is how every number in this project is read (docs/14)
        "trivial_floor_f1": round(2 * float(t.mean()) / (1 + float(t.mean())), 4),
    })
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    segments = sorted(d.name for d in args.pseudo_root.iterdir() if d.is_dir())
    rows = []
    for seg in segments:
        row = score_segment(args.pseudo_root / seg, args.truth_root / seg, seg, args.level)
        if row is None:
            print(f"  {seg}: missing a required array, skipped")
            continue
        rows.append(row)
        if "error" in row:
            print(f"  {seg}: {row['error']}")
        else:
            print(f"  {seg}: F1 {row['f1']:.4f}  (floor {row['trivial_floor_f1']:.4f})  "
                  f"P {row['precision']:.4f} R {row['recall']:.4f}  "
                  f"covers {row['coverage_of_annotation']:.1%} of the annotation")
    scored = [r for r in rows if "f1" in r]
    summary = {
        "pseudo_root": str(args.pseudo_root),
        "truth_root": str(args.truth_root),
        "level": args.level,
        "segments": rows,
        "n_scored": len(scored),
        "mean_f1": round(float(np.mean([r["f1"] for r in scored])), 4) if scored else None,
        "min_f1": round(min(r["f1"] for r in scored), 4) if scored else None,
        "max_f1": round(max(r["f1"] for r in scored), 4) if scored else None,
        "mean_coverage_of_annotation": (
            round(float(np.mean([r["coverage_of_annotation"] for r in scored])), 4)
            if scored else None),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"-> {args.out}  mean F1 {summary['mean_f1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
