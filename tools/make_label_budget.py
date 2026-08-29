#!/usr/bin/env python3
"""Build reduced-annotation copies of a segment's labels.

A fine-tune on one annotated segment closes most of the cross-scroll gap
(``docs/15``), which raises the next question: how much of that one segment do
you actually have to annotate?  This tool answers it by *removing* annotation
rather than simulating it -- it writes label trees that hold a nested subset of
the segment's annotated regions and nothing else, so a training run against one
of them sees exactly the corpus an annotator who stopped early would have left.

The subsets are nested (25% of the annotation is a subset of the 50%), so the
resulting curve reads as "what does the next region buy me", not as a
comparison between unrelated annotation sets.  Regions are kept whole, and
regions closer together than a training patch stay together, for the same
reason ``make_validation_mask.py`` does it: a patch straddling the boundary
would otherwise carry supervision the arm is supposed not to have.

Both the supervision mask and the ink labels are zeroed outside the kept
regions.  Supervision alone would be enough -- the trainer gates the loss on it
-- but zeroing the labels too means no downstream reader can pick up ink the
arm is not entitled to see.

Example
-------
    python tools/make_label_budget.py \
        data/ink_9um/labels/aligned-scrollprizeorg-21slices/phercparis4-w00 \
        --out-root data/ink_9um/labels/labelbudget \
        --keep 0.5 0.25 0.125 --level 0
"""
from __future__ import annotations

import argparse
import itertools
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_validation_mask import (  # noqa: E402
    group_regions,
    group_stats,
    label_regions,
    open_label_pyramid,
    surface_slice,
)

BAND = 128  # rows per streamed write; matches the label chunk height


def nested_subsets(stats, targets, *, total_area, global_density):
    """Pick a nested chain of group subsets, one per target area fraction.

    Each subset is searched exhaustively inside the previous one, scoring on
    how close it lands to the target share of annotated area and on how far its
    ink density drifts from the whole segment's.  Density matters because a
    subset that happened to collect the sparsest regions would understate what
    the annotation budget buys.
    """
    current = [s["group"] for s in stats]
    by_group = {s["group"]: s for s in stats}
    chain = []
    for target in targets:
        best, best_score = None, None
        for size in range(1, len(current) + 1):
            for subset in itertools.combinations(current, size):
                area = sum(by_group[g]["area"] for g in subset)
                if area == 0:
                    continue
                ink = sum(by_group[g]["ink"] for g in subset)
                size_error = abs(area / total_area - target) / target
                density_error = abs(ink / area - global_density) / max(global_density, 1e-9)
                score = size_error + density_error
                if best_score is None or score < best_score:
                    best, best_score = list(subset), score
        if best is None:
            sys.exit(f"error: no subset available for target {target}")
        area = sum(by_group[g]["area"] for g in best)
        ink = sum(by_group[g]["ink"] for g in best)
        chain.append({
            "target_keep": target,
            "groups": best,
            "regions": sorted(r for g in best for r in by_group[g]["regions"]),
            "area": area,
            "ink": ink,
            "achieved_keep": area / total_area,
            "ink_density": ink / area,
        })
        current = best
    return chain


