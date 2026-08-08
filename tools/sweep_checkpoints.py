#!/usr/bin/env python3
"""sweep_checkpoints.py -- score a training run's checkpoints on the held-out band.

Training writes a checkpoint every ``save_every`` steps and nothing tells you
which one to keep. With a validation mask in place that question becomes
answerable: run inference restricted to the held-out band (``infer --mask-path``
skips every block outside it, so this costs a fraction of a full-segment pass),
score it with ``eval_validation.py``, and plot the curve.

    python tools/sweep_checkpoints.py runs/ink_val_20k SEGMENT_DIR

Outputs, in ``<run_dir>/validation/``:

    val_<step>.tif      band-only prediction per checkpoint
    val_<step>.json     full metric report per checkpoint
    summary.csv         one row per checkpoint
    curve.png           F1 / IoU / balanced-accuracy against training step

The chart is drawn with Pillow rather than matplotlib: the ink-detection
environment does not ship a plotting stack, and adding one just to draw three
lines is a poor trade for anyone who wants to run this.

Run it from the repo root through the pipeline's environment (``--project``
borrows that environment without changing the working directory, so the paths
below stay relative to where you are):

    uv run --project external/villa/ink-detection \
        python tools/sweep_checkpoints.py external/villa/ink-detection/runs/ink_val_20k SEGMENT_DIR

License: MIT.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

CHECKPOINT_RE = re.compile(r"ckpt_(?P<step>\d+)\.pth$")


def load_sibling_module(name: str):
    """Import a tool sitting next to this file (works regardless of cwd)."""
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        sys.exit(f"error: cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_checkpoints(run_dir: Path, *, every: int) -> list[tuple[int, Path]]:
    found = []
    for path in sorted(run_dir.glob("ckpt_*.pth")):
        match = CHECKPOINT_RE.search(path.name)
        if match:
            found.append((int(match.group("step")), path))
    found.sort()
    if every > 1:
        # always keep the last checkpoint, it is the one people ship
        keep = {step for index, (step, _) in enumerate(found) if index % every == 0}
        keep.add(found[-1][0] if found else 0)
        found = [(step, path) for step, path in found if step in keep]
    return found


def run_inference(
    *,
    volume_zarr: Path,
    checkpoint: Path,
    output_tif: Path,
    mask_path: Path,
    batch_size: int,
    compile_model: bool,
    z_window: str | None = None,
) -> None:
    command = [
        sys.executable, "-m", "koine_machines.inference.infer",
        str(volume_zarr), str(checkpoint), str(output_tif),
        "--mask-path", str(mask_path),
        "--batch-size", str(batch_size),
    ]
    if z_window:
        # Depth-target runs predict a volume, and only the supervised column of
        # it means anything; without this the surface map is a max over noise.
        command += ["--z-window", str(z_window)]
    if not compile_model:
        # torch.compile's inductor backend needs Triton, which has no native
        # Windows build; without this the first forward pass dies.
        command.append("--no-compile")
    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError(f"inference failed for {checkpoint.name} (exit {result.returncode})")


def draw_curve(path: Path, rows: list[dict], *, series: list[tuple[str, tuple[int, int, int]]]) -> None:
    """Minimal multi-line chart: steps on x, metric value (0..1) on y."""
    from PIL import Image, ImageDraw

    width, height = 900, 460
    left, right, top, bottom = 70, 30, 40, 55
    plot_w = width - left - right
    plot_h = height - top - bottom

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    steps = [int(row["step"]) for row in rows]
    if not steps:
        return
    x_min, x_max = min(steps), max(steps)
    x_span = max(1, x_max - x_min)

    values = [float(row[key]) for key, _ in series for row in rows if row.get(key) not in (None, "")]
    y_max = min(1.0, max(values) * 1.08) if values else 1.0
    y_min = max(0.0, min(values) * 0.92) if values else 0.0
    y_span = max(1e-6, y_max - y_min)

    # frame + gridlines
    draw.rectangle([left, top, left + plot_w, top + plot_h], outline=(200, 200, 200))
    for tick in range(5):
        y_value = y_min + y_span * tick / 4
        y_pixel = top + plot_h - int(plot_h * (y_value - y_min) / y_span)
        draw.line([left, y_pixel, left + plot_w, y_pixel], fill=(235, 235, 235))
        draw.text((8, y_pixel - 6), f"{y_value:.3f}", fill=(90, 90, 90))
    for tick in range(6):
        step_value = x_min + x_span * tick / 5
        x_pixel = left + int(plot_w * (step_value - x_min) / x_span)
        draw.line([x_pixel, top, x_pixel, top + plot_h], fill=(243, 243, 243))
        draw.text((x_pixel - 18, top + plot_h + 8), f"{int(step_value)}", fill=(90, 90, 90))

    for index, (key, color) in enumerate(series):
        points = []
        for row in rows:
            if row.get(key) in (None, ""):
                continue
            x_pixel = left + int(plot_w * (int(row["step"]) - x_min) / x_span)
            y_pixel = top + plot_h - int(plot_h * (float(row[key]) - y_min) / y_span)
            points.append((x_pixel, y_pixel))
        if len(points) > 1:
            draw.line(points, fill=color, width=2)
        for point in points:
            draw.ellipse([point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3], fill=color)
        draw.rectangle([left + 10 + index * 150, top + 8, left + 24 + index * 150, top + 18], fill=color)
        draw.text((left + 30 + index * 150, top + 6), key, fill=(60, 60, 60))

    draw.text((left, height - 22), "training step", fill=(60, 60, 60))
    image.save(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate every checkpoint of a run on the held-out validation band.",
    )
    parser.add_argument("run_dir", type=Path, help="Training output dir holding ckpt_*.pth")
    parser.add_argument("segment_dir", type=Path, help="Segment folder (volume + label pyramids)")
    parser.add_argument("--every", type=int, default=1, help="Evaluate every Nth checkpoint. Default: 1")
    parser.add_argument("--batch-size", type=int, default=4, help="Inference batch size. Default: 4")
    parser.add_argument("--compile", dest="compile_model", action="store_true",
                        help="Let inference use torch.compile (needs Triton; not on native Windows).")
    parser.add_argument("--z-window", default=None, metavar="START:STOP",
                        help="For depth-target runs: reduce only these z slices of the volume "
                             "prediction, e.g. 16:48 for a +-16 supervised column. Default: all.")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Where predictions and summary.csv land. Default: RUN_DIR/validation. "
                             "Use a separate dir when re-scoring, since existing val_*.tif are reused.")
    parser.add_argument("--keep-going", action="store_true", help="Continue if one checkpoint fails.")
    parser.add_argument("--no-image-metrics", dest="image_metrics", action="store_false",
                        help="Skip DRD / pseudo-F-measure for a faster sweep.")
    args = parser.parse_args(argv)

    # A sweep is long enough that people redirect it to a log; without this the
    # progress lines sit in the block buffer while inference output (written by
    # the subprocess straight to the fd) streams past them.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    run_dir = args.run_dir.resolve()
    segment_dir = args.segment_dir.resolve()
    if not run_dir.is_dir():
        sys.exit(f"error: not a directory: {run_dir}")
    if not segment_dir.is_dir():
        sys.exit(f"error: not a directory: {segment_dir}")

    volume_zarr = segment_dir / f"{segment_dir.name}.zarr"
    mask_path = segment_dir / f"{segment_dir.name}_validation_mask.tif"
    for required in (volume_zarr, mask_path):
        if not required.exists():
            sys.exit(f"error: missing {required}")

    checkpoints = find_checkpoints(run_dir, every=args.every)
    if not checkpoints:
        sys.exit(f"error: no ckpt_*.pth under {run_dir}")

    out_dir = args.out_dir.resolve() if args.out_dir else run_dir / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    evaluator = load_sibling_module("eval_validation")

    print(f"run        : {run_dir}")
    print(f"segment    : {segment_dir.name}")
    print(f"checkpoints: {len(checkpoints)} ({checkpoints[0][0]} .. {checkpoints[-1][0]})")
    print(f"z window   : {args.z_window or 'whole volume'}")
    print(f"output     : {out_dir}\n")

    rows: list[dict] = []
    for index, (step, checkpoint) in enumerate(checkpoints, start=1):
        prediction = out_dir / f"val_{step:06d}.tif"
        report_path = out_dir / f"val_{step:06d}.json"
        started = time.time()
        print(f"[{index}/{len(checkpoints)}] step {step}")
        try:
            if not prediction.exists():
                run_inference(
                    volume_zarr=volume_zarr,
                    checkpoint=checkpoint,
                    output_tif=prediction,
                    mask_path=mask_path,
                    batch_size=args.batch_size,
                    compile_model=args.compile_model,
                    z_window=args.z_window,
                )
            else:
                print(f"    reusing {prediction.name}")

            eval_argv = [str(prediction), str(segment_dir), "--json", str(report_path),
                         "--label", f"step_{step}"]
            if not args.image_metrics:
                eval_argv.append("--no-image-metrics")
            evaluator.main(eval_argv)
        except Exception as exc:  # noqa: BLE001
            print(f"    FAILED: {type(exc).__name__}: {exc}")
            if not args.keep_going:
                raise
            continue

        report = json.loads(report_path.read_text(encoding="utf-8"))
        best = report["best_f1"]
        image = report.get("image_metrics", {})
        rows.append({
            "step": step,
            "threshold": best["threshold"],
            "f1": round(best["f1"], 6),
            "precision": round(best["precision"], 6),
            "recall": round(best["recall"], 6),
            "iou": round(best["iou"], 6),
            "balanced_accuracy": round(best["balanced_accuracy"], 6),
            "drd": image.get("drd", ""),
            "pseudo_fmeasure": image.get("pseudo_fmeasure", ""),
            "seconds": round(time.time() - started, 1),
        })
        print(f"    F1 {best['f1']:.4f} @ {best['threshold']}  "
              f"({time.time() - started:.0f}s)\n")

    if not rows:
        sys.exit("error: every checkpoint failed")

    summary = out_dir / "summary.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    curve = out_dir / "curve.png"
    draw_curve(curve, rows, series=[
        ("f1", (30, 110, 200)),
        ("iou", (220, 120, 40)),
        ("balanced_accuracy", (60, 160, 90)),
    ])

    best_row = max(rows, key=lambda row: row["f1"])
    print(f"summary -> {summary}")
    print(f"curve   -> {curve}")
    print(f"\nbest checkpoint: step {best_row['step']}  "
          f"F1 {best_row['f1']:.4f} @ threshold {best_row['threshold']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
