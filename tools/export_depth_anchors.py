#!/usr/bin/env python3
"""export_depth_anchors.py -- dump the measured depth band as scroll-space anchors.

Turns the per-pixel band in ``<seg>_inkdepth.zarr`` back into its native
resolution -- one record per measured 64 px cell -- and attaches everything an
external depth-validation pipeline needs to score the band against an
independent scan (villa #192): the cell's position on the segment grid, the
band centre/half-width in surface-volume layers, and the scroll-space base
point plus surface normal derived from the segment's ``x/y/z.tif`` coordinate
maps.

The composition into 3D points is deliberately left to the consumer:

    P(layer) = base + (layer - annotation_plane) * step * normal_hat

because two conventions are ours to assert but not to verify: the sign of the
normal (the cross product below fixes an orientation, but whether surface
volume layers increase along +normal or -normal is a property of the rendering
that produced the volume), and the sampling step (assumed 1 voxel per layer).
Both are recorded in the JSON sidecar so the consumer can flip/scale once
against a couple of known anchors instead of trusting us blindly.

Usage:
    python tools/export_depth_anchors.py data/ink-dataset/phercparis4/w00_20231016151002

Outputs (next to the segment, or --out-dir):
    <seg>_depth_anchors.csv    one row per measured cell
    <seg>_depth_anchors.json   provenance + the assumptions above

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import zarr


def bilinear(arr: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Sample arr (H, W) or (H, W, C) at float coordinates, clamped to the rectangle."""
    h, w = arr.shape[:2]
    ys = np.clip(ys, 0.0, h - 1.000001)
    xs = np.clip(xs, 0.0, w - 1.000001)
    y0 = np.floor(ys).astype(np.int64)
    x0 = np.floor(xs).astype(np.int64)
    fy = (ys - y0)[:, None] if arr.ndim == 3 else ys - y0
    fx = (xs - x0)[:, None] if arr.ndim == 3 else xs - x0
    a = arr[y0, x0]
    b = arr[y0, x0 + 1]
    c = arr[y0 + 1, x0]
    d = arr[y0 + 1, x0 + 1]
    return (a * (1 - fy) * (1 - fx) + b * (1 - fy) * fx
            + c * fy * (1 - fx) + d * fy * fx)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Export measured depth band as anchors.")
    parser.add_argument("segment_dir", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Where the CSV/JSON land. Default: the segment folder.")
    parser.add_argument("--cell", type=int, default=None,
                        help="Cell size in px. Default: read from <seg>_inklabels3d.json.")
    parser.add_argument("--tangent-step", type=float, default=2.0,
                        help="Central-difference step on the coordinate-map grid used "
                             "for the surface tangents. Default: 2 map pixels.")
    args = parser.parse_args(argv)

    seg = args.segment_dir.resolve()
    name = seg.name
    out_dir = (args.out_dir or seg).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    label3d_meta = json.loads((seg / f"{name}_inklabels3d.json").read_text(encoding="utf-8"))
    seg_meta = json.loads((seg / "meta.json").read_text(encoding="utf-8"))
    cell = args.cell or int(label3d_meta["parameters"]["cell"])
    plane = int(label3d_meta["annotation_plane"])
    regions = label3d_meta.get("regions", [])

    depth = zarr.open(str(seg / f"{name}_inkdepth.zarr"), mode="r")
    center_arr, half_arr = depth["center"], depth["half_width"]
    full_h, full_w = center_arr.shape

    # Cell centres on the full-resolution grid. The band was estimated per
    # cell and bilinearly upsampled, so sampling at the centres recovers the
    # cell values (up to the median filter, which also ran on the cell grid).
    rows = np.arange(full_h // cell)
    cols = np.arange(full_w // cell)
    cy = rows * cell + cell // 2
    cx = cols * cell + cell // 2
    yy, xx = np.meshgrid(cy, cx, indexing="ij")
    yy, xx = yy.ravel(), xx.ravel()

    centers = center_arr.get_orthogonal_selection((cy, cx)).ravel()
    halves = half_arr.get_orthogonal_selection((cy, cx)).ravel()
    keep = np.isfinite(centers) & np.isfinite(halves)

    # Cells whose exact centre pixel is NaN can still carry a band (the
    # upsampled field is NaN-ragged at region edges). Recover them from the
    # cell's own 64 px block -- but only look inside the annotation bounding
    # boxes, everything else is empty by construction.
    in_bbox = np.zeros(len(yy), dtype=bool)
    for reg in regions:
        y0, y1, x0, x1 = reg["bbox"]
        in_bbox |= (yy >= y0 - cell) & (yy < y1 + cell) & (xx >= x0 - cell) & (xx < x1 + cell)
    sampled_from = np.where(keep, "center", "")
    recovered = 0
    for i in np.flatnonzero(~keep & in_bbox):
        r0, c0 = int(yy[i]) - cell // 2, int(xx[i]) - cell // 2
        block_c = center_arr[r0:r0 + cell, c0:c0 + cell]
        if np.isfinite(block_c).any():
            centers[i] = np.nanmedian(block_c)
            halves[i] = np.nanmedian(half_arr[r0:r0 + cell, c0:c0 + cell])
            keep[i] = True
            sampled_from[i] = "block_median"
            recovered += 1

    yy, xx, centers, halves = yy[keep], xx[keep], centers[keep], halves[keep]
    sampled_from = sampled_from[keep]
    print(f"measured cells: {keep.sum()} ({recovered} recovered from cell blocks; "
          f"label build measured {label3d_meta.get('measured_cells')})")

    # Coordinate maps are released at ~0.1x of the mask grid ("tifxyz");
    # meta.json's scale converts full-resolution pixels to map pixels.
    sy, sx = (float(s) for s in seg_meta["scale"])
    maps = np.stack([tifffile.imread(str(seg / f"{axis}.tif")) for axis in ("x", "y", "z")],
                    axis=-1).astype(np.float64)  # (mh, mw, 3) scroll-space points
    my = yy * sy
    mx = xx * sx

    base = bilinear(maps, my, mx)  # (N, 3)
    step = args.tangent_step
    t_x = (bilinear(maps, my, mx + step) - bilinear(maps, my, mx - step)) / (2 * step)
    t_y = (bilinear(maps, my + step, mx) - bilinear(maps, my - step, mx)) / (2 * step)
    normal = np.cross(t_x, t_y)
    norm = np.linalg.norm(normal, axis=1, keepdims=True)
    ok = norm[:, 0] > 1e-9
    normal = np.where(ok[:, None], normal / np.where(norm == 0, 1, norm), np.nan)

    # Region id from the annotation bounding boxes recorded at label build.
    region_ids = np.zeros(len(yy), dtype=np.int64)
    for reg in regions:
        y0, y1, x0, x1 = reg["bbox"]
        inside = (yy >= y0) & (yy < y1) & (xx >= x0) & (xx < x1)
        region_ids[inside] = int(reg["region"])

    csv_path = out_dir / f"{name}_depth_anchors.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "cell_row", "cell_col", "y_px", "x_px", "region", "sampled_from",
            "center_layer", "offset_from_plane", "half_width_layers",
            "base_x", "base_y", "base_z", "normal_x", "normal_y", "normal_z",
        ])
        for i in range(len(yy)):
            writer.writerow([
                int(yy[i]) // cell, int(xx[i]) // cell, int(yy[i]), int(xx[i]),
                int(region_ids[i]), sampled_from[i],
                f"{centers[i]:.3f}", f"{centers[i] - plane:.3f}", f"{halves[i]:.3f}",
                f"{base[i, 0]:.3f}", f"{base[i, 1]:.3f}", f"{base[i, 2]:.3f}",
                f"{normal[i, 0]:.6f}", f"{normal[i, 1]:.6f}", f"{normal[i, 2]:.6f}",
            ])

    sidecar = {
        "segment": name,
        "scroll_source": seg_meta.get("scroll_source"),
        "coordinate_volume": seg_meta.get("volume"),
        "coordinate_maps": "x/y/z.tif sampled bilinearly at full_px * meta.scale",
        "map_scale": [sy, sx],
        "cell_px": cell,
        "annotation_plane_layer": plane,
        "volume_depth_layers": int(label3d_meta["volume_depth"]),
        "anchors": int(len(yy)),
        "band_source": f"{name}_inkdepth.zarr (per-cell centroid centre + FWHM half-width, "
                       "median-filtered on the cell grid)",
        "readback_caveat": "values are read back from the released per-pixel field, not the "
                           "estimator's internal cell table; rows with sampled_from="
                           "block_median sit at region edges where the field is NaN-ragged "
                           "and may mix neighbouring cells -- filter on sampled_from=center "
                           "for the strictest anchor set",
        "composition": "P(layer) = base + (layer - annotation_plane_layer) * layer_step * normal",
        "assumptions": {
            "layer_step_voxels": 1.0,
            "normal_orientation": "cross(d/dx, d/dy) of the coordinate maps; the sign "
                                  "relative to increasing layer index is UNVERIFIED -- "
                                  "calibrate against a couple of known anchors and flip "
                                  "if needed",
        },
        "estimator_parameters": label3d_meta.get("parameters"),
    }
    json_path = out_dir / f"{name}_depth_anchors.json"
    json_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    print(f"wrote {csv_path} ({len(yy)} anchors)")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
