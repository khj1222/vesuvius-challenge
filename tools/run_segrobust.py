#!/usr/bin/env python3
"""run_segrobust.py -- docs/30: does training with a local depth wander make a 9 um ink reader hold up
when the surface it reads is off along the normal?

    python tools/run_segrobust.py configs              # four fine-tune configs (2 arms x 2 seeds)
    python tools/run_segrobust.py train [--smoke N]    # fine-tune, resumable by finished checkpoint
    uv run --project external/villa/ink-detection --no-sync python tools/run_segrobust.py perturb
    python tools/run_segrobust.py infer                # base + 4 fine-tunes on every test variant
    uv run --project external/villa/ink-detection --no-sync python tools/run_segrobust.py score

Arms differ in one config key: `flat_z_local_wander` (treatment) adds a smooth in-plane varying depth
shift inside each training patch on top of the recipe's whole-window jitter; the control keeps the recipe.
Both start from the released ink_9um checkpoint of the same seed, train the same steps on the same corpus.

License: MIT.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ENV_PROJECT = ROOT / "external/villa/ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")
MODELS = ROOT / "data/ink_9um/models"
CONFIGS = ROOT / "configs"
RUNS = ROOT / "runs"
SRC = ROOT / "data/ink_9um/surface-volumes/openlabels9"
LABELS = ROOT / "data/ink_9um/labels/openlabels9"
PERT = ROOT / "data/ink_9um/surface-volumes/perturbed30"
PREDS = RUNS / "ink9um_openlabels/preds_segrobust"
OUT = RUNS / "ink9um_scorecard"

SEEDS = ("42", "43")
ARMS = ("control", "wander")
STEPS = 10000
FINAL = f"ckpt_{STEPS:06d}.pth"
WANDER = {"enabled": True, "max_amplitude": 2.0, "corr_px": [64, 256], "probability": 1.0}

SEGMENTS = {"pherc0841-w00": "PHerc0841", "pherc0841-ag144": "PHerc0841", "pherc0841-ag174": "PHerc0841",
            "pherc0009b-ag055": "PHerc0009B", "pherc0500p2-s1": "PHerc0500P2"}
SCROLLS = ("PHerc0841", "PHerc0009B", "PHerc0500P2")
# test variants: clean, whole-surface shifts, and smooth local wander (three fields each)
VARIANTS = {"clean": ("const", 0.0, 0)}
for k in (-2, -1, 1, 2):
    VARIANTS[f"const{k:+d}"] = ("const", float(k), 0)
for amp in (1, 2):
    for field_seed in (101, 102, 103):
        VARIANTS[f"wander{amp}_f{field_seed}"] = ("wander", float(amp), field_seed)
TEST_CORR_PX = 200


def run_name(arm: str, seed: str) -> str:
    return f"ink9um_segrobust_{arm}_s{seed}"


def models() -> dict:
    out = {f"base_s{s}": MODELS / f"hybrid_3d2d-seed{s}" / "step-075000.pth" for s in SEEDS}
    for arm in ARMS:
        for s in SEEDS:
            out[f"{arm}_s{s}"] = RUNS / run_name(arm, s) / FINAL
    return out


def configs(args) -> None:
    for arm in ARMS:
        for seed in SEEDS:
            path = CONFIGS / f"{run_name(arm, seed)}.json"
            subprocess.run([sys.executable, str(ROOT / "tools/make_ink9um_config.py"), "--out", str(path),
                            "--run-dir", str(RUNS / run_name(arm, seed)), "--iterations", str(STEPS),
                            "--seed", seed, "--save-every", "2500", "--val-every", "1000000"], check=True)
            config = json.loads(path.read_text(encoding="utf-8"))
            config.update({"checkpoint": str(MODELS / f"hybrid_3d2d-seed{seed}" / "step-075000.pth").replace("\\", "/"),
                           "weights_only": True, "warmup_steps": 1000})
            if arm == "wander":
                config["flat_z_local_wander"] = dict(WANDER)
            path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {path.name}")


def train(args) -> None:
    for arm in (("wander",) if args.smoke else ARMS):    # the smoke run exercises the new code path
        for seed in SEEDS:
            name = run_name(arm, seed)
            if (RUNS / name / FINAL).exists() and not args.smoke:
                continue
            config = CONFIGS / f"{name}.json"
            if args.smoke:
                cfg = json.loads(config.read_text(encoding="utf-8"))
                cfg.update({"num_iterations": args.smoke, "save_every": args.smoke, "warmup_steps": 10,
                            "out_dir": str(RUNS / f"{name}_smoke").replace("\\", "/")})
                config = RUNS / f"{name}_smoke.json"
                config.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            t0 = time.time()
            cmd = ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", "-m",
                   "koine_machines.training.train", str(config)]
            log = RUNS / f"{name}{'_smoke' if args.smoke else ''}.log"
            with open(log, "w", encoding="utf-8") as fh:
                code = subprocess.run(cmd, cwd=RUN_TREE, stdout=fh, stderr=subprocess.STDOUT).returncode
            print(f"{name}: exit {code} in {(time.time() - t0) / 60:.1f} min (log {log.name})", flush=True)
            if code != 0:
                sys.exit(f"error: training {name} failed")
            if args.smoke:
                return


def offset_field(shape, kind, amount, field_seed):
    if kind == "const":
        return np.full(shape, amount, np.float32)
    from scipy.ndimage import gaussian_filter, zoom

    rng = np.random.default_rng(field_seed)
    small = (max(4, shape[0] // 25), max(4, shape[1] // 25))
    noise = gaussian_filter(rng.standard_normal(small), sigma=TEST_CORR_PX / 25)
    field = zoom(noise, (shape[0] / small[0], shape[1] / small[1]), order=1)[: shape[0], : shape[1]]
    return (field / np.abs(field).max() * amount).astype(np.float32)


def perturb(args) -> None:
    import zarr

    PERT.mkdir(parents=True, exist_ok=True)
    for seg in SEGMENTS:
        src = zarr.open(str(SRC / f"{seg}.zarr"), mode="r")
        vol = np.asarray(src["0"][:]).astype(np.float32)
        depth = vol.shape[0]
        z = np.arange(depth, dtype=np.float32)[:, None, None]
        valid = vol.max(axis=0, keepdims=True) > 0
        for name, (kind, amount, field_seed) in VARIANTS.items():
            dst = PERT / f"{seg}__{name}.zarr"
            if dst.exists():
                continue
            d = offset_field(vol.shape[1:], kind, amount, field_seed)[None]
            pos = np.clip(z + d, 0, depth - 1)
            lo = np.floor(pos).astype(np.int64)
            hi = np.minimum(lo + 1, depth - 1)
            w = pos - lo
            out = np.take_along_axis(vol, lo, 0) * (1 - w) + np.take_along_axis(vol, hi, 0) * w
            out = np.where(valid, out, 0)
            root = zarr.open_group(str(dst), mode="w")
            root.attrs.update(dict(src.attrs))
            root.create_dataset("0", data=np.rint(out).astype(np.uint8), chunks=src["0"].chunks)
            print(f"{seg} {name}: max |shift| {np.abs(d).max():.2f}, mean {np.abs(d).mean():.2f}", flush=True)


def infer(args) -> None:
    PREDS.mkdir(parents=True, exist_ok=True)
    for model, ckpt in models().items():
        if not ckpt.exists():
            sys.exit(f"error: missing checkpoint {ckpt}")
        for seg in SEGMENTS:
            for name in VARIANTS:
                out = PREDS / f"{seg}__{name}__{model}.tif"
                if out.exists():
                    continue
                cmd = ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", "-m",
                       "koine_machines.inference.infer", str(PERT / f"{seg}__{name}.zarr"), str(ckpt), str(out),
                       "--overlap", "0.5", "--blend-mode", "hann", "--batch-size", "4", "--no-compile"]
                for attempt in range(3):
                    proc = subprocess.run(cmd, cwd=RUN_TREE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                          text=True)
                    if proc.returncode == 0 and out.exists():
                        break
                    time.sleep(30)
                if not out.exists():
                    sys.exit(f"error: no prediction {out.name}\n{proc.stderr[-1500:]}")
            print(f"{model} {seg}: done", flush=True)


def score(args) -> None:
    import csv

    import tifffile
    import zarr

    sys.path.insert(0, str(ROOT / "tools"))
    from score_label_free_threshold import f1_curve

    rows = []
    for seg, scroll in SEGMENTS.items():
        sup = np.asarray(zarr.open(str(LABELS / seg / f"{seg}_supervision_mask.zarr"), mode="r")["0"][0]) > 0
        ink = (np.asarray(zarr.open(str(LABELS / seg / f"{seg}_inklabels.zarr"), mode="r")["0"][0]) > 0) & sup
        bg = sup & ~ink
        for model in models():
            for name in VARIANTS:
                p = tifffile.imread(PREDS / f"{seg}__{name}__{model}.tif")
                pos = np.bincount(p[ink], minlength=256).astype(float)
                neg = np.bincount(p[bg], minlength=256).astype(float)
                neg_below = np.concatenate([[0.0], np.cumsum(neg)[:-1]])
                auc = float((pos * (neg_below + 0.5 * neg)).sum() / (pos.sum() * neg.sum()))
                rows.append({"scroll": scroll, "segment": seg, "model": model, "variant": name,
                             "f1_best": float(f1_curve(pos, neg).max()), "auc": auc})
    with open(OUT / "segrobust_cells.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def mean(model, variants, scroll):
        vals = [r["f1_best"] for r in rows if r["model"] == model and r["scroll"] == scroll and r["variant"] in variants]
        return float(np.mean(vals))

    perturbed = [v for v in VARIANTS if v != "clean"]
    wander = [v for v in VARIANTS if v.startswith("wander")]
    summary = {"per_model": {}, "contrast": {}}
    for model in models():
        summary["per_model"][model] = {s: {"clean": mean(model, ["clean"], s), "perturbed": mean(model, perturbed, s),
                                           "wander": mean(model, wander, s)} for s in SCROLLS}
    for seed in SEEDS:
        t, c = summary["per_model"][f"wander_s{seed}"], summary["per_model"][f"control_s{seed}"]
        summary["contrast"][f"s{seed}"] = {s: {k: t[s][k] - c[s][k] for k in ("clean", "perturbed", "wander")}
                                          for s in SCROLLS}
    # docs/30 decision rules, exactly as pre-registered
    def over_scrolls(model, key):
        return float(np.mean([summary["per_model"][model][s][key] for s in SCROLLS]))

    spread = abs(over_scrolls("control_s42", "wander") - over_scrolls("control_s43", "wander"))
    p1_means = {seed: float(np.mean([summary["contrast"][f"s{seed}"][s]["wander"] for s in SCROLLS])) for seed in SEEDS}
    p1_positive = {seed: sum(summary["contrast"][f"s{seed}"][s]["wander"] > 0 for s in SCROLLS) for seed in SEEDS}
    p2_means = {seed: float(np.mean([summary["contrast"][f"s{seed}"][s]["clean"] for s in SCROLLS])) for seed in SEEDS}
    p1 = all(p1_means[s] >= 0.015 and p1_positive[s] >= 2 and p1_means[s] > spread for s in SEEDS)
    p2 = all(p2_means[s] >= -0.01 for s in SEEDS)
    summary["decision"] = {"P1_mean_contrast_wander": p1_means, "P1_scrolls_positive": p1_positive,
                           "control_seed_spread_wander": spread, "P1_pass": p1,
                           "P2_mean_contrast_clean": p2_means, "P2_pass": p2, "success": p1 and p2}
    (OUT / "segrobust_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contrast": summary["contrast"], "decision": summary["decision"]}, indent=1))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("configs", "perturb", "infer", "score"):
        sub.add_parser(name)
    p = sub.add_parser("train")
    p.add_argument("--smoke", type=int, default=0, help="run only the first config for N steps (timing check)")
    args = parser.parse_args(argv)
    {"configs": configs, "train": train, "perturb": perturb, "infer": infer, "score": score}[args.cmd](args)


if __name__ == "__main__":
    main()
