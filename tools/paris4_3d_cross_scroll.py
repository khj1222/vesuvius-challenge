#!/usr/bin/env python3
"""paris4_3d_cross_scroll.py -- docs/34: the Paris4 3D ink model on held-out human-labelled scrolls.

Stages (pre-registration: docs/34, commit f9037dc):
    uv run --no-project --with "zarr>=3" --with numpy --with fsspec --with aiohttp --with requests \
        python tools/paris4_3d_cross_scroll.py labels        # level-2 ink labels + supervision -> data/ink_3d/labels
    $PY tools/paris4_3d_cross_scroll.py mesh                  # tifxyz x/y/z + meta.json -> data/ink_3d/mesh
    $PY tools/paris4_3d_cross_scroll.py windows               # 3 windows per segment, chosen from labels only
    $PY tools/paris4_3d_cross_scroll.py check                 # method checks 1-2 (labels equal openlabels9, CT alignment)
    $PY tools/paris4_3d_cross_scroll.py infer NAME [--repeat] # the branch's infer_volume per window
    $PY tools/paris4_3d_cross_scroll.py score                 # AUCs, controls, verdict
$PY = villa's ink-detection venv; infer needs G3PKG (a package dir holding the branch's paris4_3d_gambiarra, copied
byte for byte, under empty vesuvius/ and vesuvius/ink_detection/ __init__ files). License: MIT.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BUCKET = "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/"
DATA = ROOT / "data/ink_3d"
CFG = json.loads((DATA / "segments.json").read_text())
LABELS = DATA / "labels"
MESH = DATA / "mesh"
OUTS = DATA / "out"
RUNS = ROOT / "runs/paris4_3d"
OPENLABELS = ROOT / "data/ink_9um/labels/openlabels9/_npy"
PREDS = ROOT / "runs/ink9um_openlabels"
WEIGHTS = DATA / "models/raw_gambiarra/model.safetensors"
PRIMARY = ("pherc0841-w00", "pherc0841-ag144", "pherc0841-ag174", "pherc0009b-ag055")
SECONDARY = ("pherc0500p2-s1",)
CONTROL = "phercparis4-20230702185753"
TILE, NWIN, BAND, PAD = 256, 3, 12, 32


def http_get(url, rng=None, tries=6):
    import requests
    for k in range(tries):
        try:
            r = requests.get(url, headers={"Range": rng} if rng else None, timeout=120)
            if r.status_code in (403, 404):
                return None
            r.raise_for_status()
            return r.content
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


# ---------------------------------------------------------------- labels / mesh / windows
def labels(_a=None):
    import zarr
    LABELS.mkdir(parents=True, exist_ok=True)
    rep = {}
    for name, c in CFG.items():
        for kind in ("inklabels", "supervision"):
            arr = np.asarray(zarr.open_array(f"{BUCKET}{c['labels']}/{kind}.zarr/2", mode="r")[:])
            np.save(LABELS / f"{name}_{kind}.npy", arr)
            rep[f"{name}_{kind}"] = [list(arr.shape), int((arr > 0).sum())]
        print(name, rep[f"{name}_inklabels"], rep[f"{name}_supervision"], flush=True)
    (LABELS / "report.json").write_text(json.dumps(rep, indent=1))


def mesh(_a=None):
    for name, c in CFG.items():
        d = MESH / name
        d.mkdir(parents=True, exist_ok=True)
        for f in ("meta.json", "x.tif", "y.tif", "z.tif"):
            if not (d / f).exists():
                b = http_get(f"{BUCKET}{c['mesh']}/{f}")
                assert b is not None, (name, f)
                (d / f).write_bytes(b)
        print(name, json.loads((d / "meta.json").read_text())["scale"], flush=True)


def load_labels(name):
    ink = np.load(LABELS / f"{name}_inklabels.npy") > 0
    sup = np.load(LABELS / f"{name}_supervision.npy") > 0
    return ink, sup


def windows(_a=None):
    out = {}
    for name in CFG:
        ink, sup = load_labels(name)
        H, W = sup.shape
        cand = []
        for i in range(H // TILE):
            for j in range(W // TILE):
                s = sup[i * TILE:(i + 1) * TILE, j * TILE:(j + 1) * TILE]
                k = ink[i * TILE:(i + 1) * TILE, j * TILE:(j + 1) * TILE] & s
                n, p = int(s.sum()), int(k.sum())
                if n and p >= 0.1 * n and n - p >= 0.1 * n:
                    cand.append((-n, i, j, n, p))
        cand.sort()
        out[name] = [{"row": c[1] * TILE, "col": c[2] * TILE, "supervised": c[3], "ink": c[4]} for c in cand[:NWIN]]
        print(name, out[name], flush=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / "windows.json").write_text(json.dumps(out, indent=1))


# ---------------------------------------------------------------- geometry
class Mesh:
    def __init__(self, name):
        import tifffile
        d = MESH / name
        self.scale = json.loads((d / "meta.json").read_text())["scale"][0]
        self.xyz = np.stack([tifffile.imread(d / f"{a}.tif").astype(np.float64) for a in "zyx"], -1)  # (rows, cols, zyx)
        self.valid = np.all(self.xyz > 0, -1)

    def nodes(self, u_row, u_col, convention):
        s = self.scale
        if convention == "A":
            return u_row * s, u_col * s
        return (u_row + 0.5) * s - 0.5, (u_col + 0.5) * s - 0.5

    def point_normal(self, r, c):
        """Bilinear point and unit normal at node coords (r, c) (arrays); NaN where any corner is invalid."""
        R, C = self.valid.shape
        r0 = np.clip(np.floor(r).astype(int), 0, R - 2)
        c0 = np.clip(np.floor(c).astype(int), 0, C - 2)
        fr, fc = (r - r0)[..., None], (c - c0)[..., None]
        P = self.xyz
        p00, p01, p10, p11 = P[r0, c0], P[r0, c0 + 1], P[r0 + 1, c0], P[r0 + 1, c0 + 1]
        ok = self.valid[r0, c0] & self.valid[r0, c0 + 1] & self.valid[r0 + 1, c0] & self.valid[r0 + 1, c0 + 1]
        ok &= (r >= 0) & (c >= 0) & (r <= R - 1) & (c <= C - 1)
        p = (1 - fr) * ((1 - fc) * p00 + fc * p01) + fr * ((1 - fc) * p10 + fc * p11)
        dr = (1 - fc) * (p10 - p00) + fc * (p11 - p01)
        dc = (1 - fr) * (p01 - p00) + fr * (p11 - p10)
        n = np.cross(dr, dc)
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
        p[~ok] = np.nan
        n[~ok] = np.nan
        return p, n


def window_grid(win, center):
    """L0 canvas coords of the window's L2 pixels: 4i (+1.5 for the L2 block centre)."""
    i = np.arange(win["row"], win["row"] + TILE)
    j = np.arange(win["col"], win["col"] + TILE)
    off = 1.5 if center else 0.0
    return np.meshgrid(4 * i + off, 4 * j + off, indexing="ij")


