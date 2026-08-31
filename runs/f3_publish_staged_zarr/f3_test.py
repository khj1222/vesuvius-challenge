"""Three things publish_partial has to do, checked against the real function."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import threading
import time
from pathlib import Path

SCRIPT = Path("D:/vw8/ink-detection/scripts/prepare_9um_isotropic_input.py")

spec = importlib.util.spec_from_file_location("prepare_9um", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
publish_partial = module.publish_partial


def staged_pair() -> tuple[Path, Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="f3test."))
    staged = root / "out.zarr.partial"
    staged.mkdir()
    (staged / "chunk.0.0").write_bytes(b"payload")
    return root, staged, root / "out.zarr"


results: list[dict[str, object]] = []

# 1. nothing held: publishes immediately
root, staged, output = staged_pair()
started = time.perf_counter()
publish_partial(staged, output)
results.append({
    "case": "nothing held",
    "published": output.is_dir() and (output / "chunk.0.0").read_bytes() == b"payload",
    "seconds": round(time.perf_counter() - started, 3),
})
shutil.rmtree(root, ignore_errors=True)

# 2. a handle released shortly after: retries, then publishes
root, staged, output = staged_pair()
handle = open(staged / "chunk.0.0", "rb")
threading.Timer(0.8, handle.close).start()
started = time.perf_counter()
try:
    publish_partial(staged, output)
    outcome = "published after retrying"
except SystemExit:
    outcome = "gave up"
results.append({
    "case": "handle released after 0.8 s",
    "outcome": outcome,
    "published": output.is_dir(),
    "seconds": round(time.perf_counter() - started, 3),
})
handle.close()
shutil.rmtree(root, ignore_errors=True)

# 3. a handle never released: fails with an actionable message, not a traceback
root, staged, output = staged_pair()
handle = open(staged / "chunk.0.0", "rb")
started = time.perf_counter()
try:
    publish_partial(staged, output, attempts=3, delay=0.05)
    message = "(no error raised)"
    kind = "none"
except SystemExit as exc:
    message = str(exc)
    kind = "SystemExit"
except Exception as exc:  # noqa: BLE001
    message = str(exc)
    kind = type(exc).__name__
results.append({
    "case": "handle never released",
    "raised": kind,
    "says_nothing_needs_recomputing": "Nothing needs recomputing" in message,
    "names_both_paths": str(staged) in message and str(output) in message,
    "staging_dir_still_intact": staged.is_dir() and (staged / "chunk.0.0").is_file(),
    "seconds": round(time.perf_counter() - started, 3),
})
handle.close()
shutil.rmtree(root, ignore_errors=True)

print(json.dumps(results, indent=1))
