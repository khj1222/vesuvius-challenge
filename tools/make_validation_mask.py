#!/usr/bin/env python3
"""make_validation_mask.py -- carve a reproducible, leak-free held-out region
out of an ink-detection segment.

Why this exists
---------------
The ink-detection pipeline (``koine_machines``) already supports a per-segment
``<name>_validation_mask`` asset: ``data/patch_finding/default.py`` turns every
patch that touches it into a *validation* patch, and ``data/ink_dataset.py``
zeroes those voxels out of the *training* supervision so the two sets never
overlap. ``training/train.py`` then reports Confusion / BalancedAccuracy over
them every ``val_every`` steps.

None of that runs for the tutorial, because the published segments ship only
``_inklabels`` and ``_supervision_mask`` -- no ``_validation_mask``. The result
is a training run with **zero** validation patches: ``val_every`` iterates over
an empty set, ``val_previews/`` stays empty, and the metrics implemented under
``koine_machines/evaluation/metrics/`` (Confusion, BalancedAccuracy, DRD,
pseudo-F-measure) never fire. Anyone following the tutorial therefore has no
quantitative way to say whether a change to the model, the augmentations or the
config made things better or worse.

How the split is made
---------------------
Supervision on these segments is *not* a continuous ribbon. On
``w00_20231016151002`` it is **15 disconnected regions** -- boxes drawn around
annotated letters -- ranging from 1.5% to 20.7% of the supervised area, with ink
densities from 0.11 to 0.44. Two consequences drive the design:

* **Split by region, never by pixel.** A naive rectangular band cuts letters in
  half: the model trains on the left stroke of a letter and is scored on the
  right one, a few pixels away. This tool assigns whole regions.
* **Keep near neighbours together.** Four of those 15 regions sit closer to
  another region than one patch width (104 and 216 px against a 256 px patch),
  so a single training patch could straddle the train/val line. Regions closer
  than ``--min-gap`` are merged into one indivisible *group* before splitting.

Selection is exhaustive over group subsets (there are only a dozen), scored by
how closely the held-out ink density matches the segment as a whole. There is no
RNG: the same segment and options give everybody the same split.

Because the granularity is coarse, ``--folds K`` is provided: it partitions the
groups into K area-balanced folds so a claim can be checked against the spread
of K runs rather than one lucky split.

Usage
-----
    # plan only -- prints the split and writes nothing
    python tools/make_validation_mask.py SEGMENT_DIR --dry-run

    # write <name>_validation_mask.tif (+ .json spec, + preview png)
    python tools/make_validation_mask.py SEGMENT_DIR --preview split.png

    # k-fold: write the mask for fold 0 of 5 (repeat with --fold 1, 2, ...)
    python tools/make_validation_mask.py SEGMENT_DIR --folds 5 --fold 0

    # then convert to zarr with the pipeline's own converter
    uv run --project external/villa/ink-detection \
        python -m koine_machines.preprocessing.create_label_zarrs SEGMENT_DIR

Design notes
------------
* Planning happens on a downsampled pyramid level (default 3, 1/8 scale) so the
  region geometry is faithful but the sweep is quick; the mask itself is written
  at full resolution.
* The mask is intersected with the supervision mask, because validation patches
  use it *as* their supervision (``supervision_mask_override`` in
  ``find_segment_patches``). Unsupervised voxels would otherwise be scored as
  labeled background.
* Output is a **tiled** TIFF. ``create_label_zarrs`` streams level 0 only for
  tiled input (``_get_tiled_tiff_metadata`` -> ``_convert_tiled_tiff``); given a
  striped TIFF it falls back to ``build_pyramid``, which materializes the whole
  65-deep volume and dies with ``Unable to allocate 25.1 GiB``.

Dependencies: numpy, scipy, zarr, tifffile (+ Pillow for --preview). All present
in the ink-detection uv environment; ``--project`` borrows it without changing
the working directory, so relative paths keep resolving from the repo root:

    uv run --project external/villa/ink-detection python tools/make_validation_mask.py ...

License: MIT.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- #
# Segment IO
# --------------------------------------------------------------------------- #
def open_label_pyramid(segment_dir: Path, kind: str):
    """Open ``<segment>/<name>_<kind>.zarr`` as a multiscale group."""
    import zarr

    path = segment_dir / f"{segment_dir.name}_{kind}.zarr"
    if not path.exists():
        sys.exit(f"error: missing {path}")
    return zarr.open(str(path), mode="r")


def surface_slice(group, level: int) -> np.ndarray:
    """Return the labeled z-slice of a label pyramid level as a bool array.

    ``create_label_zarrs`` writes 2-D label images into a 65-deep volume at
    slice 32, and ``find_segment_patches`` reads ``shape[0] // 2`` -- same index.
    """
    array = group[str(level)]
    return np.asarray(array[array.shape[0] // 2]) > 0


# --------------------------------------------------------------------------- #
# Regions -> groups
# --------------------------------------------------------------------------- #
def label_regions(supervised: np.ndarray):
    from scipy import ndimage

    labels, count = ndimage.label(supervised)
    if count == 0:
        sys.exit("error: supervision mask is empty")
    return labels, count


def group_regions(labels: np.ndarray, count: int, *, min_gap_px: float) -> list[list[int]]:
    """Merge regions closer than ``min_gap_px`` (planning-level px) into groups.

    Two regions that close together can fall inside a single training patch, so
    they must land on the same side of the train/val split.
    """
    from scipy import ndimage

    parent = list(range(count + 1))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for region in range(1, count + 1):
        distance = ndimage.distance_transform_edt(labels != region)
        near = (labels > 0) & (labels != region) & (distance < min_gap_px)
        for neighbour in np.unique(labels[near]):
            union(region, int(neighbour))

    groups: dict[int, list[int]] = {}
    for region in range(1, count + 1):
        groups.setdefault(find(region), []).append(region)
    return [sorted(members) for _, members in sorted(groups.items())]


def group_stats(groups, labels, supervised, ink) -> list[dict]:
    stats = []
    for index, members in enumerate(groups):
        mask = np.isin(labels, members)
        area = int(np.count_nonzero(mask & supervised))
        ink_area = int(np.count_nonzero(mask & supervised & ink))
        stats.append({
            "group": index,
            "regions": members,
            "area": area,
            "ink": ink_area,
            "ink_density": ink_area / max(1, area),
        })
    return stats


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
def select_subset(stats: list[dict], *, fraction: float, total_area: int, global_density: float) -> list[int]:
    """Exhaustively pick the group subset that best matches size and ink density."""
    best_subset, best_score = None, None
    indices = range(len(stats))
    for size in range(1, len(stats)):
        for subset in itertools.combinations(indices, size):
            area = sum(stats[i]["area"] for i in subset)
            if area == 0:
                continue
            ink = sum(stats[i]["ink"] for i in subset)
            achieved = area / total_area
            density = ink / area
            size_error = abs(achieved - fraction) / fraction
            density_error = abs(density - global_density) / max(global_density, 1e-9)
            score = size_error + density_error
            if best_score is None or score < best_score:
                best_subset, best_score = list(subset), score
    if best_subset is None:
        sys.exit("error: could not choose a held-out subset")
    return best_subset


def partition_folds(stats: list[dict], folds: int) -> list[list[int]]:
    """Area-balanced partition of groups into folds (largest-first greedy)."""
    assignment: list[list[int]] = [[] for _ in range(folds)]
    totals = [0] * folds
    for stat in sorted(stats, key=lambda s: s["area"], reverse=True):
        target = int(np.argmin(totals))
        assignment[target].append(stat["group"])
        totals[target] += stat["area"]
    return assignment


# --------------------------------------------------------------------------- #
# Mask writing
# --------------------------------------------------------------------------- #
def write_mask_tif(out_path: Path, supervision_group, selection_plan: np.ndarray, *, scale: int) -> dict:
    """Upsample the planning-level selection and intersect it with supervision."""
    import tifffile

    level0 = supervision_group["0"]
    z = level0.shape[0] // 2
    height, width = int(level0.shape[1]), int(level0.shape[2])

    selection = np.repeat(np.repeat(selection_plan, scale, axis=0), scale, axis=1)
    selection = selection[:height, :width]
    if selection.shape != (height, width):
        pad_y = height - selection.shape[0]
        pad_x = width - selection.shape[1]
        selection = np.pad(selection, ((0, max(0, pad_y)), (0, max(0, pad_x))))

    mask = np.zeros((height, width), dtype=np.uint8)
    block = 4096
    for y0 in range(0, height, block):
        y1 = min(height, y0 + block)
        rows = np.asarray(level0[z, y0:y1, :]) > 0
        mask[y0:y1][rows & selection[y0:y1]] = 255

    tifffile.imwrite(out_path, mask, compression="lzw", tile=(256, 256))
    return {"shape": [height, width], "validation_pixels_full_res": int(np.count_nonzero(mask))}


def write_preview(out_path: Path, supervised, ink, selection_plan) -> None:
    """Gray = training region, blue = held out; ink in red / light blue."""
    from PIL import Image

    step = max(1, min(supervised.shape) // 900)
    sup = supervised[::step, ::step]
    ink_s = ink[::step, ::step]
    val = selection_plan[::step, ::step]

    rgb = np.zeros((*sup.shape, 3), dtype=np.uint8)
    rgb[sup] = (70, 70, 70)
    rgb[sup & val] = (30, 80, 160)
    rgb[ink_s & sup & ~val] = (210, 90, 70)
    rgb[ink_s & sup & val] = (120, 190, 255)
    Image.fromarray(rgb).save(out_path)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a leak-free held-out validation mask for an ink-detection segment.",
    )
    parser.add_argument("segment_dir", type=Path, help="Segment folder (holds <name>.zarr etc.)")
    parser.add_argument("--fraction", type=float, default=0.2,
                        help="Target share of supervised area to hold out. Default: 0.2")
    parser.add_argument("--folds", type=int, default=None,
                        help="Partition the groups into K area-balanced folds instead.")
    parser.add_argument("--fold", type=int, default=0, help="Which fold to write (with --folds).")
    parser.add_argument("--level", type=int, default=3,
                        help="Pyramid level used to plan the split. Default: 3")
    parser.add_argument("--min-gap", type=int, default=256,
                        help="Regions closer than this (full-res px) are kept together. "
                             "Default: 256, the patch size.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output TIFF. Default: <segment>/<name>_validation_mask.tif")
    parser.add_argument("--preview", type=Path, default=None, help="Also write a split preview PNG.")
    parser.add_argument("--dry-run", action="store_true", help="Plan and report, write nothing.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing mask.")
    args = parser.parse_args(argv)

    segment_dir = args.segment_dir.resolve()
    if not segment_dir.is_dir():
        sys.exit(f"error: not a directory: {segment_dir}")
    if not 0.0 < args.fraction < 1.0:
        sys.exit("error: --fraction must be in (0, 1)")
    if args.folds is not None and not 2 <= args.folds:
        sys.exit("error: --folds must be at least 2")

    supervision = open_label_pyramid(segment_dir, "supervision_mask")
    inklabels = open_label_pyramid(segment_dir, "inklabels")
    supervised = surface_slice(supervision, args.level)
    ink = surface_slice(inklabels, args.level)
    if supervised.shape != ink.shape:
        sys.exit(f"error: mask shape mismatch {supervised.shape} vs {ink.shape}")

    level0 = supervision["0"]
    planning = supervision[str(args.level)]
    scale = int(round(level0.shape[1] / planning.shape[1]))
    min_gap_plan = args.min_gap / scale

    labels, count = label_regions(supervised)
    groups = group_regions(labels, count, min_gap_px=min_gap_plan)
    stats = group_stats(groups, labels, supervised, ink)
    total_area = sum(stat["area"] for stat in stats)
    total_ink = sum(stat["ink"] for stat in stats)
    global_density = total_ink / max(1, total_area)

    print(f"segment          : {segment_dir.name}")
    print(f"planning level   : {args.level} ({planning.shape[1]}x{planning.shape[2]}, "
          f"full-res {level0.shape[1]}x{level0.shape[2]}, scale {scale}x)")
    print(f"supervised regions: {count}  ->  {len(stats)} groups "
          f"(merged below {args.min_gap} full-res px)")
    print(f"supervised area  : {total_area:,} px @level{args.level}, ink density {global_density:.4f}")

    if args.folds:
        assignment = partition_folds(stats, args.folds)
        if not 0 <= args.fold < args.folds:
            sys.exit(f"error: --fold must be in [0, {args.folds})")
        print(f"\n{args.folds}-fold partition (area-balanced):")
        for index, members in enumerate(assignment):
            area = sum(stats[m]["area"] for m in members)
            ink_area = sum(stats[m]["ink"] for m in members)
            marker = " <- selected" if index == args.fold else ""
            print(f"  fold {index}: groups {members}  area {area:,} "
                  f"({100 * area / total_area:.1f}%)  ink {ink_area / max(1, area):.4f}{marker}")
        selected = assignment[args.fold]
        split_kind = f"fold {args.fold} of {args.folds}"
    else:
        selected = select_subset(stats, fraction=args.fraction, total_area=total_area,
                                 global_density=global_density)
        split_kind = f"single split (target {args.fraction:.2f})"

    val_area = sum(stats[i]["area"] for i in selected)
    val_ink = sum(stats[i]["ink"] for i in selected)
    train_area = total_area - val_area
    train_ink = total_ink - val_ink

    print(f"\nheld out         : {split_kind}")
    print(f"  groups         : {selected}  "
          f"(regions {[r for i in selected for r in stats[i]['regions']]})")
    print(f"  fraction       : {val_area / total_area:.3f} of supervised area")
    print(f"  ink density    : global {global_density:.4f} | "
          f"train {train_ink / max(1, train_area):.4f} | val {val_ink / max(1, val_area):.4f}")
    print(f"  supervised px  : train {train_area:,} | val {val_area:,} (@level{args.level})")

    selection_plan = np.isin(labels, [region for i in selected for region in stats[i]["regions"]])

    if args.dry_run:
        print("\ndry run -- nothing written")
        return 0

    out_path = args.out or (segment_dir / f"{segment_dir.name}_validation_mask.tif")
    if out_path.exists() and not args.force:
        sys.exit(f"error: {out_path} exists (use --force to overwrite)")

    print(f"\nwriting {out_path} ...")
    written = write_mask_tif(out_path, supervision, selection_plan, scale=scale)
    print(f"  {written['shape'][0]}x{written['shape'][1]}, "
          f"{written['validation_pixels_full_res']:,} validation px")

    spec = {
        "tool": "make_validation_mask.py",
        "segment": segment_dir.name,
        "split": split_kind,
        "planning_level": args.level,
        "min_gap_full_res_px": args.min_gap,
        "supervised_regions": count,
        "groups": len(stats),
        "held_out_groups": selected,
        "held_out_regions": [region for i in selected for region in stats[i]["regions"]],
        "achieved_fraction_of_supervised_area": round(val_area / total_area, 6),
        "ink_density": {
            "global": round(global_density, 6),
            "train": round(train_ink / max(1, train_area), 6),
            "validation": round(val_ink / max(1, val_area), 6),
        },
        "group_table": [
            {k: (round(v, 6) if isinstance(v, float) else v) for k, v in stat.items()}
            for stat in stats
        ],
        **written,
    }
    sidecar = out_path.with_suffix(".json")
    sidecar.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"  spec -> {sidecar}")

    if args.preview:
        write_preview(args.preview, supervised, ink, selection_plan)
        print(f"  preview -> {args.preview}")

    print(
        "\nnext: convert to zarr so the loader picks it up --\n"
        "  uv run --project external/villa/ink-detection \\\n"
        "      python -m koine_machines.preprocessing.create_label_zarrs "
        f"{segment_dir}\n"
        "  (and train into a FRESH out_dir: the patch cache is keyed by asset\n"
        "   *paths*, so an existing run dir would reuse its stale patch list)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
