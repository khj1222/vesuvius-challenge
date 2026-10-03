#!/usr/bin/env python3
"""fiber9_check.py -- the docs/28 run: how much of a 2.4 um fiber reading survives at 9 um?

PHerc. 0139 segments carry one tifxyz mesh on the native 9.362 um scan and one on the
2.399 um scan. Each mesh keeps a vertex every 20 voxels of its own scan, so native grid index
(i, j) maps to (i * (H2-1)/(H1-1), j * (W2-1)/(W1-1)) on the 2.399 um grid.

``uv-check`` tests that correspondence without any fiber model: it renders the same 3 mm
surface window from both scans (2.399 um read at level 2) and reports the normalised
cross-correlation of the high-passed images at the mapped points, at shifted points, for a
window 12 vertices away, and on a fine shift grid. This is gate G1 of docs/28.

    E:/envs/fiber9/Scripts/python.exe tools/fiber9_check.py uv-check w035 w040 w044

Meshes are downloaded once into runs/fiber9/meshes/ (gitignored).

License: MIT.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runs" / "fiber9"
BUCKET = "vesuvius-challenge-open-data"
HTTP = f"https://{BUCKET}.s3.amazonaws.com"
SCROLL = "PHerc0139"
VOL_NATIVE = f"{BUCKET}/{SCROLL}/volumes/20250728140407-9.362um-1.2m-113keV-masked.zarr"
VOL_HIRES = f"{BUCKET}/{SCROLL}/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr"
SEGMENTS = {
    "w035": "20260317000000-w035_2026031718",
    "w039": "20260302000000-w039_2026030210",
    "w040": "20250831000000-w040_2025083102",
    "w041": "20260108000000-w041_2026010816",
    "w044": "20260115000000-w044_2026011522",
}
MESH_NATIVE = "on-20250728140407-9.362um"
MESH_HIRES = "on-20260102150214-2.399um"
NOMINAL_RATIO = 9.362 / 2.399


def mesh_dir(seg: str, which: str) -> Path:
    return OUT / "meshes" / f"{seg}-{which}"


def fetch_mesh(seg: str, which: str) -> np.ndarray:
    """Return the tifxyz vertex grid as (H, W, 3) float64 in xyz voxel units of its scan."""
    import tifffile

    d = mesh_dir(seg, which)
    d.mkdir(parents=True, exist_ok=True)
    seg_id = SEGMENTS[seg]
    stem = f"{seg_id.split('-')[0]}-{which}.tifxyz"
    for name in ("x.tif", "y.tif", "z.tif", "meta.json"):
        p = d / name
        if not p.exists():
            url = f"{HTTP}/{SCROLL}/segments/{seg_id}/mesh/{stem}/{name}"
            urllib.request.urlretrieve(url, p)
    return np.stack([tifffile.imread(d / f"{c}.tif") for c in "xyz"], -1).astype(np.float64)


def valid(m: np.ndarray) -> np.ndarray:
    return np.isfinite(m).all(-1) & (m[..., 2] > 0)


def bilinear(grid: np.ndarray, ii: np.ndarray, jj: np.ndarray) -> np.ndarray:
    from scipy.ndimage import map_coordinates

    out = np.empty(ii.shape + (3,))
    for c in range(3):
        out[..., c] = map_coordinates(grid[..., c], [ii, jj], order=1, mode="nearest")
    return out


class Block:
    """One remote zarr block read once and sampled many times."""

    def __init__(self, vol: str, level: int, pts_zyx: np.ndarray, pad: int = 3):
        import s3fs
        import zarr

        arr = zarr.open(s3fs.S3Map(f"{vol}/{level}", s3=s3fs.S3FileSystem(anon=True)), mode="r")
        flat = pts_zyx.reshape(-1, 3)
        self.lo = np.maximum(np.floor(flat.min(0)).astype(int) - pad, 0)
        hi = np.ceil(flat.max(0)).astype(int) + pad + 1
        self.data = arr[self.lo[0]:hi[0], self.lo[1]:hi[1], self.lo[2]:hi[2]].astype(np.float32)

    def sample(self, pts_zyx: np.ndarray) -> np.ndarray:
        from scipy.ndimage import map_coordinates

        rel = (pts_zyx - self.lo).reshape(-1, 3).T
        return map_coordinates(self.data, rel, order=1, mode="nearest").reshape(pts_zyx.shape[:-1])


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    from scipy.ndimage import gaussian_filter

    a = a - gaussian_filter(a, 8)
    b = b - gaussian_filter(b, 8)
    a = (a - a.mean()) / (a.std() + 1e-9)
    b = (b - b.mean()) / (b.std() + 1e-9)
    return float((a * b).mean())


def uv_check(seg: str, up: int = 8, w: int = 16) -> dict:
    n, h = fetch_mesh(seg, MESH_NATIVE), fetch_mesh(seg, MESH_HIRES)
    vn = valid(n)
    ry, rx = (h.shape[0] - 1) / (n.shape[0] - 1), (h.shape[1] - 1) / (n.shape[1] - 1)
    ci, cj = np.argwhere(vn).mean(0).astype(int)
    i0, j0 = ci - w // 2, cj - w // 2
    if not vn[i0:i0 + w, j0:j0 + w].all():
        raise SystemExit(f"{seg}: central {w}-vertex window is not fully valid on the native mesh")
    ii, jj = np.meshgrid(np.arange(w * up) / up + i0, np.arange(w * up) / up + j0, indexing="ij")

    def hires_pts(sh=(0.0, 0.0), scale=None):
        sy, sx = scale or (ry, rx)
        return bilinear(h, ii * sy + sh[0], jj * sx + sh[1])[..., ::-1] / 4.0  # level 2

    coarse = [(0, 4), (4, 0), (0, -4), (-4, 0), (0, 16), (16, 0)]
    fine = [(float(dy), float(dx)) for dy in np.arange(-2, 2.01, 0.5) for dx in np.arange(-2, 2.01, 0.5)]
    far = (12 * ry, 0.0)
    nominal = (NOMINAL_RATIO, NOMINAL_RATIO)
    pn = bilinear(n, ii, jj)[..., ::-1]
    ph_all = [hires_pts(s) for s in [(0.0, 0.0)] + coarse + fine + [far]] + [hires_pts(scale=nominal)]
    bn = Block(VOL_NATIVE, 0, pn)
    bh = Block(VOL_HIRES, 2, np.concatenate([p.reshape(-1, 3) for p in ph_all]))
    a = bn.sample(pn)
    at = ncc(a, bh.sample(hires_pts()))
    fine_scores = sorted(((ncc(a, bh.sample(hires_pts(s))), s) for s in fine), reverse=True)
    res = {
        "segment": seg,
        "grid_native": list(n.shape[:2]),
        "grid_hires": list(h.shape[:2]),
        "ratio": [round(ry, 4), round(rx, 4)],
        "ncc_mapped": round(at, 4),
        "ncc_shift_one_vertex": {str(s): round(ncc(a, bh.sample(hires_pts(s))), 4) for s in coarse},
        "ncc_far_window": round(ncc(a, bh.sample(hires_pts(far))), 4),
        "ncc_nominal_ratio": round(ncc(a, bh.sample(hires_pts(scale=nominal))), 4),
        "fine_best": [{"ncc": round(v, 4), "shift": list(s)} for v, s in fine_scores[:3]],
    }
    best = fine_scores[0][1]
    res["g1_pass"] = bool(at >= 0.5 and abs(best[0]) <= 1 and abs(best[1]) <= 1)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("uv-check", help="gate G1: do the two meshes share a UV parametrisation?")
    p.add_argument("segments", nargs="*", default=list(SEGMENTS))
    p.add_argument("--out", default=None, help="write results as JSON here")
    args = ap.parse_args()

    if args.cmd == "uv-check":
        results = []
        for seg in args.segments:
            r = uv_check(seg)
            results.append(r)
            print(json.dumps(r), flush=True)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
