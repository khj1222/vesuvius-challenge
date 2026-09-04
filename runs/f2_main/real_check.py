"""Point main's patched maybe_compile_model at the REAL torch.compile on this box."""
import importlib.util, json, logging, sys, types, platform
import torch
from torch import nn

ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius", "vesuvius.ink_detection", "vesuvius.ink_detection.models",
             "vesuvius.ink_detection.inference"):
    m = types.ModuleType(name); m.__path__ = []; sys.modules[name] = m; parents[name] = m
    if "." in name:
        h, _, t = name.rpartition("."); setattr(parents[h], t, m)
def _load(full, path):
    spec = importlib.util.spec_from_file_location(full, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[full] = mod
    spec.loader.exec_module(mod)
    h, _, t = full.rpartition("."); setattr(sys.modules[h], t, mod); return mod
_load("vesuvius.ink_detection.models.input_padding", f"{ROOT}/ink_detection/models/input_padding.py")
rt = _load("vesuvius.ink_detection.inference.inference_runtime", f"{ROOT}/ink_detection/inference/inference_runtime.py")

records = []
class Capture(logging.Handler):
    def emit(self, record): records.append(record.getMessage())
logging.getLogger("vesuvius.ink_detection.inference.inference_runtime").addHandler(Capture())

out = {"platform": platform.platform(), "python": sys.version.split()[0],
       "torch": torch.__version__, "cuda_available": torch.cuda.is_available()}
try:
    import triton  # noqa: F401
    out["triton_importable"] = True
except Exception as exc:
    out["triton_importable"] = False
    out["triton_import_error"] = type(exc).__name__

torch.manual_seed(0)
eager = nn.Sequential(nn.Conv2d(1, 4, 3, padding=1), nn.ReLU(), nn.Conv2d(4, 1, 3, padding=1)).eval()
batch = torch.randn(2, 1, 16, 16)
with torch.no_grad():
    expected = eager(batch)

model, enabled = rt.maybe_compile_model(eager, enabled=True, mode="reduce-overhead")
out["compile_returned_without_raising"] = True
out["maybe_compile_model_flag"] = enabled
out["wrapper_type"] = type(model).__name__

with torch.no_grad():
    first = model(batch)
    second = model(batch)
out["first_forward_matches_eager"] = torch.allclose(first, expected, atol=1e-6)
out["second_forward_matches_eager"] = torch.allclose(second, expected, atol=1e-6)
out["fell_back"] = any("first forward" in m for m in records)
out["warnings"] = records
out["compiled_dropped_after_failure"] = model._compiled_model is None
print(json.dumps(out, indent=1))
