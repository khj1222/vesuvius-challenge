"""Run the whole prepare script on a synthetic volume, patched and unpatched."""
import json, subprocess, sys, tempfile, shutil
from pathlib import Path
import numpy as np, zarr

SCRIPTS = {"patched": "D:/vw8/ink-detection/scripts/prepare_9um_isotropic_input.py"}

def build_source(root: Path) -> Path:
    src = root / "src.zarr"
    rng = np.random.default_rng(0)
    data = rng.integers(0, 255, size=(84, 300, 260), dtype=np.uint8)   # 84 = 21 * POOL_Z
    g = zarr.open_group(str(src), mode="w")
    g.create_dataset("0", data=data, chunks=(84, 128, 128), dtype=np.uint8)
    return src, data

out = {}
for name, script in SCRIPTS.items():
    root = Path(tempfile.mkdtemp(prefix="f3e2e."))
    src, data = build_source(root)
    dst = root / "out.zarr"
    proc = subprocess.run([sys.executable, script, str(src), str(dst), "--level", "0", "--workers", "4"],
                          capture_output=True, text=True)
    entry = {"returncode": proc.returncode, "tail": proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr.strip()[-160:]}
    if dst.exists():
        arr = zarr.open_group(str(dst), mode="r")["0"]
        entry["shape"] = list(arr.shape)
        expected = np.rint(data.reshape(21, 4, 300, 260).mean(axis=1)).astype(np.uint8)
        entry["bytes_match_expected_pooling"] = bool(np.array_equal(np.asarray(arr[:]), expected))
        entry["staging_left_behind"] = (root / "out.zarr.partial").exists()
    out[name] = entry
    shutil.rmtree(root, ignore_errors=True)
print(json.dumps(out, indent=1))
