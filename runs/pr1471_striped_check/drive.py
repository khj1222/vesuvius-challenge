"""Drive the #1471 odd-extent check.

For every (extent, strip layout, codec) variant we run the same content through
two trees:

  head = jaideepsaipadhi:fix/1231-stream-striped-tiff @ 6cec011  (streams strips)
  base = its parent aab644c on main                              (in-memory path)

and compare the resulting zarr stores byte-for-byte. Three questions:

  regression      head(striped) == base(striped)   does the PR change today's output?
  layout          head(striped) == head(tiled)     does a strip layout change the answer?
  preexisting     base(tiled)   == base(striped)   was there already a difference?

The tiled reference is written with tile=(256, 256) + LZW, which is what our
validation-mask harness writes.
"""

from __future__ import annotations

import argparse
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
TREES = {"head": Path("D:/vw4"), "base": Path("D:/vw5")}

# (case, height, width, kind, mode)
CASES = [
    ("even_block", 2048, 2048, "label", "nearest"),
    ("odd_odd", 2049, 2051, "label", "nearest"),
    ("odd_cross_block", 1025, 1027, "label", "nearest"),
    ("coprime", 1543, 2311, "label", "nearest"),
    ("tall_narrow", 4099, 37, "label", "nearest"),
    ("wide_short", 37, 4099, "label", "nearest"),
    ("parity_flip", 2050, 2050, "label", "nearest"),
    ("tiny_odd", 63, 65, "label", "nearest"),
    ("mean_odd_odd", 2049, 2051, "gray", "mean"),
    ("mean_coprime", 1543, 2311, "gray", "mean"),
    ("mean_parity_flip", 2050, 2050, "gray", "mean"),
    ("u16_odd", 2049, 2051, "u16", "nearest"),
]

FULL_LAYOUTS = ["tiled256", "strip1", "strip7", "strip1024", "stripfull"]
MEAN_LAYOUTS = ["tiled256", "strip1", "strip7"]
U16_LAYOUTS = ["tiled256", "strip7"]
CODECS = ["none", "deflate", "packbits", "jpeg"]


