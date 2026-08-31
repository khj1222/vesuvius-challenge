#!/usr/bin/env python
"""Run the pre-registered annotation-targeting arms (docs/20) unattended.

Trains one fine-tune per (arm, seed) from the leave-Paris-4-out base and scores the seven
Paris 4 segments the base never saw, writing the same CSV schema as the label-efficiency
matrix it extends, so the two can be read side by side.

Training is retried: a CUDA worker from another process on this box has killed runs before
(`CUDA error: resource already mapped`), and the fix is to try again rather than to take
the card from whoever else is using it.

Usage
-----
    python tools/run_annotation_targeting.py --phase all
    python tools/run_annotation_targeting.py --phase score --only disagreemin
    python tools/run_annotation_targeting.py --reproduce keep0250 42 phercparis4-w01 002500
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV_PROJECT = REPO / "external" / "villa" / "ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")          # the tree whose schema matches ink_9um
VOLUMES = REPO / "data" / "ink_9um" / "surface-volumes" / "aligned9"
LABELS = REPO / "data" / "ink_9um" / "labels" / "aligned-scrollprizeorg-21slices"
LOGS = REPO / "runs" / "annotarget_logs"
PREDS = REPO / "runs" / "annotarget_preds"
OUT_CSV = REPO / "runs" / "ink9um_scorecard" / "annotarget_matrix.csv"

ARMS = ["disagreemin", "disagreemax", "randomsel"]
SEEDS = [42, 43]
SEGMENTS = [
    "phercparis4-w01", "phercparis4-w02", "phercparis4-w03", "phercparis4-w05",
    "phercparis4-w06", "phercparis4-w07", "phercparis4-w09",
]
SCORE_STEPS = ["002500"]          # the pre-registered step
FIELDS = ["arm", "seed", "segment", "step", "scored_px", "ink_px",
          "best_f1", "best_threshold", "precision", "recall"]


def log(message: str, stream=None) -> None:
    line = f"{datetime.now():%H:%M:%S} {message}"
    print(line, flush=True)
    if stream is not None:
        stream.write(line + "\n")
        stream.flush()


def run(command: list[str], *, cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} {' '.join(command)} =====\n")
        handle.flush()
        return subprocess.run(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT).returncode


def uv(*arguments: str) -> list[str]:
    return ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", *arguments]


def newest_checkpoint(out_dir: Path) -> int:
    steps = [int(p.stem.split("_")[1]) for p in out_dir.glob("ckpt_*.pth")]
    return max(steps) if steps else -1


def train(arm: str, seed: int, *, attempts: int, driver) -> bool:
    config = REPO / "configs" / f"ink9um_at_{arm}_s{seed}.json"
    out_dir = REPO / "runs" / f"ink9um_at_{arm}_s{seed}"
    for attempt in range(1, attempts + 1):
        if newest_checkpoint(out_dir) >= int(SCORE_STEPS[-1]):
            log(f"{arm} s{seed}: already has ckpt {newest_checkpoint(out_dir)}, skipping", driver)
            return True
        log(f"{arm} s{seed}: attempt {attempt}/{attempts}, from the LOSO base", driver)
        started = time.perf_counter()
        code = run(uv("-m", "koine_machines.training.train", str(config)),
                   cwd=RUN_TREE, log_path=LOGS / f"{arm}_s{seed}.log")
        minutes = (time.perf_counter() - started) / 60
        log(f"{arm} s{seed}: attempt {attempt} exit={code} after {minutes:.1f} min, "
            f"newest ckpt {newest_checkpoint(out_dir)}", driver)
        if code == 0:
            return True
    return False


def score_one(arm: str, seed: int, segment: str, step: str, *, checkpoint: Path,
              driver) -> dict | None:
    prediction = PREDS / f"{arm}_s{seed}_{segment}_{step}.tif"
    if not prediction.exists():
        started = time.perf_counter()
        code = run(uv("-m", "koine_machines.inference.infer",
                      str(VOLUMES / f"{segment}.zarr"), str(checkpoint), str(prediction),
                      "--batch-size", "4", "--no-compile"),
                   cwd=RUN_TREE, log_path=LOGS / f"{arm}_s{seed}_infer.log")
        log(f"{arm} s{seed} {segment} {step}: inferred in "
            f"{(time.perf_counter() - started) / 60:.1f} min (exit {code})", driver)
        if code != 0 or not prediction.exists():
            return None

    report_path = PREDS / f"{arm}_s{seed}_{segment}_{step}.json"
    code = run(uv(str(REPO / "tools" / "eval_validation.py"), str(prediction),
                  str(LABELS / segment), "--region-kind", "supervision_mask",
                  "--json", str(report_path), "--no-image-metrics",
                  "--label", f"{arm}_s{seed}_{segment}_{step}"),
               cwd=REPO, log_path=LOGS / f"{arm}_s{seed}_eval.log")
    if code != 0 or not report_path.exists():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    best = report["best_f1"]
    chosen = report.get("at_threshold")
    if isinstance(chosen, dict):
        threshold = chosen.get("threshold")
        precision, recall = chosen.get("precision"), chosen.get("recall")
    else:
        threshold, precision, recall = chosen, report.get("precision"), report.get("recall")
    f1 = best.get("f1") if isinstance(best, dict) else best
    row = {
        "arm": arm, "seed": seed, "segment": segment, "step": step,
        "scored_px": report["scored_pixels"], "ink_px": report["ink_pixels"],
        "best_f1": round(float(f1), 4),
        "best_threshold": threshold,
        "precision": round(float(precision), 4) if precision is not None else "",
        "recall": round(float(recall), 4) if recall is not None else "",
    }
    log(f"  {arm} s{seed} {segment} {step}: F1 {row['best_f1']} @ {row['best_threshold']}", driver)
    return row


def load_rows() -> list[dict]:
    if not OUT_CSV.exists():
        return []
    with OUT_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save_rows(rows: list[dict]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=["train", "score", "all"], default="all")
    parser.add_argument("--only", nargs="*", default=None, help="Restrict to these arms.")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--reproduce", nargs=4, metavar=("ARM", "SEED", "SEGMENT", "STEP"),
                        help="Score an existing published arm to check the scoring path.")
    args = parser.parse_args(argv)

    LOGS.mkdir(parents=True, exist_ok=True)
    PREDS.mkdir(parents=True, exist_ok=True)
    with (LOGS / "_driver.log").open("a", encoding="utf-8") as driver:
        if args.reproduce:
            arm, seed, segment, step = args.reproduce
            checkpoint = REPO / "runs" / f"ink9um_lb_{arm}_s{seed}" / f"ckpt_{step}.pth"
            if not checkpoint.exists():
                sys.exit(f"error: {checkpoint} not found")
            row = score_one(arm, int(seed), segment, step, checkpoint=checkpoint, driver=driver)
            print(json.dumps(row, indent=1))
            return 0 if row else 1

        arms = args.only or ARMS
        log(f"=== annotation-targeting driver start: arms={arms} ===", driver)

        if args.phase in ("train", "all"):
            for arm in arms:
                for seed in SEEDS:
                    if not train(arm, seed, attempts=args.attempts, driver=driver):
                        log(f"{arm} s{seed}: FAILED after {args.attempts} attempts", driver)

        if args.phase in ("score", "all"):
            log("=== scoring ===", driver)
            rows = load_rows()
            done = {(r["arm"], int(r["seed"]), r["segment"], r["step"]) for r in rows}
            for arm in arms:
                for seed in SEEDS:
                    for step in SCORE_STEPS:
                        checkpoint = REPO / "runs" / f"ink9um_at_{arm}_s{seed}" / f"ckpt_{step}.pth"
                        if not checkpoint.exists():
                            log(f"{arm} s{seed}: no ckpt_{step}, skipping scoring", driver)
                            continue
                        for segment in SEGMENTS:
                            if (arm, seed, segment, step) in done:
                                continue
                            row = score_one(arm, seed, segment, step,
                                            checkpoint=checkpoint, driver=driver)
                            if row is not None:
                                rows.append(row)
                                save_rows(rows)
            save_rows(rows)
            log(f"=== done, {len(rows)} cells in {OUT_CSV} ===", driver)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