# ---------------------------------------------------------------- method checks
class ChunkReader:
    """Uncompressed zarr v2 reader (whole chunks, cached)."""

    def __init__(self, url):
        self.url = url.rstrip("/")
        self.meta = json.loads(http_get(self.url + "/.zarray"))
        assert self.meta["compressor"] is None and self.meta["dtype"] == "|u1", self.meta
        self.shape, self.chunks = self.meta["shape"], self.meta["chunks"]
        self.sep = self.meta.get("dimension_separator", ".")
        self.cache = {}

    def chunk(self, key):
        if key not in self.cache:
            b = http_get(self.url + "/" + self.sep.join(map(str, key)))
            self.cache[key] = None if b is None else np.frombuffer(b, np.uint8).reshape(self.chunks)
        return self.cache[key]

    def fetch(self, keys):
        keys = [k for k in keys if k not in self.cache]
        with ThreadPoolExecutor(32) as ex:
            for k, v in zip(keys, ex.map(lambda k: http_get(self.url + "/" + self.sep.join(map(str, k))), keys)):
                self.cache[k] = None if v is None else np.frombuffer(v, np.uint8).reshape(self.chunks)

    def at(self, pts):
        """Nearest-voxel values at (..., 3) zyx points; 0 outside/absent/NaN."""
        q = np.rint(pts).astype(np.int64)
        good = np.all(np.isfinite(pts), -1) & np.all(q >= 0, -1) & np.all(q < np.array(self.shape), -1)
        out = np.zeros(pts.shape[:-1], np.float32)
        ch = np.array(self.chunks)
        keys = q[good] // ch
        uniq = {tuple(k) for k in keys}
        self.fetch(list(uniq))
        idx = np.argwhere(good)
        for (a, b), k, qq in zip(idx, keys, q[good]):
            arr = self.chunk(tuple(k))
            if arr is not None:
                r = qq - k * ch
                out[a, b] = arr[r[0], r[1], r[2]]
        return out


