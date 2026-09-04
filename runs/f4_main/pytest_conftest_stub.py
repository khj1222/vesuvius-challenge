"""Load the ink_detection modules under test from their real files, without the package
__init__ chain (it pulls optional deps such as nrrd that are not installed here)."""
import importlib.util, sys, types
ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius", "vesuvius.ink_detection", "vesuvius.ink_detection.data"):
    m = types.ModuleType(name); m.__path__ = []; sys.modules[name] = m; parents[name] = m
    if "." in name:
        h, _, t = name.rpartition("."); setattr(parents[h], t, m)
def _load(full, path):
    s = importlib.util.spec_from_file_location(full, path)
    mo = importlib.util.module_from_spec(s); sys.modules[full] = mo
    s.loader.exec_module(mo)
    h, _, t = full.rpartition("."); setattr(sys.modules[h], t, mo); return mo
_load("vesuvius.ink_detection.config", f"{ROOT}/ink_detection/config.py")
_load("vesuvius.ink_detection.types", f"{ROOT}/ink_detection/types.py")
_load("vesuvius.ink_detection.data.patch_cache", f"{ROOT}/ink_detection/data/patch_cache.py")
