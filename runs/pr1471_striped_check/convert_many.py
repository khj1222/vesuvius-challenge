"""Convert every TIFF named in a manifest, using whichever villa tree is on sys.path.

One process per tree keeps interpreter start-up out of the timings and out of the
wall clock. Emits one JSON object per line on stdout.
"""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

import tifffile

from vesuvius.ink_detection.preprocessing.create_label_zarrs import convert_image


def geometry_of(input_path: Path) -> dict[str, object]:
    with tifffile.TiffFile(input_path) as tif:
        page = tif.pages[0]
        return {
            "pages": len(tif.pages),
            "shape": list(page.shape),
            "dtype": str(page.dtype),
            "is_tiled": bool(page.is_tiled),
            "chunks": list(page.chunks),
            "chunked": list(page.chunked),
            "compression": int(page.compression),
            "n_blocks": len(page.dataoffsets),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--levels", type=int, default=6)
    parser.add_argument("--chunk-workers", type=int, default=1)
    args = parser.parse_args()

    entries = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    for entry in entries:
        input_path = Path(entry["input"])
        record: dict[str, object] = {"case": entry.get("case"), "input": str(input_path)}
        try:
            record["input_geometry"] = geometry_of(input_path)
            started = time.perf_counter()
            result = convert_image(
                input_path,
                levels=args.levels,
                overwrite=True,
                chunk_workers=args.chunk_workers,
            )
            record["seconds"] = round(time.perf_counter() - started, 3)
            record["result"] = result
            record["ok"] = True
        except Exception as error:  # noqa: BLE001 - the failure itself is the datum
            record["ok"] = False
            record["error"] = f"{type(error).__name__}: {error}"
            record["traceback"] = traceback.format_exc(limit=6)
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
