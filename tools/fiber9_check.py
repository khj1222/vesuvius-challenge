#!/usr/bin/env python3
"""fiber9_check.py -- the docs/28 run: how much of a 2.4 um fiber reading survives at 9 um?

PHerc. 0139 segments carry one tifxyz mesh on the native 9.362 um scan and one on the
2.399 um scan. Each mesh keeps a vertex every 20 voxels of its own scan, so native grid index
(i, j) maps to (i * (H2-1)/(H1-1), j * (W2-1)/(W1-1)) on the 2.399 um grid.

``uv-check`` tests that correspondence without any fiber model: it renders the same 3 mm
surface window from both scans (2.399 um read at level 2) and reports the normalised
cross-correlation of the high-passed images at the mapped points, at shifted points, for a
window 12 vertices away, and on a fine shift grid. This is gate G1 of docs/28.

``tiles`` draws the tiles, ``run`` runs arms A/B (nnUNet, 9.362 um) and the reference R
(villa scripts/fiber_5class, 2.399 um) on every tile and saves the sampled label stacks
(resumable), and ``score`` evaluates gates G2/G3 and hypotheses H1-H3, then packs the 2-D
maps every score reads into runs/fiber9/fiber9_maps.npz.

    E:/envs/fiber9/Scripts/python.exe tools/fiber9_check.py uv-check --out runs/fiber9/g1.json
    E:/envs/fiber9/Scripts/python.exe tools/fiber9_check.py tiles
    E:/envs/fiber9/Scripts/python.exe tools/fiber9_check.py run
    E:/envs/fiber9/Scripts/python.exe tools/fiber9_check.py score

Environment: Python 3.12, torch 2.11.0+cu128, nnunetv2 2.8.1, zarr 2.18.7, plus pynrrd and a
sparse checkout of villa main (vesuvius/src and scripts/fiber_5class) at VILLA_MAIN.
Meshes, checkpoints and tiles are downloaded or written under runs/fiber9/ (gitignored).

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


# --------------------------------------------------------------------------- tiles, run, score

TILE = 96  # native voxels per tile side
STEP = 20  # native voxels per mesh vertex (tifxyz scale 0.05)
PER_SEG = 20
SEED = 20261003
DEPTH_N, DEPTH_H = 10, 39  # largest normal offset sampled: native / 2.399 um voxels (both ~94 um)
WINDOWS = {"19um": (2, 8), "47um": (5, 20), "94um": (10, 39)}  # (native, 2.399 um) half-widths
PRIMARY_WINDOW = "47um"
CTX_N, CTX_H = 32, 64  # context beyond the deepest sample, per side
MIN_CROP = 256
MODELS = OUT / "models"
ARMS = {
    "A": MODELS / "scrollprize__fiber_hz_vt",
    "B": MODELS / "Qualzz20__afv_fiber_9um",
}
REF_CKPT = MODELS / "scrollprize__fiber_ink_4class_selfdistill" / "p4_4class_ddp8_20260526_step029000.pth"
VILLA_MAIN = Path("D:/vw13")  # sparse worktree of villa origin/main (vesuvius/, scripts/fiber_5class/)


def vertex_normals(g: np.ndarray) -> np.ndarray:
    gi, gj = np.gradient(g, axis=0), np.gradient(g, axis=1)
    nrm = np.cross(gi, gj)
    return nrm / (np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-9)


def select_tiles() -> dict:
    """Draw PER_SEG non-overlapping tiles per segment, one rng over the segments in order."""
    rng = np.random.default_rng(SEED)
    span = (TILE - 1) / STEP
    out = {}
    for seg in SEGMENTS:
        n, h = fetch_mesh(seg, MESH_NATIVE), fetch_mesh(seg, MESH_HIRES)
        vn, vh = valid(n), valid(h)
        ry, rx = (h.shape[0] - 1) / (n.shape[0] - 1), (h.shape[1] - 1) / (n.shape[1] - 1)
        cands = []
        for i0 in range(1, n.shape[0]):
            for j0 in range(1, n.shape[1]):
                i1, j1 = int(np.ceil(i0 + span)) + 1, int(np.ceil(j0 + span)) + 1  # one vertex margin for normals
                if i1 >= n.shape[0] or j1 >= n.shape[1] or not vn[i0 - 1:i1 + 1, j0 - 1:j1 + 1].all():
                    continue
                hi0, hi1 = int(np.floor((i0 - 1) * ry)), int(np.ceil(i1 * ry)) + 1
                hj0, hj1 = int(np.floor((j0 - 1) * rx)), int(np.ceil(j1 * rx)) + 1
                if hi1 >= h.shape[0] or hj1 >= h.shape[1] or not vh[hi0:hi1 + 1, hj0:hj1 + 1].all():
                    continue
                cands.append((i0, j0))
        chosen: list[tuple[int, int]] = []
        for k in rng.permutation(len(cands)):
            i0, j0 = cands[k]
            if all(abs(i0 - a) >= 5 or abs(j0 - b) >= 5 for a, b in chosen):
                chosen.append((i0, j0))
                if len(chosen) == PER_SEG:
                    break
        out[seg] = {"candidates": len(cands), "tiles": [list(t) for t in chosen]}
        print(seg, "candidates", len(cands), "chosen", len(chosen), flush=True)
    return out


def tile_points(seg: str, i0: int, j0: int):
    """Surface points and unit normals (zyx) of one tile on both meshes."""
    n, h = fetch_mesh(seg, MESH_NATIVE), fetch_mesh(seg, MESH_HIRES)
    ry, rx = (h.shape[0] - 1) / (n.shape[0] - 1), (h.shape[1] - 1) / (n.shape[1] - 1)
    k = np.arange(TILE) / STEP
    ii, jj = np.meshgrid(i0 + k, j0 + k, indexing="ij")
    pn = bilinear(n, ii, jj)[..., ::-1]
    nn = bilinear(vertex_normals(n), ii, jj)[..., ::-1]
    ph = bilinear(h, ii * ry, jj * rx)[..., ::-1]
    nh = bilinear(vertex_normals(h), ii * ry, jj * rx)[..., ::-1]
    nn /= np.linalg.norm(nn, axis=-1, keepdims=True) + 1e-9
    nh /= np.linalg.norm(nh, axis=-1, keepdims=True) + 1e-9
    return pn, nn, ph, nh


def depth_stack(p: np.ndarray, nrm: np.ndarray, depth: int) -> np.ndarray:
    d = np.arange(-depth, depth + 1, dtype=np.float64)[:, None, None, None]
    return p[None] + d * nrm[None]  # (2*depth+1, TILE, TILE, 3) zyx


def read_crop(vol: str, pts: np.ndarray, ctx: int):
    """Read the box around pts (zyx) plus ctx, at least MIN_CROP per axis; zero-pad outside the volume."""
    import s3fs
    import zarr

    arr = zarr.open(s3fs.S3Map(f"{vol}/0", s3=s3fs.S3FileSystem(anon=True)), mode="r")
    flat = pts.reshape(-1, 3)
    lo = np.floor(flat.min(0)).astype(int) - ctx
    hi = np.ceil(flat.max(0)).astype(int) + ctx + 1
    grow = np.maximum(MIN_CROP - (hi - lo), 0)
    lo -= grow // 2
    hi += grow - grow // 2
    shape = np.array(arr.shape)
    slo, shi = np.maximum(lo, 0), np.minimum(hi, shape)
    crop = np.zeros(tuple(hi - lo), dtype=np.uint8)
    crop[tuple(slice(a - l, b - l) for a, b, l in zip(slo, shi, lo))] = arr[slo[0]:shi[0], slo[1]:shi[1], slo[2]:shi[2]]
    return crop, lo


def nearest(crop_shape, lo, pts: np.ndarray) -> tuple:
    idx = np.rint(pts - lo).astype(int)
    for ax in range(3):
        idx[..., ax] = np.clip(idx[..., ax], 0, crop_shape[ax] - 1)
    return idx[..., 0], idx[..., 1], idx[..., 2]


class NnunetArm:
    """nnUNet 3d_fullres built from plans.json, weights from checkpoint_final.pth.

    Built by hand rather than through initialize_from_trained_model_folder because
    fiber_hz_vt's checkpoint names a custom trainer class (nnUNetTrainerMedialSurfaceRecall)
    that ships only with its training code; the trainer does not enter inference.
    """

    def __init__(self, folder: Path):
        import torch
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
        from nnunetv2.utilities.get_network_from_plans import get_network_from_plans
        from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

        plans = json.loads((folder / "plans.json").read_text())
        dataset_json = json.loads((folder / "dataset.json").read_text())
        pm = PlansManager(plans)
        cm = pm.get_configuration("3d_fullres")
        lm = pm.get_label_manager(dataset_json)
        net = get_network_from_plans(cm.network_arch_class_name, cm.network_arch_init_kwargs,
                                     cm.network_arch_init_kwargs_req_import, 1,
                                     lm.num_segmentation_heads, allow_init=True, deep_supervision=False)
        ckpt = torch.load(folder / "checkpoint_final.pth", map_location="cpu", weights_only=False)
        params = {k.replace("_orig_mod.", ""): v for k, v in ckpt["network_weights"].items()}
        net.load_state_dict(params)
        self.pred = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=True,
                                    perform_everything_on_device=True, device=torch.device("cuda"),
                                    verbose=False, verbose_preprocessing=False, allow_tqdm=False)
        self.pred.manual_initialization(net, pm, cm, [params], dataset_json, "nnUNetTrainer",
                                        tuple(ckpt.get("inference_allowed_mirroring_axes", (0, 1, 2))))
        self.trainer_name = ckpt.get("trainer_name")

    def __call__(self, crop: np.ndarray) -> np.ndarray:
        img = crop[None].astype(np.float32)
        seg = self.pred.predict_single_npy_array(img, {"spacing": [1.0, 1.0, 1.0]}, None, None, False)
        return np.asarray(seg, dtype=np.uint8)


class ReferenceModel:
    """fiber_ink_4class_selfdistill: villa scripts/fiber_5class NetworkFromConfig, EMA weights."""

    def __init__(self, ckpt_path: Path = REF_CKPT):
        import torch

        sys.path[:0] = [str(VILLA_MAIN / "vesuvius" / "src"), str(VILLA_MAIN / "scripts" / "fiber_5class")]
        from model import build_fiber_unet  # villa scripts/fiber_5class/model.py
        from dataset import percentile_minmax_normalize  # villa scripts/fiber_5class/dataset.py

        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        cfg = ckpt["config"]
        net = build_fiber_unet(crop_size=tuple(cfg["patch_size"]), target_name=cfg["target_name"],
                               out_channels=cfg["out_channels"], activation=cfg["activation"],
                               in_channels=cfg["in_channels"])
        net.load_state_dict(ckpt["ema"]["model_state"])
        self.net = net.cuda().eval()
        self.target = cfg["target_name"]
        self.patch = int(cfg["patch_size"][0])
        self.norm = percentile_minmax_normalize
        self.torch = torch

    def __call__(self, crop: np.ndarray, idx: tuple) -> np.ndarray:
        """Average softmax over every 256^3 window (stride 128) that contains a sample point."""
        torch = self.torch
        P, S = self.patch, self.patch // 2
        pts = np.stack(idx, -1).reshape(-1, 3)
        acc = np.zeros((len(pts), 4), np.float64)
        cnt = np.zeros(len(pts), np.int64)
        starts = []
        for ax in range(3):
            s = list(range(0, crop.shape[ax] - P + 1, S))
            if s[-1] != crop.shape[ax] - P:
                s.append(crop.shape[ax] - P)
            starts.append(s)
        for z in starts[0]:
            for y in starts[1]:
                for x in starts[2]:
                    o = np.array([z, y, x])
                    inside = np.all((pts >= o) & (pts < o + P), axis=1)
                    if not inside.any():
                        continue
                    win = self.norm(crop[z:z + P, y:y + P, x:x + P]).astype(np.float32)
                    t = torch.from_numpy(win)[None, None].cuda()
                    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                        out = self.net(t)
                    logits = out[self.target] if isinstance(out, dict) else out
                    prob = torch.softmax(logits.float(), dim=1)[0]
                    q = torch.from_numpy(pts[inside] - o).cuda()
                    acc[inside] += prob[:, q[:, 0], q[:, 1], q[:, 2]].T.cpu().numpy()
                    cnt[inside] += 1
        prob = acc / np.maximum(cnt, 1)[:, None]
        return prob.reshape(idx[0].shape + (4,)).astype(np.float32), cnt.reshape(idx[0].shape)


def run_tiles(tiles: dict, segments: list[str]) -> None:
    import time

    tdir = OUT / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    arms = {name: NnunetArm(folder) for name, folder in ARMS.items()}
    ref = ReferenceModel()
    for seg in segments:
        for t, (i0, j0) in enumerate(tiles[seg]["tiles"]):
            dst = tdir / f"{seg}_{t:02d}.npz"
            if dst.exists():
                continue
            t0 = time.time()
            pn, nn, ph, nh = tile_points(seg, i0, j0)
            sn, sh = depth_stack(pn, nn, DEPTH_N), depth_stack(ph, nh, DEPTH_H)
            crop_n, lo_n = read_crop(VOL_NATIVE, sn, CTX_N)
            idx_n = nearest(crop_n.shape, lo_n, sn)
            labels = {name: arm(crop_n)[idx_n] for name, arm in arms.items()}
            crop_h, lo_h = read_crop(VOL_HIRES, sh, CTX_H)
            idx_h = nearest(crop_h.shape, lo_h, sh)
            prob_r, cnt_r = ref(crop_h, idx_h)
            np.savez_compressed(
                dst, A=labels["A"], B=labels["B"], R=prob_r.argmax(-1).astype(np.uint8),
                R_prob=prob_r.astype(np.float16), R_windows=cnt_r.astype(np.uint8),
                raw_native=crop_n[idx_n], raw_hires=crop_h[idx_h],
                tile=np.array([i0, j0]), crop_native=np.array([*lo_n, *crop_n.shape]),
                crop_hires=np.array([*lo_h, *crop_h.shape]))
            print(f"{seg} tile {t:02d} ({i0},{j0}) native crop {crop_n.shape} hires crop {crop_h.shape} "
                  f"{time.time() - t0:.0f}s", flush=True)


def f1_tol(a: np.ndarray, r: np.ndarray, tol: int):
    """Presence F1 with an 8-neighbourhood tolerance of tol pixels; None if both maps are empty."""
    from scipy.ndimage import binary_dilation

    if not a.any() and not r.any():
        return None
    st = np.ones((3, 3), bool)
    ad = binary_dilation(a, st, iterations=tol) if tol else a
    rd = binary_dilation(r, st, iterations=tol) if tol else r
    prec = (a & rd).sum() / a.sum() if a.any() else 0.0
    rec = (r & ad).sum() / r.sum() if r.any() else 0.0
    f1 = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    return float(f1), float(prec), float(rec)


def maps(stack: np.ndarray, half: int, kind: str) -> dict:
    """Collapse a (depth, TILE, TILE) label stack over the central +-half window to 2-D maps."""
    c = stack.shape[0] // 2
    w = stack[c - half:c + half + 1]
    if kind == "arm":  # 1 vertical, 2 horizontal, 3 intersection
        return {"fiber": np.isin(w, (1, 2, 3)).any(0), "vt": np.isin(w, (1, 3)).any(0), "hz": np.isin(w, (2, 3)).any(0)}
    return {"fiber": np.isin(w, (1, 2)).any(0), "vt": (w == 1).any(0), "hz": (w == 2).any(0)}  # 3 = ink


def derangement(n: int, rng) -> np.ndarray:
    while True:
        p = rng.permutation(n)
        if not (p == np.arange(n)).any():
            return p


def boot_ci(values_by_seg: dict, stat=np.mean, n_boot: int = 10000, seed: int = SEED):
    """95% percentile interval of stat over tiles, resampling tiles within each segment."""
    rng = np.random.default_rng(seed)
    segs = [np.asarray(v, float) for v in values_by_seg.values() if len(v)]
    point = float(stat(np.concatenate(segs)))
    draws = np.empty(n_boot)
    for b in range(n_boot):
        draws[b] = stat(np.concatenate([s[rng.integers(0, len(s), len(s))] for s in segs]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return point, float(lo), float(hi)


def score(segments: list[str]) -> dict:
    import csv

    from scipy.stats import spearmanr

    tdir = OUT / "tiles"
    data = {seg: sorted(tdir.glob(f"{seg}_*.npz")) for seg in segments}
    tiles = {seg: [dict(np.load(p)) for p in paths] for seg, paths in data.items()}
    rows = []
    rng = np.random.default_rng(SEED)
    perms = {seg: derangement(len(tiles[seg]), rng) for seg in segments}
    for seg in segments:
        for t, d in enumerate(tiles[seg]):
            for wname, (hn, hh) in WINDOWS.items():
                r = maps(d["R"], hh, "ref")
                r_null = maps(tiles[seg][perms[seg][t]]["R"], hh, "ref")
                row = {"segment": seg, "tile": t, "window": wname,
                       "ref_fiber_frac": float(r["fiber"].mean()), "ref_vt_frac": float(r["vt"].mean()),
                       "ref_hz_frac": float(r["hz"].mean())}
                for arm in ARMS:
                    a = maps(d[arm], hn, "arm")
                    row[f"{arm}_fiber_frac"] = float(a["fiber"].mean())
                    for tol in (0, 1, 2):
                        f = f1_tol(a["fiber"], r["fiber"], tol)
                        fnull = f1_tol(a["fiber"], r_null["fiber"], tol)
                        row[f"{arm}_f1_t{tol}"] = None if f is None else f[0]
                        row[f"{arm}_prec_t{tol}"] = None if f is None else f[1]
                        row[f"{arm}_rec_t{tol}"] = None if f is None else f[2]
                        row[f"{arm}_null_f1_t{tol}"] = None if fnull is None else fnull[0]
                    for cls_a, cls_r, tag in (("vt", "vt", "vt"), ("hz", "hz", "hz"), ("vt", "hz", "vt_swap"), ("hz", "vt", "hz_swap")):
                        f = f1_tol(a[cls_a], r[cls_r], 1)
                        row[f"{arm}_{tag}_f1_t1"] = None if f is None else f[0]
                rows.append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "fiber9_tiles.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def col(name, window=PRIMARY_WINDOW, tiles_ok=None):
        out = {}
        for seg in segments:
            vals = [r[name] for r in rows if r["segment"] == seg and r["window"] == window]
            out[seg] = vals
        return out

    def paired(f, window=PRIMARY_WINDOW, keys=()):
        """Per segment list of f(row) over tiles where every key is defined."""
        out = {}
        for seg in segments:
            out[seg] = [f(r) for r in rows if r["segment"] == seg and r["window"] == window
                        and all(r[k] is not None for k in keys)]
        return out

    prim = [r for r in rows if r["window"] == PRIMARY_WINDOW]
    summary = {"tiles_per_segment": {s: len(tiles[s]) for s in segments}}
    # G2
    ff = np.array([r["ref_fiber_frac"] for r in prim])
    vt = np.array([r["ref_vt_frac"] for r in prim])
    hz = np.array([r["ref_hz_frac"] for r in prim])
    summary["G2"] = {"median_ref_fiber_frac": float(np.median(ff)), "median_ref_vt_frac": float(np.median(vt)),
                     "median_ref_hz_frac": float(np.median(hz)),
                     "pass": bool(0.05 <= np.median(ff) <= 0.95 and np.median(vt) >= 0.02 and np.median(hz) >= 0.02)}
    # G3
    def mean_def(key):
        v = [r[key] for r in prim if r[key] is not None]
        return float(np.mean(v)) if v else float("nan")
    direct = np.nanmean([mean_def("A_vt_f1_t1"), mean_def("A_hz_f1_t1")])
    swapped = np.nanmean([mean_def("A_vt_swap_f1_t1"), mean_def("A_hz_swap_f1_t1")])
    summary["G3"] = {"A_direct": float(direct), "A_swapped": float(swapped), "pass": bool(direct > swapped)}
    excluded = sum(1 for r in prim if r["A_f1_t1"] is None or r["B_f1_t1"] is None)
    summary["tiles_excluded_both_empty"] = excluded

    res = {}
    for wname in WINDOWS:
        for tol in (0, 1, 2):
            key = f"{wname}_t{tol}"
            entry = {}
            for arm in ARMS:
                k, kn = f"{arm}_f1_t{tol}", f"{arm}_null_f1_t{tol}"
                entry[f"{arm}_f1"] = boot_ci(paired(lambda r: r[k], wname, (k,)))
                entry[f"{arm}_null"] = boot_ci(paired(lambda r: r[kn], wname, (kn,)))
                entry[f"{arm}_minus_null"] = boot_ci(paired(lambda r: r[k] - r[kn], wname, (k, kn)))
            ka, kb = f"A_f1_t{tol}", f"B_f1_t{tol}"
            diff = paired(lambda r: r[kb] - r[ka], wname, (ka, kb))
            entry["B_minus_A"] = boot_ci(diff)
            entry["B_minus_A_by_segment"] = {s: float(np.mean(v)) for s, v in diff.items() if v}
            res[key] = entry
    summary["results"] = res

    prim_key = f"{PRIMARY_WINDOW}_t1"
    e = res[prim_key]
    summary["H1"] = {arm: {"mean_minus_null": e[f"{arm}_minus_null"], "pass": e[f"{arm}_minus_null"][1] > 0} for arm in ARMS}
    signs = np.sign(list(e["B_minus_A_by_segment"].values()))
    _, lo, hi = e["B_minus_A"]
    if lo > 0 and (signs > 0).sum() >= 4:
        verdict = "helps"
    elif hi < 0 and (signs < 0).sum() >= 4:
        verdict = "hurts"
    else:
        verdict = "no measurable difference"
    summary["H2"] = {"B_minus_A": e["B_minus_A"], "by_segment": e["B_minus_A_by_segment"], "verdict": verdict}

    pairs = paired(lambda r: (r["ref_fiber_frac"], r["B_rec_t1"]), PRIMARY_WINDOW, ("B_rec_t1",))
    allp = np.array([p for v in pairs.values() for p in v])
    rho = float(spearmanr(allp[:, 0], allp[:, 1]).statistic)
    rngb = np.random.default_rng(SEED)
    segp = [np.array(v) for v in pairs.values() if len(v)]
    draws = []
    for _ in range(10000):
        s = np.concatenate([v[rngb.integers(0, len(v), len(v))] for v in segp])
        draws.append(spearmanr(s[:, 0], s[:, 1]).statistic)
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    summary["H3"] = {"spearman_rho": rho, "ci": [float(lo), float(hi)], "pass": bool(hi < 0)}
    if summary["G3"]["pass"]:
        summary["per_class_t1"] = {f"{arm}_{c}": boot_ci(paired(lambda r, k=f"{arm}_{c}_f1_t1": r[k], PRIMARY_WINDOW, (f"{arm}_{c}_f1_t1",)))
                                   for arm in ARMS for c in ("vt", "hz")}
    (OUT / "fiber9_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def export_maps(segments: list[str]) -> Path:
    """Pack the 2-D maps every score reads into one small file (the tiles are ~500 MB)."""
    out = {}
    for seg in segments:
        for p in sorted((OUT / "tiles").glob(f"{seg}_*.npz")):
            d = np.load(p)
            for wname, (hn, hh) in WINDOWS.items():
                for src, half, kind in (("A", hn, "arm"), ("B", hn, "arm"), ("R", hh, "ref")):
                    for cls, m in maps(d[src], half, kind).items():
                        out[f"{p.stem}/{wname}/{src}/{cls}"] = np.packbits(m)
            out[f"{p.stem}/tile"] = d["tile"]
    dst = OUT / "fiber9_maps.npz"
    np.savez_compressed(dst, tile_shape=np.array([TILE, TILE]), **out)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("uv-check", help="gate G1: do the two meshes share a UV parametrisation?")
    p.add_argument("segments", nargs="*", default=list(SEGMENTS))
    p.add_argument("--out", default=None, help="write results as JSON here")
    sub.add_parser("tiles", help="draw the tiles (writes runs/fiber9/tiles.json)")
    p = sub.add_parser("run", help="run arms A, B and reference R on every tile (resumable)")
    p.add_argument("segments", nargs="*", default=None)
    p = sub.add_parser("score", help="gates G2/G3 and H1-H3 from the saved tiles")
    p.add_argument("segments", nargs="*", default=None)
    args = ap.parse_args()

    if args.cmd == "tiles":
        t = select_tiles()
        (OUT / "tiles.json").write_text(json.dumps(t, indent=2) + "\n", encoding="utf-8")
        return
    if args.cmd in ("run", "score"):
        g1 = json.loads((OUT / "g1.json").read_text())
        segs = args.segments or [r["segment"] for r in g1 if r["g1_pass"]]
        if args.cmd == "run":
            run_tiles(json.loads((OUT / "tiles.json").read_text()), segs)
        else:
            print(json.dumps(score(segs), indent=2))
            print("maps:", export_maps(segs))
        return
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
