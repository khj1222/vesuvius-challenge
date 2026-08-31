#!/usr/bin/env python
"""Rank candidate annotation subsets by the model's own disagreement, using no labels.

The pre-registration is docs/20_annotation_targeting.md. This tool performs the part of
it that decides which subsets the arms train on:

  1. rebuild the segment's annotated regions and their groups, exactly as
     tools/make_label_budget.py does (regions closer than one training patch stay
     together, because splitting them would leak across the boundary);
  2. read two predictions of the same segment from two seeds of a base model that never
     saw this scroll, and take the per-pixel disagreement |p_a - p_b|;
  3. average that inside each group's supervised area;
  4. enumerate every subset of groups whose area lands within a tolerance of the target
     budget, and apply the three selection rules fixed in the pre-registration:
     highest mean disagreement, lowest, and one uniform draw with a fixed seed.

Only the images and the model are used. No label is read except to define where the
candidate areas are and to report their density, which is why the report separates the
two: the ranking is label-free, the candidate set is not.

Usage
-----
    python tools/score_annotation_candidates.py \\
        data/ink_9um/labels/aligned-scrollprizeorg-21slices/phercparis4-w00 \\
        --predictions runs/ink9um_scorecard/preds/phercparis4-w00_loso42_020000.tif \\
                      runs/ink9um_scorecard/preds/phercparis4-w00_loso43_020000.tif \\
        --target-keep 0.2072 --tolerance 0.03 \\
        --out runs/ink9um_scorecard/annotation_candidates.json
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_validation_mask import (  # noqa: E402
    group_regions,
    group_stats,
    label_regions,
    open_label_pyramid,
    surface_slice,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("segment_dir", type=Path, help="Segment label directory.")
    parser.add_argument("--predictions", type=Path, nargs=2, required=True,
                        help="Two prediction images of this segment, from two seeds.")
    parser.add_argument("--level", type=int, default=0, help="Label pyramid level (default 0).")
    parser.add_argument("--min-gap-px", type=float, default=256.0,
                        help="Regions closer than this join one group (default 256, one patch).")
    parser.add_argument("--target-keep", type=float, required=True,
                        help="Annotated-area fraction the arms must all spend.")
    parser.add_argument("--tolerance", type=float, default=0.03,
                        help="Admissible distance from the target, in area fraction (default 0.03).")
    parser.add_argument("--random-seed", type=int, default=0, help="Seed for the random arm.")
    parser.add_argument("--reference-groups", type=int, nargs="*", default=None,
                        help="Groups of the already-published arm, excluded from the random draw.")
    parser.add_argument("--out", type=Path, required=True, help="Where to write the report.")
    return parser.parse_args(argv)


def read_prediction(path: Path) -> np.ndarray:
    import tifffile

    image = tifffile.imread(path)
    if image.ndim != 2:
        sys.exit(f"error: expected a 2D prediction at {path}, got shape {image.shape}")
    return image.astype(np.float32) / 255.0


def main(argv=None) -> int:
    args = parse_args(argv)
    segment_dir = args.segment_dir

    supervision = open_label_pyramid(segment_dir, "supervision_mask")
    inklabels = open_label_pyramid(segment_dir, "inklabels")
    supervised = surface_slice(supervision, args.level)
    ink = surface_slice(inklabels, args.level)

    labels, count = label_regions(supervised)
    groups = group_regions(labels, count, min_gap_px=args.min_gap_px)
    stats = group_stats(groups, labels, supervised, ink)
    total_area = sum(entry["area"] for entry in stats)

    predictions = [read_prediction(path) for path in args.predictions]
    if predictions[0].shape != supervised.shape:
        sys.exit(
            f"error: prediction shape {predictions[0].shape} does not match the label plane "
            f"{supervised.shape}"
        )
    disagreement = np.abs(predictions[0] - predictions[1])
    mean_probability = (predictions[0] + predictions[1]) / 2.0
    clipped = np.clip(mean_probability, 1e-6, 1 - 1e-6)
    entropy = -(clipped * np.log2(clipped) + (1 - clipped) * np.log2(1 - clipped))

    for entry in stats:
        mask = np.isin(labels, entry["regions"]) & supervised
        entry["mean_disagreement"] = float(disagreement[mask].mean())
        entry["mean_entropy"] = float(entropy[mask].mean())
        entry["mean_probability"] = float(mean_probability[mask].mean())

    by_group = {entry["group"]: entry for entry in stats}
    admissible = []
    for size in range(1, len(stats) + 1):
        for subset in itertools.combinations(sorted(by_group), size):
            area = sum(by_group[g]["area"] for g in subset)
            fraction = area / total_area
            if abs(fraction - args.target_keep) > args.tolerance:
                continue
            ink_area = sum(by_group[g]["ink"] for g in subset)
            weighted = sum(by_group[g]["area"] * by_group[g]["mean_disagreement"] for g in subset)
            admissible.append({
                "groups": list(subset),
                "area": area,
                "keep": fraction,
                "ink_density": ink_area / max(1, area),
                "mean_disagreement": weighted / max(1, area),
            })
    if not admissible:
        sys.exit("error: no subset lands within the tolerance of the target budget")

    # Pre-registered rules. Ties break on the lower group index, so this is reproducible.
    ordered = sorted(admissible, key=lambda c: (c["mean_disagreement"], c["groups"]))
    selection = {"disagree-min": ordered[0], "disagree-max": ordered[-1]}

    reference = sorted(args.reference_groups) if args.reference_groups else None
    taken = {tuple(c["groups"]) for c in selection.values()}
    if reference is not None:
        taken.add(tuple(reference))
    rng = np.random.default_rng(args.random_seed)
    pool = [c for c in admissible if tuple(c["groups"]) not in taken]
    if not pool:
        sys.exit("error: every admissible subset is already taken by another arm")
    selection["random"] = pool[int(rng.integers(len(pool)))]

    report = {
        "segment": segment_dir.name,
        "level": args.level,
        "min_gap_px": args.min_gap_px,
        "regions": count,
        "groups": len(stats),
        "total_area": total_area,
        "predictions": [str(p) for p in args.predictions],
        "target_keep": args.target_keep,
        "tolerance": args.tolerance,
        "admissible_subsets": len(admissible),
        "group_stats": stats,
        "reference_groups": reference,
        "selection": selection,
        "admissible": sorted(admissible, key=lambda c: -c["mean_disagreement"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(f"regions={count} groups={len(stats)} admissible={len(admissible)}")
    for entry in stats:
        print(
            f"  group {entry['group']}: area={entry['area']:>9,} density={entry['ink_density']:.4f} "
            f"disagreement={entry['mean_disagreement']:.4f} entropy={entry['mean_entropy']:.4f}"
        )
    for name, choice in selection.items():
        print(
            f"  {name:13s} groups={choice['groups']} keep={choice['keep']:.4f} "
            f"density={choice['ink_density']:.4f} disagreement={choice['mean_disagreement']:.4f}"
        )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
