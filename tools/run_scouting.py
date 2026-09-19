"""Driver for docs/25: render -> infer -> score, per target, resumable.

For each target in runs/scouting/targets.json (plus the control), it
  1. renders the tifxyz with the native vc_render_tifxyz build (skipped when the output
     zarr already has level 0 and a sentinel `_render_done` file),
  2. runs the released ink_9um checkpoints (seed42/43 x step 10k/20k) with the docs/16
     inference flags -- and, for the control only, the leave-0139-out checkpoints too,
  3. scores with tools/score_scouting.py.
Every step writes a log line to logs/scouting_driver.log; a target that fails is recorded
and skipped, never retried in the same run (rerun the driver to retry).

Usage:
  python tools/run_scouting.py --only control
  python tools/run_scouting.py                # everything not yet done
  python tools/run_scouting.py --scroll PHerc0800
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("E:/vesuvius-challenge")
DATA = ROOT / "data/first_letters"
BIN = DATA / "bin/VC3D-88d4aa8/VC3D-88d4aa8-2026-09-18-win64/bin/vc_render_tifxyz.exe"
RENDER_DIR = DATA / "scouting_render_native"
CACHE_DIR = DATA / "cache_native"
PRED_DIR = DATA / "scouting_pred"
SCORE_DIR = ROOT / "runs/scouting/scores"
LOG = ROOT / "logs/scouting_driver.log"
S3 = "https://vesuvius-challenge-open-data.s3.amazonaws.com"
VOLUMES = {
    "reference_PHerc1447": "20250521151220-8.640um-1.2m-116keV-masked.zarr",
    "PHerc0800": "20250521135224-8.640um-1.2m-116keV-masked.zarr",
    "PHerc1447": "20250521151220-8.640um-1.2m-116keV-masked.zarr",
    "PHerc1203": "20250820131727-9.362um-1.2m-113keV-masked.zarr",
    "control_PHerc0139": "20250728140407-9.362um-1.2m-113keV-masked.zarr",
}
RELEASED = {
    f"seed{seed}:{step}": ROOT / f"data/ink_9um/models/hybrid_3d2d-seed{seed}/step-{step}.pth"
    for seed in (42, 43) for step in ("010000", "020000")
}
LOSO = {
    f"loso{seed}:020000": Path(f"Z:/아카이브/vesuvius-runs/ink9um_loso_no0139_s{seed}/ckpt_020000.pth")
    for seed in (42, 43)
}
INFER_CWD = Path("D:/vw2/ink-detection")
INFER_CMD = ["uv", "run", "--project", str(ROOT / "external/villa/ink-detection"), "--no-sync",
             "python", "-m", "koine_machines.inference.infer"]
SCORER = ROOT / "external/villa/ink-detection/.venv/Scripts/python.exe"
# plain "bash" resolves to WSL's bash from a Windows python, which cannot see E:/ paths
GIT_BASH = "C:/Program Files/Git/bin/bash.exe"


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def scroll_of(target: dict) -> str:
    return target["scroll"]


def render(target: dict) -> Path:
    """Render with --flip-normals: on the 0139 w040 control that reproduces the team's
    published surface volume to 99.7% of bytes, while the default orientation reverses the
    slice order and turns every checkpoint into the trivial classifier (docs/25 section 8)."""
    scroll, seg = target["scroll"], target["segment"]
    out = RENDER_DIR / f"{scroll}_{seg}.zarr"
    if (out / "_render_done").exists():
        return out
    mesh = DATA / "scouting" / scroll / seg / "tifxyz"
    if not (mesh / "x.tif").exists():
        raise RuntimeError(f"mesh missing: {mesh}")
    volume_scroll = scroll.replace("control_", "")
    t0 = time.time()
    # bash on Windows: forward slashes everywhere, or the backslashes are eaten as escapes
    cmd = [GIT_BASH, (ROOT / "tools/render_native.sh").as_posix(), volume_scroll, VOLUMES[scroll],
           mesh.as_posix(), out.as_posix(), "--flip-normals"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=4000)
    dt = time.time() - t0
    if proc.returncode != 0 or not (out / "_render_done").exists():
        tail = (proc.stdout + proc.stderr)[-600:].replace("\r", "\n")
        raise RuntimeError(f"render exit={proc.returncode} after {dt:.0f}s: {tail}")
    log(f"  rendered {scroll}/{seg} in {dt/60:.1f} min")
    return out


def zflip_copy(src: Path) -> Path:
    """The other orientation, made from the render rather than re-rendered (byte-identical
    to a render without --flip-normals on the control)."""
    dst = src.with_name(src.name.replace(".zarr", "_zflip.zarr"))
    if (dst / "_render_done").exists():
        return dst
    import numpy as np
    import zarr
    s = zarr.open(str(src), mode="r")
    a = s["0"]
    g = zarr.open_group(str(dst), mode="w")
    g.attrs.update(dict(s.attrs))
    d = g.create_dataset("0", shape=a.shape, chunks=a.chunks, dtype=a.dtype, compressor=a.compressor,
                         fill_value=0, dimension_separator="/")
    cy = a.chunks[1]
    for y in range(0, a.shape[1], cy * 8):
        block = np.asarray(a[:, y:y + cy * 8, :])
        if block.any():
            d[:, y:y + cy * 8, :] = block[::-1]
    (dst / "_render_done").write_text(f"z-flipped copy of {src.name}\n")
    return dst


def infer(target: dict, render_zarr: Path, checkpoints: dict[str, Path]) -> dict[str, Path]:
    scroll, seg = target["scroll"], target["segment"]
    preds = {}
    for key, ckpt in checkpoints.items():
        out = PRED_DIR / f"{scroll}_{seg}" / f"{key.replace(':', '_')}.tif"
        preds[key] = out
        if out.exists() and out.stat().st_size > 0:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if not ckpt.exists():
            raise RuntimeError(f"checkpoint missing: {ckpt}")
        t0 = time.time()
        cmd = INFER_CMD + [str(render_zarr), str(ckpt), str(out), "--overlap", "0.5",
                           "--blend-mode", "hann", "--no-compile"]
        proc = subprocess.run(cmd, cwd=str(INFER_CWD), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=3600)
        if proc.returncode != 0 or not out.exists():
            tail = (proc.stdout + proc.stderr)[-800:]
            raise RuntimeError(f"infer {key} exit={proc.returncode}: {tail}")
        log(f"  inferred {key} in {time.time()-t0:.0f}s")
    return preds


def score(name: str, render_zarr: Path, preds: dict[str, Path], primary: str, partner: str) -> Path:
    out = SCORE_DIR / f"{name}__{primary.replace(':', '_')}.json"
    if out.exists():
        return out
    cmd = [str(SCORER), str(ROOT / "tools/score_scouting.py"), "--render", str(render_zarr),
           "--name", name, "--out", str(out), "--primary", primary, "--partner", partner, "--pred"]
    cmd += [f"{k}={v}" for k, v in preds.items()]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"score exit={proc.returncode}: {(proc.stdout + proc.stderr)[-800:]}")
    log(f"  scored {name} ({primary}): {proc.stdout.strip()[:300]}")
    return out


def run_target(target: dict) -> None:
    scroll, seg = target["scroll"], target["segment"]
    log(f"== {scroll}-{seg}")
    render_zarr = render(target)
    variants = {"flipnormals": render_zarr}
    if not seg.endswith("_zflip"):
        variants["zflip"] = zflip_copy(render_zarr)
    for variant, zarr_path in variants.items():
        name = f"{scroll}-{seg}__{variant}"
        sub = {"scroll": scroll, "segment": f"{seg}__{variant}"}
        preds = infer(sub, zarr_path, RELEASED)
        score(name, zarr_path, preds, "seed42:020000", "seed43:020000")
        score(name, zarr_path, preds, "seed42:010000", "seed43:010000")
        if scroll.startswith("control_"):
            loso = infer(sub, zarr_path, LOSO)
            score(name + "__unseen", zarr_path, {**preds, **loso}, "loso42:020000", "loso43:020000")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["control", "targets"], default=None)
    ap.add_argument("--scroll", default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    targets = json.loads((ROOT / "runs/scouting/targets.json").read_text())
    if args.only == "control":
        targets = [t for t in targets if t["scroll"].startswith("control_")]
    elif args.only == "targets":
        targets = [t for t in targets if not t["scroll"].startswith("control_")]
    if args.scroll:
        targets = [t for t in targets if t["scroll"] == args.scroll]
    if args.limit:
        targets = targets[: args.limit]
    failures = []
    for target in targets:
        try:
            run_target(target)
        except Exception as exc:  # noqa: BLE001 - record and continue
            log(f"  FAILED {target['scroll']}/{target['segment']}: {exc}")
            failures.append(target)
    log(f"done: {len(targets) - len(failures)} ok, {len(failures)} failed")
    if failures:
        (ROOT / "runs/scouting/failures.json").write_text(json.dumps(failures, indent=1))
        sys.exit(1)


if __name__ == "__main__":
    main()
