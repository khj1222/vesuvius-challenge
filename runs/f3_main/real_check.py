"""Confirm a REAL Windows failure lands in the retry gate, and what the user sees."""
import importlib.util, json, os, sys, tempfile, time
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "sw", r"D:/vw9/vesuvius/src/vesuvius/ink_detection/preprocessing/staged_write.py")
sw = importlib.util.module_from_spec(spec); spec.loader.exec_module(sw)

out = {"platform": sys.platform, "cases": []}
root = Path(tempfile.mkdtemp(prefix="f3main."))

# 1. a real handle held open inside the staged directory, never released
staged = root / "v.zarr.partial"; staged.mkdir()
chunk = staged / "0.0.0"; chunk.write_bytes(b"chunk")
output = root / "v.zarr"
handle = chunk.open("rb")
t0 = time.monotonic()
try:
    sw.publish_staged_output(staged, output, attempts=3, retry_delay=0.05)
    out["cases"].append({"case": "handle never released", "result": "published (unexpected)"})
except PermissionError as exc:
    out["cases"].append({
        "case": "handle never released",
        "winerror": getattr(exc, "winerror", None),
        "entered_retry_gate": getattr(exc, "winerror", None) in sw._SHARING_VIOLATION_WINERRORS,
        "seconds": round(time.monotonic() - t0, 3),
        "note": "\n".join(getattr(exc, "__notes__", [])),
        "staged_intact": (staged / "0.0.0").read_bytes() == b"chunk",
        "output_absent": not output.exists(),
    })
finally:
    handle.close()

# 2. same directory, now that nothing holds it
t0 = time.monotonic()
sw.publish_staged_output(staged, output)
out["cases"].append({"case": "after the handle closes", "published": (output / "0.0.0").read_bytes() == b"chunk",
                     "seconds": round(time.monotonic() - t0, 3)})

# 3. the process cwd inside the tree (the other Windows refusal)
staged2 = root / "w.zarr.partial"; staged2.mkdir(); (staged2 / "0.0.0").write_bytes(b"c")
cwd = os.getcwd(); os.chdir(staged2)
try:
    sw.publish_staged_output(staged2, root / "w.zarr", attempts=2, retry_delay=0.05)
    out["cases"].append({"case": "cwd inside", "result": "published (unexpected)"})
except PermissionError as exc:
    out["cases"].append({"case": "cwd inside", "winerror": getattr(exc, "winerror", None),
                         "entered_retry_gate": getattr(exc, "winerror", None) in sw._SHARING_VIOLATION_WINERRORS})
finally:
    os.chdir(cwd)
print(json.dumps(out, indent=1))
