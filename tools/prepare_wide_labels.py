#!/usr/bin/env python3
"""prepare_wide_labels.py -- 27-slice label arrays to go with the wide ink_9um surface volumes.

The recipe's labels are (21, H, W) arrays aligned slice for slice with the 21-slice surface volumes (the
annotation sits in channel 10). tools/prepare_wide_volumes.py re-pooled the volumes 27 slices deep, with
the old 21 slices at 3..23 of the new ones. This writes (27, H, W) labels with the old 21 channels copied
unchanged to 3..23 (segments without a validation mask get none) and zeros in the six new channels, so the annotation moves to channel 13 and stays at
the same depth relative to the image. Nothing is resampled.

After writing, every array is read back tile by tile and checked: new[3:24] equals old, the rest is zero.
The result goes to labels/aligned-scrollprizeorg-27slices/wide_labels_report.json. Resumable.

    uv run --project external/villa/ink-detection --no-sync python tools/prepare_wide_labels.py

License: MIT.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "data/ink_9um/labels"
SRC = LABELS / "aligned-scrollprizeorg-21slices"
DST = LABELS / "aligned-scrollprizeorg-27slices"
WIDE_VOLUMES = ROOT / "data/ink_9um/surface-volumes/aligned9_wide"
KINDS = ("inklabels", "supervision_mask", "validation_mask")
OLD_Z, NEW_Z, OFFSET, TILE = 21, 27, 3, 1024
REPORT = DST / "wide_labels_report.json"


def convert(seg: str, kind: str) -> dict:
    import zarr

    src = zarr.open(str(SRC / seg / f"{seg}_{kind}.zarr"), mode="r")
    wide = zarr.open(str(WIDE_VOLUMES / f"{seg}.zarr"), mode="r")
    if list(wide.attrs["slices_matching_21slice_volume"]) != [OFFSET, OFFSET + OLD_Z]:
        raise ValueError(f"{seg}: wide volume offset is {wide.attrs['slices_matching_21slice_volume']}")
    old = src["0"]
    if old.shape[0] != OLD_Z or tuple(old.shape[1:]) != tuple(wide["0"].shape[1:]):
        raise ValueError(f"{seg} {kind}: shape {old.shape} vs wide volume {wide['0'].shape}")
    out = DST / seg / f"{seg}_{kind}.zarr"
    partial = out.with_name(out.name + ".partial")
    group = zarr.open_group(str(partial), mode="w")
    attrs = dict(src.attrs)
    attrs.update({"annotation_center_channel": int(attrs["annotation_center_channel"]) + OFFSET,
                  "output_channels": NEW_Z, "format": "aligned-public-level2-zmean4-27slice-v1",
                  "source_z_slice": list(wide.attrs["source_z_slice"]),
                  "z_pool": "27 complete means of 4 source planes",
                  "widened_from": f"aligned-scrollprizeorg-21slices channels 0..20 -> {OFFSET}..{OFFSET + OLD_Z - 1}",
                  "made_by": "tools/prepare_wide_labels.py"})
    group.attrs.update(attrs)
    H, W = old.shape[1:]
    new = group.create_dataset("0", shape=(NEW_Z, H, W), chunks=(NEW_Z,) + tuple(old.chunks[1:]),
                               dtype=old.dtype, fill_value=0, compressor=old.compressor)
    tiles = [(y, min(H, y + TILE), x, min(W, x + TILE)) for y in range(0, H, TILE) for x in range(0, W, TILE)]
    nonzero_old_outside_center = 0
    for y0, y1, x0, x1 in tiles:
        block = np.asarray(old[:, y0:y1, x0:x1])
        center = int(src.attrs["annotation_center_channel"])
        nonzero_old_outside_center += int(np.count_nonzero(np.delete(block, center, axis=0)))
        buf = np.zeros((NEW_Z, y1 - y0, x1 - x0), dtype=block.dtype)
        buf[OFFSET:OFFSET + OLD_Z] = block
        new[:, y0:y1, x0:x1] = buf
    partial.rename(out)
    # read back from disk
    check = zarr.open(str(out), mode="r")["0"]
    bad = 0
    positives = 0
    for y0, y1, x0, x1 in tiles:
        a = np.asarray(check[:, y0:y1, x0:x1])
        b = np.asarray(old[:, y0:y1, x0:x1])
        bad += int((a[OFFSET:OFFSET + OLD_Z] != b).sum()) + int(np.count_nonzero(a[:OFFSET]))
        bad += int(np.count_nonzero(a[OFFSET + OLD_Z:]))
        positives += int(np.count_nonzero(a[OFFSET + int(src.attrs["annotation_center_channel"])]))
    return {"shape": [NEW_Z, H, W], "center_channel": attrs["annotation_center_channel"],
            "readback_mismatch_voxels": bad, "center_nonzero": positives,
            "old_nonzero_outside_center": nonzero_old_outside_center}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    for seg_dir in sorted(p for p in SRC.iterdir() if p.is_dir()):
        seg = seg_dir.name
        (DST / seg).mkdir(exist_ok=True)
        for kind in KINDS:
            key = f"{seg}/{kind}"
            if not (seg_dir / f"{seg}_{kind}.zarr").exists():    # some segments have no validation mask
                continue
            if (DST / seg / f"{seg}_{kind}.zarr").exists() and key in report:
                continue
            t0 = time.time()
            report[key] = convert(seg, kind)
            report[key]["seconds"] = round(time.time() - t0, 1)
            REPORT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
            print(key, report[key], flush=True)
    bad = {k: v for k, v in report.items() if v["readback_mismatch_voxels"]}
    print(f"{len(report)} arrays, read-back mismatches in {len(bad)}")


if __name__ == "__main__":
    main()
