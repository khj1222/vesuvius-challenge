#!/usr/bin/env python
"""make_label_version.py -- write a depth-resolved label version of a segment.

The published ink assets hold one annotated plane: ``_inklabels.zarr`` is
(65, H, W) with a single non-zero z, and so is ``_supervision_mask.zarr``. That
is enough for the flat pipeline's default target, which collapses z anyway, but
it cannot supervise *where along the normal* the ink sits. villa #192 asks for
labels that can.

This tool packages one such label as a **label version**, the mechanism villa's
``Segment.discover_labels`` already understands: assets named ``_v2``, ``_v3``,
... alongside the published ``v1``, selected with ``"label_version": "v2"`` in
the training config. Nothing is overwritten, and a run that does not ask for a
version still sees exactly the published data.

Three bands are available, and they are meant to be compared against each other
with the same folds and seed -- one is the honest control for the next:

``plane``
    The annotated plane, extruded nowhere. This is what today's assets carry;
    as a 3D target it says "ink is exactly one voxel thick, at the surface".
``constant``
    A fixed band around the surface, matching what ``full_3d`` builds today
    (``_DEFAULT_FULL_3D_PROJECTION_HALF_THICKNESS``) but with the thickness this
    segment actually measured. Separates "thicker label" from "measured label":
    if this arm captures the whole gain, depth localization bought nothing.
``measured``
    The per-pixel band from ``_inkdepth.zarr`` (see make_3d_labels.py), which
    moves with the sheet -- region centers span z 29-40 on this segment.

All three get the same supervision geometry, which is the point: a column of
+-``--supervision-half-depth`` voxels around the annotated plane, at annotated
pixels only. Without that column the off-plane voxels are unsupervised and the
bands are indistinguishable to the loss. The column stops well short of the
volume's edge on purpose -- the far end of the flat volume drifts into the
neighbouring wrap, and calling that "background" would be a claim this tool
cannot support.

The validation mask is extruded through the same column. It has to be: the
trainer zeroes held-out voxels out of the training supervision voxel by voxel,
so a plane-only validation mask would leak every off-plane voxel of the held-out
letters back into training.

Usage
-----

    # inspect what would be written
    python tools/make_label_version.py SEGMENT_DIR --version 4 --band measured --dry-run

    # the three arms of the comparison
    python tools/make_label_version.py SEGMENT_DIR --version 2 --band plane
    python tools/make_label_version.py SEGMENT_DIR --version 3 --band constant
    python tools/make_label_version.py SEGMENT_DIR --version 4 --band measured

Then train with ``"label_version": "v4"`` and ``"flat_depth_targets": true``.

Needs zarr/numpy, so run it in the ink-detection environment:

    uv run --project external/villa/ink-detection python tools/make_label_version.py ...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import zarr
except ImportError:  # pragma: no cover - guidance is the whole point
    sys.exit("error: zarr is missing. Run this with "
             "`uv run --project external/villa/ink-detection python tools/make_label_version.py ...`")

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, **_kwargs):
        return iterable


BANDS = ("plane", "constant", "measured")
TILE = 1024
SCAN_LEVEL = 3


# --------------------------------------------------------------------------- #
# Reading the published assets
# --------------------------------------------------------------------------- #
def open_asset(segment_dir: Path, kind: str, *, required: bool = True):
    path = segment_dir / f"{segment_dir.name}_{kind}.zarr"
    if not path.exists():
        if required:
            sys.exit(f"error: {path} not found")
        return None
    return zarr.open(str(path), mode="r")


def annotated_plane(group) -> int:
    """The one z index the published labels actually fill."""
    coarse = np.asarray(group[str(SCAN_LEVEL)])
    filled = np.flatnonzero(coarse.reshape(coarse.shape[0], -1).any(axis=1))
    if filled.size == 0:
        sys.exit("error: the label asset is empty")
    if filled.size > 1:
        sys.exit(f"error: expected a single annotated plane, found z={filled.tolist()}")
    return int(filled[0])


def occupied_tiles(group, plane: int, *, height: int, width: int) -> list[tuple[int, int]]:
    """Tile origins whose annotated footprint is non-empty, found on level 3."""
    factor = 2 ** SCAN_LEVEL
    coarse = np.asarray(group[str(SCAN_LEVEL)][plane]) > 0
    tiles = []
    for y0 in range(0, height, TILE):
        for x0 in range(0, width, TILE):
            cy0, cx0 = y0 // factor, x0 // factor
            cy1 = min(coarse.shape[0], (y0 + TILE) // factor + 1)
            cx1 = min(coarse.shape[1], (x0 + TILE) // factor + 1)
            if cy1 > cy0 and cx1 > cx0 and coarse[cy0:cy1, cx0:cx1].any():
                tiles.append((y0, x0))
    return tiles


# --------------------------------------------------------------------------- #
# Zarr output -- the pyramid geometry of the published labels, level for level
# --------------------------------------------------------------------------- #
def multiscale_attrs(name: str, levels: int) -> dict:
    return {
        "multiscales": [{
            "axes": [{"name": "z", "type": "space"},
                     {"name": "y", "type": "space"},
                     {"name": "x", "type": "space"}],
            "datasets": [
                {"path": str(level),
                 "coordinateTransformations": [
                     {"type": "scale", "scale": [1.0, float(2 ** level), float(2 ** level)]}]}
                for level in range(levels)
            ],
            "name": name,
            "version": "0.4",
        }]
    }


def create_label_pyramid(path: Path, reference_group, name: str) -> dict[int, "zarr.Array"]:
    root = zarr.open(str(path), mode="w")
    arrays = {}
    for key in sorted(reference_group.array_keys(), key=int):
        reference = reference_group[key]
        array = root.create_dataset(
            key,
            shape=tuple(int(v) for v in reference.shape),
            chunks=tuple(int(v) for v in reference.chunks),
            dtype="uint8",
            compressor=reference.compressor,
            overwrite=True,
        )
        array.attrs["_ARRAY_DIMENSIONS"] = ["z", "y", "x"]
        arrays[int(key)] = array
    root.attrs.update(multiscale_attrs(name, len(arrays)))
    return arrays


def downsample_block(block: np.ndarray, factor: int) -> np.ndarray:
    """Max-pool in plane only; z is not downsampled in these pyramids."""
    if factor == 1:
        return block
    depth, height, width = block.shape
    pad_y = (-height) % factor
    pad_x = (-width) % factor
    if pad_y or pad_x:
        block = np.pad(block, ((0, 0), (0, pad_y), (0, pad_x)))
    block = block.reshape(depth, block.shape[1] // factor, factor, block.shape[2] // factor, factor)
    return block.max(axis=(2, 4))


def write_block(arrays: dict[int, "zarr.Array"], block: np.ndarray, y0: int, x0: int) -> None:
    for level, array in arrays.items():
        factor = 2 ** level
        reduced = downsample_block(block, factor)
        ly0, lx0 = y0 // factor, x0 // factor
        ly1 = min(int(array.shape[1]), ly0 + reduced.shape[1])
        lx1 = min(int(array.shape[2]), lx0 + reduced.shape[2])
        if ly1 <= ly0 or lx1 <= lx0:
            continue
        existing = np.asarray(array[:, ly0:ly1, lx0:lx1])
        array[:, ly0:ly1, lx0:lx1] = np.maximum(existing, reduced[:, :ly1 - ly0, :lx1 - lx0])


# --------------------------------------------------------------------------- #
# Per-fold refresh
# --------------------------------------------------------------------------- #
def refresh_validation(segment_dir: Path, *, version: int, dry_run: bool) -> int:
    """Rewrite one version's validation mask from the current v1 mask.

    Cross-validation swaps the held-out split between folds while the labels
    stay put, so re-deriving the whole version each time would be ten minutes of
    rewriting identical voxels. The column geometry comes from the report the
    version was written with, which is also what keeps the refreshed mask
    aligned with the supervision it has to cancel."""
    name = segment_dir.name
    suffix = f"_v{version}"
    report_path = segment_dir / f"{name}_labels{suffix}.json"
    if not report_path.exists():
        sys.exit(f"error: {report_path} not found; write the version first")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    validation = open_asset(segment_dir, "validation_mask", required=False)
    if validation is None:
        sys.exit("error: no published validation mask to extrude")

    plane = int(report["annotation_plane"])
    half_depth = float(report["supervision_half_depth"])
    depth, height, width = (int(v) for v in validation["0"].shape)
    z_axis = np.arange(depth, dtype=np.float32)[:, None, None]
    column = np.abs(z_axis - float(plane)) <= half_depth

    tiles = occupied_tiles(validation, plane, height=height, width=width)
    print(f"refreshing {name}_validation_mask{suffix}.zarr "
          f"from {len(tiles)} tiles, column z {plane - half_depth:.0f}..{plane + half_depth:.0f}")
    if dry_run:
        print("--dry-run: nothing written")
        return 0

    out_path = segment_dir / f"{name}_validation_mask{suffix}.zarr"
    arrays = create_label_pyramid(out_path, validation, f"{name}_validation_mask{suffix}")
    held_out_voxels = 0
    for y0, x0 in tqdm(tiles, desc="Refresh", unit="tile"):
        y1, x1 = min(height, y0 + TILE), min(width, x0 + TILE)
        held_out = np.asarray(validation["0"][plane, y0:y1, x0:x1]) > 0
        if not held_out.any():
            continue
        held_out_column = column & held_out[None]
        held_out_voxels += int(held_out_column.sum())
        write_block(arrays, np.where(held_out_column, np.uint8(255), np.uint8(0)), y0, x0)

    report["validation_voxels"] = held_out_voxels
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nheld-out voxels  : {held_out_voxels:,}")
    return 0


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Write a depth-resolved label version (_vN assets) for a segment.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("segment_dir", type=Path, help="Segment folder holding the published labels.")
    parser.add_argument("--version", type=int, required=True,
                        help="Label version to write. v1 is the published data and is refused.")
    parser.add_argument("--band", choices=BANDS, default=None,
                        help="How the label extends along z. Required unless --refresh-validation.")
    parser.add_argument("--supervision-half-depth", type=float, default=16.0,
                        help="Half height of the supervised column around the annotated plane.")
    parser.add_argument("--center", type=float, default=None,
                        help="constant band center. Default: the segment median from _inklabels3d.json.")
    parser.add_argument("--half-width", type=float, default=None,
                        help="constant band half width, and the fallback for measured pixels "
                             "without a depth estimate. Default: the segment median.")
    parser.add_argument("--refresh-validation", action="store_true",
                        help="Rewrite only the version's validation mask from the current v1 mask, "
                             "reusing the geometry recorded when the version was written. This is "
                             "the per-fold step: the held-out split changes, the labels do not.")
    parser.add_argument("--dry-run", action="store_true", help="Report the geometry, write nothing.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing version.")
    args = parser.parse_args(argv)

    segment_dir = args.segment_dir.resolve()
    name = segment_dir.name
    if args.version < 2:
        return parser.error("--version must be >= 2; v1 is the published label set")
    if args.supervision_half_depth <= 0:
        return parser.error("--supervision-half-depth must be positive")
    if args.band is None and not args.refresh_validation:
        return parser.error("--band is required unless --refresh-validation is given")

    if args.refresh_validation:
        return refresh_validation(segment_dir, version=args.version, dry_run=args.dry_run)

    inklabels = open_asset(segment_dir, "inklabels")
    supervision = open_asset(segment_dir, "supervision_mask")
    validation = open_asset(segment_dir, "validation_mask", required=False)

    depth, height, width = (int(v) for v in inklabels["0"].shape)
    plane = annotated_plane(inklabels)

    # Defaults come from the measurement, so `constant` is this segment's own
    # thickness rather than a number carried over from another dataset.
    summary_path = segment_dir / f"{name}_inklabels3d.json"
    median = {}
    if summary_path.exists():
        median = json.loads(summary_path.read_text(encoding="utf-8")).get("segment_median") or {}
    center = args.center if args.center is not None else float(median.get("center", plane))
    half_width = args.half_width if args.half_width is not None else float(median.get("half_width", 4.0))

    depth_group = None
    if args.band == "measured":
        depth_path = segment_dir / f"{name}_inkdepth.zarr"
        if not depth_path.exists():
            sys.exit(f"error: {depth_path} not found; run tools/make_3d_labels.py first")
        depth_group = zarr.open(str(depth_path), mode="r")

    suffix = f"_v{args.version}"
    outputs = {
        "inklabels": segment_dir / f"{name}_inklabels{suffix}.zarr",
        "supervision_mask": segment_dir / f"{name}_supervision_mask{suffix}.zarr",
    }
    if validation is not None:
        outputs["validation_mask"] = segment_dir / f"{name}_validation_mask{suffix}.zarr"
    existing = [path for path in outputs.values() if path.exists()]
    if existing and not args.force and not args.dry_run:
        sys.exit(f"error: {existing[0]} exists. Pass --force to replace it.")

    z_axis = np.arange(depth, dtype=np.float32)[:, None, None]
    column = np.abs(z_axis - float(plane)) <= float(args.supervision_half_depth)

    print(f"segment          : {name}")
    print(f"volume           : {depth} x {height} x {width}, annotated plane z={plane}")
    print(f"band             : {args.band}")
    if args.band == "constant":
        print(f"                   center {center:.2f}, half width {half_width:.2f}")
    elif args.band == "measured":
        print(f"                   per pixel, falling back to center {center:.2f} / "
              f"half width {half_width:.2f}")
    print(f"supervised column: z {plane - args.supervision_half_depth:.0f}"
          f"..{plane + args.supervision_half_depth:.0f} "
          f"({int(column.sum())} of {depth} slices)")
    if validation is None:
        print("validation mask  : none published; skipping")

    tiles = occupied_tiles(supervision, plane, height=height, width=width)
    print(f"tiles            : {len(tiles)} of {TILE}px with annotation\n")

    if args.dry_run:
        print("--dry-run: nothing written")
        return 0

    label_arrays = create_label_pyramid(outputs["inklabels"], inklabels, f"{name}_inklabels{suffix}")
    supervision_arrays = create_label_pyramid(
        outputs["supervision_mask"], supervision, f"{name}_supervision_mask{suffix}")
    validation_arrays = (
        create_label_pyramid(outputs["validation_mask"], validation, f"{name}_validation_mask{suffix}")
        if validation is not None else None
    )

    ink_pixels = 0
    label_voxels = 0
    supervised_voxels = 0
    validation_voxels = 0
    fallback_pixels = 0
    thickness_histogram = np.zeros(depth + 1, dtype=np.int64)

    for y0, x0 in tqdm(tiles, desc="Write", unit="tile"):
        y1, x1 = min(height, y0 + TILE), min(width, x0 + TILE)
        supervised = np.asarray(supervision["0"][plane, y0:y1, x0:x1]) > 0
        if not supervised.any():
            continue
        ink = (np.asarray(inklabels["0"][plane, y0:y1, x0:x1]) > 0) & supervised

        if args.band == "plane":
            band = np.zeros((depth, y1 - y0, x1 - x0), dtype=bool)
            band[plane] = ink
        else:
            if args.band == "constant":
                tile_center = np.full(ink.shape, center, dtype=np.float32)
                tile_half_width = np.full(ink.shape, half_width, dtype=np.float32)
            else:
                tile_center = np.asarray(depth_group["center"][y0:y1, x0:x1], dtype=np.float32)
                tile_half_width = np.asarray(depth_group["half_width"][y0:y1, x0:x1], dtype=np.float32)
                missing = ~np.isfinite(tile_center) | ~np.isfinite(tile_half_width)
                fallback_pixels += int((missing & ink).sum())
                tile_center = np.where(missing, np.float32(center), tile_center)
                tile_half_width = np.where(missing, np.float32(half_width), tile_half_width)
            band = (np.abs(z_axis - tile_center[None]) <= tile_half_width[None]) & ink[None]

        # The column is what makes the band falsifiable: everything inside it
        # that is not labelled ink is a negative the model has to get right.
        supervised_column = (column & supervised[None]) | band

        ink_pixels += int(ink.sum())
        label_voxels += int(band.sum())
        supervised_voxels += int(supervised_column.sum())
        thickness_histogram += np.bincount(band.sum(axis=0)[ink], minlength=depth + 1)

        write_block(label_arrays, np.where(band, np.uint8(255), np.uint8(0)), y0, x0)
        write_block(supervision_arrays,
                    np.where(supervised_column, np.uint8(255), np.uint8(0)), y0, x0)
        if validation_arrays is not None:
            held_out = np.asarray(validation["0"][plane, y0:y1, x0:x1]) > 0
            held_out_column = column & held_out[None]
            validation_voxels += int(held_out_column.sum())
            write_block(validation_arrays,
                        np.where(held_out_column, np.uint8(255), np.uint8(0)), y0, x0)

    mean_thickness = float(
        (np.arange(depth + 1) * thickness_histogram).sum() / max(1, thickness_histogram.sum()))
    print(f"\nink pixels       : {ink_pixels:,}")
    print(f"label voxels     : {label_voxels:,}  ({mean_thickness:.2f} per ink pixel)")
    print(f"supervised voxels: {supervised_voxels:,}")
    if validation_arrays is not None:
        print(f"held-out voxels  : {validation_voxels:,}")
    if fallback_pixels:
        print(f"fallback pixels  : {fallback_pixels:,} "
              f"({100.0 * fallback_pixels / max(1, ink_pixels):.1f}% had no depth estimate)")

    report = {
        "segment": name,
        "version": f"v{args.version}",
        "band": args.band,
        "annotation_plane": plane,
        "volume_depth": depth,
        "supervision_half_depth": float(args.supervision_half_depth),
        "constant_center": float(center),
        "constant_half_width": float(half_width),
        "ink_pixels": ink_pixels,
        "label_voxels": label_voxels,
        "supervised_voxels": supervised_voxels,
        "validation_voxels": validation_voxels if validation_arrays is not None else None,
        "fallback_pixels": fallback_pixels,
        "mean_thickness": mean_thickness,
        "thickness_histogram": thickness_histogram.tolist(),
        "outputs": {kind: path.name for kind, path in outputs.items()},
    }
    report_path = segment_dir / f"{name}_labels{suffix}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {', '.join(path.name for path in outputs.values())}")
    print(f"      {report_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
