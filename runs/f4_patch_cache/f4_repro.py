"""Does the patch cache notice that a label asset changed under it?

The cache records each patch's label and mask *paths* and refuses a cache whose paths are
not among the current segments, so pointing at a different label tree is caught. This asks
the other case: the paths stay the same and the mask is regenerated in place, which is what
happens when you rebuild a held-out split and rerun in the same out_dir.

Prints one JSON object per phase.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import zarr

from koine_machines.common.common import flat_patch_cache_path, flat_patch_finding_cache_token
from koine_machines.data.ink_dataset import InkDataset

SOURCE_SEGMENT = Path("D:/vesuvius-challenge/data/ink_9um/labels/annotarget/disagreemin/phercparis4-w00")
VOLUME = "D:/vesuvius-challenge/data/ink_9um/surface-volumes/aligned9/phercparis4-w00.zarr"


REAL_CONFIG = Path("D:/vesuvius-challenge/configs/ink9um_at_disagreemin_s42.json")


def build_config(segments_path: Path, out_dir: Path) -> dict:
    """The real training config, with only the label tree and the out_dir moved."""
    config = json.loads(REAL_CONFIG.read_text(encoding="utf-8"))
    config["datasets"][0]["segments_path"] = str(segments_path)
    config["out_dir"] = str(out_dir)
    return config


def discover(config: dict) -> dict:
    dataset = InkDataset(config, do_augmentations=False)
    return {
        "patches": len(dataset.patches),
        "training": len(dataset.training_patches),
        "validation": len(dataset.validation_patches),
        "bbox_signature": hash(tuple(sorted(tuple(p.bbox) for p in dataset.patches))) & 0xFFFFFFFF,
    }


def shrink_supervision(segment_dir: Path, keep_fraction: float) -> int:
    """Zero the bottom part of the supervision mask, in place."""
    path = segment_dir / f"{segment_dir.name}_supervision_mask.zarr"
    group = zarr.open_group(str(path), mode="r+")
    array = group["0"]
    height = array.shape[1]
    cut = int(height * keep_fraction)
    remaining = 0
    for y0 in range(cut, height, 512):
        y1 = min(y0 + 512, height)
        block = np.asarray(array[:, y0:y1, :])
        if block.any():
            array[:, y0:y1, :] = 0
    for y0 in range(0, height, 512):
        y1 = min(y0 + 512, height)
        remaining += int(np.count_nonzero(np.asarray(array[array.shape[0] // 2, y0:y1, :])))
    return remaining


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="f4repro."))
    labels = work / "labels"
    labels.mkdir()
    segment = labels / SOURCE_SEGMENT.name
    shutil.copytree(SOURCE_SEGMENT, segment)
    out_dir = work / "run"
    out_dir.mkdir()

    config = build_config(labels, out_dir)
    cache = flat_patch_cache_path(config)
    token = flat_patch_finding_cache_token(config)

    first = discover(config)
    print(json.dumps({"phase": "1. first discovery", **first,
                      "cache_written": cache.exists(), "token": token}))

    kept = shrink_supervision(segment, 0.5)
    print(json.dumps({"phase": "2. supervision mask halved in place",
                      "supervised_pixels_left": kept,
                      "cache_still_there": cache.exists(),
                      "token_now": flat_patch_finding_cache_token(config),
                      "token_changed": flat_patch_finding_cache_token(config) != token}))

    second = discover(config)
    print(json.dumps({"phase": "3. rerun, same out_dir", **second,
                      "identical_to_stale": second["bbox_signature"] == first["bbox_signature"]}))

    fresh_out = work / "run_fresh"
    fresh_out.mkdir()
    third = discover(build_config(labels, fresh_out))
    print(json.dumps({"phase": "4. rerun, fresh out_dir (the truth)", **third,
                      "differs_from_stale": third["bbox_signature"] != first["bbox_signature"]}))

    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
