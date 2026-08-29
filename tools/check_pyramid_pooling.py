#!/usr/bin/env python3
"""Is a surface volume's XY pyramid built by averaging, or by decimation?

The question is not academic here. `scripts/prepare_9um_isotropic_input.py`
builds the `aligned` inputs by reading **level 2** of a 2.399 um render and then
mean-pooling 4 planes in z. If each level of that pyramid is a 2x2 mean, one
aligned voxel is the average of 4x4x4 = 64 acquired voxels, against a single
acquired voxel for a `native` 9.362 um volume covering the same space -- which
is a concrete mechanism for the transfer difference docs/15 appendix 2 measured.
If the pyramid were decimated instead, the aligned input would be a subsample,
the sample count would be one either way, and the mechanism would be wrong.

So this reads a few small windows straight from the published zarr and compares
each level against the level below it, pooled two ways:

* `mean`  -- levelN[i, j] vs the mean of levelN-1[2i:2i+2, 2j:2j+2]
* `decim` -- levelN[i, j] vs levelN-1[2i, 2j]

Windows are located from the coarsest level so the comparison lands on sheet
rather than on padding, and no label or annotation is involved anywhere.

Reads are anonymous over https; a run costs a few MB.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import zarr


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="OME-Zarr surface volume (URL or path)")
    parser.add_argument("--out", type=Path, default=None, help="write the report as JSON")
    parser.add_argument("--windows", type=int, default=3, help="windows per level pair")
    parser.add_argument("--size", type=int, default=64,
                        help="window edge, in pixels of the coarser level")
    parser.add_argument("--planes", type=int, nargs="+", default=None,
                        help="z planes to read (default: three spread through the volume)")
    parser.add_argument("--pairs", type=int, nargs="+", default=[1, 2],
                        help="coarse levels to check against the level below")
    return parser.parse_args(argv)


def read_retry(array, index, attempts: int = 6):
    """S3 drops connections mid-read often enough to need this at tile level."""
    delay = 2.0
    for attempt in range(1, attempts + 1):
        try:
            return np.asarray(array[index])
        except Exception as error:  # noqa: BLE001 - any transport error is retryable
            if attempt == attempts:
                raise
            print(f"  read failed ({type(error).__name__}), retry {attempt}/{attempts - 1} "
                  f"in {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)


_ARRAY_CACHE: dict = {}


def array_of(group, path: str):
    """Open one pyramid level, retrying: opening reads .zarray over the network."""
    if path in _ARRAY_CACHE:
        return _ARRAY_CACHE[path]
    delay = 2.0
    for attempt in range(1, 7):
        try:
            _ARRAY_CACHE[path] = group[path]
            return _ARRAY_CACHE[path]
        except Exception as error:  # noqa: BLE001
            if attempt == 6:
                raise
            print(f"  open of level {path} failed ({type(error).__name__}), "
                  f"retry {attempt}/5 in {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)


def multiscale_levels(group) -> list[tuple[str, list[float]]]:
    multiscales = group.attrs.get("multiscales")
    if not multiscales:
        raise SystemExit("error: no multiscales metadata; cannot enumerate levels")
    levels = []
    for dataset in multiscales[0]["datasets"]:
        scale = None
        for transform in dataset.get("coordinateTransformations", []):
            if transform.get("type") == "scale":
                scale = [float(v) for v in transform["scale"]]
        levels.append((str(dataset["path"]), scale))
    return levels


def locate_windows(group, levels, coarse_index: int, size: int, count: int) -> list[tuple[int, int]]:
    """Window origins, in the coarse level's pixels, over non-empty sheet."""
    scout_path, _ = levels[-1]
    scout = array_of(group, scout_path)
    factor = 2 ** (len(levels) - 1 - coarse_index)
    plane = read_retry(scout, scout.shape[0] // 2)
    rows, cols = np.nonzero(plane > 0)
    if rows.size == 0:
        raise SystemExit("error: the coarsest level is empty; cannot place a window")
    order = np.argsort(rows * plane.shape[1] + cols)
    picks = []
    for k in range(count):
        index = order[int((k + 1) * order.size / (count + 1))]
        y = int(rows[index]) * factor
        x = int(cols[index]) * factor
        coarse = array_of(group, levels[coarse_index][0])
        y = max(0, min(y, coarse.shape[1] - size))
        x = max(0, min(x, coarse.shape[2] - size))
        picks.append((y, x))
    return picks


def compare(coarse: np.ndarray, fine: np.ndarray) -> dict:
    z, h, w = fine.shape
    pooled = fine.reshape(z, h // 2, 2, w // 2, 2).mean(axis=(2, 4))
    decimated = fine[:, ::2, ::2]
    def stats(reference):
        difference = coarse - reference
        return {
            "max_abs": float(np.abs(difference).max()),
            "mean_abs": float(np.abs(difference).mean()),
            "exact_after_rounding": float(np.mean(np.round(reference) == coarse)),
            "correlation": float(np.corrcoef(reference.ravel(), coarse.ravel())[0, 1]),
        }
    within = fine.reshape(z, h // 2, 2, w // 2, 2).std(axis=(2, 4))
    return {"mean": stats(pooled), "decimate": stats(decimated),
            "fine_within_block_std": float(within.mean())}


def main(argv=None) -> int:
    args = parse_args(argv)
    started = time.time()
    group = zarr.open(args.source, mode="r")
    levels = multiscale_levels(group)
    level0 = array_of(group, levels[0][0])
    depth = int(level0.shape[0])
    planes = args.planes or [depth // 4, depth // 2, (3 * depth) // 4]

    report = {
        "source": str(args.source),
        "levels": [{"path": path, "scale": scale,
                    "shape": [int(v) for v in array_of(group, path).shape]}
                   for path, scale in levels],
        "planes": planes,
        "window_size": args.size,
        "pairs": [],
    }
    xy_only = all(
        scale is not None and abs(scale[0] - levels[0][1][0]) < 1e-9 for _, scale in levels
    ) if levels[0][1] is not None else None
    report["pyramid_is_xy_only"] = xy_only

    for coarse_index in args.pairs:
        if coarse_index >= len(levels):
            continue
        coarse_path = levels[coarse_index][0]
        fine_path = levels[coarse_index - 1][0]
        windows = locate_windows(group, levels, coarse_index, args.size, args.windows)
        entries = []
        for (y, x) in windows:
            coarse = read_retry(array_of(group, coarse_path),
                                (planes, slice(y, y + args.size),
                                 slice(x, x + args.size))).astype(np.float64)
            fine = read_retry(array_of(group, fine_path),
                              (planes, slice(y * 2, (y + args.size) * 2),
                               slice(x * 2, (x + args.size) * 2))).astype(np.float64)
            entry = {"y": int(y), "x": int(x), "coarse_mean": float(coarse.mean())}
            entry.update(compare(coarse, fine))
            entries.append(entry)
            print(f"level {fine_path}->{coarse_path} window ({y},{x}): "
                  f"mean max|d| {entry['mean']['max_abs']:.2f} "
                  f"exact {100 * entry['mean']['exact_after_rounding']:.1f}%  |  "
                  f"decimate max|d| {entry['decimate']['max_abs']:.1f} "
                  f"exact {100 * entry['decimate']['exact_after_rounding']:.1f}%", flush=True)
        verdict = "mean" if all(
            e["mean"]["max_abs"] <= 1.0 and e["mean"]["max_abs"] < e["decimate"]["max_abs"]
            for e in entries) else "inconclusive"
        report["pairs"].append({
            "coarse": coarse_path, "fine": fine_path, "verdict": verdict, "windows": entries,
        })
        print(f"level {fine_path}->{coarse_path}: verdict {verdict}", flush=True)

    report["seconds"] = time.time() - started
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