def surface_volume_l2(name, win):
    url = f"{BUCKET}{CFG[name]['surface_volume']}/2"
    meta = json.loads(http_get(url + "/.zarray"))
    nz = meta["shape"][0]
    z = nz // 2
    cz, cy, cx = meta["chunks"]
    sep = meta.get("dimension_separator", ".")
    out = np.zeros((TILE, TILE), np.float32)
    y0, x0 = win["row"], win["col"]
    for by in range(y0 // cy, (y0 + TILE - 1) // cy + 1):
        for bx in range(x0 // cx, (x0 + TILE - 1) // cx + 1):
            b = http_get(f"{url}/{sep.join(map(str, (z // cz, by, bx)))}")
            if b is None:
                continue
            if meta["compressor"] is not None:
                import numcodecs
                b = numcodecs.get_codec(meta["compressor"]).decode(b)
            arr = np.frombuffer(b, np.uint8).reshape(meta["chunks"])[z % cz]
            gy, gx = by * cy, bx * cx
            sy0, sx0, sy1, sx1 = max(y0, gy), max(x0, gx), min(y0 + TILE, gy + cy), min(x0 + TILE, gx + cx)
            out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = arr[sy0 - gy:sy1 - gy, sx0 - gx:sx1 - gx]
    return out, {"z": z, "nz": nz, "compressor": meta["compressor"]}


def phase_shift(ref, mov):
    from scipy import ndimage
    from skimage.registration import phase_cross_correlation

    def prep(a):
        m = (a > 0).astype(np.float32)
        blur = ndimage.gaussian_filter(a * m, 4) / np.maximum(ndimage.gaussian_filter(m, 4), 1e-6)
        return ((a - blur) * m * np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]).astype(np.float32)

    d, _, _ = phase_cross_correlation(prep(ref), prep(mov), upsample_factor=20)
    return [float(d[0]), float(d[1])]


def check(_a=None):
    res = {"labels_equal_openlabels9": {}, "ct_alignment": {}}
    for name in PRIMARY + SECONDARY:
        ink, sup = load_labels(name)
        oi = np.load(OPENLABELS / f"{name}_inklabels.npy") > 0
        os_ = np.load(OPENLABELS / f"{name}_supervision.npy") > 0
        res["labels_equal_openlabels9"][name] = bool(np.array_equal(ink, oi) and np.array_equal(sup, os_))
    wins = json.loads((RUNS / "windows.json").read_text())
    for name in (CONTROL,) + PRIMARY + SECONDARY:
        win = wins[name][0]
        m = Mesh(name)
        ct = ChunkReader(BUCKET + CFG[name]["ct"])
        sv, info = surface_volume_l2(name, win)
        rr, cc = window_grid(win, center=True)
        row = {"window": win, "surface_volume": info}
        for conv in ("A", "B"):
            p, _ = m.point_normal(*m.nodes(rr, cc, conv))
            img = ct.at(p)
            row[conv] = {"d": phase_shift(sv, img), "nonzero": float((img > 0).mean())}
        good = [cv for cv in ("A", "B") if all(abs(v) <= 1 for v in row[cv]["d"])]
        row["chosen"] = min(good, key=lambda cv: sum(abs(v) for v in row[cv]["d"])) if good else None
        res["ct_alignment"][name] = row
        print(name, {cv: row[cv]["d"] for cv in ("A", "B")}, "->", row["chosen"], flush=True)
        ct.cache.clear()
    (RUNS / "method_check.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["labels_equal_openlabels9"]))


# ---------------------------------------------------------------- inference
def local_ct(name):
    return DATA / "ct" / CFG[name]["ct"].replace("/", "__")


def band_units(name, win, conv):
    """64^3 output units within PAD output voxels of the window's band."""
    q1 = ((band_points(name, win, conv) - 0.5) / 2).reshape(-1, 3)
    b = np.floor(q1[np.all(np.isfinite(q1), 1)]).astype(np.int64)
    d = np.array([(i, j, k) for i in (-PAD, 0, PAD) for j in (-PAD, 0, PAD) for k in (-PAD, 0, PAD)])
    return np.unique(((b[:, None, :] + d[None]) // 64).reshape(-1, 3), axis=0)


def fetchct(_a=None):
    """Copy the level-0 chunks every band unit's crops read (parent256 context): unit t -> chunks t-2 .. t+2 per axis."""
    conv = json.loads((RUNS / "method_check.json").read_text())["ct_alignment"]
    wins = json.loads((RUNS / "windows.json").read_text())
    off = np.array([(i, j, k) for i in range(-2, 3) for j in range(-2, 3) for k in range(-2, 3)])
    per_ct = {}
    for name in CFG:
        for win in wins[name]:
            u = band_units(name, win, conv[name]["chosen"])
            per_ct.setdefault(CFG[name]["ct"], set()).update(map(tuple, np.unique((u[:, None] + off[None]).reshape(-1, 3), axis=0)))
    total = sum(len(v) for v in per_ct.values())
    print("chunks to copy:", {k: len(v) for k, v in per_ct.items()}, "total", total, flush=True)
    done = 0
    for ct, keys in per_ct.items():
        name = next(n for n in CFG if CFG[n]["ct"] == ct)
        root = local_ct(name)
        root.mkdir(parents=True, exist_ok=True)
        meta = json.loads(http_get(BUCKET + ct + "/.zarray"))
        (root / ".zarray").write_text(json.dumps(meta))
        shape = np.array(meta["shape"]) // np.array(meta["chunks"]) + 1
        todo = [k for k in sorted(keys) if all(0 <= k[a] < shape[a] for a in range(3))
                and not (root / "/".join(map(str, k))).exists()]

        def get(k):
            b = http_get(BUCKET + ct + "/" + "/".join(map(str, k)))
            if b is not None:
                f = root / "/".join(map(str, k))
                f.parent.mkdir(parents=True, exist_ok=True)
                tmp = f.with_suffix(".part")
                tmp.write_bytes(b)
                tmp.replace(f)
            return b is not None

        t0 = time.time()
        with ThreadPoolExecutor(48) as ex:
            for i, ok in enumerate(ex.map(get, todo), 1):
                if i % 500 == 0:
                    print(f"{ct}: {i}/{len(todo)} {(time.time() - t0) / 60:.1f} min", flush=True)
        done += len(todo)
        print(f"{ct}: copied {len(todo)} (others present or outside) in {(time.time() - t0) / 60:.1f} min", flush=True)


def band_points(name, win, conv):
    m = Mesh(name)
    rr, cc = window_grid(win, center=False)
    p, n = m.point_normal(*m.nodes(rr, cc, conv))
    t = np.arange(-BAND, BAND + 1, dtype=np.float64)
    return p[..., None, :] + t[None, None, :, None] * n[..., None, :]  # (TILE, TILE, 2*BAND+1, zyx) level 0


def infer(args):
    name = args[0]
    repeat = "--repeat" in args
    conv = json.loads((RUNS / "method_check.json").read_text())["ct_alignment"][name]["chosen"]
    assert conv, f"{name}: mapping failed, not run"
    wins = json.loads((RUNS / "windows.json").read_text())[name]
    env = dict(os.environ, PYTHONPATH=os.environ["G3PKG"])
    for k, win in enumerate(wins[:1] if repeat else wins):
        pts = band_points(name, win, conv)
        q1 = (pts - 0.5) / 2
        fin = np.all(np.isfinite(q1), -1)
        lo = np.floor(q1[fin].min(0)).astype(int) - PAD
        hi = np.ceil(q1[fin].max(0)).astype(int) + 1 + PAD
        out = OUTS / f"local_{name}_w{k}{'_repeat' if repeat else ''}"
        cmd = [sys.executable, "-m", "vesuvius.ink_detection.paris4_3d_gambiarra.infer_volume", "--weights", str(WEIGHTS),
               "--out", str(out), "--ct", str(local_ct(name)), "--box", *map(str, lo), *map(str, hi),
               "--unit", "64", "--chunk", "64", "--compressor", "none", "--batch", "16"]
        t0 = time.time()
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (out / "box.json").parent.mkdir(parents=True, exist_ok=True)
        (out / "box.json").write_text(json.dumps({"lo": lo.tolist(), "hi": hi.tolist(), "convention": conv,
                                                  "exit": proc.returncode, "minutes": (time.time() - t0) / 60}))
        print(f"{name} w{k}: exit {proc.returncode} box {lo.tolist()}..{hi.tolist()} {(time.time() - t0) / 60:.1f} min",
              flush=True)
        if proc.returncode:
            sys.exit(proc.stderr[-3000:])


# ---------------------------------------------------------------- scoring
class CodeVolume:
    def __init__(self, out):
        a = json.loads((out / "code.zarr/0/.zarray").read_text())
        self.root, self.shape, self.ch = out / "code.zarr/0", a["shape"], a["chunks"]
        self.sep = a.get("dimension_separator", ".")
        self.cache = {}

    def chunk(self, key):
        if key not in self.cache:
            f = self.root / self.sep.join(map(str, key))
            self.cache[key] = np.fromfile(f, np.uint8).reshape(self.ch) if f.exists() else None
        return self.cache[key]

    def logit(self, idx):
        """Decoded logit at integer level-1 indices (N, 3); NaN for code 0 or missing."""
        out = np.full(len(idx), np.nan, np.float32)
        ch = np.array(self.ch)
        good = np.all(idx >= 0, 1) & np.all(idx < np.array(self.shape), 1)
        keys = idx // ch
        for key in {tuple(k) for k in keys[good]}:
            arr = self.chunk(key)
            if arr is None:
                continue
            sel = good & np.all(keys == key, 1)
            r = idx[sel] - np.array(key) * ch
            c = arr[r[:, 0], r[:, 1], r[:, 2]].astype(np.float32)
            out[sel] = np.where(c == 0, np.nan, (c - 128) / 10 + 0.05)
        return out

    def trilinear(self, q):
        """Trilinear logit at level-1 coords q (N, 3); NaN if any corner is NaN."""
        f = np.floor(q).astype(np.int64)
        w = q - f
        acc = np.zeros(len(q), np.float64)
        for dz in (0, 1):
            for dy in (0, 1):
                for dx in (0, 1):
                    v = self.logit(f + np.array([dz, dy, dx]))
                    ww = (w[:, 0] if dz else 1 - w[:, 0]) * (w[:, 1] if dy else 1 - w[:, 1]) * (w[:, 2] if dx else 1 - w[:, 2])
                    acc += ww * v
        return acc


def auc(score, pos):
    from scipy.stats import rankdata
    ok = np.isfinite(score)
    s, y = score[ok], pos[ok]
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def window_maps(name, k, win, conv):
    cv = CodeVolume(OUTS / f"local_{name}_w{k}")
    pts = band_points(name, win, conv)
    q1 = ((pts - 0.5) / 2).reshape(-1, 3)
    fin = np.all(np.isfinite(q1), 1)
    v = np.full(len(q1), np.nan)
    v[fin] = cv.trilinear(q1[fin])
    v = v.reshape(TILE, TILE, 2 * BAND + 1)
    with np.errstate(all="ignore"):
        allnan = np.all(np.isnan(v), -1)
        mx = np.where(allnan, np.nan, np.nanmax(np.where(np.isnan(v), -np.inf, v), -1))
        mean = np.nanmean(v, -1)
    return {"max": mx, "t0": v[..., BAND], "mean": mean}


def baseline_map(name, model, win):
    import tifffile
    f = {"ink9um_s43": PREDS / "preds" / f"{name}_s43_075000.tif",
         "reader_v3": PREDS / "preds_docs33" / f"{name}_reader_v3.tif"}[model]
    a = tifffile.imread(f)
    return a[win["row"]:win["row"] + TILE, win["col"]:win["col"] + TILE].astype(np.float32)


def score(_a=None):
    wins = json.loads((RUNS / "windows.json").read_text())
    checks = json.loads((RUNS / "method_check.json").read_text())["ct_alignment"]
    rows = {}
    for name in (CONTROL,) + PRIMARY + SECONDARY:
        conv = checks[name]["chosen"]
        if conv is None:
            rows[name] = {"status": "mapping failed"}
            continue
        ink, sup = load_labels(name)
        acc = {key: [] for key in ("max", "t0", "mean", "neg", "lab", "ink9um_s43", "reader_v3")}
        for k, win in enumerate(wins[name]):
            sl = (slice(win["row"], win["row"] + TILE), slice(win["col"], win["col"] + TILE))
            lab, s = ink[sl], sup[sl]
            maps = window_maps(name, k, win, conv)
            for key in ("max", "t0", "mean"):
                acc[key].append(maps[key][s])
            acc["neg"].append(maps["max"][s])
            acc["lab"].append((lab[s], np.roll(lab, TILE // 2, 0)[s]))
            if name != CONTROL:
                for model in ("ink9um_s43", "reader_v3"):
                    acc[model].append(baseline_map(name, model, win)[s])
        y = np.concatenate([a for a, _ in acc["lab"]])
        yneg = np.concatenate([b for _, b in acc["lab"]])
        r = {"convention": conv, "n_supervised": int(len(y)), "ink_fraction": float(y.mean())}
        for key in ("max", "t0", "mean"):
            sc = np.concatenate(acc[key])
            r[f"auc_{key}"] = auc(sc, y)
            r[f"coverage_{key}"] = float(np.isfinite(sc).mean())
        r["auc_negative_control"] = auc(np.concatenate(acc["neg"]), yneg)
        if name != CONTROL:
            for model in ("ink9um_s43", "reader_v3"):
                r[f"auc_{model}"] = auc(np.concatenate(acc[model]), y)
        rows[name] = r
        print(name, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    ctrl = rows[CONTROL].get("auc_max", float("nan"))
    prim = [rows[n].get("auc_max", float("nan")) for n in PRIMARY]
    judged = [a for a in prim if np.isfinite(a)]
    verdict = "pipeline or protocol failure"
    if np.isfinite(ctrl) and ctrl >= 0.80:
        if sum(a >= 0.70 for a in judged) >= 3:
            verdict = "transfers"
        elif sum(a <= 0.60 for a in judged) >= 3:
            verdict = "does not transfer"
        else:
            verdict = "partial"
    comp = [rows[n]["auc_max"] - rows[n]["auc_ink9um_s43"] for n in PRIMARY if "auc_ink9um_s43" in rows[n]]
    summary = {"verdict": verdict, "control_auc": ctrl, "primary_auc": dict(zip(PRIMARY, prim)),
               "competitive": sum(d >= -0.02 for d in comp) >= 3, "better": sum(d >= 0.02 for d in comp) >= 3,
               "rows": rows}
    (RUNS / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    stage = sys.argv[1]
    {"labels": labels, "mesh": mesh, "windows": windows, "check": check, "fetchct": fetchct, "infer": infer,
     "score": score}[stage](sys.argv[2:])
