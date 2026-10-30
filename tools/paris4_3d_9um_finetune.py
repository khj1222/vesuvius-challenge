#!/usr/bin/env python3
"""paris4_3d_9um_finetune.py -- docs/35: the Paris4 3D ink model fine-tuned on 9.6 um CT (level 2), scored on
held-out human-labelled scrolls.

Stages (pre-registration: docs/35, commit 80411bb):
    $PY tools/paris4_3d_9um_finetune.py setup      # training segments (meshes, labels) -> data/ink_3d9
    $PY tools/paris4_3d_9um_finetune.py tiles      # training tiles, from labels only (seed 0, 3 M px per scroll)
    $PY tools/paris4_3d_9um_finetune.py check      # method checks 1-2: level-2 CT alignment, labels
    $PY tools/paris4_3d_9um_finetune.py pyramid    # method check 3 (reported): level 2 vs 4x4x4 means of level 0
    $PY tools/paris4_3d_9um_finetune.py chunks     # level-2 chunk lists (stops above 25 GiB)
    $PY tools/paris4_3d_9um_finetune.py fetch      # copy them locally
    $PY tools/paris4_3d_9um_finetune.py loopcheck  # rule (a): our loop on level 0 vs the branch's infer_volume codes
    $PY tools/paris4_3d_9um_finetune.py train ARM SEED [--steps N] [--smoke]   # ARM in A1, A2
    $PY tools/paris4_3d_9um_finetune.py infer ARM [SEED]                       # ARM in A0, A1, A2
    $PY tools/paris4_3d_9um_finetune.py score
$PY = villa's ink-detection venv with PYTHONPATH=$G3PKG (the branch's paris4_3d_gambiarra and models packages,
copied byte for byte under empty vesuvius/ and vesuvius/ink_detection/ __init__ files; see docs/34). License: MIT.

Geometry. Level-2 voxel j covers level-0 [4j, 4j + 4): q2 = (p0 - 1.5) / 4. A level-2 label pixel (i, j) samples the
mesh at canvas (4i, 4j) (node = canvas * 0.05 under convention A), as in docs/34. Band: t in {-3, -2.5, ..., 3}
level-2 voxels along the unit normal.
Crops (level 2, no pooling): output = input grid; origins grid_axes(size, 64) per axis, kept where the 128^3 parent
[a - 32, a + 96) lies inside the array; the crop [a, a + 64) is normalised by the parent's p1 / p99 (np.percentile,
linear); logits are blended with the branch's gaussian (sigma 8) in float64. With pool = 2 the same loop reads level
0 exactly as the branch does (parent256, crop 128, average-pooled), which is what loopcheck compares.
"""
from __future__ import annotations

import itertools
import json
import math
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import paris4_3d_cross_scroll as G  # noqa: E402  (docs/34: test segments, meshes, http, phase correlation, AUC)

BUCKET = G.BUCKET
DATA = ROOT / "data/ink_3d9"
RUNS = ROOT / "runs/paris4_3d9"
TRAIN_LAB = ROOT / "data/ink_9um/labels/aligned-scrollprizeorg-21slices"
SV = {"train": ROOT / "data/ink_9um/surface-volumes/aligned9", "test": ROOT / "data/ink_9um/surface-volumes/openlabels9"}
VALSEG = ("pherc0139-w016", "pherc0814-46527", "pherc1667-w029")
TEST = G.PRIMARY + G.SECONDARY
TILE, CAP, VALPAD = 256, 3_000_000, 64
TS = np.arange(-6, 7, dtype=np.float64) / 2  # band, level-2 voxels
CROP, MARGIN, MAXPTS, JITTER = 64, 8, 512, 16
CAP_GIB = 25


def jdump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))


def segcfg():
    return json.loads((DATA / "segments.json").read_text())


# ---------------------------------------------------------------- setup / labels / tiles
def setup(_a=None):
    import re
    import xml.etree.ElementTree as ET

    import requests
    import zarr

    def ls(prefix):
        r = requests.get(BUCKET, params={"list-type": "2", "prefix": prefix, "delimiter": "/"}, timeout=60)
        r.raise_for_status()
        t = ET.fromstring(r.content)
        ns = {"s": t.tag.split("}")[0][1:]}
        return [e.text for e in t.findall("s:CommonPrefixes/s:Prefix", ns)]

    src = json.loads((ROOT / "data/ink_9um/aligned_sources.json").read_text())
    cfg = {}
    for name, v in src.items():
        rel = v["url"].split(".amazonaws.com/")[1]
        sample, seg = rel.split("/")[0], rel.split("/segments/")[1].split("/")[0]
        ctid = re.search(r"volume-(\d+)\.zarr", rel).group(1)
        meshes = [d for d in ls(f"{sample}/segments/{seg}/mesh/") if f"-on-{ctid}-" in d]
        cts = [d for d in ls(f"{sample}/volumes/") if d.split("/")[-2].startswith(ctid)]
        assert len(meshes) == 1 and len(cts) == 1, (name, meshes, cts)
        cfg[name] = {"role": "train", "sample": sample, "segment": seg, "mesh": meshes[0].rstrip("/"),
                     "ct_root": cts[0].rstrip("/")}
    for name in TEST + (G.CONTROL,):
        c = G.CFG[name]
        cfg[name] = {"role": "test" if name in TEST else "control", "sample": c["sample"], "segment": c["segment"],
                     "mesh": c["mesh"], "ct_root": c["ct"].rsplit("/0", 1)[0]}
    jdump(DATA / "segments.json", cfg)
    lab = DATA / "labels"
    lab.mkdir(parents=True, exist_ok=True)
    for name, c in cfg.items():
        if c["role"] != "train":
            continue
        d = DATA / "mesh" / name
        d.mkdir(parents=True, exist_ok=True)
        for f in ("meta.json", "x.tif", "y.tif", "z.tif"):
            if not (d / f).exists():
                b = G.http_get(f"{BUCKET}{c['mesh']}/{f}")
                assert b is not None, (name, f)
                (d / f).write_bytes(b)

        def arr(path):
            a = zarr.open(str(path), mode="r")
            return a if hasattr(a, "shape") else a["0"]

        for kind, fn in (("ink", "inklabels"), ("sup", "supervision_mask"), ("val", "validation_mask")):
            out = lab / f"{name}_{kind}.npy"
            p = TRAIN_LAB / name / f"{name}_{fn}.zarr"
            if not out.exists():
                np.save(out, (np.asarray(arr(p)[10]) > 0) if p.exists() else
                        np.zeros(np.load(lab / f"{name}_sup.npy").shape, bool))
        print(name, json.loads((d / "meta.json").read_text())["scale"], np.load(lab / f"{name}_sup.npy").shape, flush=True)


