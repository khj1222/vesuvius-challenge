"""Partial local copy of PHerc0841 9.366 um level 0: only the 128^3 chunks within +-24 voxels of the w00
surface (bilinear 10x on the tifxyz grid). Uncompressed public S3 zarr v2; .zattrs announces level 0 only
(ink-sdk's CT preflight rejects announced levels that do not exist). Missing chunks read as fill 0."""
import json, sys, urllib.request, concurrent.futures as cf
from pathlib import Path
import numpy as np, tifffile
from scipy.ndimage import zoom
U = "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0841/volumes/20250821151531-9.366um-1.2m-113keV-masked.zarr"
SEG = Path("E:/vesuvius-challenge/data/a_lite/PHerc0841_w00/20260220213127-w00")
OUT = Path("E:/vesuvius-challenge/data/ct_partial/PHerc0841_20250821151531_w00band.zarr")
X, Y, Z = [tifffile.imread(SEG / f"{a}.tif").astype(np.float64) for a in "xyz"]
ok = zoom(((X != -1) & np.isfinite(X)).astype(float), 10, order=1) > 0.999
P = np.stack([zoom(Z, 10, order=1)[ok], zoom(Y, 10, order=1)[ok], zoom(X, 10, order=1)[ok]], 1)
m = 24; chunks = set()
for dz in (-m, 0, m):
    for dy in (-m, 0, m):
        for dx in (-m, 0, m):
            chunks.update(map(tuple, np.unique(np.floor((P + [dz, dy, dx]) / 128).astype(int), axis=0)))
chunks = sorted(c for c in chunks if min(c) >= 0)
print("chunks", len(chunks), flush=True)
(OUT / "0").mkdir(parents=True, exist_ok=True)
za = json.loads(urllib.request.urlopen(f"{U}/0/.zarray").read())
(OUT / "0" / ".zarray").write_text(json.dumps(za, indent=2))
(OUT / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
attrs = json.loads(urllib.request.urlopen(f"{U}/.zattrs").read())
ms = attrs["multiscales"][0]; ms["datasets"] = [d for d in ms["datasets"] if d["path"] == "0"]
attrs["partial_copy"] = {"source": U, "chunks": len(chunks), "margin_voxels": m, "mesh": str(SEG)}
(OUT / ".zattrs").write_text(json.dumps(attrs, indent=2))
def get(c):
    p = OUT / "0" / str(c[0]) / str(c[1]) / str(c[2])
    if p.is_file() and p.stat().st_size == 128 ** 3:
        return "skip"
    p.parent.mkdir(parents=True, exist_ok=True)
    for t in range(4):
        try:
            r = urllib.request.urlopen(f"{U}/0/{c[0]}/{c[1]}/{c[2]}", timeout=120)
            b = r.read()
            if len(b) != 128 ** 3:
                return f"size {len(b)}"
            tmp = p.with_suffix(".tmp"); tmp.write_bytes(b); tmp.replace(p); return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404"
        except Exception as e:
            err = e
    return f"fail {err}"
res = {}
with cf.ThreadPoolExecutor(32) as ex:
    for i, r in enumerate(ex.map(get, chunks)):
        res[r] = res.get(r, 0) + 1
        if i % 200 == 0:
            print(i, res, flush=True)
print("done", res, flush=True)
