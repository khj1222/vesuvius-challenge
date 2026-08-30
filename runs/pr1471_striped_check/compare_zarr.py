"""Compare two label zarr stores.

Primary test is byte-level: every file under the store (metadata and chunk
payloads) is hashed and the two maps are compared. Both stores are written by
the same code with the same compressor, so equal data compresses to equal bytes;
an unequal hash map is then re-checked numerically so the report says what
actually differs rather than just that something does.

Prints one JSON object on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import zarr

SLAB = 2048


def hash_tree(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        digests[path.relative_to(root).as_posix()] = digest.hexdigest()
    return digests


def numeric_diff(left: Path, right: Path) -> list[dict[str, object]]:
    """Per-level numeric comparison, read in row slabs so a huge level 0 fits."""
    group_left = zarr.open_group(str(left), mode="r")
    group_right = zarr.open_group(str(right), mode="r")
    report: list[dict[str, object]] = []
    levels = sorted(int(key) for key in group_left.array_keys())
    for level in levels:
        array_left = group_left[str(level)]
        array_right = group_right[str(level)]
        entry: dict[str, object] = {
            "level": level,
            "shape_left": list(array_left.shape),
            "shape_right": list(array_right.shape),
            "dtype_left": str(array_left.dtype),
            "dtype_right": str(array_right.dtype),
        }
        if array_left.shape != array_right.shape or array_left.dtype != array_right.dtype:
            entry["equal"] = False
            entry["reason"] = "shape or dtype differ"
            report.append(entry)
            continue
        mismatched = 0
        first: list[int] | None = None
        for y0 in range(0, array_left.shape[1], SLAB):
            y1 = min(y0 + SLAB, array_left.shape[1])
            block_left = np.asarray(array_left[:, y0:y1, :])
            block_right = np.asarray(array_right[:, y0:y1, :])
            if block_left.shape != block_right.shape:
                entry["equal"] = False
                entry["reason"] = "slab shape differ"
                break
            difference = block_left != block_right
            count = int(difference.sum())
            if count and first is None:
                index = np.argwhere(difference)[0]
                first = [int(index[0]), int(index[1]) + y0, int(index[2])]
                entry["first_mismatch_zyx"] = first
                entry["left_value"] = int(block_left[tuple(index)])
                entry["right_value"] = int(block_right[tuple(index)])
            mismatched += count
        entry.setdefault("equal", mismatched == 0)
        entry["mismatched_voxels"] = mismatched
        entry["voxels"] = int(np.prod(array_left.shape))
        report.append(entry)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--label", default="")
    parser.add_argument("--skip-numeric", action="store_true")
    args = parser.parse_args()

    left = Path(args.left)
    right = Path(args.right)
    hashes_left = hash_tree(left)
    hashes_right = hash_tree(right)
    byte_identical = hashes_left == hashes_right

    result: dict[str, object] = {
        "label": args.label,
        "left": str(left),
        "right": str(right),
        "byte_identical": byte_identical,
        "files_left": len(hashes_left),
        "files_right": len(hashes_right),
    }
    if not byte_identical:
        only_left = sorted(set(hashes_left) - set(hashes_right))
        only_right = sorted(set(hashes_right) - set(hashes_left))
        changed = sorted(
            name
            for name in set(hashes_left) & set(hashes_right)
            if hashes_left[name] != hashes_right[name]
        )
        result["only_left"] = only_left[:12]
        result["only_right"] = only_right[:12]
        result["changed"] = changed[:12]
        result["n_only_left"] = len(only_left)
        result["n_only_right"] = len(only_right)
        result["n_changed"] = len(changed)
        if not args.skip_numeric:
            result["numeric"] = numeric_diff(left, right)
            result["numerically_equal"] = all(
                entry.get("equal") for entry in result["numeric"]
            )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
