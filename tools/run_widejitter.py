#!/usr/bin/env python3
"""run_widejitter.py -- docs/31: does training with a wider whole-window depth jitter (+-5 slices instead of
the recipe's +-2) make a 9 um ink reader hold up when the surface it reads is off by 3-5 slices (~30-48 um)?

    python tools/run_widejitter.py configs             # four fine-tune configs (2 arms x 2 seeds)
    uv run --project external/villa/ink-detection --no-sync python tools/run_widejitter.py check
    python tools/run_widejitter.py train [--smoke N]   # fine-tune, resumable by finished checkpoint
    uv run --project external/villa/ink-detection --no-sync python tools/run_widejitter.py perturb
    python tools/run_widejitter.py infer               # base + 4 fine-tunes on every test variant
    uv run --project external/villa/ink-detection --no-sync python tools/run_widejitter.py score

Both arms train on the 27-slice volumes and labels (tools/prepare_wide_volumes.py, prepare_wide_labels.py)
and differ in one config key: `flat_z_window_jitter.max_offset` 2 (control: the recipe's window positions,
which the wider volumes do not change) or 5 (treatment). The configs are the docs/30 control configs with
the paths switched to the wide data and the five native 9.36 um PHerc0139 representations dropped (they
come from a 9 um volume and cannot be widened). Test renders are built from the 27-slice open-label
volumes, so shifts up to +-5 slices read real layers.

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
sys.path.insert(0, str(ROOT / "tools"))
from run_segrobust import ENV_PROJECT, MODELS, RUN_TREE, SCROLLS, SEGMENTS, offset_field  # noqa: E402

CONFIGS = ROOT / "configs"
RUNS = ROOT / "runs"
VOL = ROOT / "data/ink_9um/surface-volumes"
LABELS = ROOT / "data/ink_9um/labels"
SRC = VOL / "openlabels9_wide"
TEST_LABELS = LABELS / "openlabels9"
PERT = VOL / "perturbed31"
PREDS = RUNS / "ink9um_openlabels/preds_widejitter"
OUT = RUNS / "ink9um_scorecard"
WIDE_LABELS = (LABELS / "aligned-scrollprizeorg-27slices").as_posix()

SEEDS = ("42", "43")
ARMS = {"control": 2, "jitter5": 5}
STEPS = 10000
FINAL = f"ckpt_{STEPS:06d}.pth"

VARIANTS = {"clean": ("const", 0.0, 0)}
for k in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5):
    VARIANTS[f"const{k:+d}"] = ("const", float(k), 0)
for amp in (3, 5):
    for field_seed in (101, 102, 103):
        VARIANTS[f"wander{amp}_f{field_seed}"] = ("wander", float(amp), field_seed)
LARGE = [f"const{k:+d}" for k in (-5, -4, -3, 3, 4, 5)] + [f"wander5_f{s}" for s in (101, 102, 103)]
SMALL = [f"const{k:+d}" for k in (-2, -1, 1, 2)] + [f"wander3_f{s}" for s in (101, 102, 103)]


def run_name(arm: str, seed: str) -> str:
    return f"ink9um_widejitter_{arm}_s{seed}"


def models() -> dict:
    out = {f"base_s{s}": MODELS / f"hybrid_3d2d-seed{s}" / "step-075000.pth" for s in SEEDS}
    for arm in ARMS:
        for s in SEEDS:
            out[f"{arm}_s{s}"] = RUNS / run_name(arm, s) / FINAL
    return out


def configs(args) -> None:
    for seed in SEEDS:
        base = json.loads((CONFIGS / f"ink9um_segrobust_control_s{seed}.json").read_text(encoding="utf-8"))
        for arm, max_offset in ARMS.items():
            cfg = json.loads(json.dumps(base))
            datasets = []
            for ds in cfg["datasets"]:
                if "native9" in ds["segments_path"]:
                    continue
                if not ds["segments_path"].endswith("aligned-scrollprizeorg-21slices"):
                    raise ValueError(f"unexpected dataset {ds['segments_path']}")
                ds["segments_path"] = WIDE_LABELS
                ds["surface_volume_paths"] = {k: v.replace("/aligned9/", "/aligned9_wide/")
                                              for k, v in ds["surface_volume_paths"].items()}
                datasets.append(ds)
            cfg["datasets"] = datasets
            cfg["flat_z_window_jitter"]["max_offset"] = max_offset
            cfg["out_dir"] = str(RUNS / run_name(arm, seed)).replace("\\", "/")
            cfg["description"] = (f"docs/31 {arm}: docs/30 control recipe on the 27-slice wide volumes, "
                                  f"native9 dropped, whole-window jitter +-{max_offset}.")
            assert "flat_z_local_wander" not in cfg
            path = CONFIGS / f"{run_name(arm, seed)}.json"
            path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            n = sum(len(d["segments"]) for d in datasets)
            print(f"wrote {path.name}: {n} representations, jitter +-{max_offset}")


def check(args) -> None:
    """Build each arm's training set as the trainer does and record the window offsets drawn."""
    import random
    from copy import deepcopy

    import koine_machines.data.ink_dataset as ds_module
    from koine_machines.data.ink_dataset import InkDataset

    print("koine_machines from", ds_module.__file__, flush=True)
    result = {"module": ds_module.__file__}
    for arm in ARMS:
        cfg = json.loads((CONFIGS / f"{run_name(arm, '42')}.json").read_text(encoding="utf-8"))
        seen = {"offsets": [], "base_depths": [], "image_depths": [], "label_z_profile": None}
        original = ds_module._flat_z_window_bbox

        def recording(bbox, **kwargs):
            out, offset = original(bbox, **kwargs)
            seen["offsets"].append(int(offset))
            seen["base_depths"].append(int(bbox[3] - bbox[0]))
            return out, offset

        ds_module._flat_z_window_bbox = recording
        random.seed(0)
        np.random.seed(0)
        shared = InkDataset(deepcopy(cfg), do_augmentations=False)
        train = InkDataset(deepcopy(cfg), do_augmentations=True, patches=shared.training_patches,
                           segments=shared.segments)
        for i in random.sample(range(len(train)), 200):
            sample = train[i]
            image = sample["image"] if isinstance(sample, dict) else sample[0]
            seen["image_depths"].append(int(np.asarray(image).shape[-3]))
        ds_module._flat_z_window_bbox = original
        offs = np.array(seen["offsets"])
        result[arm] = {"samples": 200, "training_patches": len(train),
                       "base_depths": sorted(set(seen["base_depths"])),
                       "image_depths": sorted(set(seen["image_depths"])),
                       "offset_min": int(offs.min()), "offset_max": int(offs.max()),
                       "offset_counts": {str(k): int((offs == k).sum()) for k in range(-6, 7) if (offs == k).any()}}
        print(arm, result[arm], flush=True)
    (RUNS / "segrobust/widejitter_active_check.json").write_text(json.dumps(result, indent=1) + "\n",
                                                                 encoding="utf-8")


