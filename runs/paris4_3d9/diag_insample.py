"""docs/35 post-hoc diagnostic (not pre-registered): AUC of A0 / A1 s0 / A2 s0 on (a) training tiles they were fit on
and (b) eligible tiles NOT selected for training, two of each per training segment of 0139, 1667, Paris4 (seeded).
Tells whether the fine-tune fits its own pixels, and whether it generalises within a training scroll."""
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(r"E:\vesuvius-challenge")
sys.path.insert(0, str(ROOT / "tools"))
import paris4_3d_9um_finetune as T  # noqa: E402

cfg = T.segcfg()
tl = json.loads((T.RUNS / "tiles.json").read_text())
conv = T.conventions()
rng = np.random.default_rng(7)
picks = {}
for name in sorted(tl["tiles"]):
    if cfg[name]["sample"] == "PHerc0814":
        continue
    ink, sup, val = T.train_labels(name)
    used = {(t["row"], t["col"]) for t in tl["tiles"][name]}
    H, W = sup.shape
    from scipy import ndimage
    near = ndimage.maximum_filter(val, size=2 * T.VALPAD + 1) if val.any() else val
    free = []
    for i in range(H // T.TILE):
        for j in range(W // T.TILE):
            r, c = i * T.TILE, j * T.TILE
            sl = (slice(r, r + T.TILE), slice(c, c + T.TILE))
            s = sup[sl]
            if (r, c) not in used and s.sum() >= 0.1 * T.TILE ** 2 and not near[sl].any() and 0.1 < (ink[sl] & s).sum() / s.sum() < 0.9:
                free.append((r, c))
    tr = [(t["row"], t["col"]) for t in tl["tiles"][name]]
    picks[name] = {"train": [tr[k] for k in rng.choice(len(tr), min(2, len(tr)), replace=False)],
                   "unused": [free[k] for k in rng.choice(len(free), min(2, len(free)), replace=False)] if free else []}
out = {}
for tag, arm, seed in (("A0", "A0", 0), ("A1_s0", "A1", 0), ("A2_s0", "A2", 0)):
    s = T.student(T.weights_of(arm, seed))
    s.eval().requires_grad_(False)
    fn = T.net_level2(s)
    acc = {"train": ([], []), "unused": ([], [])}
    per = {}
    for name, pk in picks.items():
        ink, sup, _ = T.train_labels(name)
        st = T.Store(cfg[name]["ct_root"], 2, lazy=True)
        for kind in ("train", "unused"):
            for r, c in pk[kind]:
                ii, jj = np.nonzero(sup[r:r + T.TILE, c:c + T.TILE])
                ii, jj = ii + r, jj + c
                y = ink[ii, jj]
                q, n, ok = T.points_of(name, ii, jj, conv[name])
                v, _ = T.band_values(st, 1, fn, q[ok], n[ok])
                mx = T.band_summary(v)["max"]
                acc[kind][0].append(mx)
                acc[kind][1].append(y[ok])
                per[f"{name}:{kind}:{r},{c}"] = T.G.auc(mx, y[ok])
        st.drop_cache()
    out[tag] = {k: T.G.auc(np.concatenate(a), np.concatenate(b)) for k, (a, b) in acc.items()}
    out[tag]["per_tile"] = per
    print(tag, {k: round(v, 3) for k, v in out[tag].items() if k != "per_tile"}, flush=True)
    del s
    torch.cuda.empty_cache()
(T.RUNS / "diag_insample.json").write_text(json.dumps({"picks": picks, "auc": out}, indent=1))
