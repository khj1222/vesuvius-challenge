"""Decoded-pixel comparison of exported channels against the TIFFs segment_ink fed in."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

src_dir, exp_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
grid = tifffile.imread(src_dir / "x.tif").shape
rep = {"grid": list(grid), "files": {}}
ok = True
for s_path in sorted(src_dir.glob("*.tif")):
    f = exp_dir / s_path.name
    if not f.is_file():
        rep["files"][f.name] = {"identical": False, "note": "missing from export"}
        ok = False
        continue
    e = tifffile.imread(f)
    s = tifffile.imread(s_path)
    same = s.shape == e.shape and s.dtype == e.dtype and bool(np.array_equal(s, e, equal_nan=s.dtype.kind == "f"))
    ok &= same
    rep["files"][f.name] = {"shape": list(e.shape), "dtype": str(e.dtype), "identical": same,
                            "pixel_sha256_16": hashlib.sha256(np.ascontiguousarray(e).tobytes()).hexdigest()[:16],
                            "px_per_grid_step": [e.shape[0] / grid[0], e.shape[1] / grid[1]]}
meta = json.loads((exp_dir / "meta.json").read_text(encoding="utf-8"))
rep["exported_uuid"] = meta.get("uuid")
rep["all_identical"] = ok
out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
print(json.dumps(rep, indent=1))
