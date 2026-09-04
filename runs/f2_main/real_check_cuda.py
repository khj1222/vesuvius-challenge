"""Same check on the CUDA path, where the backend needs Triton."""
import importlib.util, json, logging, sys, types
import torch
from torch import nn
ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius","vesuvius.ink_detection","vesuvius.ink_detection.models","vesuvius.ink_detection.inference"):
    m = types.ModuleType(name); m.__path__=[]; sys.modules[name]=m; parents[name]=m
    if "." in name:
        h,_,t=name.rpartition("."); setattr(parents[h],t,m)
def _load(full,path):
    s=importlib.util.spec_from_file_location(full,path); mo=importlib.util.module_from_spec(s)
    sys.modules[full]=mo; s.loader.exec_module(mo)
    h,_,t=full.rpartition("."); setattr(sys.modules[h],t,mo); return mo
_load("vesuvius.ink_detection.models.input_padding", f"{ROOT}/ink_detection/models/input_padding.py")
rt=_load("vesuvius.ink_detection.inference.inference_runtime", f"{ROOT}/ink_detection/inference/inference_runtime.py")
recs=[]
class C(logging.Handler):
    def emit(self,r): recs.append(r.getMessage())
logging.getLogger("vesuvius.ink_detection.inference.inference_runtime").addHandler(C())
out={"device":"cuda","cuda":torch.cuda.is_available()}
if not torch.cuda.is_available():
    print(json.dumps({**out,"skipped":"no cuda"},indent=1)); raise SystemExit
torch.manual_seed(0)
eager=nn.Sequential(nn.Conv2d(1,4,3,padding=1),nn.ReLU(),nn.Conv2d(4,1,3,padding=1)).eval().cuda()
batch=torch.randn(2,1,16,16,device="cuda")
with torch.no_grad(): expected=eager(batch)
model,enabled=rt.maybe_compile_model(eager,enabled=True,mode="reduce-overhead")
out["compile_returned_without_raising"]=True
with torch.no_grad():
    first=model(batch); second=model(batch)
out["first_matches_eager"]=torch.allclose(first,expected,atol=1e-6)
out["second_matches_eager"]=torch.allclose(second,expected,atol=1e-6)
out["fell_back"]=any("first forward" in m for m in recs)
out["error_class_in_warning"]=recs[0].split("(",1)[1][:60] if recs else None
out["mentions_triton"]=any("riton" in m for m in recs)
print(json.dumps(out,indent=1))
