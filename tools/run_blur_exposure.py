#!/usr/bin/env python
"""Run the pre-registered blur-exposure arm (docs/23) unattended.

Trains the two seeds of the leave-0139-out configuration with the extra blur, stopping each
run once `ckpt_020000` exists -- `num_iterations` stays at the recipe's 78,125 so the
learning-rate schedule matches the baseline, and with the same seed and data order that
checkpoint is what the full run would have produced at that step.

Then scores the four paired PHerc0139 segments in both representations and writes the same
CSV schema as `no0139_matrix.csv`, which holds the baseline it is compared against.

Usage
-----
    python tools/run_blur_exposure.py --phase all
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV_PROJECT = REPO / "external" / "villa" / "ink-detection"
RUN_TREE = Path("D:/vw2/ink-detection")
VOLUMES = REPO / "data" / "ink_9um" / "surface-volumes"
LABELS = REPO / "data" / "ink_9um" / "labels"
LOGS = REPO / "runs" / "blurexp_logs"
PREDS = REPO / "runs" / "blurexp_preds"
OUT_CSV = REPO / "runs" / "ink9um_scorecard" / "blurexp_matrix.csv"

SEEDS = [42, 43]
STEP = "020000"
SHORTS = ["w035", "w039", "w040", "w041"]
FIELDS = ["arm", "representation", "segment", "step", "scored_px", "ink_px",
          "best_f1", "best_threshold", "precision", "recall"]


def log(message: str, stream=None) -> None:
    line = f"{datetime.now():%H:%M:%S} {message}"
    print(line, flush=True)
    if stream is not None:
        stream.write(line + "\n")
        stream.flush()


def uv(*arguments: str) -> list[str]:
    return ["uv", "run", "--project", str(ENV_PROJECT), "--no-sync", "python", *arguments]


def run(command: list[str], *, cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} {' '.join(command)} =====\n")
        handle.flush()
        return subprocess.run(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT).returncode


def train_until_step(seed: int, *, driver) -> bool:
    """Start training and stop it once the scored checkpoint is written and stable."""
    config = REPO / "configs" / f"ink9um_blurexp_s{seed}.json"
    out_dir = REPO / "runs" / f"ink9um_blurexp_s{seed}"
    target = out_dir / f"ckpt_{STEP}.pth"
    if target.exists():
        log(f"seed {seed}: {target.name} already present, skipping training", driver)
        return True

    log_path = LOGS / f"train_s{seed}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"seed {seed}: training until {target.name}", driver)
    started = time.perf_counter()
    with log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            uv("-m", "koine_machines.training.train", str(config)),
            cwd=RUN_TREE, stdout=handle, stderr=subprocess.STDOUT,
        )
        previous = -1
        while True:
            if process.poll() is not None:
                break
            if target.exists():
                size = target.stat().st_size
                if size == previous and size > 0:
                    log(f"seed {seed}: {target.name} written ({size/1e6:.0f} MB), stopping the run",
                        driver)
                    process.terminate()
                    try:
                        process.wait(timeout=120)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                previous = size
            time.sleep(20)
    minutes = (time.perf_counter() - started) / 60
    ok = target.exists()
    log(f"seed {seed}: training finished after {minutes:.1f} min, checkpoint present={ok}", driver)
    return ok


def volume_for(representation: str, short: str) -> Path | None:
    if representation == "aligned":
        return VOLUMES / "aligned9" / f"pherc0139-{short}.zarr"
    folder = VOLUMES / "native9" / short
    candidates = sorted(folder.glob("*.zarr")) if folder.is_dir() else []
    return candidates[0] if candidates else None


def segment_dir_for(representation: str, short: str) -> Path:
    if representation == "aligned":
        return LABELS / "aligned-scrollprizeorg-21slices" / f"pherc0139-{short}"
    return LABELS / "native9-scrollprizeorg-21slices" / short


def score_one(seed: int, representation: str, short: str, *, driver) -> dict | None:
    checkpoint = REPO / "runs" / f"ink9um_blurexp_s{seed}" / f"ckpt_{STEP}.pth"
    volume = volume_for(representation, short)
    if volume is None or not volume.exists():
        log(f"  missing volume for {representation}/{short}", driver)
        return None
    name = f"pherc0139-{short}" if representation == "aligned" else short
    prediction = PREDS / f"blurexp_s{seed}_{representation}_{short}_{STEP}.tif"
    if not prediction.exists():
        started = time.perf_counter()
        code = run(uv("-m", "koine_machines.inference.infer", str(volume), str(checkpoint),
                      str(prediction), "--batch-size", "4", "--no-compile"),
                   cwd=RUN_TREE, log_path=LOGS / f"infer_s{seed}.log")
        log(f"  s{seed} {representation} {short}: inferred in "
            f"{(time.perf_counter()-started)/60:.1f} min (exit {code})", driver)
        if code != 0 or not prediction.exists():
            return None

    report_path = prediction.with_suffix(".json")
    code = run(uv(str(REPO / "tools" / "eval_validation.py"), str(prediction),
                  str(segment_dir_for(representation, short)),
                  "--region-kind", "supervision_mask", "--json", str(report_path),
                  "--no-image-metrics", "--label", f"blurexp_s{seed}_{representation}_{short}"),
               cwd=REPO, log_path=LOGS / f"eval_s{seed}.log")
    if code != 0 or not report_path.exists():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    chosen = report.get("at_threshold")
    threshold = chosen.get("threshold") if isinstance(chosen, dict) else chosen
    precision = chosen.get("precision") if isinstance(chosen, dict) else None
    recall = chosen.get("recall") if isinstance(chosen, dict) else None
    best = report["best_f1"]
    row = {
        "arm": f"blurexp{seed}", "representation": representation, "segment": name,
        "step": STEP, "scored_px": report["scored_pixels"], "ink_px": report["ink_pixels"],
        "best_f1": round(float(best.get("f1") if isinstance(best, dict) else best), 4),
        "best_threshold": threshold,
        "precision": round(float(precision), 4) if precision is not None else "",
        "recall": round(float(recall), 4) if recall is not None else "",
    }
    log(f"  s{seed} {representation} {short}: F1 {row['best_f1']} @ {row['best_threshold']}", driver)
    return row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=["train", "score", "all"], default="all")
    args = parser.parse_args(argv)

    LOGS.mkdir(parents=True, exist_ok=True)
    PREDS.mkdir(parents=True, exist_ok=True)
    with (LOGS / "_driver.log").open("a", encoding="utf-8") as driver:
        log("=== blur-exposure driver start (docs/23) ===", driver)
        if args.phase in ("train", "all"):
            for seed in SEEDS:
                if not train_until_step(seed, driver=driver):
                    log(f"seed {seed}: FAILED to produce ckpt_{STEP}", driver)

        if args.phase in ("score", "all"):
            rows = []
            if OUT_CSV.exists():
                with OUT_CSV.open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
            done = {(r["arm"], r["representation"], r["segment"]) for r in rows}
            for seed in SEEDS:
                for representation in ("aligned", "native"):
                    for short in SHORTS:
                        name = f"pherc0139-{short}" if representation == "aligned" else short
                        if (f"blurexp{seed}", representation, name) in done:
                            continue
                        row = score_one(seed, representation, short, driver=driver)
                        if row is not None:
                            rows.append(row)
                            OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
                            with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
                                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                                writer.writeheader()
                                writer.writerows(rows)
            log(f"=== done, {len(rows)} cells in {OUT_CSV} ===", driver)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
