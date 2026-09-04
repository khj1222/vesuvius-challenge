"""Load inference_runtime.py from its real file without the package __init__ chain,
which pulls optional deps (nrrd) that are not installed here."""
import importlib.util, sys, types

ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius", "vesuvius.ink_detection", "vesuvius.ink_detection.models",
             "vesuvius.ink_detection.inference"):
    mod = types.ModuleType(name); mod.__path__ = []
    sys.modules[name] = mod; parents[name] = mod
    if "." in name:
        head, _, tail = name.rpartition("."); setattr(parents[head], tail, mod)

def _load(full, path):
    spec = importlib.util.spec_from_file_location(full, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    head, _, tail = full.rpartition("."); setattr(sys.modules[head], tail, mod)
    return mod

_load("vesuvius.ink_detection.models.input_padding", f"{ROOT}/ink_detection/models/input_padding.py")
_load("vesuvius.ink_detection.inference.inference_runtime", f"{ROOT}/ink_detection/inference/inference_runtime.py")
