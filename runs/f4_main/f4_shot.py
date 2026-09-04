"""F4: a real label asset edited in place, before and after this PR. Real w00 labels."""
import importlib.util, shutil, subprocess, sys, tempfile, time, types
from dataclasses import replace
from pathlib import Path
import os
BASE = os.environ.get("SHOT_TMP", r"D:/shots/tmp")

VW9 = r"D:/vw9/vesuvius/src/vesuvius"
REAL = Path(r"D:/vesuvius-challenge/data/ink-dataset/phercparis4/w00_20231016151002")
ASSET = REAL / "w00_20231016151002_inklabels.zarr"

def build(tag, patch_cache_source):
    """Load config/types plus one patch_cache implementation under a private package name."""
    pkg = f"vx{tag}"
    parents = {}
    for name in (pkg, f"{pkg}.ink_detection", f"{pkg}.ink_detection.data"):
        m = types.ModuleType(name); m.__path__ = []; sys.modules[name] = m; parents[name] = m
        if "." in name:
            h, _, t = name.rpartition("."); setattr(parents[h], t, m)
    def load(full, path):
        s = importlib.util.spec_from_file_location(full, path)
        mo = importlib.util.module_from_spec(s); sys.modules[full] = mo; s.loader.exec_module(mo)
        h, _, t = full.rpartition("."); setattr(sys.modules[h], t, mo); return mo
    # patch_cache imports these by the real package name, so alias it for the duration
    for real, alias in ((f"{pkg}", "vesuvius"),):
        pass
    return load, pkg

# patch_cache.py imports `vesuvius.ink_detection.*`, so only one implementation can be live at
# a time. Run each half in its own subprocess instead.
HALF = r'''
import importlib.util, os, shutil, sys, tempfile, types
from dataclasses import replace
from pathlib import Path
impl, tag = sys.argv[1], sys.argv[2]
ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius","vesuvius.ink_detection","vesuvius.ink_detection.data"):
    m = types.ModuleType(name); m.__path__=[]; sys.modules[name]=m; parents[name]=m
    if "." in name:
        h,_,t=name.rpartition("."); setattr(parents[h],t,m)
def load(full, path):
    s=importlib.util.spec_from_file_location(full,path); mo=importlib.util.module_from_spec(s)
    sys.modules[full]=mo; s.loader.exec_module(mo)
    h,_,t=full.rpartition("."); setattr(sys.modules[h],t,mo); return mo
cfg=load("vesuvius.ink_detection.config", f"{ROOT}/ink_detection/config.py")
typ=load("vesuvius.ink_detection.types", f"{ROOT}/ink_detection/types.py")
pc =load("vesuvius.ink_detection.data.patch_cache", impl)

work = Path(tempfile.mkdtemp(prefix="f4shot.", dir=os.environ.get("SHOT_TMP", r"D:/shots/tmp")))
asset = work / "w00_inklabels.zarr"
shutil.copytree(sys.argv[3], asset)
n = sum(1 for p in asset.rglob("*") if p.is_file())

config = cfg.InkDataConfig.from_mapping({
    "mode":"flat","patch_size":[3,2,2],"patch_overlap":0.5,"patch_min_labeled_coverage":0.0,
    "image_normalization":"none","out_dir":str(work),"dataloader_workers":1,
    "datasets":[{"segments_path":str(work),"volume_scale":0}]})
seg = typ.Segment(data_config=config, source=config.datasets[0], dataset_idx=0,
                  segment_relpath="w00_20231016151002", segment_dir=work,
                  segment_name="w00_20231016151002", image_volume="w00.zarr",
                  inklabels=asset)
cache = work / "patches.json"
pc.save_patch_cache(cache, [typ.Patch(segment=seg, bbox=(0,0,0,3,2,2)),
                           typ.Patch(segment=seg, bbox=(0,2,2,3,4,4))])
hit = pc.load_patch_cache(cache, config=config, segments=[seg])
print(f"  real asset copied: {n:,} files from w00_20231016151002_inklabels.zarr")
print(f"  discovery cached  : {len(hit)} patches")
victims = sorted(p for p in asset.rglob("*") if p.is_file() and p.name[0].isdigit())[:40]
for v in victims: v.unlink()
print(f"  edited IN PLACE   : removed {len(victims)} chunks, same path, same name")
again = pc.load_patch_cache(cache, config=config, segments=[seg])
if again is None:
    print(f"  cache lookup      : REJECTED -> rediscovery runs against the labels that exist")
else:
    print(f"  cache lookup      : still returns {len(again)} patches  <-- STALE")
shutil.rmtree(work, ignore_errors=True)
'''
work = Path(tempfile.mkdtemp(prefix="f4half.", dir=BASE))
half = work / "half.py"; half.write_text(HALF, encoding="utf-8")
main_impl = work / "patch_cache_main.py"
main_impl.write_bytes(subprocess.run(
    ["git","-C",r"D:/vw9","show","origin/main:vesuvius/src/vesuvius/ink_detection/data/patch_cache.py"],
    capture_output=True).stdout)
branch_impl = f"{VW9}/ink_detection/data/patch_cache.py"

print("=" * 78, flush=True); print(" BEFORE  --  main today: the cache is keyed on label PATHS", flush=True); print("=" * 78, flush=True)
subprocess.run([sys.executable, str(half), str(main_impl), "before", str(ASSET)])
print("", flush=True); print("=" * 78, flush=True); print(" AFTER   --  this PR: the labels are fingerprinted too", flush=True); print("=" * 78, flush=True)
subprocess.run([sys.executable, str(half), branch_impl, "after", str(ASSET)])
shutil.rmtree(work, ignore_errors=True)
