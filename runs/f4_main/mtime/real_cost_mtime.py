"""Cost of the fingerprint on the real w00 label assets, with mtime vs the size-only version it replaces."""
import importlib.util, json, sys, time, types
from pathlib import Path
ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius","vesuvius.ink_detection","vesuvius.ink_detection.data"):
    m=types.ModuleType(name); m.__path__=[]; sys.modules[name]=m; parents[name]=m
    if "." in name:
        h,_,t=name.rpartition("."); setattr(parents[h],t,m)
def _load(full,path):
    s=importlib.util.spec_from_file_location(full,path); mo=importlib.util.module_from_spec(s)
    sys.modules[full]=mo; s.loader.exec_module(mo)
    h,_,t=full.rpartition("."); setattr(sys.modules[h],t,mo); return mo
_load("vesuvius.ink_detection.config", f"{ROOT}/ink_detection/config.py")
_load("vesuvius.ink_detection.types", f"{ROOT}/ink_detection/types.py")
new=_load("vesuvius.ink_detection.data.patch_cache", f"{ROOT}/ink_detection/data/patch_cache.py")
old=_load("vesuvius.ink_detection.data.patch_cache_sizeonly", str(Path(__file__).parent/"patch_cache_sizeonly.py"))

seg = Path(r"E:/vesuvius-challenge/data/ink-dataset/phercparis4/w00_20231016151002")
assets = [seg/"w00_20231016151002_inklabels.zarr", seg/"w00_20231016151002_supervision_mask.zarr"]
counts = {a.name: sum(1 for _ in a.rglob("*") if _.is_file()) for a in assets}

def timed(fn, *a, n=5):
    fn(*a)
    best = min(( (lambda t0: (fn(*a), time.perf_counter()-t0)[1])(time.perf_counter()) ) for _ in range(n))
    return round(best*1000, 1)

runs = [{"size_mtime_ms": timed(new.label_asset_fingerprint, assets),
         "size_only_ms": timed(old.label_asset_fingerprint, assets)} for _ in range(5)]
a = sorted(r["size_mtime_ms"] for r in runs); b = sorted(r["size_only_ms"] for r in runs)
out = {"files_per_asset": counts, "files_total": sum(counts.values()), "repeats": 5,
       "size_mtime_ms_range": [a[0], a[-1]], "size_only_ms_range": [b[0], b[-1]], "runs": runs,
       "digest_size_mtime": new.label_asset_fingerprint(assets),
       "stable_across_calls": new.label_asset_fingerprint(assets) == new.label_asset_fingerprint(assets),
       "order_independent": new.label_asset_fingerprint(assets) == new.label_asset_fingerprint(assets[::-1])}
print(json.dumps(out, indent=1))