def train(args) -> None:
    for arm in (("jitter5",) if args.smoke else ARMS):
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
            for attempt in range(3):     # GPU contention ("resource already mapped") kills a start now and then
                with open(log, "w", encoding="utf-8") as fh:
                    code = subprocess.run(cmd, cwd=RUN_TREE, stdout=fh, stderr=subprocess.STDOUT).returncode
                if code == 0:
                    break
                print(f"{name}: exit {code} (attempt {attempt + 1}), retrying", flush=True)
                time.sleep(60)
            print(f"{name}: exit {code} in {(time.time() - t0) / 60:.1f} min (log {log.name})", flush=True)
            if code != 0:
                sys.exit(f"error: training {name} failed")
            if args.smoke:
                return


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

    from score_label_free_threshold import f1_curve

    rows = []
    for seg, scroll in SEGMENTS.items():
        sup = np.asarray(zarr.open(str(TEST_LABELS / seg / f"{seg}_supervision_mask.zarr"), mode="r")["0"][0]) > 0
        ink = (np.asarray(zarr.open(str(TEST_LABELS / seg / f"{seg}_inklabels.zarr"), mode="r")["0"][0]) > 0) & sup
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
    with open(OUT / "widejitter_cells.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def mean(model, variants, scroll):
        # PHerc0841's three segments are averaged first (they are the rows of that scroll)
        vals = [r["f1_best"] for r in rows if r["model"] == model and r["scroll"] == scroll and r["variant"] in variants]
        return float(np.mean(vals))

    groups = {"clean": ["clean"], "large": LARGE, "small": SMALL}
    summary = {"per_model": {}, "contrast": {}}
    for model in models():
        summary["per_model"][model] = {s: {g: mean(model, v, s) for g, v in groups.items()} for s in SCROLLS}
        summary["per_model"][model]["by_variant"] = {
            name: float(np.mean([mean(model, [name], s) for s in SCROLLS])) for name in VARIANTS}
    for seed in SEEDS:
        t, c = summary["per_model"][f"jitter5_s{seed}"], summary["per_model"][f"control_s{seed}"]
        summary["contrast"][f"s{seed}"] = {s: {g: t[s][g] - c[s][g] for g in groups} for s in SCROLLS}

    # docs/31 decision rules, exactly as pre-registered
    def over_scrolls(model, key):
        return float(np.mean([summary["per_model"][model][s][key] for s in SCROLLS]))

    spread = abs(over_scrolls("control_s42", "large") - over_scrolls("control_s43", "large"))
    p1_means = {seed: float(np.mean([summary["contrast"][f"s{seed}"][s]["large"] for s in SCROLLS])) for seed in SEEDS}
    p1_positive = {seed: sum(summary["contrast"][f"s{seed}"][s]["large"] > 0 for s in SCROLLS) for seed in SEEDS}
    p2_means = {seed: float(np.mean([summary["contrast"][f"s{seed}"][s]["clean"] for s in SCROLLS])) for seed in SEEDS}
    p1 = all(p1_means[s] >= 0.015 and p1_positive[s] >= 2 and p1_means[s] > spread for s in SEEDS)
    p2 = all(p2_means[s] >= -0.01 for s in SEEDS)
    summary["decision"] = {"P1_mean_contrast_large": p1_means, "P1_scrolls_positive": p1_positive,
                           "control_seed_spread_large": spread, "P1_pass": p1,
                           "P2_mean_contrast_clean": p2_means, "P2_pass": p2, "success": p1 and p2}
    (OUT / "widejitter_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"contrast": summary["contrast"], "decision": summary["decision"]}, indent=1))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("configs", "check", "perturb", "infer", "score"):
        sub.add_parser(name)
    p = sub.add_parser("train")
    p.add_argument("--smoke", type=int, default=0, help="run only the first treatment config for N steps")
    args = parser.parse_args(argv)
    {"configs": configs, "check": check, "train": train, "perturb": perturb, "infer": infer,
     "score": score}[args.cmd](args)


if __name__ == "__main__":
    main()