def train_labels(name):
    lab = DATA / "labels"
    return (np.load(lab / f"{name}_ink.npy"), np.load(lab / f"{name}_sup.npy"), np.load(lab / f"{name}_val.npy"))


def test_labels(name):
    o = G.OPENLABELS
    return np.load(o / f"{name}_inklabels.npy") > 0, np.load(o / f"{name}_supervision.npy") > 0


def tiles(_a=None):
    from scipy import ndimage
    cfg = segcfg()
    rng = np.random.default_rng(0)
    by_scroll = {}
    for name in sorted(n for n, c in cfg.items() if c["role"] == "train"):
        by_scroll.setdefault(cfg[name]["sample"], []).append(name)
    out, report = {}, {}
    for scroll, names in sorted(by_scroll.items()):
        decks = {}
        for name in names:
            ink, sup, val = train_labels(name)
            near = ndimage.maximum_filter(val, size=2 * VALPAD + 1) if val.any() else val
            H, W = sup.shape
            cand = []
            for i in range(H // TILE):
                for j in range(W // TILE):
                    sl = (slice(i * TILE, (i + 1) * TILE), slice(j * TILE, (j + 1) * TILE))
                    n = int(sup[sl].sum())
                    if n >= 0.1 * TILE * TILE and not near[sl].any():
                        cand.append((i * TILE, j * TILE, n, int((sup[sl] & ink[sl]).sum())))
            order = rng.permutation(len(cand))
            decks[name] = [cand[k] for k in order]
        total, ptr = 0, {n: 0 for n in names}
        while total < CAP and any(ptr[n] < len(decks[n]) for n in names):
            for name in names:
                if total >= CAP:
                    break
                if ptr[name] < len(decks[name]):
                    r, c, n, k = decks[name][ptr[name]]
                    ptr[name] += 1
                    out.setdefault(name, []).append({"row": r, "col": c, "supervised": n, "ink": k})
                    total += n
        report[scroll] = {"supervised": total, "tiles": sum(ptr.values()),
                          "per_segment": {n: ptr[n] for n in names}}
        print(scroll, report[scroll], flush=True)
    jdump(RUNS / "tiles.json", {"tiles": out, "report": report})


# ---------------------------------------------------------------- geometry
class Mesh(G.Mesh):
    def __init__(self, name):
        import tifffile
        d = (DATA / "mesh" / name) if segcfg()[name]["role"] == "train" else (G.MESH / name)
        self.scale = json.loads((d / "meta.json").read_text())["scale"][0]
        self.xyz = np.stack([tifffile.imread(d / f"{a}.tif").astype(np.float64) for a in "zyx"], -1)
        self.valid = np.all(self.xyz > 0, -1)


def surface(mesh, ii, jj, conv):
    """Level-2 points and unit normals of label pixels (ii, jj): canvas (4i, 4j)."""
    p, n = mesh.point_normal(*mesh.nodes(4.0 * ii, 4.0 * jj, conv))
    return (p - 1.5) / 4.0, n


def conventions():
    return {k: v["chosen"] for k, v in json.loads((RUNS / "method_check.json").read_text())["ct_alignment"].items()}


# ---------------------------------------------------------------- method checks
def check_tile(name, cfg, tl):
    if cfg[name]["role"] == "train":
        return tl["tiles"][name][0] if name in tl["tiles"] else None
    return json.loads((G.RUNS / "windows.json").read_text())[name][0]


def sv_middle(name, role, win):
    import zarr
    a = zarr.open(str(SV["train" if role == "train" else "test"] / f"{name}.zarr"), mode="r")["0"]
    z = a.shape[0] // 2
    return np.asarray(a[z, win["row"]:win["row"] + TILE, win["col"]:win["col"] + TILE]).astype(np.float32), z


def check(_a=None):
    cfg = segcfg()
    tl = json.loads((RUNS / "tiles.json").read_text())
    res = {"labels_equal_openlabels9": {}, "training_tiles_without_validation": {}, "ct_alignment": {}}
    for name in TEST:
        ink, sup = G.load_labels(name)
        oi, os_ = test_labels(name)
        res["labels_equal_openlabels9"][name] = bool(np.array_equal(ink, oi) and np.array_equal(sup, os_))
    for name, ts in tl["tiles"].items():
        val = train_labels(name)[2]
        res["training_tiles_without_validation"][name] = int(sum(
            val[t["row"]:t["row"] + TILE, t["col"]:t["col"] + TILE].sum() for t in ts))
    readers = {}
    for name in [n for n in cfg if cfg[n]["role"] != "control"]:
        win = check_tile(name, cfg, tl)
        if win is None:
            res["ct_alignment"][name] = {"chosen": None, "note": "no training tile"}
            continue
        ct = cfg[name]["ct_root"]
        if ct not in readers:
            readers.clear()
            readers[ct] = G.ChunkReader(BUCKET + ct + "/2")
        rd = readers[ct]
        m = Mesh(name)
        sv, z = sv_middle(name, cfg[name]["role"], win)
        i = np.arange(win["row"], win["row"] + TILE)
        j = np.arange(win["col"], win["col"] + TILE)
        rr, cc = np.meshgrid(4.0 * i + 1.5, 4.0 * j + 1.5, indexing="ij")
        row = {"window": win, "surface_volume_layer": z}
        for conv in ("A", "B"):
            p, _ = m.point_normal(*m.nodes(rr, cc, conv))
            img = rd.at((p - 1.5) / 4.0)
            row[conv] = {"d": G.phase_shift(sv, img), "nonzero": float((img > 0).mean())}
        good = [cv for cv in ("A", "B") if all(abs(v) <= 1 for v in row[cv]["d"])]
        row["chosen"] = min(good, key=lambda cv: sum(abs(v) for v in row[cv]["d"])) if good else None
        res["ct_alignment"][name] = row
        print(name, {cv: [round(v, 2) for v in row[cv]["d"]] for cv in ("A", "B")}, "->", row["chosen"], flush=True)
        if len(rd.cache) > 400:
            rd.cache.clear()
    by_scroll = {}
    for name, c in cfg.items():
        if c["role"] == "train" and name in tl["tiles"]:
            by_scroll.setdefault(c["sample"], []).append(res["ct_alignment"][name]["chosen"] is not None)
    res["training_scrolls_ok"] = {s: sum(v) / len(v) > 0.5 for s, v in by_scroll.items()}
    jdump(RUNS / "method_check.json", res)
    print(json.dumps({k: res[k] for k in ("labels_equal_openlabels9", "training_tiles_without_validation",
                                          "training_scrolls_ok")}))


def pyramid(_a=None):
    cfg = segcfg()
    tl = json.loads((RUNS / "tiles.json").read_text())
    conv = conventions()
    out = {}
    for ct in sorted({c["ct_root"] for c in cfg.values()}):
        name = next(n for n, c in cfg.items() if c["ct_root"] == ct and conv.get(n))
        win = check_tile(name, cfg, tl)
        q, _ = surface(Mesh(name), np.array([win["row"] + 128.0]), np.array([win["col"] + 128.0]), conv[name])
        k2 = tuple(int(v) for v in np.floor(q[0] / 128))
        k0 = tuple(4 * v for v in k2)
        meta2 = json.loads(G.http_get(f"{BUCKET}{ct}/2/.zarray"))
        sep = meta2.get("dimension_separator", ".")
        b2 = G.http_get(f"{BUCKET}{ct}/2/{sep.join(map(str, k2))}")
        b0 = G.http_get(f"{BUCKET}{ct}/0/{sep.join(map(str, k0))}")
        if b2 is None or b0 is None:
            out[ct] = {"note": "chunk absent", "k2": k2}
            continue
        l2 = np.frombuffer(b2, np.uint8).reshape(128, 128, 128)[:32, :32, :32].astype(np.float64)
        l0 = np.frombuffer(b0, np.uint8).reshape(128, 128, 128).astype(np.float64)
        mean = l0.reshape(32, 4, 32, 4, 32, 4).mean((1, 3, 5))
        out[ct] = {"k2": k2, "max_abs_vs_rounded_mean": float(np.abs(l2 - np.rint(mean)).max()),
                   "max_abs_vs_floor_mean": float(np.abs(l2 - np.floor(mean)).max()),
                   "mean_abs_vs_mean": float(np.abs(l2 - mean).mean()),
                   "max_abs_vs_stride4": float(np.abs(l2 - l0[::4, ::4, ::4]).max()),
                   "mean_abs_vs_stride4": float(np.abs(l2 - l0[::4, ::4, ::4]).mean())}
        print(ct, out[ct], flush=True)
    jdump(RUNS / "pyramid_check.json", out)


# ---------------------------------------------------------------- chunk lists / local store
def points_of(name, ii, jj, conv):
    q, n = surface(Mesh(name), ii.astype(np.float64), jj.astype(np.float64), conv)
    ok = np.all(np.isfinite(q), 1) & np.all(np.isfinite(n), 1)
    return q, n, ok


def chunk_set(q, reach):
    d = np.array(list(itertools.product((-reach, 0, reach), repeat=3)))
    return {tuple(k) for k in np.unique(np.floor((q[:, None, :] + d[None]) / 128).astype(np.int64).reshape(-1, 3), axis=0)}


def scoring_pixels(name):
    """(ii, jj, label) of the pixels inferred for scoring: test = supervised; val segments = the validation mask,
    which is disjoint from the supervision mask and stands in for it (koine_machines: supervision_mask_override)."""
    if name in TEST:
        ink, sup = test_labels(name)
        m = sup
    else:
        ink, sup, val = train_labels(name)
        m = val
    ii, jj = np.nonzero(m)
    return ii, jj, ink[ii, jj]


def training_pixels(name, tl):
    ink, sup, _ = train_labels(name)
    ii, jj = [], []
    for t in tl["tiles"][name]:
        a, b = np.nonzero(sup[t["row"]:t["row"] + TILE, t["col"]:t["col"] + TILE])
        ii.append(a + t["row"])
        jj.append(b + t["col"])
    ii, jj = np.concatenate(ii), np.concatenate(jj)
    return ii, jj, ink[ii, jj]


def chunks(_a=None):
    cfg = segcfg()
    tl = json.loads((RUNS / "tiles.json").read_text())
    conv = conventions()
    per = {}
    rep = {}
    jobs = [(n, "train") for n in tl["tiles"]] + [(n, "score") for n in TEST + VALSEG]
    for name, kind in jobs:
        if not conv.get(name):
            rep[f"{name}:{kind}"] = "mapping failed, skipped"
            continue
        ii, jj, _ = training_pixels(name, tl) if kind == "train" else scoring_pixels(name)
        sel = (ii % 4 == 0) & (jj % 4 == 0)
        q, _, ok = points_of(name, ii[sel], jj[sel], conv[name])
        s = chunk_set(q[ok], 92 if kind == "train" else 108)
        per.setdefault(cfg[name]["ct_root"], set()).update(s)
        rep[f"{name}:{kind}"] = len(s)
        print(name, kind, len(s), flush=True)
    total = sum(len(v) for v in per.values())
    gib = total * 128 ** 3 / 2 ** 30
    summary = {"per_ct": {k: len(v) for k, v in per.items()}, "total_chunks": total, "GiB": round(gib, 2),
               "per_job": rep, "cap_GiB": CAP_GIB}
    jdump(RUNS / "chunks.json", summary)
    jdump(DATA / "chunk_lists.json", {k: sorted([int(x) for x in t] for t in v) for k, v in per.items()})
    print(json.dumps({k: summary[k] for k in ("per_ct", "total_chunks", "GiB")}))
    if gib > CAP_GIB:
        sys.exit(f"{gib:.1f} GiB > {CAP_GIB} GiB: stop and ask the user")


class Store:
    """128^3 uint8 chunks of one zarr level: local directory first; with lazy=True a missing local chunk is fetched
    from the bucket and saved (counted). Chunks absent on the bucket read as None (zeros)."""

    def __init__(self, ct_root, level, lazy=True, local=None):
        self.url = f"{BUCKET}{ct_root}/{level}"
        self.root = Path(local) if local else DATA / "ct" / ct_root.replace("/", "__") / str(level)
        self.lazy = lazy
        mf = self.root / ".zarray"
        if not mf.exists():
            mf.parent.mkdir(parents=True, exist_ok=True)
            mf.write_text(G.http_get(self.url + "/.zarray").decode())
        meta = json.loads(mf.read_text())
        assert meta["compressor"] is None and meta["dtype"] == "|u1" and meta["chunks"] == [128] * 3, meta
        self.shape = tuple(meta["shape"])
        self.sep = meta.get("dimension_separator", ".")
        self.cache, self.absent, self.fetched = {}, set(), 0
        self.lock = threading.Lock()

    def path(self, key):
        return self.root / self.sep.join(map(str, key)) if self.sep == "." else self.root.joinpath(*map(str, key))

    def chunk(self, key):
        if key in self.cache:
            return self.cache[key]
        if key in self.absent:
            return None
        f = self.path(key)
        if f.exists():
            a = np.fromfile(f, np.uint8).reshape(128, 128, 128)
        elif self.lazy and all(0 <= key[i] < -(-self.shape[i] // 128) for i in range(3)):
            b = G.http_get(f"{self.url}/{self.sep.join(map(str, key))}")
            if b is None:
                with self.lock:
                    self.absent.add(key)
                return None
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_name(f"{f.name}.{threading.get_ident()}.part")
            tmp.write_bytes(b)
            tmp.replace(f)
            with self.lock:
                self.fetched += 1
            a = np.frombuffer(b, np.uint8).reshape(128, 128, 128)
        else:
            with self.lock:
                self.absent.add(key)
            return None
        with self.lock:
            self.cache[key] = a
        return a

    def present(self, lo, hi):
        """Whether any chunk overlapping [lo, hi) is present."""
        ks = [range(max(lo[i], 0) // 128, (min(hi[i], self.shape[i]) - 1) // 128 + 1) for i in range(3)]
        return any(self.chunk(k) is not None for k in itertools.product(*ks))

    def region(self, lo, size):
        out = np.zeros((size,) * 3, np.uint8)
        hi = [lo[i] + size for i in range(3)]
        ks = [range(max(lo[i], 0) // 128, (min(hi[i], self.shape[i]) - 1) // 128 + 1) for i in range(3)]
        for k in itertools.product(*ks):
            a = self.chunk(k)
            if a is None:
                continue
            g0 = [k[i] * 128 for i in range(3)]
            s0 = [max(lo[i], g0[i]) for i in range(3)]
            s1 = [min(hi[i], g0[i] + 128) for i in range(3)]
            out[s0[0] - lo[0]:s1[0] - lo[0], s0[1] - lo[1]:s1[1] - lo[1], s0[2] - lo[2]:s1[2] - lo[2]] = \
                a[s0[0] - g0[0]:s1[0] - g0[0], s0[1] - g0[1]:s1[1] - g0[1], s0[2] - g0[2]:s1[2] - g0[2]]
        return out

    def drop_cache(self):
        self.cache.clear()


def fetch(_a=None):
    lists = json.loads((DATA / "chunk_lists.json").read_text())
    for ct, keys in lists.items():
        st = Store(ct, 2, lazy=True)
        todo = [tuple(k) for k in keys if not st.path(tuple(k)).exists()]
        t0 = time.time()

        def get(k):
            a = st.chunk(k)
            st.cache.pop(k, None)
            return a is not None

        with ThreadPoolExecutor(48) as ex:
            n_ok = 0
            for i, ok in enumerate(ex.map(get, todo), 1):
                n_ok += ok
                if i % 500 == 0:
                    print(f"{ct}: {i}/{len(todo)} {(time.time() - t0) / 60:.1f} min", flush=True)
        print(f"{ct}: {len(todo)} requested, {n_ok} present, {len(todo) - n_ok} absent on the bucket, "
              f"{(time.time() - t0) / 60:.1f} min", flush=True)


# ---------------------------------------------------------------- inference (sparse, at sampled voxels)
_TABLES = {}


def percentiles(counts, n):
    """(p1, p99) of n uint8 values from their 256-bin histogram, equal to np.percentile (linear) of float32 values."""
    from vesuvius.ink_detection.paris4_3d_gambiarra import volume as V
    if n not in _TABLES:
        _TABLES[n] = V.percentile_table(n)
    lo_i, hi_i, table = _TABLES[n]
    cum = np.cumsum(counts)
    a = np.searchsorted(cum, lo_i, side="right")
    b = np.searchsorted(cum, hi_i, side="right")
    return float(table[0, a[0], b[0]]), float(table[1, a[1], b[1]])


def normalized_crop(store, origin_in, pool):
    """(crop float32 [64p]^3, lo, hi) of the crop whose input origin is origin_in (parent [o - 32p, o + 96p))."""
    from vesuvius.ink_detection.paris4_3d_gambiarra import volume as V
    P = 32 * pool
    parent = store.region([o - P for o in origin_in], 128 * pool)
    lo, hi = percentiles(np.bincount(parent.reshape(-1), minlength=256), parent.size)
    crop = parent[P:P + 64 * pool, P:P + 64 * pool, P:P + 64 * pool]
    return V.normalize_reference(crop, lo, hi), lo, hi


class Sparse:
    """Blended logits at a fixed set of output voxels (float64 accumulators in 32^3 units)."""
    U = 32

    def __init__(self, voxels):
        self.units = {}
        for key in {tuple(k) for k in np.unique(voxels // self.U, axis=0)}:
            self.units[key] = [np.zeros((self.U,) * 3, np.float64), np.zeros((self.U,) * 3, np.float64)]

    def add(self, a, field, g):
        U = self.U
        gv = (g * field).astype(np.float64)
        g64 = g.astype(np.float64)
        for key in itertools.product(*[range(a[i] // U, (a[i] + 63) // U + 1) for i in range(3)]):
            acc = self.units.get(key)
            if acc is None:
                continue
            lo = [max(a[i], key[i] * U) for i in range(3)]
            hi = [min(a[i] + 64, key[i] * U + U) for i in range(3)]
            us = tuple(slice(lo[i] - key[i] * U, hi[i] - key[i] * U) for i in range(3))
            cs = tuple(slice(lo[i] - a[i], hi[i] - a[i]) for i in range(3))
            acc[0][us] += gv[cs]
            acc[1][us] += g64[cs]

    def values(self, voxels):
        out = np.full(len(voxels), np.nan, np.float32)
        keys = voxels // self.U
        order = np.lexsort(keys.T[::-1])
        ks, vs = keys[order], voxels[order]
        bounds = np.flatnonzero(np.any(np.diff(ks, axis=0) != 0, 1)) + 1
        for s, e in zip(np.r_[0, bounds], np.r_[bounds, len(ks)]):
            acc = self.units.get(tuple(ks[s]))
            if acc is None:
                continue
            r = vs[s:e] - ks[s] * self.U
            num, den = acc[0][r[:, 0], r[:, 1], r[:, 2]], acc[1][r[:, 0], r[:, 1], r[:, 2]]
            with np.errstate(all="ignore"):
                out[order[s:e]] = np.where(den > 0, (num / den).astype(np.float32), np.nan)
        return out


def crop_axes(shape_in, pool):
    from vesuvius.ink_detection.paris4_3d_gambiarra import volume as V
    out = []
    for k in range(3):
        a = V.grid_axes(-(-shape_in[k] // pool))
        out.append(a[(pool * a - 32 * pool >= 0) & (pool * a + 96 * pool <= shape_in[k])])
    return out


def crops_covering(voxels, axes):
    blocks = np.unique(voxels // 8, axis=0)
    lo, hi = blocks * 8, blocks * 8 + 8
    start = np.stack([np.searchsorted(axes[k], lo[:, k] - 64, side="right") for k in range(3)], 1)
    stop = np.stack([np.searchsorted(axes[k], hi[:, k], side="left") for k in range(3)], 1)
    got = []
    for d in itertools.product(range(4), repeat=3):
        d = np.array(d)
        ok = np.all(start + d < stop, 1)
        got.append(start[ok] + d)
    idx = np.unique(np.concatenate(got), axis=0)
    return np.stack([axes[k][idx[:, k]] for k in range(3)], 1)


def run_crops(store, pool, net_fn, crops, sparse, batch=16, log=None):
    """Crops (output origins, lexicographic) through net_fn, blended into sparse. Crops whose input region lies
    entirely in absent chunks are skipped."""
    import torch
    from vesuvius.ink_detection.paris4_3d_gambiarra import volume as V
    g = V.gaussian()
    crops = crops[np.lexsort(crops.T[::-1])]
    todo = [a for a in crops if store.present([pool * v for v in a], [pool * v + 64 * pool for v in a])]
    t0, done = time.time(), 0
    with ThreadPoolExecutor(8) as ex:
        for s in range(0, len(todo), batch):
            part = todo[s:s + batch]
            ims = list(ex.map(lambda a: normalized_crop(store, [pool * v for v in a], pool)[0], part))
            x = torch.zeros((batch, 1) + ims[0].shape, dtype=torch.float32, device="cuda")
            for k, im in enumerate(ims):
                x[k, 0] = torch.from_numpy(im)
            with torch.no_grad():
                y = net_fn(x)[:len(part), 0].cpu().numpy()
            for a, field in zip(part, y):
                sparse.add([int(v) for v in a], field, g)
            done += len(part)
            if log and (s // batch) % 200 == 0:
                log(f"  crops {done}/{len(todo)} {(time.time() - t0) / 60:.1f} min")
    return len(todo)


def band_values(store, pool, net_fn, q, n, ts=TS, log=None):
    """Band samples (N, len(ts)) of blended logits at output coords q + t n (q, n: (N, 3) output-grid units)."""
    pts = q[:, None, :] + ts[None, :, None] * n[:, None, :]
    flat = pts.reshape(-1, 3)
    fin = np.all(np.isfinite(flat), 1)
    f = np.floor(flat[fin]).astype(np.int64)
    corners = np.unique((f[:, None, :] + np.array(list(itertools.product((0, 1), repeat=3)))[None]).reshape(-1, 3), axis=0)
    sparse = Sparse(corners)
    crops = crops_covering(corners, crop_axes(store.shape, pool))
    ncrops = run_crops(store, pool, net_fn, crops, sparse, log=log)
    vals = sparse.values(corners)
    ckey = vkey(corners)
    assert np.all(np.diff(ckey) > 0)
    w = flat[fin] - f
    acc = np.zeros(len(f), np.float64)
    for d in itertools.product((0, 1), repeat=3):
        idx = f + np.array(d)
        pos = np.searchsorted(ckey, vkey(idx))
        ww = np.prod(np.where(np.array(d)[None] == 1, w, 1 - w), 1)
        acc += ww * vals[pos]
    out = np.full(len(flat), np.nan)
    out[fin] = acc
    return out.reshape(pts.shape[:2]), ncrops


def vkey(a):
    """One int64 per voxel, ordered like np.unique(axis=0) (coords in [0, 2^21))."""
    a = np.asarray(a, np.int64)
    assert a.min() >= 0 and a.max() < (1 << 21)
    return (a[:, 0] << 42) | (a[:, 1] << 21) | a[:, 2]


def band_summary(v):
    with np.errstate(all="ignore"):
        allnan = np.all(np.isnan(v), 1)
        mx = np.where(allnan, np.nan, np.nanmax(np.where(np.isnan(v), -np.inf, v), 1))
        return {"max": mx.astype(np.float32), "t0": v[:, len(TS) // 2].astype(np.float32),
                "mean": np.nanmean(v, 1).astype(np.float32)}


def student(weights=None, seed=27):
    from vesuvius.ink_detection.paris4_3d_gambiarra.student import Student, load_weights
    s = Student(seed=seed)
    if weights:
        load_weights(s.network, weights)
    return s


def net_level2(s):
    import torch

    def fn(x):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            return s.network(x)["ink"].float()
    return fn


def loopcheck(_a=None):
    """Rule (a): our loop with pool = 2 on the docs/34 local level-0 copy vs the branch's codes, at the voxels the
    docs/34 window-0 band samples (positive control)."""
    import torch
    name = G.CONTROL
    win = json.loads((G.RUNS / "windows.json").read_text())[name][0]
    pts = G.band_points(name, win, "A")
    q1 = ((pts - 0.5) / 2).reshape(-1, 3)
    q1 = q1[np.all(np.isfinite(q1), 1)]
    vox = np.unique(np.floor(q1).astype(np.int64), axis=0)
    rng = np.random.default_rng(0)
    vox = vox[rng.choice(len(vox), min(len(vox), 200_000), replace=False)]
    cv = G.CodeVolume(G.OUTS / f"local_{name}_w0")
    ref = np.zeros(len(vox), np.int64)
    ch = np.array(cv.ch)
    keys = vox // ch
    for key in {tuple(k) for k in keys}:
        a = cv.chunk(key)
        sel = np.all(keys == key, 1)
        if a is not None:
            r = vox[sel] - np.array(key) * ch
            ref[sel] = a[r[:, 0], r[:, 1], r[:, 2]]
    st = Store(G.CFG[name]["ct"].rsplit("/0", 1)[0], 0, lazy=False, local=G.local_ct(name))
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    s = student(G.WEIGHTS)
    s.eval().requires_grad_(False)
    sparse = Sparse(vox)
    t0 = time.time()
    n = run_crops(st, 2, s.low, crops_covering(vox, crop_axes(st.shape, 2)), sparse, log=print)
    ours_logit = sparse.values(vox)
    ours = np.where(np.isfinite(ours_logit), np.clip(np.floor(ours_logit.astype(np.float64) * 10) + 128, 1, 255), 0)
    m = ref > 0
    d = np.abs(ours[m] - ref[m])
    res = {"voxels": int(len(vox)), "compared": int(m.sum()), "crops": n, "minutes": (time.time() - t0) / 60,
           "identical_fraction": float((d == 0).mean()), "max_code_diff": int(d.max()),
           "ours_missing_where_branch_has_code": int((ours[m] == 0).sum()),
           "pass": bool((d == 0).mean() >= 0.99 and d.max() <= 1)}
    print(res)
    jdump(RUNS / "loopcheck.json", res)


# ---------------------------------------------------------------- training
class TrainSet:
    def __init__(self, seed):
        cfg = segcfg()
        tl = json.loads((RUNS / "tiles.json").read_text())
        conv = conventions()
        self.rng = np.random.default_rng(1000 + seed)
        self.stores, self.segs = {}, []
        for name in sorted(tl["tiles"]):
            if not conv.get(name):
                continue
            ii, jj, y = training_pixels(name, tl)
            q, n, ok = points_of(name, ii, jj, conv[name])
            q, n, y = q[ok].astype(np.float32), n[ok].astype(np.float32), y[ok]
            ct = cfg[name]["ct_root"]
            if ct not in self.stores:
                self.stores[ct] = Store(ct, 2, lazy=True)
            blocks = np.floor(q / 16).astype(np.int64)
            order = np.lexsort(blocks.T[::-1])
            bs = blocks[order]
            cut = np.flatnonzero(np.any(np.diff(bs, axis=0) != 0, 1)) + 1
            index = {tuple(bs[s]): order[s:e] for s, e in zip(np.r_[0, cut], np.r_[cut, len(bs)])}
            self.segs.append({"name": name, "scroll": cfg[name]["sample"], "ct": ct, "q": q, "n": n, "y": y,
                              "pos": np.flatnonzero(y), "neg": np.flatnonzero(~y), "index": index})
            print(f"  {name}: {len(y)} px, ink {y.mean():.3f}", flush=True)
        self.scrolls = sorted({s["scroll"] for s in self.segs})
        self.lock = threading.Lock()

    def draw(self):
        with self.lock:
            sc = self.scrolls[self.rng.integers(len(self.scrolls))]
            cand = [s for s in self.segs if s["scroll"] == sc]
            w = np.array([len(s["y"]) for s in cand], np.float64)
            seg = cand[self.rng.choice(len(cand), p=w / w.sum())]
            pool = seg["pos"] if self.rng.random() < 0.5 and len(seg["pos"]) else seg["neg"]
            k = pool[self.rng.integers(len(pool))]
            jitter = self.rng.integers(-JITTER, JITTER + 1, 3)
            perm = list(self.rng.permutation(3))
            flips = self.rng.integers(0, 2, 3).astype(bool)
            contrast = float(self.rng.uniform(.65, 1.5)) if self.rng.random() < .8 else 1.
            gamma = float(np.exp(self.rng.uniform(np.log(.7), np.log(1.5)))) if self.rng.random() < .8 else 1.
            sub = int(self.rng.integers(1 << 31))
        a = np.floor(seg["q"][k]).astype(np.int64) - CROP // 2 + jitter
        crop, _, _ = normalized_crop(self.stores[seg["ct"]], [int(v) for v in a], 1)
        lo, hi = a + MARGIN + 3, a + CROP - MARGIN - 3
        bl, bh = np.floor(lo / 16).astype(int), np.floor((hi - 1) / 16).astype(int)
        idx = [seg["index"][b] for b in itertools.product(*[range(bl[i], bh[i] + 1) for i in range(3)])
               if b in seg["index"]]
        idx = np.concatenate(idx) if idx else np.zeros(0, np.int64)
        q = seg["q"][idx]
        inside = np.all((q >= lo) & (q < hi), 1)
        idx = idx[inside]
        r = np.random.default_rng(sub)
        yy = seg["y"][idx]
        pick = np.concatenate([r.permutation(idx[yy])[:MAXPTS // 2], r.permutation(idx[~yy])[:MAXPTS // 2]])
        q = seg["q"][pick] - a
        n = seg["n"][pick].copy()
        y = seg["y"][pick]
        crop = np.transpose(crop, perm)
        q, n = q[:, perm], n[:, perm]
        for ax in range(3):
            if flips[ax]:
                crop = np.flip(crop, ax)
                q[:, ax] = CROP - 1 - q[:, ax]
                n[:, ax] = -n[:, ax]
        return np.ascontiguousarray(crop), q, n, y, contrast, gamma


def lr_at(arm, step, steps):
    warm = min(1.0, (step + 1) / 50)
    if arm == "A1":
        return 3e-5 * warm
    t = min(1.0, step / max(1, steps))
    return warm * (3e-5 + 0.5 * (3e-4 - 3e-5) * (1 + math.cos(math.pi * t)))


def train(args):
    import torch
    import torch.nn.functional as F
    arm, seed = args[0], int(args[1])
    assert arm in ("A1", "A2")
    smoke = "--smoke" in args
    steps = int(args[args.index("--steps") + 1]) if "--steps" in args else (200 if smoke else None)
    assert steps, "--steps N (fixed in the docs/35 addendum)"
    out = RUNS / "train" / f"{arm}_s{seed}{'_smoke' if smoke else ''}"
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(seed)
    s = student(G.WEIGHTS if arm == "A1" else None, seed=27 if arm == "A1" else 27 + seed)
    net = s.network
    net.train()
    opt = torch.optim.AdamW(net.parameters(), lr=3e-5, weight_decay=0.01)
    ds = TrainSet(seed)
    tsg = torch.tensor(TS, dtype=torch.float32, device="cuda")
    curve = open(out / "curve.jsonl", "a")
    pool = ThreadPoolExecutor(12)
    pending = [pool.submit(ds.draw) for _ in range(32)]
    t0 = time.time()
    for step in range(steps):
        for gp in opt.param_groups:
            gp["lr"] = lr_at(arm, step, steps)
        opt.zero_grad(set_to_none=True)
        tot, npos, nneg = 0.0, 0, 0
        for _mb in range(2):
            items = [pending.pop(0).result() for _ in range(8)]
            pending += [pool.submit(ds.draw) for _ in range(8)]
            x = torch.from_numpy(np.stack([it[0] for it in items])[:, None]).cuda()
            for k, it in enumerate(items):
                v = x[k]
                c, gmm = it[4], it[5]
                m = v.double().mean().float()
                v = ((v - m) * c + m).clamp_(0, 1)
                x[k] = v ** gmm
            P = MAXPTS
            grid = torch.zeros((8, P, len(TS), 1, 3), device="cuda")
            lab = torch.zeros((8, P), device="cuda")
            msk = torch.zeros((8, P), dtype=torch.bool, device="cuda")
            for k, it in enumerate(items):
                q, n, y = (torch.from_numpy(np.asarray(z, np.float32)).cuda() for z in it[1:4])
                m = len(q)
                if m == 0:
                    continue
                pts = q[:, None, :] + tsg[None, :, None] * n[:, None, :]
                grid[k, :m, :, 0] = (pts.flip(-1) / (CROP - 1)) * 2 - 1
                lab[k, :m] = y
                msk[k, :m] = True
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = net(x)["ink"]
            v = F.grid_sample(logits.float(), grid, mode="bilinear", align_corners=True)[:, 0, :, :, 0]
            band = v.max(-1).values
            bce = F.binary_cross_entropy_with_logits(band, lab, reduction="none")
            pos, neg = msk & (lab > 0.5), msk & (lab < 0.5)
            loss = 0.5 * (bce[pos].mean() if pos.any() else 0 * bce.sum()) + \
                0.5 * (bce[neg].mean() if neg.any() else 0 * bce.sum())
            (loss / 2).backward()
            tot += float(loss) / 2
            npos += int(pos.sum())
            nneg += int(neg.sum())
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        if step % 50 == 0 or step == steps - 1:
            row = {"step": step + 1, "loss": tot, "lr": opt.param_groups[0]["lr"], "pos": npos, "neg": nneg,
                   "sec_per_update": (time.time() - t0) / (step + 1),
                   "lazy_fetched": sum(st.fetched for st in ds.stores.values())}
            curve.write(json.dumps(row) + "\n")
            curve.flush()
            print(row, flush=True)
        if step + 1 in (20,):
            t20 = time.time()
    rate = (time.time() - t20) / (steps - 20) if steps > 20 else None
    from vesuvius.ink_detection.paris4_3d_gambiarra.student import save_weights
    save_weights(net, out / f"step-{steps:06d}.safetensors", metadata={"arm": arm, "seed": str(seed)})
    jdump(out / "COMPLETE.json", {"steps": steps, "sec_per_update_after_20": rate, "minutes": (time.time() - t0) / 60,
                                  "lazy_fetched": sum(st.fetched for st in ds.stores.values())})
    pool.shutdown(cancel_futures=True)
    print("done", out, rate)


# ---------------------------------------------------------------- inference on test / validation, scoring
def weights_of(arm, seed):
    if arm == "A0":
        return G.WEIGHTS
    d = RUNS / "train" / f"{arm}_s{seed}"
    return next(d.glob("step-*.safetensors"))


def infer(args):
    import torch
    arm = args[0]
    seed = int(args[1]) if len(args) > 1 else 0
    tag = arm if arm == "A0" else f"{arm}_s{seed}"
    cfg = segcfg()
    conv = conventions()
    torch.backends.cudnn.benchmark = False
    s = student(weights_of(arm, seed))
    s.eval().requires_grad_(False)
    fn = net_level2(s)
    mdir = DATA / "maps" / tag
    mdir.mkdir(parents=True, exist_ok=True)
    for name in TEST + VALSEG:
        f = mdir / f"{name}.npz"
        if f.exists() or not conv.get(name):
            continue
        ii, jj, y = scoring_pixels(name)
        q, n, ok = points_of(name, ii, jj, conv[name])
        st = Store(cfg[name]["ct_root"], 2, lazy=True)
        t0 = time.time()
        maps = {k: np.full(len(ii), np.nan, np.float32) for k in ("max", "t0", "mean")}
        tiles_ = np.stack([ii // 512, jj // 512], 1)
        ncrops = 0
        for key in np.unique(tiles_, axis=0):
            sel = np.flatnonzero(np.all(tiles_ == key, 1) & ok)
            if not len(sel):
                continue
            v, nc = band_values(st, 1, fn, q[sel], n[sel])
            ncrops += nc
            for k2, val in band_summary(v).items():
                maps[k2][sel] = val
            st.drop_cache()
        np.savez(f, ii=ii.astype(np.int32), jj=jj.astype(np.int32), y=y, **maps)
        print(f"{tag} {name}: {len(ii)} px, {ncrops} crops, lazily fetched {st.fetched}, "
              f"{(time.time() - t0) / 60:.1f} min", flush=True)


def score(_a=None):
    import tifffile
    res = {}
    tags = ["A0"] + [f"{a}_s{s}" for a in ("A1", "A2") for s in (0, 1)]
    wins = json.loads((G.RUNS / "windows.json").read_text())
    for tag in tags:
        mdir = DATA / "maps" / tag
        if not mdir.exists():
            continue
        r = {}
        for name in TEST:
            f = mdir / f"{name}.npz"
            if not f.exists():
                continue
            z = np.load(f)
            y = z["y"].astype(bool)
            row = {f"auc_{k}": G.auc(z[k], y) for k in ("max", "t0", "mean")}
            row["coverage"] = float(np.isfinite(z["max"]).mean())
            H = test_labels(name)[1].shape[0]
            lab = test_labels(name)[0]
            row["auc_negative_control"] = G.auc(z["max"], np.roll(lab, H // 2, 0)[z["ii"], z["jj"]])
            inwin = np.zeros(len(y), bool)
            for w in wins[name]:
                inwin |= (z["ii"] >= w["row"]) & (z["ii"] < w["row"] + TILE) & (z["jj"] >= w["col"]) & (z["jj"] < w["col"] + TILE)
            row["auc_max_docs34_windows"] = G.auc(z["max"][inwin], y[inwin])
            r[name] = row
        ys, vs = [], []
        for name in VALSEG:
            f = mdir / f"{name}.npz"
            if f.exists():
                z = np.load(f)
                ys.append(z["y"].astype(bool))
                vs.append(z["max"])
        if ys:
            r["validation_pooled_auc"] = G.auc(np.concatenate(vs), np.concatenate(ys))
            r["validation_per_segment"] = {n: G.auc(np.load(mdir / f"{n}.npz")["max"], np.load(mdir / f"{n}.npz")["y"].astype(bool))
                                           for n in VALSEG if (mdir / f"{n}.npz").exists()}
        res[tag] = r
        print(tag, json.dumps(r, default=lambda v: round(v, 4)), flush=True)
    base = {}
    grids = json.loads((ROOT / "runs/label_offset/stage1_grids.json").read_text())
    for name in TEST:
        base[name] = {"ink9um_s43": grids["ink9um_s43"][name]["auc0"], "reader_v3": grids["reader_v3"][name]["auc0"]}
    docs34 = json.loads((G.RUNS / "summary.json").read_text())["rows"]

    def mean_arm(arm, name):
        v = [res[f"{arm}_s{s}"][name]["auc_max"] for s in (0, 1) if f"{arm}_s{s}" in res and name in res[f"{arm}_s{s}"]]
        return float(np.mean(v)) if len(v) == 2 else float("nan")

    prim = {n: mean_arm("A1", n) for n in G.PRIMARY}
    a2 = {n: mean_arm("A2", n) for n in G.PRIMARY}
    loop = json.loads((RUNS / "loopcheck.json").read_text()) if (RUNS / "loopcheck.json").exists() else {}
    valid_b = all(res.get(f"A1_s{s}", {}).get("validation_pooled_auc", 0) >= 0.75 for s in (0, 1))
    valid = bool(loop.get("pass")) and valid_b
    verdict = "pipeline failure, no verdict"
    if valid:
        if sum(a >= 0.80 for a in prim.values()) >= 3:
            verdict = "reads held-out scrolls"
        elif sum(a <= 0.65 for a in prim.values()) >= 3:
            verdict = "does not"
        else:
            verdict = "partial"
    d9 = {n: prim[n] - base[n]["ink9um_s43"] for n in G.PRIMARY}
    d2 = {n: prim[n] - a2[n] for n in G.PRIMARY}
    same_sign = {n: all((res[f"A1_s{s}"][n]["auc_max"] - res[f"A2_s{s}"][n]["auc_max"]) > 0 for s in (0, 1))
                 if all(f"{a}_s{s}" in res for a in ("A1", "A2") for s in (0, 1)) else None for n in G.PRIMARY}
    yes = [n for n in G.PRIMARY if d2[n] >= 0.02 and same_sign[n]]
    pretrain = "yes" if len(yes) >= 3 else ("no" if sum(abs(v) < 0.02 for v in d2.values()) >= 3 else "unclear")
    summary = {
        "valid": valid, "loopcheck_pass": loop.get("pass"), "validation_rule_pass": valid_b, "verdict": verdict,
        "A1_mean_auc": prim, "A2_mean_auc": a2, "A0_auc": {n: res.get("A0", {}).get(n, {}).get("auc_max") for n in G.PRIMARY},
        "baselines": base, "A1_minus_ink9um": d9,
        "competitive": sum(v >= -0.02 for v in d9.values()) >= 3, "better": sum(v >= 0.02 for v in d9.values()) >= 3,
        "A1_minus_A2": d2, "A1_gt_A2_both_seed_pairs": same_sign, "pretraining_matters": pretrain,
        "A1_minus_A0": {n: prim[n] - (res.get("A0", {}).get(n, {}).get("auc_max") or float("nan")) for n in G.PRIMARY},
        "docs34_released_4p8um_windows": {n: docs34[n].get("auc_max") for n in TEST if n in docs34},
        "secondary_0500p2": {t: res[t].get("pherc0500p2-s1", {}).get("auc_max") for t in res},
        "rows": res,
    }
    jdump(RUNS / "summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1, default=str))


if __name__ == "__main__":
    stage = sys.argv[1]
    {"setup": setup, "tiles": tiles, "check": check, "pyramid": pyramid, "chunks": chunks, "fetch": fetch,
     "loopcheck": loopcheck, "train": train, "infer": infer, "score": score}[stage](sys.argv[2:])
