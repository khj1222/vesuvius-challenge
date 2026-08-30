"""Re-encode the real held-out validation mask into the layouts under test.

Our harness writes tiled(256, 256) + LZW, so the tiled copy is the original
bytes; the striped copies are the same pixels re-encoded, which is stated as
such in the report.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import tifffile

SOURCE = Path(
    "D:/vesuvius-challenge/data/ink-dataset/phercparis4/w00_20231016151002/"
    "w00_20231016151002_validation_mask.tif"
)
ROOT = Path(__file__).resolve().parent / "real"
LAYOUTS = {
    "tiled256": {"tile": (256, 256)},
    "strip1024": {"rowsperstrip": 1024},
    "strip7": {"rowsperstrip": 7},
}


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    image = tifffile.imread(SOURCE)
    report = {
        "source": str(SOURCE),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "nonzero": int(np.count_nonzero(image)),
        "layouts": {},
    }
    for layout, kwargs in LAYOUTS.items():
        target_dir = ROOT / layout / "seg"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "seg_inklabels.tif"
        zarr_path = target.with_suffix(".zarr")
        if zarr_path.exists():
            shutil.rmtree(zarr_path)
        if layout == "tiled256":
            shutil.copyfile(SOURCE, target)
        else:
            tifffile.imwrite(target, image, compression="lzw", **kwargs)
        with tifffile.TiffFile(target) as tif:
            page = tif.pages[0]
            report["layouts"][layout] = {
                "path": str(target),
                "file_mb": round(target.stat().st_size / (1 << 20), 2),
                "is_tiled": bool(page.is_tiled),
                "chunks": list(page.chunks),
                "chunked": list(page.chunked),
                "n_blocks": len(page.dataoffsets),
                "compression": int(page.compression),
            }
        print(json.dumps({layout: report["layouts"][layout]}), flush=True)
    (ROOT / "inputs.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
