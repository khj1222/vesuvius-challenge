"""Name the exact cause of the single-row-strip crash, rather than infer it.

Decodes the first and last strip of a few layouts and prints the raw shape
tifffile hands back, what np.squeeze does to it, and what _normalize_to_2d
then decides.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import tifffile

from vesuvius.ink_detection.preprocessing.create_label_zarrs import _normalize_to_2d

CASES = [
    ("even_block/strip1", 2048, 2048, 1),
    ("odd_odd/strip1024", 2049, 2051, 1024),
    ("odd_cross_block/strip1024", 1025, 1027, 1024),
    ("odd_odd/strip7", 2049, 2051, 7),
    ("even_block/strip1024", 2048, 2048, 1024),
]

WORK = Path(__file__).resolve().parent / "work"


def describe(path: Path) -> dict[str, object]:
    out: dict[str, object] = {"path": str(path)}
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        out["page_shape"] = list(page.shape)
        out["chunks"] = list(page.chunks)
        out["chunked"] = list(page.chunked)
        out["n_strips"] = len(page.dataoffsets)
        strips = []
        for index in (0, len(page.dataoffsets) - 1):
            tif.filehandle.seek(page.dataoffsets[index])
            data = tif.filehandle.read(page.databytecounts[index])
            decoded, position, shape = page.decode(
                data, index, jpegtables=page.jpegtables
            )
            entry: dict[str, object] = {
                "strip": index,
                "decoded_shape": list(np.asarray(decoded).shape),
                "position": list(position),
                "reported_shape": list(shape),
                "squeezed_shape": list(np.squeeze(np.asarray(decoded)).shape),
            }
            try:
                entry["normalize_to_2d"] = list(
                    _normalize_to_2d(decoded, path).shape
                )
            except Exception as error:  # noqa: BLE001 - the failure is the datum
                entry["normalize_to_2d"] = f"{type(error).__name__}: {error}"
            strips.append(entry)
        out["strips"] = strips
    return out


def main() -> None:
    for case, height, width, rows_per_strip in CASES:
        path = WORK / case / "head" / "seg" / "seg_inklabels.tif"
        if not path.exists():
            print(json.dumps({"case": case, "missing": str(path)}))
            continue
        remainder = height % rows_per_strip
        record = {
            "case": case,
            "height": height,
            "width": width,
            "rows_per_strip": rows_per_strip,
            "last_strip_rows": remainder or rows_per_strip,
        }
        record.update(describe(path))
        print(json.dumps(record))


if __name__ == "__main__":
    main()
