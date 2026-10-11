#!/usr/bin/env python3
"""check_wander_active.py -- did the docs/30 wander augmentation actually run in training?

Builds the training dataset exactly as koine_machines.training.train does (shared dataset, then the
augmented training view over its patches) from each arm's config, draws N training samples, and counts
calls to `_apply_local_wander`. Run from D:/vw2/ink-detection in the ink-detection env:

    uv run --project E:/vesuvius-challenge/external/villa/ink-detection --no-sync \
        python E:/vesuvius-challenge/tools/check_wander_active.py

License: MIT.
"""
import json
import random
from copy import deepcopy
from pathlib import Path

import numpy as np

import koine_machines.data.ink_dataset as ds_module
from koine_machines.data.ink_dataset import InkDataset

ROOT = Path("E:/vesuvius-challenge")
N = 40
result = {}
for arm in ("control", "wander"):
    config = json.loads((ROOT / f"configs/ink9um_segrobust_{arm}_s42.json").read_text(encoding="utf-8"))
    calls = {"n": 0, "max_abs_shift_samples": []}
    original = ds_module._apply_local_wander

    def counting(full_crop, **kwargs):
        calls["n"] += 1
        return original(full_crop, **kwargs)

    ds_module._apply_local_wander = counting
    random.seed(0)
    np.random.seed(0)
    cfg = deepcopy(config)
    shared = InkDataset(cfg, do_augmentations=False)
    train = InkDataset(cfg, do_augmentations=True, patches=shared.training_patches, segments=shared.segments)
    picks = random.sample(range(len(train)), N)
    for i in picks:
        train[i]
    ds_module._apply_local_wander = original
    result[arm] = {"samples": N, "wander_calls": calls["n"]}
    print(arm, result[arm], flush=True)
(ROOT / "runs/segrobust/wander_active_check.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
