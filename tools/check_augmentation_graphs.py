#!/usr/bin/env python3
"""check_augmentation_graphs.py -- docs/36: dump an ink training augmentation graph as a normalized tree.

Builds the transform graph for the ink_9um patch (17 x 128 x 128) and prints every member's class and
parameters in order, so two graphs can be compared with `diff`.

    # what koine_machines' `augmentation_preset: "default"` builds (ink_dataset.py imports it from the library)
    PYTHONPATH=D:/vw2/ink-detection <ink-detection venv python> tools/check_augmentation_graphs.py released > a.json
    # the unused builder in koine_machines/augmentation/default_augmentations.py
    PYTHONPATH=D:/vw2/ink-detection <ink-detection venv python> tools/check_augmentation_graphs.py koine_unused > b.json
    # villa main's ink default; main's library imports SimpleITK and fft_conv_pytorch, which these members
    # never use, so empty stand-in modules on PYTHONPATH are enough
    PYTHONPATH="<main>/vesuvius/src;<stubs>" <python> tools/check_augmentation_graphs.py main <main> > c.json

License: MIT.
"""
from __future__ import annotations

import importlib.util
import json
import sys

PATCH = (17, 128, 128)
SKIP = {"benchmark", "benchmark_use_fft", "benchmark_num_runs"}  # main-only speed switch, same math


def build(which: str):
    if which == "released":
        from vesuvius.models.augmentation.pipelines.training_transforms import create_training_transforms
        return create_training_transforms(PATCH)
    if which == "koine_unused":
        from koine_machines.augmentation.default_augmentations import create_training_transforms
        return create_training_transforms(PATCH)
    if which == "main":
        path = f"{sys.argv[2]}/vesuvius/src/vesuvius/ink_detection/data/augmentations.py"
        spec = importlib.util.spec_from_file_location("main_ink_augmentations", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.create_default_training_transforms(PATCH)
    raise SystemExit(f"unknown graph {which!r}")


def norm(o, depth=0):
    if depth > 12:
        return "..."
    if isinstance(o, (int, float, str, bool)) or o is None:
        return o
    if isinstance(o, (list, tuple)):
        return [norm(x, depth + 1) for x in o]
    if isinstance(o, set):
        return sorted(norm(x, depth + 1) for x in o)
    if isinstance(o, dict):
        return {str(k): norm(v, depth + 1) for k, v in sorted(o.items(), key=lambda kv: str(kv[0]))
                if k not in SKIP}
    if callable(o) and not hasattr(o, "__dict__"):
        return f"<fn {getattr(o, '__name__', type(o).__name__)}>"
    if hasattr(o, "__dict__"):
        fields = {k: v for k, v in vars(o).items() if k not in SKIP and not k.startswith("_")}
        return {"__class__": type(o).__name__, **{k: norm(v, depth + 1) for k, v in sorted(fields.items())}}
    return repr(o)


if __name__ == "__main__":
    print(json.dumps(norm(build(sys.argv[1])), indent=1, default=str))
