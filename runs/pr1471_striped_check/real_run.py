"""Convert one real label image through one villa tree, with peak-RSS sampling.

Used for the 32249 x 51380 held-out validation mask our harness produces, which
is the size at which the memory question in #1231 is actually decided.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

import psutil
import tifffile

from vesuvius.ink_detection.preprocessing.create_label_zarrs import convert_image


class PeakRSS:
    def __init__(self, interval: float = 0.05) -> None:
        self.process = psutil.Process()
        self.interval = interval
        self.peak = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.peak = max(self.peak, self.process.memory_info().rss)
            except Exception:  # noqa: BLE001
                pass
            self._stop.wait(self.interval)

    def __enter__(self) -> "PeakRSS":
        self.peak = self.process.memory_info().rss
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--levels", type=int, default=6)
    parser.add_argument("--chunk-workers", type=int, default=1)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    with tifffile.TiffFile(input_path) as tif:
        page = tif.pages[0]
        geometry = {
            "shape": list(page.shape),
            "dtype": str(page.dtype),
            "is_tiled": bool(page.is_tiled),
            "chunks": list(page.chunks),
            "chunked": list(page.chunked),
            "compression": int(page.compression),
            "n_blocks": len(page.dataoffsets),
        }

    with PeakRSS() as sampler:
        started = time.perf_counter()
        result = convert_image(
            input_path,
            levels=args.levels,
            overwrite=True,
            chunk_workers=args.chunk_workers,
        )
        elapsed = time.perf_counter() - started

    print(
        json.dumps(
            {
                "label": args.label,
                "input": str(input_path),
                "input_geometry": geometry,
                "result": result,
                "seconds": round(elapsed, 2),
                "peak_rss_gib": round(sampler.peak / (1 << 30), 3),
                "file_mb": round(input_path.stat().st_size / (1 << 20), 2),
            }
        )
    )


if __name__ == "__main__":
    main()
