#!/usr/bin/env python3
"""Stage 2 of docs/24: score one prediction with both yardsticks.

Stage 1 measured how well the pseudo-labels agree with the annotation withheld from the run
that consumed them: F1 0.40-0.46, below a trivial all-positive classifier in 11 of 24 cells.
That says the yardstick is poor. It does not say it *misranks*, which is the question a
practitioner actually faces when a validation score is the only thing available.

So: re-infer arm D's 1667 checkpoints and score every prediction twice -- once against the
withheld annotation, once against the pseudo-labels of the same segment. One inference serves
both, so the two sticks measure the identical output and any disagreement is the sticks.

The two scorings run on different supports by construction (pseudo-labels only have an opinion
where the base model was confident). That is not a flaw to correct: it is the situation, since
someone validating on pseudo-labels has no other support available. Both supports are recorded.
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
RUN_TREE = Path("D:/vw2/ink-detection")
VOLUMES = REPO / "data" / "ink_9um" / "surface-volumes" / "aligned9"
TRUTH = REPO / "data" / "ink_9um" / "labels" / "aligned-scrollprizeorg-21slices"
CKPT_ROOT = Path("Z:/아카이브/vesuvius-runs")
LOGS = REPO / "runs" / "pseudo_rank_logs"
PREDS = REPO / "runs" / "pseudo_rank_preds"
OUT_CSV = REPO / "runs" / "ink9um_scorecard" / "pseudo_rank_matrix.csv"

SEEDS = [42, 43]
SEGMENTS = ["pherc1667-w013", "pherc1667-w023", "pherc1667-w028",
            "pherc1667-w029", "pherc1667-w031"]
STEPS = ["002500", "005000", "010000"]     # the steps r1667_matrix.csv already scores
FIELDS = ["seed", "segment", "step", "yardstick", "scored_px", "ink_px",
          "best_f1", "best_threshold", "precision", "recall"]


def log(message: str, stream=None) -> None:
    line = f"{datetime.now():%H:%M:%S} {message}"
    print(line, flush=True)
    if stream is not None:
        stream.write(line + "\n")
        stream.flush()


def uv(*args: str) -> list[str]:
    return ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", *args]


def run(command: list[str], *, cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        return subprocess.run(command, cwd=cwd, stdout=handle,
                              stderr=subprocess.STDOUT).returncode


def score(prediction: Path, label_dir: Path, tag: str, driver) -> dict | None:
    report = PREDS / f"{tag}.json"
    code = run(uv(str(REPO / "tools" / "eval_validation.py"), str(prediction), str(label_dir),
                  "--region-kind", "supervision_mask", "--json", str(report),
                  "--no-image-metrics", "--label", tag),
               cwd=REPO, log_path=LOGS / "eval.log")
    if code != 0 or not report.exists():
        log(f"  !! scoring failed for {tag} (exit {code})", driver)
        return None
    d = json.loads(report.read_text(encoding="utf-8"))
    best = d["best_f1"]
    chosen = d.get("at_threshold")
    if isinstance(chosen, dict):
        threshold, precision, recall = (chosen.get("threshold"), chosen.get("precision"),
                                        chosen.get("recall"))
    else:
        threshold, precision, recall = chosen, d.get("precision"), d.get("recall")
    return {
        "scored_px": d.get("scored_pixels") or d.get("scored_px"),
        "ink_px": d.get("ink_pixels") or d.get("ink_px"),
        "best_f1": round(best.get("f1") if isinstance(best, dict) else best, 4),
        "best_threshold": threshold,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep-predictions", action="store_true",
                        help="keep the prediction TIFFs (they are large); default deletes each "
                             "once both yardsticks have read it")
    args = parser.parse_args(argv)

    LOGS.mkdir(parents=True, exist_ok=True)
    PREDS.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    done = 0
    total = len(SEEDS) * len(SEGMENTS) * len(STEPS)

    with (LOGS / "driver.log").open("a", encoding="utf-8") as driver:
        log(f"=== docs/24 stage 2 start: {total} cells ===", driver)
        for seed in SEEDS:
            pseudo_root = REPO / "data" / "ink_9um" / "labels" / f"pseudo1667D_s{seed}"
            for step in STEPS:
                checkpoint = CKPT_ROOT / f"ink9um_1667_D_s{seed}" / f"ckpt_{step}.pth"
                if not checkpoint.exists():
                    log(f"!! missing checkpoint {checkpoint}", driver)
                    continue
                for segment in SEGMENTS:
                    done += 1
                    tag = f"s{seed}_{segment}_{step}"
                    prediction = PREDS / f"{tag}.tif"
                    if not prediction.exists():
                        started = time.perf_counter()
                        code = run(uv("-m", "koine_machines.inference.infer",
                                      str(VOLUMES / f"{segment}.zarr"), str(checkpoint),
                                      str(prediction), "--batch-size", "4", "--no-compile"),
                                   cwd=RUN_TREE, log_path=LOGS / "infer.log")
                        log(f"[{done}/{total}] {tag}: inferred in "
                            f"{(time.perf_counter()-started)/60:.1f} min (exit {code})", driver)
                        if code != 0 or not prediction.exists():
                            continue
                    for yard, label_dir in (("truth", TRUTH / segment),
                                            ("pseudo", pseudo_root / segment)):
                        if not label_dir.exists():
                            log(f"  !! no {yard} labels at {label_dir}", driver)
                            continue
                        got = score(prediction, label_dir, f"{tag}_{yard}", driver)
                        if got is None:
                            continue
                        rows.append({"seed": seed, "segment": segment, "step": step,
                                     "yardstick": yard, **got})
                        log(f"  {tag} [{yard}]: F1 {got['best_f1']} @ {got['best_threshold']}",
                            driver)
                    if not args.keep_predictions and prediction.exists():
                        prediction.unlink()
                    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
                        writer = csv.DictWriter(handle, fieldnames=FIELDS)
                        writer.writeheader()
                        writer.writerows(rows)
        log(f"=== done: {len(rows)} rows -> {OUT_CSV} ===", driver)
    return 0


if __name__ == "__main__":
    sys.exit(main())
