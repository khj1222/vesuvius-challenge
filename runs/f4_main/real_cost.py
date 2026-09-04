"""Cost of the fingerprint on the real w00 label assets, and the scandir-vs-stat gap."""
import importlib.util, json, os, sys, time, types
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
pc=_load("vesuvius.ink_detection.data.patch_cache", f"{ROOT}/ink_detection/data/patch_cache.py")

seg = Path(r"D:/vesuvius-challenge/data/ink-dataset/phercparis4/w00_20231016151002")
assets = [seg/"w00_20231016151002_inklabels.zarr", seg/"w00_20231016151002_supervision_mask.zarr"]
counts = {a.name: sum(1 for _ in a.rglob("*") if _.is_file()) for a in assets}

def stat_based(paths):          # the obvious implementation, for comparison
    import hashlib
    d=hashlib.sha256()
    for p in sorted(str(x) for x in paths if x):
        for f in sorted(Path(p).rglob("*")):
            if f.is_file():
                d.update(str(f).encode()); d.update(str(f.stat().st_size).encode())
    return d.hexdigest()[:16]

def timed(fn, *a, n=5):
    fn(*a)                       # warm the OS cache so we time the walk, not the disk
    best = min(( (lambda t0: (fn(*a), time.perf_counter()-t0)[1])(time.perf_counter()) ) for _ in range(n))
    return round(best*1000, 1)

runs = [{"fingerprint_ms": timed(pc.label_asset_fingerprint, assets),
          "path_stat_equivalent_ms": timed(stat_based, assets)} for _ in range(5)]
fp = sorted(r["fingerprint_ms"] for r in runs)
st = sorted(r["path_stat_equivalent_ms"] for r in runs)
out = {
 "files_per_asset": counts,
 "repeats": 5,
 "fingerprint_ms_range": [fp[0], fp[-1]],
 "path_stat_equivalent_ms_range": [st[0], st[-1]],
 "runs": runs,
 "files_total": sum(counts.values()),
 "fingerprint_ms": timed(pc.label_asset_fingerprint, assets),
 "path_stat_equivalent_ms": timed(stat_based, assets),
 "digest": pc.label_asset_fingerprint(assets),
 "stable_across_calls": pc.label_asset_fingerprint(assets) == pc.label_asset_fingerprint(assets),
 "order_independent": pc.label_asset_fingerprint(assets) == pc.label_asset_fingerprint(assets[::-1]),
}
print(json.dumps(out, indent=1))
