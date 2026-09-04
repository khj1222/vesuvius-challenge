"""F2: torch.compile returns fine and the backend fails at the first forward. Real CUDA."""
import importlib.util, logging, sys, types, traceback
import torch
from torch import nn

ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius","vesuvius.ink_detection","vesuvius.ink_detection.models","vesuvius.ink_detection.inference"):
    m = types.ModuleType(name); m.__path__=[]; sys.modules[name]=m; parents[name]=m
    if "." in name:
        h,_,t=name.rpartition("."); setattr(parents[h],t,m)
def _load(full, path):
    s=importlib.util.spec_from_file_location(full,path); mo=importlib.util.module_from_spec(s)
    sys.modules[full]=mo; s.loader.exec_module(mo)
    h,_,t=full.rpartition("."); setattr(sys.modules[h],t,mo); return mo
_load("vesuvius.ink_detection.models.input_padding", f"{ROOT}/ink_detection/models/input_padding.py")
rt=_load("vesuvius.ink_detection.inference.inference_runtime", f"{ROOT}/ink_detection/inference/inference_runtime.py")
logging.basicConfig(level=logging.WARNING, stream=sys.stdout, format="  %(levelname)s  %(message)s")

torch.manual_seed(0)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = nn.Sequential(nn.Conv2d(1,4,3,padding=1), nn.ReLU(), nn.Conv2d(4,1,3,padding=1)).eval().to(dev)
batch = torch.randn(2,1,16,16, device=dev)
with torch.no_grad():
    expected = model(batch)
print(f"  device={dev}   torch={torch.__version__}   triton importable=", end="")
try:
    import triton; print("True")
except Exception: print("False")

print()
print("=" * 78)
print(" BEFORE  --  main today: torch.compile(), then the first forward")
print("=" * 78)
compiled = torch.compile(model, mode="reduce-overhead", fullgraph=False, dynamic=False)
print("  torch.compile() returned without raising  <- the except in maybe_compile_model")
print("                                               guards THIS call, and it did not fail")
try:
    with torch.no_grad():
        compiled(batch)
    print("  first forward ok (unexpected)")
except Exception:
    exc = sys.exc_info()[1]
    cls = f"{type(exc).__module__}.{type(exc).__name__}"
    first = str(exc).strip().splitlines()[0]
    print("  first forward raised:")
    print(f"    {cls}")
    print(f"    {first}")
    print("  -> inference stops here, part way through a run")

print()
print("=" * 78)
print(" AFTER   --  this PR: the first forward is guarded")
print("=" * 78)
guarded, enabled = rt.maybe_compile_model(model, enabled=True, mode="reduce-overhead")
print(f"  maybe_compile_model -> {type(guarded).__name__}, compile set up = {enabled}")
with torch.no_grad():
    first = guarded(batch); second = guarded(batch)
print(f"  forward 1 matches uncompiled output : {torch.allclose(first, expected, atol=1e-6)}")
print(f"  forward 2 matches uncompiled output : {torch.allclose(second, expected, atol=1e-6)}")
print(f"  compiled module dropped after the failure : {guarded._compiled_model is None}")
print("  -> the run continues")
