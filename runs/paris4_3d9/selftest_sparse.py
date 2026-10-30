"""Synthetic check of the docs/35 sparse loop: blended values at sampled voxels equal a dense brute-force blend over
every crop of the grid, with net_fn = identity on the normalised crop (pool 1) and a 2x avg-pool (pool 2)."""
import itertools
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, r"E:\vesuvius-challenge\tools")
import paris4_3d_9um_finetune as T  # noqa: E402
from vesuvius.ink_detection.paris4_3d_gambiarra import volume as V  # noqa: E402


class FakeStore:
    def __init__(self, vol):
        self.vol = vol
        self.shape = vol.shape

    def present(self, lo, hi):
        return True

    def region(self, lo, size):
        out = np.zeros((size,) * 3, np.uint8)
        src = [slice(max(lo[i], 0), min(lo[i] + size, self.shape[i])) for i in range(3)]
        dst = tuple(slice(src[i].start - lo[i], src[i].stop - lo[i]) for i in range(3))
        out[dst] = self.vol[tuple(src)]
        return out


def dense(store, pool, net_fn):
    shp = [-(-s // pool) for s in store.shape]
    num = np.zeros(shp)
    den = np.zeros(shp)
    g = V.gaussian()
    axes = T.crop_axes(store.shape, pool)
    for a in itertools.product(*axes):
        im, _, _ = T.normalized_crop(store, [pool * v for v in a], pool)
        y = net_fn(torch.from_numpy(im)[None, None].cuda())[0, 0].cpu().numpy()
        sl = tuple(slice(v, v + 64) for v in a)
        num[sl] += (g * y).astype(np.float64)
        den[sl] += g
    with np.errstate(all="ignore"):
        return np.where(den > 0, (num / den).astype(np.float32), np.nan)


rng = np.random.default_rng(0)
res = {}
for pool, size in ((1, 200), (2, 400)):
    vol = rng.integers(0, 256, (size,) * 3).astype(np.uint8)
    st = FakeStore(vol)
    fn = (lambda x: x) if pool == 1 else (lambda x: torch.nn.functional.avg_pool3d(x, 2))
    ref = dense(st, pool, fn)
    out_shape = ref.shape
    # random sample points with normals, inside the covered region
    q = rng.uniform(70, out_shape[0] - 70, (300, 3))
    n = rng.normal(size=(300, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    v, nc = T.band_values(st, pool, fn, q, n)
    pts = (q[:, None, :] + T.TS[None, :, None] * n[:, None, :]).reshape(-1, 3)
    from scipy.ndimage import map_coordinates
    want = map_coordinates(ref.astype(np.float64), pts.T, order=1, mode="nearest").reshape(v.shape)
    res[pool] = {"max_abs_diff": float(np.nanmax(np.abs(v - want))), "nan": int(np.isnan(v).sum()), "crops": nc}
    print(pool, res[pool], flush=True)
assert all(r["max_abs_diff"] < 1e-5 and r["nan"] == 0 for r in res.values()), res
print("PASS")