def write_reduced(src_dir: Path, dst_dir: Path, keep2d: np.ndarray, kinds) -> dict:
    """Copy each label pyramid, zeroing everything outside ``keep2d``."""
    import zarr

    dst_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for kind in kinds:
        src = open_label_pyramid(src_dir, kind)
        out_path = dst_dir / f"{dst_dir.name}_{kind}.zarr"
        if out_path.exists():
            shutil.rmtree(out_path)
        dst = zarr.open(str(out_path), mode="w")
        dst.attrs.update(dict(src.attrs))
        kept_voxels = dropped_voxels = 0
        for level in sorted(src.array_keys(), key=int):
            if int(level) != 0:
                sys.exit(f"error: {kind} has level {level}; only single-level trees are handled")
            a = src[level]
            b = dst.create_dataset(
                level, shape=a.shape, chunks=a.chunks, dtype=a.dtype,
                compressor=a.compressor, overwrite=True,
            )
            for y0 in range(0, a.shape[1], BAND):
                y1 = min(y0 + BAND, a.shape[1])
                block = np.asarray(a[:, y0:y1, :])
                keep = keep2d[y0:y1, :][None, :, :]
                masked = np.where(keep, block, 0)
                kept_voxels += int(np.count_nonzero(masked))
                dropped_voxels += int(np.count_nonzero(block)) - int(np.count_nonzero(masked))
                b[:, y0:y1, :] = masked
        report[kind] = {"kept_voxels": kept_voxels, "dropped_voxels": dropped_voxels}
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("segment_dir", type=Path,
                    help="Segment folder holding <name>_supervision_mask.zarr")
    ap.add_argument("--out-root", type=Path, required=True,
                    help="Where the reduced label trees are written")
    ap.add_argument("--keep", type=float, nargs="+", required=True,
                    help="Retained annotation fractions, descending (e.g. 0.5 0.25 0.125)")
    ap.add_argument("--level", type=int, default=0,
                    help="Pyramid level used to plan the split. Default: 0")
    ap.add_argument("--min-gap", type=float, default=256,
                    help="Regions closer than this (planning-level px) stay together. Default: 256")
    ap.add_argument("--dry-run", action="store_true", help="Plan and report, write nothing")
    args = ap.parse_args(argv)

    targets = sorted(args.keep, reverse=True)
    if targets != list(args.keep):
        print(f"note: reordering --keep to descending {targets}")

    seg = args.segment_dir.resolve()
    supervision = open_label_pyramid(seg, "supervision_mask")
    ink_group = open_label_pyramid(seg, "inklabels")
    supervised = surface_slice(supervision, args.level)
    ink = surface_slice(ink_group, args.level)

    labels, count = label_regions(supervised)
    groups = group_regions(labels, count, min_gap_px=args.min_gap)
    stats = group_stats(groups, labels, supervised, ink)
    total_area = sum(s["area"] for s in stats)
    total_ink = sum(s["ink"] for s in stats)
    global_density = total_ink / max(1, total_area)

    print(f"segment          : {seg.name}")
    print(f"planning level   : {args.level} ({supervised.shape[0]}x{supervised.shape[1]})")
    print(f"annotated regions: {count}  ->  {len(groups)} groups (merged below {args.min_gap:g} px)")
    print(f"annotated area   : {total_area:,} px, ink density {global_density:.4f}")

    chain = nested_subsets(stats, targets, total_area=total_area, global_density=global_density)
    previous = set(s["group"] for s in stats)
    for arm in chain:
        assert set(arm["groups"]) <= previous, "subsets must nest"
        previous = set(arm["groups"])
        print(f"\nkeep {arm['target_keep']:.3f} -> achieved {arm['achieved_keep']:.3f}")
        print(f"  groups        : {arm['groups']}  regions {arm['regions']}")
        print(f"  annotated px  : {arm['area']:,}   ink density {arm['ink_density']:.4f}"
              f"  (global {global_density:.4f})")

    if args.dry_run:
        print("\ndry run -- nothing written")
        return 0

    manifest = {
        "segment": seg.name,
        "source": str(seg),
        "level": args.level,
        "min_gap_px": args.min_gap,
        "regions": count,
        "groups": [{k: s[k] for k in ("group", "regions", "area", "ink", "ink_density")}
                   for s in stats],
        "total_area": total_area,
        "global_ink_density": global_density,
        "arms": [],
    }
    for arm in chain:
        name = f"keep{int(round(arm['target_keep'] * 1000)):04d}"
        dst = args.out_root.resolve() / name / seg.name
        keep2d = np.isin(labels, arm["regions"])
        print(f"\nwriting {dst}")
        report = write_reduced(seg, dst, keep2d, ("supervision_mask", "inklabels"))
        for kind, numbers in report.items():
            print(f"  {kind}: kept {numbers['kept_voxels']:,} voxels,"
                  f" dropped {numbers['dropped_voxels']:,}")
        manifest["arms"].append({**arm, "name": name, "path": str(dst), "voxels": report})

    args.out_root.mkdir(parents=True, exist_ok=True)
    out_json = args.out_root.resolve() / f"{seg.name}_label_budget.json"
    out_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
