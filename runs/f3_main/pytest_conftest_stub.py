"""Make `vesuvius.ink_detection.preprocessing.staged_write` importable without the
package __init__ chain, which pulls optional deps (nrrd) not installed here.
The module itself is loaded from its real file, unmodified."""
import importlib.util, sys, types

REAL = r"D:/vw9/vesuvius/src/vesuvius/ink_detection/preprocessing/staged_write.py"
parents = {}
for name in ("vesuvius", "vesuvius.ink_detection", "vesuvius.ink_detection.preprocessing"):
    mod = types.ModuleType(name); mod.__path__ = []
    sys.modules[name] = mod; parents[name] = mod
    if "." in name:                       # attach to parent so attribute walks work
        head, _, tail = name.rpartition(".")
        setattr(parents[head], tail, mod)
full = "vesuvius.ink_detection.preprocessing.staged_write"
spec = importlib.util.spec_from_file_location(full, REAL)
mod = importlib.util.module_from_spec(spec)
sys.modules[full] = mod
spec.loader.exec_module(mod)
setattr(parents["vesuvius.ink_detection.preprocessing"], "staged_write", mod)
