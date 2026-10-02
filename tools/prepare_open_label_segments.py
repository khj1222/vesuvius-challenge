#!/usr/bin/env python3
"""prepare_open_label_segments.py -- inputs for the docs/27 replication on scrolls the public
ink_9um models never saw (PHerc0841, PHerc0009B, PHerc0500P2).

The open-data bucket now carries reviewed ink labels next to each segment's ~2.4 um surface volume
(`ink-labels/<volume>/20260918/{inklabels,supervision,validation}.zarr`, zarr v3, sharded). This
prepares both sides on the same ~9.6 um grid the ink_9um recipe reads:

* ``volumes`` -- the recipe's own pooling (villa ``prepare_9um_isotropic_input.py``): XY pyramid
  level 2, the 84 centred z planes, rounded mean of 4 -> 21 slices. Same arithmetic, plus a retry
  per tile, because public S3 reads drop now and then. Runs in the ink-detection env (zarr 2).
* ``labels`` -- level 2 of each label pyramid. In the open data that level is a 4x nearest-neighbour
  sample of level 0 (checked on PHerc1667 w029: identical to ``level0[::4, ::4]``; and identical on
  the grid to this repo's earlier labels, IoU 0.986 with no shift). Needs zarr>=3 to read; writes
  ``.npy`` that ``volumes`` turns into the zarr layout ``eval_validation.py`` reads.

    uv run --no-project --with "zarr>=3" --with numpy --with fsspec --with aiohttp --with requests \\
        python tools/prepare_open_label_segments.py labels
    uv run --project external/villa/ink-detection --no-sync python tools/prepare_open_label_segments.py volumes

License: MIT.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BUCKET = "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/"
VOLUME_OUT = ROOT / "data/ink_9um/surface-volumes/openlabels9"
LABEL_OUT = ROOT / "data/ink_9um/labels/openlabels9"
NPY_DIR = LABEL_OUT / "_npy"

TARGETS = {
    "pherc0841-w00": (
        "PHerc0841/segments/20260220213127-w00/surface-volumes/2.403um-0.22m-77keV-volume-20260319124803.zarr",
        "PHerc0841/segments/20260220213127-w00/ink-labels/2.403um-volume-20260319124803/20260918"),
    "pherc0841-ag144": (
        "PHerc0841/segments/20260220214732-auto_grown_20260220144552896/surface-volumes/2.403um-0.22m-77keV-volume-20260319124803.zarr",
        "PHerc0841/segments/20260220214732-auto_grown_20260220144552896/ink-labels/2.403um-volume-20260319124803/20260918"),
    "pherc0841-ag174": (
        "PHerc0841/segments/20260221022814-auto_grown_20260220174252405/surface-volumes/2.403um-0.22m-77keV-volume-20260319124803.zarr",
        "PHerc0841/segments/20260221022814-auto_grown_20260220174252405/ink-labels/2.403um-volume-20260319124803/20260918"),
    "pherc0009b-ag055": (
        "PHerc0009B/segments/20250919125754-auto_grown_20250919055754487_inp_hr/surface-volumes/2.401um-0.35m-77keV-volume-20250820154339.zarr",
        "PHerc0009B/segments/20250919125754-auto_grown_20250919055754487_inp_hr/ink-labels/2.401um-volume-20250820154339/20260918"),
    "pherc0500p2-s1": (
        "PHerc0500P2/segments/20250825181859--1/surface-volumes/2.215um-0.4m-111keV-volume-20250526151718.zarr",
        "PHerc0500P2/segments/20250825181859--1/ink-labels/2.215um-volume-20250526151718/20260918"),
}
LABEL_KINDS = {"inklabels": "inklabels", "supervision": "supervision_mask", "validation": "validation_mask"}
OUTPUT_Z, POOL_Z, TILE = 21, 4, 512


def labels(args) -> None:
    import zarr

    NPY_DIR.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, (_, label_path) in TARGETS.items():
        report[name] = {}
        for kind in LABEL_KINDS:
            url = f"{BUCKET}{label_path}/{kind}.zarr/2"
            try:
                array = np.asarray(zarr.open_array(url, mode="r")[:])
            except Exception as exc:  # validation.zarr exists on only some sets
                report[name][kind] = f"absent ({type(exc).__name__})"
                continue
            np.save(NPY_DIR / f"{name}_{kind}.npy", array)
            report[name][kind] = {"shape": list(array.shape), "values": sorted(int(v) for v in np.unique(array)),
                                  "nonzero": int((array > 0).sum())}
        print(name, json.dumps(report[name]), flush=True)
    (NPY_DIR / "labels_report.json").write_text(json.dumps(report, indent=1) + "\n")


def read_tile(source, z0, z1, y0, y1, x0, x1, attempts=6):
    for attempt in range(attempts):
        try:
            return np.asarray(source[z0:z1, y0:y1, x0:x1], dtype=np.float32)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def volumes(args) -> None:
    import zarr
    from numcodecs import Blosc

    VOLUME_OUT.mkdir(parents=True, exist_ok=True)
    for name, (volume_path, _) in TARGETS.items():
        out = VOLUME_OUT / f"{name}.zarr"
        if out.exists():
            print(f"{name}: exists, skipped", flush=True)
        else:
            url = f"{BUCKET}{volume_path}"
            source = zarr.open(url, mode="r")["2"]
            shape = tuple(int(v) for v in source.shape)
            start = math.ceil((shape[0] - OUTPUT_Z * POOL_Z) / 2)
            z0, z1 = start, start + OUTPUT_Z * POOL_Z
            partial = out.with_name(out.name + ".partial")
            group = zarr.open_group(str(partial), mode="w")
            group.attrs.update({"format": "level2-zmean4-21slice-v1", "source": url, "source_level": "2",
                                "source_shape_zyx": list(shape), "source_z_slice": [z0, z1],
                                "z_pool": "rounded mean of 4 centered source planes",
                                "made_by": "tools/prepare_open_label_segments.py (same arithmetic as villa "
                                           "prepare_9um_isotropic_input.py, retry per tile)"})
            target = group.create_dataset("0", shape=(OUTPUT_Z, shape[1], shape[2]),
                                          chunks=(OUTPUT_Z, min(128, shape[1]), min(128, shape[2])),
                                          dtype=np.uint8, fill_value=0,
                                          compressor=Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE))
            tiles = [(y0, min(shape[1], y0 + TILE), x0, min(shape[2], x0 + TILE))
                     for y0 in range(0, shape[1], TILE) for x0 in range(0, shape[2], TILE)]

            def process(tile):
                y0, y1, x0, x1 = tile
                block = read_tile(source, z0, z1, y0, y1, x0, x1)
                target[:, y0:y1, x0:x1] = np.rint(
                    block.reshape(OUTPUT_Z, POOL_Z, y1 - y0, x1 - x0).mean(axis=1)).astype(np.uint8)
                return 1

            t0, done = time.time(), 0
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                for count in pool.map(process, tiles):
                    done += count
                    if done % 100 == 0 or done == len(tiles):
                        print(f"{name}: tiles={done}/{len(tiles)} {time.time() - t0:.0f}s", flush=True)
            partial.rename(out)
            print(f"{name}: wrote {out} source {shape} z {z0}:{z1}", flush=True)

        # labels -> the layout eval_validation.py / score_label_free_threshold.py read
        seg_dir = LABEL_OUT / name
        vol_shape = zarr.open(str(out), mode="r")["0"].shape
        for kind, suffix in LABEL_KINDS.items():
            npy = NPY_DIR / f"{name}_{kind}.npy"
            dest = seg_dir / f"{name}_{suffix}.zarr"
            if not npy.exists() or dest.exists():
                continue
            plane = np.load(npy)
            if plane.shape != tuple(vol_shape[1:]):
                sys.exit(f"error: {name} {kind} {plane.shape} != volume {vol_shape[1:]}")
            group = zarr.open_group(str(dest), mode="w")
            group.create_dataset("0", data=plane[None].astype(np.uint8), chunks=(1, 1024, 1024))
        print(f"{name}: labels written to {seg_dir}", flush=True)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("labels")
    v = sub.add_parser("volumes")
    v.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    {"labels": labels, "volumes": volumes}[args.cmd](args)


if __name__ == "__main__":
    main()
