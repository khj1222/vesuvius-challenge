"""When the backend works, the wrapper must get out of the way after one forward."""
import json, logging, torch
from koine_machines.inference import infer

class Cap(logging.Handler):
    def __init__(self): super().__init__(); self.msgs=[]
    def emit(self, r): self.msgs.append(r.getMessage())

cap = Cap(); infer.LOGGER.addHandler(cap); infer.LOGGER.setLevel(logging.INFO)

class CountingCompiled(torch.nn.Module):
    """Stands in for a backend that compiles fine."""
    def __init__(self, inner): super().__init__(); self.inner = inner; self.calls = 0
    def forward(self, *a, **k):
        self.calls += 1
        return self.inner(*a, **k)

eager = torch.nn.Conv3d(1, 1, 3, padding=1).eval()
stub = CountingCompiled(eager)
real_compile = torch.compile
torch.compile = lambda model, **kwargs: stub          # a backend that works
try:
    wrapped = infer.maybe_compile_model(eager, enabled=True, mode="reduce-overhead")
finally:
    torch.compile = real_compile

x = torch.zeros(1, 1, 8, 16, 16)
with torch.inference_mode():
    out1 = wrapped(x); out2 = wrapped(x); out3 = wrapped(x)

print(json.dumps({
    "returned_type": type(wrapped).__name__,
    "compiled_calls": stub.calls,
    "verified_flag": getattr(wrapped, "_compiled_verified", None),
    "outputs_match_eager": bool(torch.equal(out1, eager(x)) and torch.equal(out3, eager(x))),
    "fallback_warnings": [m for m in cap.msgs if "failed" in m.lower()],
}, indent=1))
