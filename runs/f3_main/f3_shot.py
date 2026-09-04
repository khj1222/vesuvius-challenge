"""F3: the rename Windows refuses, before and after this PR. Real filesystem, real errors."""
import importlib.util, sys, tempfile, threading, time, types
from pathlib import Path
import os
BASE = os.environ.get("SHOT_TMP", r"D:/shots/tmp")

ROOT = r"D:/vw9/vesuvius/src/vesuvius"
parents = {}
for name in ("vesuvius", "vesuvius.ink_detection", "vesuvius.ink_detection.preprocessing"):
    m = types.ModuleType(name); m.__path__ = []; sys.modules[name] = m; parents[name] = m
    if "." in name:
        h, _, t = name.rpartition("."); setattr(parents[h], t, m)
spec = importlib.util.spec_from_file_location(
    "vesuvius.ink_detection.preprocessing.staged_write",
    f"{ROOT}/ink_detection/preprocessing/staged_write.py")
sw = importlib.util.module_from_spec(spec); spec.loader.exec_module(sw)

def stage(root, name):
    d = root / f"{name}.zarr.partial"; d.mkdir()
    (d / ".zarray").write_bytes(b"{}")
    (d / "0.0.0").write_bytes(b"a completed chunk")
    return d, root / f"{name}.zarr"

root = Path(tempfile.mkdtemp(prefix="f3shot.", dir=BASE))
print("=" * 78)
print(" BEFORE  --  main today:  staged.replace(output)")
print("=" * 78)
staged, out = stage(root, "before")
handle = (staged / "0.0.0").open("rb")          # something holds one file inside
try:
    staged.replace(out)
    print("  published (unexpected)")
except PermissionError as exc:
    import os as _os
    print(f"  PermissionError: [WinError {exc.winerror}] {exc.strerror}"
          f"   (errno {exc.errno}: {_os.strerror(exc.errno)})")
    print(f"  output exists? {out.exists()}      staged left behind? {staged.exists()}")
    print("  -> every chunk was already written; the traceback does not say so")
handle.close()

print()
print("=" * 78)
print(" AFTER   --  this PR:  publish_staged_output(), handle released 0.4s in")
print("=" * 78)
staged, out = stage(root, "after")
h = (staged / "0.0.0").open("rb")
threading.Thread(target=lambda: (time.sleep(0.4), h.close())).start()
t0 = time.monotonic()
sw.publish_staged_output(staged, out, retry_delay=0.2)
print(f"  published after {time.monotonic() - t0:.2f}s")
print(f"  output exists? {out.exists()}      chunk intact? {(out / '0.0.0').read_bytes()!r}")

print()
print("=" * 78)
print(" AFTER   --  handle never released: it says the work is not lost")
print("=" * 78)
staged, out = stage(root, "never")
keep = (staged / "0.0.0").open("rb")
try:
    sw.publish_staged_output(staged, out, attempts=3, retry_delay=0.05)
except PermissionError as exc:
    print(f"  PermissionError: [WinError {exc.winerror}]")
    for note in getattr(exc, "__notes__", []):
        for line in note.splitlines():
            print(f"    {line}")
    print(f"  staged intact? {(staged / '0.0.0').exists()}      output created? {out.exists()}")
keep.close()
