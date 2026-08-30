"""Compare two real-scale label zarrs on the written label plane.

Level 0 here is (65, 32249, 51380); reading the whole volume twice is not
practical, and only z = LABEL_SLICE is ever written by either path (the index is
a module constant, not derived from the input), so the comparison is over that
plane at every pyramid level, in row slabs.
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import zarr

LABEL_SLICE = 32
SLAB = 4096


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    left = zarr.open_group(args.left, mode="r")
    right = zarr.open_group(args.right, mode="r")
    report: dict[str, object] = {"label": args.label, "levels": []}
    all_equal = True
    for key in sorted(left.array_keys(), key=int):
        array_left = left[key]
        array_right = right[key]
        entry: dict[str, object] = {
            "level": int(key),
            "shape_left": list(array_left.shape),
            "shape_right": list(array_right.shape),
        }
        if array_left.shape != array_right.shape or array_left.dtype != array_right.dtype:
            entry["equal"] = False
            entry["reason"] = "shape or dtype"
            all_equal = False
            report["levels"].append(entry)
            continue
        mismatched = 0
        nonzero = 0
        for y0 in range(0, array_left.shape[1], SLAB):
            y1 = min(y0 + SLAB, array_left.shape[1])
            plane_left = np.asarray(array_left[LABEL_SLICE, y0:y1, :])
            plane_right = np.asarray(array_right[LABEL_SLICE, y0:y1, :])
            mismatched += int((plane_left != plane_right).sum())
            nonzero += int(np.count_nonzero(plane_left))
        entry["mismatched_pixels"] = mismatched
        entry["nonzero_pixels_left"] = nonzero
        entry["pixels"] = int(array_left.shape[1] * array_left.shape[2])
        entry["equal"] = mismatched == 0
        all_equal = all_equal and entry["equal"]
        report["levels"].append(entry)
    report["equal"] = all_equal
    print(json.dumps(report))


if __name__ == "__main__":
    main()
