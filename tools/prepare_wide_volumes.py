#!/usr/bin/env python3
"""prepare_wide_volumes.py -- re-pool the ink_9um surface volumes 27 slices deep instead of 21.

The recipe's 21-slice inputs pool the 84 centred planes of each 2.4 um surface volume (level 2, rounded
mean of 4). The published volumes have 109 planes (PHerc0500P2: 118), so 108 centred planes give 27
slices: room to shift a 17-slice window by +-5 slices (~+-48 um) instead of +-2. Used to test larger
surface offsets than docs/30 could.

For every existing 21-slice volume (data/ink_9um/surface-volumes/{aligned9,openlabels9}) this reads the
source URL recorded in its attributes, streams level 2 tile by tile and writes
{aligned9_wide,openlabels9_wide}/<segment>.zarr. The pooling groups line up with the 21-slice ones, so
slices 3..23 of the wide volume must equal the existing volume exactly; that is checked for every volume
and recorded in surface-volumes/wide_report.json. Resumable: finished volumes are skipped.

    uv run --project external/villa/ink-detection --no-sync python tools/prepare_wide_volumes.py [--workers 8]

License: MIT.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
VOLUMES = ROOT / "data/ink_9um/surface-volumes"
SETS = (("openlabels9", "openlabels9_wide"), ("aligned9", "aligned9_wide"))   # small test set first
OUTPUT_Z, POOL_Z, TILE = 27, 4, 512
REPORT = VOLUMES / "wide_report.json"


def read_tile(source, z0, z1, y0, y1, x0, x1, attempts=8):
    for attempt in range(attempts):
        try:
            return np.asarray(source[z0:z1, y0:y1, x0:x1], dtype=np.float32)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(min(60, 2 ** attempt))


def open_remote(url):
    import zarr

    for attempt in range(8):
        try:
            return zarr.open(url, mode="r")["2"]
        except Exception:
            if attempt == 7:
                raise
            time.sleep(min(60, 2 ** attempt))


def build(name, src_path: Path, out: Path, workers: int) -> dict:
    import zarr
    from numcodecs import Blosc

    old = zarr.open(str(src_path), mode="r")
    url = old.attrs["source"]
    source = open_remote(url)
    shape = tuple(int(v) for v in source.shape)
    start = math.ceil((shape[0] - OUTPUT_Z * POOL_Z) / 2)
    z0, z1 = start, start + OUTPUT_Z * POOL_Z
    old_z0 = int(old.attrs["source_z_slice"][0])
    if (old_z0 - z0) % POOL_Z:
        raise ValueError(f"{name}: pooling groups do not line up ({z0} vs {old_z0})")
    offset = (old_z0 - z0) // POOL_Z
    partial = out.with_name(out.name + ".partial")
    group = zarr.open_group(str(partial), mode="w")
    group.attrs.update({"format": "level2-zmean4-27slice-v1", "source": url, "source_level": "2",
                        "source_shape_zyx": list(shape), "source_z_slice": [z0, z1],
                        "z_pool": "rounded mean of 4 centered source planes",
                        "slices_matching_21slice_volume": [offset, offset + 21],
                        "made_by": "tools/prepare_wide_volumes.py"})
    target = group.create_dataset("0", shape=(OUTPUT_Z, shape[1], shape[2]),
                                  chunks=(OUTPUT_Z, min(128, shape[1]), min(128, shape[2])),
                                  dtype=np.uint8, fill_value=0,
                                  compressor=Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE))
    tiles = [(y0, min(shape[1], y0 + TILE), x0, min(shape[2], x0 + TILE))
             for y0 in range(0, shape[1], TILE) for x0 in range(0, shape[2], TILE)]
    old_arr = old["0"]
    mismatch = {"tiles": 0, "voxels": 0}

    def process(tile):
        y0, y1, x0, x1 = tile
        block = read_tile(source, z0, z1, y0, y1, x0, x1)
        pooled = np.rint(block.reshape(OUTPUT_Z, POOL_Z, y1 - y0, x1 - x0).mean(axis=1)).astype(np.uint8)
        target[:, y0:y1, x0:x1] = pooled
        ref = np.asarray(old_arr[:, y0:y1, x0:x1])
        diff = int((pooled[offset: offset + 21] != ref).sum())
        return diff

    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for diff in pool.map(process, tiles):
            done += 1
            if diff:
                mismatch["tiles"] += 1
                mismatch["voxels"] += diff
            if done % 200 == 0 or done == len(tiles):
                print(f"{name}: tiles {done}/{len(tiles)} {time.time() - t0:.0f}s", flush=True)
    partial.rename(out)
    return {"source_shape": list(shape), "z": [z0, z1], "minutes": round((time.time() - t0) / 60, 1),
            "central21_equals_existing": mismatch["voxels"] == 0, "mismatch": mismatch}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    for src_dir, out_dir in SETS:
        (VOLUMES / out_dir).mkdir(parents=True, exist_ok=True)
        for src in sorted((VOLUMES / src_dir).glob("*.zarr")):
            name = src.stem
            out = VOLUMES / out_dir / src.name
            if out.exists():
                continue
            print(f"{name}: start", flush=True)
            report[f"{out_dir}/{name}"] = build(name, src, out, args.workers)
            REPORT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
            print(f"{name}: done {report[f'{out_dir}/{name}']}", flush=True)


if __name__ == "__main__":
    main()
