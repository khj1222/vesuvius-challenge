"""Re-run the crashing variants through base / head / head+candidate-fix.

Adds extents that specifically probe the one-row-strip condition:
  * rowsperstrip == 1                (every strip is one row)
  * height % rowsperstrip == 1       (only the last strip is one row)
  * height == 1                      (the whole image is one row)
  * width == 1                       (a squeeze fix must not transpose this)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
REPO = Path("D:/vesuvius-challenge")
TREES = {"base": Path("D:/vw5"), "head": Path("D:/vw4"), "headfix": Path("D:/vw6")}

# (case, height, width, kind, mode, [layouts])
CASES = [
    ("even_block", 2048, 2048, "label", "nearest", ["strip1"]),
    ("odd_odd", 2049, 2051, "label", "nearest", ["strip1", "strip1024"]),
    ("odd_cross_block", 1025, 1027, "label", "nearest", ["strip1", "strip1024"]),
    ("coprime", 1543, 2311, "label", "nearest", ["strip1"]),
    ("tall_narrow", 4099, 37, "label", "nearest", ["strip1"]),
    ("wide_short", 37, 4099, "label", "nearest", ["strip1"]),
    ("parity_flip", 2050, 2050, "label", "nearest", ["strip1"]),
    ("tiny_odd", 63, 65, "label", "nearest", ["strip1"]),
    ("mean_odd_odd", 2049, 2051, "gray", "mean", ["strip1"]),
    ("mean_coprime", 1543, 2311, "gray", "mean", ["strip1"]),
    ("mean_parity_flip", 2050, 2050, "gray", "mean", ["strip1"]),
    ("u16_odd", 2049, 2051, "u16", "nearest", ["strip1"]),
    # last strip is exactly one row at a strip size that is not 1024
    ("mod1_256", 513, 1027, "label", "nearest", ["strip256", "tiled256"]),
    ("mod1_16", 2049, 1027, "label", "nearest", ["strip16", "tiled256"]),
    # degenerate extents
    ("height1", 1, 4099, "label", "nearest", ["strip1", "stripfull", "tiled256"]),
    ("width1", 4099, 1, "label", "nearest", ["strip1", "strip7", "stripfull", "tiled256"]),
    ("both1", 1, 1, "label", "nearest", ["strip1", "tiled256"]),
]


def make_content(case: str, height: int, width: int, kind: str) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(case)) % (2**32))
    if kind == "gray":
        yy, xx = np.mgrid[0:height, 0:width]
        base = ((yy * 7 + xx * 13) % 251).astype(np.float64)
        return np.clip(base + rng.integers(0, 40, size=(height, width)), 0, 255).astype(np.uint8)
    dtype = np.uint16 if kind == "u16" else np.uint8
    high = 4095 if kind == "u16" else 255
    image = np.zeros((height, width), dtype=dtype)
    for _ in range(12):
        y0 = int(rng.integers(0, max(1, height - 1) or 1))
        x0 = int(rng.integers(0, max(1, width - 1) or 1))
        h = int(rng.integers(1, max(2, height // 3)))
        w = int(rng.integers(1, max(2, width // 3)))
        image[y0 : y0 + h, x0 : x0 + w] = high
    image[rng.random((height, width)) < 0.01] = high
    return image


def layout_kwargs(layout: str, height: int) -> dict[str, object]:
    if layout.startswith("tiled"):
        size = int(layout[5:])
        return {"tile": (size, size)}
    if layout == "stripfull":
        return {"rowsperstrip": height}
    if layout.startswith("strip"):
        return {"rowsperstrip": int(layout[5:])}
    raise ValueError(layout)


def input_path(work: Path, tree: str, case: str, layout: str, mode: str) -> Path:
    stem = "seg_max" if mode == "mean" else "seg_inklabels"
    return work / case / layout / tree / "seg" / f"{stem}.tif"


def run_tree(tree: str, work: Path, variants: list[dict]) -> dict[str, dict]:
    manifest = [
        {
            "case": f"{spec['case']}/{spec['layout']}",
            "input": str(input_path(work, tree, spec["case"], spec["layout"], spec["mode"])),
        }
        for spec in variants
    ]
    manifest_path = work / f"manifest_{tree}.json"
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(TREES[tree] / "vesuvius" / "src")
    process = subprocess.run(
        ["uv", "run", "--project", "external/villa/ink-detection", "--no-sync",
         "python", str(HERE / "convert_many.py"), str(manifest_path)],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=7200,
    )
    if process.returncode != 0:
        sys.stderr.write(process.stderr[-4000:])
        raise SystemExit(f"{tree} failed: {process.returncode}")
    return {
        json.loads(line)["case"]: json.loads(line)
        for line in process.stdout.splitlines()
        if line.strip().startswith("{")
    }


def compare(left: Path, right: Path, label: str) -> dict:
    process = subprocess.run(
        ["uv", "run", "--project", "external/villa/ink-detection", "--no-sync",
         "python", str(HERE / "compare_zarr.py"), str(left), str(right), "--label", label],
        cwd=REPO, capture_output=True, text=True, timeout=3600,
    )
    if process.returncode != 0:
        sys.stderr.write(process.stderr[-3000:])
        raise SystemExit(f"compare failed: {label}")
    for line in process.stdout.splitlines():
        if line.strip().startswith("{"):
            return json.loads(line)
    raise SystemExit(f"no output: {label}")


def numeric_verdict(detail: dict) -> str:
    if detail.get("byte_identical"):
        return "equal"
    numeric = detail.get("numeric")
    if numeric is None:
        return "unknown"
    if any(entry.get("reason") for entry in numeric):
        return "SHAPE"
    total = sum(int(entry.get("mismatched_voxels", 0)) for entry in numeric)
    return "equal" if total == 0 else f"DIFFER({total})"


def main() -> None:
    work = HERE / "work_fix"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    variants = []
    for case, height, width, kind, mode, layouts in CASES:
        image = make_content(case, height, width, kind)
        for layout in layouts:
            for tree in TREES:
                target = input_path(work, tree, case, layout, mode)
                target.parent.mkdir(parents=True, exist_ok=True)
                tifffile.imwrite(
                    target, image, compression="lzw", **layout_kwargs(layout, height)
                )
            variants.append(
                {"case": case, "layout": layout, "mode": mode,
                 "height": height, "width": width, "kind": kind}
            )
    print(f"{len(variants)} variants x {len(TREES)} trees")

    runs = {tree: run_tree(tree, work, variants) for tree in TREES}

    rows = []
    header = f"{'case':17s} {'layout':10s} {'H':>5s} {'W':>5s} {'strips':>7s} {'last':>5s}  {'base':>6s} {'head':>10s} {'headfix':>8s}  {'fix==base':>10s}"
    print(header)
    print("-" * len(header))
    for spec in variants:
        key = f"{spec['case']}/{spec['layout']}"
        record = {tree: runs[tree].get(key, {}) for tree in TREES}
        geometry = (record["base"].get("input_geometry") or {})
        chunks = geometry.get("chunks") or [None, None]
        n_strips = geometry.get("n_blocks")
        last_rows = (spec["height"] % chunks[0]) or chunks[0] if chunks[0] else None
        row = dict(spec)
        row["n_blocks"] = n_strips
        row["last_block_rows"] = last_rows
        for tree in TREES:
            row[f"{tree}_ok"] = record[tree].get("ok")
            row[f"{tree}_error"] = record[tree].get("error")
        if record["base"].get("ok") and record["headfix"].get("ok"):
            left = input_path(work, "headfix", spec["case"], spec["layout"], spec["mode"]).with_suffix(".zarr")
            right = input_path(work, "base", spec["case"], spec["layout"], spec["mode"]).with_suffix(".zarr")
            detail = compare(left, right, f"fix:{key}")
            row["fix_vs_base"] = numeric_verdict(detail)
            row["fix_vs_base_detail"] = detail
        else:
            row["fix_vs_base"] = "n/a"
        rows.append(row)
        def mark(tree: str) -> str:
            return "ok" if record[tree].get("ok") else "CRASH"
        print(
            f"{spec['case']:17s} {spec['layout']:10s} {spec['height']:5d} {spec['width']:5d} "
            f"{str(n_strips):>7s} {str(last_rows):>5s}  {mark('base'):>6s} {mark('head'):>10s} "
            f"{mark('headfix'):>8s}  {row['fix_vs_base']:>10s}"
        )

    (work / "results_fix.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    crashed_head = [r for r in rows if not r["head_ok"]]
    crashed_fix = [r for r in rows if not r["headfix_ok"]]
    mismatch = [r for r in rows if r["fix_vs_base"] not in {"equal", "n/a"}]
    print()
    print(f"head crashes    : {len(crashed_head)}/{len(rows)}")
    print(f"headfix crashes : {len(crashed_fix)}/{len(rows)}")
    print(f"fix mismatches  : {len(mismatch)}/{len(rows)}")
    for row in crashed_fix:
        print(f"  headfix still fails: {row['case']}/{row['layout']}: {row['headfix_error']}")
    for row in mismatch:
        print(f"  mismatch: {row['case']}/{row['layout']}: {row['fix_vs_base']}")


if __name__ == "__main__":
    main()
