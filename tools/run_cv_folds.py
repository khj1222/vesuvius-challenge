#!/usr/bin/env python3
"""run_cv_folds.py -- k-fold cross-validation for the ink-detection tutorial.

A single held-out split of one of these segments is a handful of annotated
regions, and per-region F1 varies by ~0.07 even when nothing has changed. So a
lone number cannot settle "did this help?". This driver runs the whole protocol
unattended: for each fold it rebuilds the validation mask, retrains from
scratch, sweeps the checkpoints, and finally reports the spread across folds.

    python tools/run_cv_folds.py SEGMENT_DIR --folds 3

Per fold it performs:

    1. make_validation_mask.py --folds K --fold i --force
    2. delete the stale <seg>_validation_mask.zarr, re-run create_label_zarrs
       (the converter skips existing outputs, and the loader's patch cache is
        keyed by asset *paths*, so a stale zarr would silently survive)
    3. with --label-version vN, re-extrude that split into the version's own
       validation mask (the labels are written once; only the split moves)
    4. train into runs/<prefix>_fold<i>       (a fresh out_dir per fold, again
                                               because of that path-keyed cache)
    5. sweep_checkpoints.py over that run

and afterwards restores the single-split mask, so the segment is left in the
state the rest of the tooling expects.

Expect roughly (training time + a few minutes) per fold -- about 1.7 h per fold
for the tutorial config on an RTX 5090, so a 3-fold run is an overnight job.

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent


def run(command: list[str], *, cwd: Path, step: str) -> None:
    print(f"\n=== {step} ===", flush=True)
    print("  " + " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=str(cwd))
    if result.returncode != 0:
        raise RuntimeError(f"{step} failed (exit {result.returncode})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run k-fold cross-validation end to end.")
    parser.add_argument("segment_dir", type=Path)
    parser.add_argument("--pipeline-dir", type=Path,
                        default=REPO / "external" / "villa" / "ink-detection",
                        help="Checkout of villa's ink-detection/ (holds configs/ and runs/).")
    parser.add_argument("--config", type=Path, default=REPO / "configs" / "ink_tutorial_val.json",
                        help="Base training config; out_dir is overridden per fold.")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--prefix", default="ink_fold", help="Run-dir prefix. Default: ink_fold")
    parser.add_argument("--only-fold", type=int, default=None, help="Run just this fold.")
    parser.add_argument("--sweep-every", type=int, default=4,
                        help="Evaluate every Nth checkpoint per fold. Default: 4")
    parser.add_argument("--label-version", default=None,
                        help="Label version the config trains on, e.g. v4. Each fold's held-out "
                             "split is re-extruded into that version's validation mask; the labels "
                             "themselves are written once by make_label_version.py.")
    parser.add_argument("--skip-restore", action="store_true",
                        help="Leave the last fold's mask in place instead of restoring the single split.")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    segment_dir = args.segment_dir.resolve()
    pipeline_dir = args.pipeline_dir.resolve()
    base_config_path = args.config.resolve()
    for path in (segment_dir, pipeline_dir, base_config_path):
        if not path.exists():
            sys.exit(f"error: missing {path}")

    base_config = json.loads(base_config_path.read_text(encoding="utf-8"))
    label_version = args.label_version
    config_version = base_config.get("label_version")
    if (label_version or None) != (config_version or None):
        # Silently disagreeing here would train one arm and score it against
        # another arm's held-out voxels, which nothing downstream would flag.
        sys.exit(f"error: --label-version {label_version!r} does not match "
                 f"the config's label_version {config_version!r}")
    version_number = int(str(label_version).lstrip("v")) if label_version else None
    mask_zarr = segment_dir / f"{segment_dir.name}_validation_mask.zarr"
    folds = [args.only_fold] if args.only_fold is not None else list(range(args.folds))
    results: list[dict] = []
    started_all = time.time()

    for fold in folds:
        started = time.time()
        print(f"\n{'#' * 70}\n# fold {fold} of {args.folds}\n{'#' * 70}", flush=True)

        run([sys.executable, str(TOOLS / "make_validation_mask.py"), str(segment_dir),
             "--folds", str(args.folds), "--fold", str(fold), "--force"],
            cwd=REPO, step=f"fold {fold}: build validation mask")

        if mask_zarr.exists():
            shutil.rmtree(mask_zarr)
        run([sys.executable, "-m", "koine_machines.preprocessing.create_label_zarrs", str(segment_dir)],
            cwd=pipeline_dir, step=f"fold {fold}: convert mask to zarr")

        if version_number is not None:
            run([sys.executable, str(TOOLS / "make_label_version.py"), str(segment_dir),
                 "--version", str(version_number), "--refresh-validation"],
                cwd=REPO, step=f"fold {fold}: extrude held-out split into {label_version}")

        out_dir = f"runs/{args.prefix}{fold}"
        fold_config = dict(base_config, out_dir=out_dir)
        config_path = pipeline_dir / "configs" / f"_cv_{args.prefix}{fold}.json"
        config_path.write_text(json.dumps(fold_config, indent=2), encoding="utf-8")

        run([sys.executable, "-m", "koine_machines.training.train", str(config_path)],
            cwd=pipeline_dir, step=f"fold {fold}: train -> {out_dir}")

        run([sys.executable, str(TOOLS / "sweep_checkpoints.py"), str(pipeline_dir / out_dir),
             str(segment_dir), "--every", str(args.sweep_every), "--no-image-metrics", "--keep-going"],
            cwd=pipeline_dir, step=f"fold {fold}: sweep checkpoints")

        summary = pipeline_dir / out_dir / "validation" / "summary.csv"
        best = None
        if summary.exists():
            with summary.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            if rows:
                best = max(rows, key=lambda row: float(row["f1"]))
        results.append({
            "fold": fold,
            "run_dir": out_dir,
            "best_step": int(best["step"]) if best else None,
            "best_f1": float(best["f1"]) if best else None,
            "threshold": int(best["threshold"]) if best else None,
            "iou": float(best["iou"]) if best else None,
            "minutes": round((time.time() - started) / 60, 1),
        })
        print(f"\nfold {fold} done in {(time.time() - started) / 60:.1f} min: "
              f"best F1 {results[-1]['best_f1']}", flush=True)

    if not args.skip_restore:
        run([sys.executable, str(TOOLS / "make_validation_mask.py"), str(segment_dir), "--force"],
            cwd=REPO, step="restore single-split mask")
        if mask_zarr.exists():
            shutil.rmtree(mask_zarr)
        run([sys.executable, "-m", "koine_machines.preprocessing.create_label_zarrs", str(segment_dir)],
            cwd=pipeline_dir, step="restore: convert mask to zarr")
        if version_number is not None:
            run([sys.executable, str(TOOLS / "make_label_version.py"), str(segment_dir),
                 "--version", str(version_number), "--refresh-validation"],
                cwd=REPO, step=f"restore: extrude single split into {label_version}")

    out_path = pipeline_dir / "runs" / f"{args.prefix}_cv_summary.json"
    scores = [r["best_f1"] for r in results if r["best_f1"] is not None]
    payload = {
        "segment": segment_dir.name,
        "folds": args.folds,
        "results": results,
        "f1_mean": round(sum(scores) / len(scores), 6) if scores else None,
        "f1_min": min(scores) if scores else None,
        "f1_max": max(scores) if scores else None,
        "f1_spread": round(max(scores) - min(scores), 6) if len(scores) > 1 else None,
        "total_minutes": round((time.time() - started_all) / 60, 1),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    for entry in results:
        print(f"  fold {entry['fold']}: best F1 {entry['best_f1']} "
              f"@ step {entry['best_step']} threshold {entry['threshold']}  "
              f"({entry['minutes']} min)")
    if scores:
        print(f"\n  mean F1 {payload['f1_mean']}  "
              f"min {payload['f1_min']}  max {payload['f1_max']}  "
              f"spread {payload['f1_spread']}")
    print(f"  summary -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