def make_content(case: str, height: int, width: int, kind: str) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(case)) % (2**32))
    if kind == "gray":
        yy, xx = np.mgrid[0:height, 0:width]
        base = ((yy * 7 + xx * 13) % 251).astype(np.float64)
        noise = rng.integers(0, 40, size=(height, width))
        return np.clip(base + noise, 0, 255).astype(np.uint8)
    # Label-like: a few filled boxes plus speckle, so edges land at odd offsets.
    dtype = np.uint16 if kind == "u16" else np.uint8
    high = 4095 if kind == "u16" else 255
    image = np.zeros((height, width), dtype=dtype)
    for _ in range(12):
        y0 = int(rng.integers(0, max(1, height - 1)))
        x0 = int(rng.integers(0, max(1, width - 1)))
        h = int(rng.integers(1, max(2, height // 3)))
        w = int(rng.integers(1, max(2, width // 3)))
        image[y0 : y0 + h, x0 : x0 + w] = high
    speckle = rng.random((height, width)) < 0.01
    image[speckle] = high
    return image


def write_variant(path: Path, image: np.ndarray, layout: str, codec: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    compression = None if codec == "none" else codec
    kwargs: dict[str, object] = {"compression": compression}
    if layout == "tiled256":
        kwargs["tile"] = (256, 256)
    elif layout == "strip1":
        kwargs["rowsperstrip"] = 1
    elif layout == "strip7":
        kwargs["rowsperstrip"] = 7
    elif layout == "strip1024":
        kwargs["rowsperstrip"] = 1024
    elif layout == "stripfull":
        kwargs["rowsperstrip"] = image.shape[0]
    else:
        raise ValueError(layout)
    tifffile.imwrite(path, image, **kwargs)


def variant_dir(work: Path, tree: str, case: str, variant: str) -> Path:
    return work / case / variant / tree / "seg"


def variant_input(work: Path, tree: str, case: str, variant: str, mode: str) -> Path:
    stem = "seg_max" if mode == "mean" else "seg_inklabels"
    return variant_dir(work, tree, case, variant) / f"{stem}.tif"


def build(work: Path) -> list[dict[str, object]]:
    variants: list[dict[str, object]] = []
    for case, height, width, kind, mode in CASES:
        image = make_content(case, height, width, kind)
        if kind == "gray":
            layouts = MEAN_LAYOUTS
        elif kind == "u16":
            layouts = U16_LAYOUTS
        else:
            layouts = FULL_LAYOUTS
        specs = [(layout, "lzw") for layout in layouts]
        if case == "coprime":
            specs += [("strip7", codec) for codec in CODECS]
        for layout, codec in specs:
            variant = layout if codec == "lzw" else f"{layout}_{codec}"
            for tree in TREES:
                target = variant_input(work, tree, case, variant, mode)
                try:
                    write_variant(target, image, layout, codec)
                except Exception as error:  # noqa: BLE001 - record and skip
                    print(f"  skip {case}/{variant}: {type(error).__name__}: {error}")
                    target = None
                    break
            if target is None:
                continue
            variants.append(
                {
                    "case": case,
                    "variant": variant,
                    "layout": layout,
                    "codec": codec,
                    "mode": mode,
                    "kind": kind,
                    "height": height,
                    "width": width,
                }
            )
    return variants


def run_tree(tree: str, work: Path, variants: list[dict[str, object]]) -> dict[str, dict]:
    manifest = [
        {
            "case": f"{spec['case']}/{spec['variant']}",
            "input": str(variant_input(work, tree, spec["case"], spec["variant"], spec["mode"])),
        }
        for spec in variants
    ]
    manifest_path = work / f"manifest_{tree}.json"
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(TREES[tree] / "vesuvius" / "src")
    command = [
        "uv", "run", "--project", "external/villa/ink-detection", "--no-sync",
        "python", str(HERE / "convert_many.py"), str(manifest_path),
    ]
    process = subprocess.run(
        command, cwd=REPO, env=env, capture_output=True, text=True, timeout=7200
    )
    if process.returncode != 0:
        sys.stderr.write(process.stderr[-4000:])
        raise SystemExit(f"{tree} tree failed with {process.returncode}")
    records = {}
    for line in process.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        record = json.loads(line)
        records[record["case"]] = record
    return records


def compare(left: Path, right: Path, label: str) -> dict[str, object]:
    command = [
        "uv", "run", "--project", "external/villa/ink-detection", "--no-sync",
        "python", str(HERE / "compare_zarr.py"), str(left), str(right), "--label", label,
    ]
    process = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, timeout=3600
    )
    if process.returncode != 0:
        sys.stderr.write(process.stderr[-3000:])
        raise SystemExit(f"compare failed for {label}")
    for line in process.stdout.splitlines():
        if line.strip().startswith("{"):
            return json.loads(line)
    raise SystemExit(f"no comparison output for {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default=str(HERE / "work"))
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    work = Path(args.work)
    if args.fresh and work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    print("building inputs ...")
    variants = build(work)
    print(f"  {len(variants)} variants x 2 trees")

    runs: dict[str, dict[str, dict]] = {}
    for tree in TREES:
        print(f"running {tree} ...")
        runs[tree] = run_tree(tree, work, variants)

    print("comparing ...")
    rows: list[dict[str, object]] = []
    for spec in variants:
        case, variant, mode = spec["case"], spec["variant"], spec["mode"]
        key = f"{case}/{variant}"
        head_record = runs["head"].get(key, {})
        base_record = runs["base"].get(key, {})
        row = dict(spec)
        row["head_ok"] = head_record.get("ok")
        row["base_ok"] = base_record.get("ok")
        row["head_error"] = head_record.get("error")
        row["base_error"] = base_record.get("error")
        row["head_streamed"] = (head_record.get("result") or {}).get("streamed_tiled_tiff")
        row["base_streamed"] = (base_record.get("result") or {}).get("streamed_tiled_tiff")
        row["head_seconds"] = head_record.get("seconds")
        row["base_seconds"] = base_record.get("seconds")
        geometry = head_record.get("input_geometry") or {}
        row["tiff_chunks"] = geometry.get("chunks")
        row["tiff_chunked"] = geometry.get("chunked")
        row["tiff_blocks"] = geometry.get("n_blocks")
        row["tiff_compression"] = geometry.get("compression")

        if head_record.get("ok") and base_record.get("ok"):
            head_zarr = variant_input(work, "head", case, variant, mode).with_suffix(".zarr")
            base_zarr = variant_input(work, "base", case, variant, mode).with_suffix(".zarr")
            regression = compare(head_zarr, base_zarr, f"regression:{key}")
            row["regression_identical"] = regression["byte_identical"]
            row["regression_detail"] = regression

            reference_variant = "tiled256"
            reference = variant_input(work, "head", case, reference_variant, mode).with_suffix(".zarr")
            if reference.exists() and reference != head_zarr:
                layout = compare(head_zarr, reference, f"layout:{key}")
                row["layout_identical"] = layout["byte_identical"]
                row["layout_detail"] = layout
            base_reference = variant_input(work, "base", case, reference_variant, mode).with_suffix(".zarr")
            if base_reference.exists() and base_reference != base_zarr:
                preexisting = compare(base_zarr, base_reference, f"preexisting:{key}")
                row["preexisting_identical"] = preexisting["byte_identical"]
                row["preexisting_detail"] = preexisting
        rows.append(row)
        flag = "OK " if row.get("regression_identical", True) and row.get("layout_identical", True) else "!! "
        print(
            f"  {flag}{key:38s} head_streamed={row['head_streamed']} "
            f"base_streamed={row['base_streamed']} "
            f"reg={row.get('regression_identical')} layout={row.get('layout_identical')}"
        )

    out = work / "results.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
