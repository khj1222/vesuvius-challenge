"""Run an ink model on one tifxyz segment and put the result where VC3D's Ink Detection panel finds it.

VC3D (villa main, apps/VC3D/overlays/InkDetectionOverlayController.cpp) lists, for every segment
folder of the open project, the records in <segment>/ink-detections.json and stretches the image
named by each record's `local_file` over the segment's point grid. A record shows on a segment
when its `segment_id` or `segment_long_id` equals the segment's key: the catalog keys in
meta.json when present, else the folder name. So no VC3D change is needed: this tool
  1. renders the segment to a flat surface volume with vc_render_tifxyz (28 slices, --flip-normals,
     the orientation that reproduces the team's published surface volumes -- docs/25 section 8),
  2. runs villa's own `vesuvius.ink_detection.inference.infer` on it (code not copied),
  3. writes <segment>/ink-detections/<name>.jpg and adds a record to ink-detections.json.

The panel image is a JPEG because VC3D hides every non-JPEG record of a segment that also has a
JPEG one (catalog maps are JPEGs), so a TIFF would vanish on exactly the segments people compare
against. The raw uint8 TIFF from villa's infer stays in the work folder, named in the record.

If ink-detections.json does not exist yet but catalog-origin.json carries `ink_detections`, those
records are copied in first: VC3D reads ink-detections.json alone once it exists, so creating it
bare would hide the team's catalog maps. Existing records are kept; a record with the same
`local_file` is replaced. VC3D ignores keys it does not know, so provenance goes in the record.

Caveats: saving a segment over itself in VC3D currently deletes its subfolders, ink-detections/
included (villa #2222, fix proposed in #2223). A catalog segment that VC3D re-downloads (refresh of
a stale cache) is replaced as a whole folder, so our records go with it; run the tool again.

Usage (Windows, render through WSL as tools/render_wsl.sh does):
  python tools/segment_ink.py SEGMENT_DIR --scroll PHerc0814 \
      --volume 20250804134230-9.362um-1.2m-113keV-masked.zarr \
      --checkpoint data/ink_9um/models/hybrid_3d2d-seed43/step-075000.pth --direction both
  python tools/segment_ink.py SEGMENT_DIR --render-zarr existing_render.zarr --checkpoint ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = "segment_ink v0"
S3 = "https://vesuvius-challenge-open-data.s3.amazonaws.com"
# The catalog keys VC3D prefers over the folder name (canonicalSegmentKey), in its order.
CATALOG_KEYS = ("vc_open_data_segment_long_id", "vc_open_data_catalog_segment_lineage_id",
                "vc_open_data_segment_id")
GIT_BASH = "C:/Program Files/Git/bin/bash.exe"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def segment_key(seg_dir: Path, meta: dict) -> tuple[str, str]:
    """(segment_id, segment_long_id) as VC3D will match them for this folder."""
    for key in CATALOG_KEYS:
        value = meta.get(key)
        if isinstance(value, str) and value:
            return value, value
    return seg_dir.name, ""


def check_segment(seg_dir: Path) -> dict:
    for name in ("meta.json", "x.tif", "y.tif", "z.tif"):
        if not (seg_dir / name).is_file():
            sys.exit(f"not a tifxyz segment folder (missing {name}): {seg_dir}")
    return json.loads((seg_dir / "meta.json").read_text(encoding="utf-8"))


def render(seg_dir: Path, scroll: str, volume: str, out: Path) -> None:
    """Render with the same flags the team's published surface volumes reproduce."""
    if (out / "0" / ".zarray").is_file():
        print(f"render exists, reusing: {out}")
        return
    t0 = time.time()
    if platform.system() == "Windows":
        # The Windows renderer can leave an unkillable process at exit; the Linux build in WSL is
        # killable (tools/render_wsl.sh). MSYS_NO_PATHCONV keeps Git Bash from rewriting paths.
        cmd = [GIT_BASH, (ROOT / "tools/render_wsl.sh").as_posix(), scroll, volume,
               seg_dir.resolve().as_posix(), out.resolve().as_posix(), "--flip-normals"]
        env = dict(os.environ, MSYS_NO_PATHCONV="1")
    else:
        cmd = ["vc_render_tifxyz", "-v", str(out.parent / f"{scroll}_cache.zarr"),
               "--remote-url", f"{S3}/{scroll}/volumes/{volume}", "-g", "0", "--scale", "1",
               "-s", str(seg_dir), "--num-slices", "28", "--slice-step", "1",
               "--zarr-output", str(out), "--flip-normals"]
        env = None
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0 or not (out / "0" / ".zarray").is_file():
        sys.exit(f"render failed (exit {proc.returncode}): {out}")
    print(f"rendered in {(time.time() - t0) / 60:.1f} min: {out}")


def infer(render_zarr: Path, checkpoint: Path, out_tif: Path, direction: str,
          python: str, villa_src: Path) -> list[Path]:
    """villa's flat inference, unmodified; --direction both also writes <stem>_reverse.tif."""
    cmd = [python, "-m", "vesuvius.ink_detection.inference.infer", str(render_zarr),
           str(checkpoint), str(out_tif), "--direction", direction]
    if platform.system() == "Windows":
        cmd.append("--no-compile")  # no Triton on Windows
    env = dict(os.environ, PYTHONPATH=str(villa_src))
    t0 = time.time()
    proc = subprocess.run(cmd, env=env)
    outs = [out_tif]
    if direction == "both":
        outs.append(out_tif.with_name(f"{out_tif.stem}_reverse{out_tif.suffix}"))
    if proc.returncode != 0 or not all(p.is_file() for p in outs):
        sys.exit(f"inference failed (exit {proc.returncode})")
    print(f"inferred in {(time.time() - t0) / 60:.1f} min")
    return outs


def read_records(seg_dir: Path) -> list[dict]:
    """The records VC3D shows today, so writing the file never hides any of them."""
    path = seg_dir / "ink-detections.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
    origin = seg_dir / "catalog-origin.json"
    if origin.is_file():
        data = json.loads(origin.read_text(encoding="utf-8")).get("ink_detections")
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
    return []


def place(seg_dir: Path, image: Path, name: str, record: dict) -> Path:
    """Write `image` (villa's uint8 TIFF) as <segment>/ink-detections/<name>.jpg and record it."""
    import tifffile
    from PIL import Image

    dest_dir = seg_dir / "ink-detections"
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / f"{name}.jpg"
    tmp_img = dest.with_name(dest.name + ".tmp")
    Image.fromarray(tifffile.imread(image)).save(tmp_img, format="JPEG", quality=95)
    os.replace(tmp_img, dest)
    record = dict(record, local_file=f"ink-detections/{dest.name}", raw_prediction=str(image))
    records = [r for r in read_records(seg_dir) if r.get("local_file") != record["local_file"]]
    records.append(record)
    tmp = seg_dir / "ink-detections.json.tmp"
    tmp.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, seg_dir / "ink-detections.json")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("segment", type=Path, help="tifxyz segment folder (meta.json, x/y/z.tif)")
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--scroll", help="open-data scroll folder, e.g. PHerc0814 (for rendering)")
    ap.add_argument("--volume", help="volume zarr name under <scroll>/volumes/ (for rendering)")
    ap.add_argument("--render-zarr", type=Path, help="use this flat surface volume instead of rendering")
    ap.add_argument("--work", type=Path, help="where renders and raw predictions go (default: <segment>/../_segment_ink)")
    ap.add_argument("--direction", choices=("forward", "reverse", "both"), default="forward")
    ap.add_argument("--name", help="output image name stem (default: <checkpoint folder>_<checkpoint stem>)")
    ap.add_argument("--label", help="label shown in VC3D's detection list")
    ap.add_argument("--segment-key", help="override the segment_id VC3D should match")
    ap.add_argument("--python", default=sys.executable, help="python with villa's ink_detection dependencies")
    ap.add_argument("--villa-src", type=Path, default=Path("D:/vw17/vesuvius/src"),
                    help="villa vesuvius/src checkout providing vesuvius.ink_detection")
    args = ap.parse_args()

    seg_dir = args.segment.resolve()
    meta = check_segment(seg_dir)
    seg_id, seg_long_id = segment_key(seg_dir, meta)
    if args.segment_key:
        seg_id = args.segment_key
    work = (args.work or seg_dir.parent / "_segment_ink").resolve()
    work.mkdir(parents=True, exist_ok=True)

    if args.render_zarr:
        render_zarr = args.render_zarr.resolve()
    else:
        if not (args.scroll and args.volume):
            sys.exit("give --scroll and --volume to render, or --render-zarr")
        render_zarr = work / f"{seg_dir.name}_render.zarr"
        render(seg_dir, args.scroll, args.volume, render_zarr)

    ckpt = args.checkpoint.resolve()
    stem = args.name or f"{ckpt.parent.name}_{ckpt.stem}"
    raw = work / f"{seg_dir.name}_{stem}.tif"
    outs = infer(render_zarr, ckpt, raw, args.direction, args.python, args.villa_src)

    ckpt_sha = sha256(ckpt)
    for out, direction in zip(outs, ("forward", "reverse") if args.direction == "both" else (args.direction,)):
        record = {
            "label": f"{args.label or stem} ({direction})",
            "segment_id": seg_id,
            "artifact_type": "local-ink-run",
            "checkpoint": ckpt.name,
            "checkpoint_sha256": ckpt_sha,
            "render": str(render_zarr),
            "layer_direction": direction,
            "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool_version": TOOL_VERSION,
        }
        if seg_long_id:
            record["segment_long_id"] = seg_long_id
        if args.scroll and args.volume:
            record["volume"] = f"{args.scroll}/volumes/{args.volume}"
        name = f"{stem}_reverse" if direction == "reverse" else stem
        dest = place(seg_dir, out, name, record)
        print(f"VC3D record: {record['label']} -> {dest}")
    print(f"open the segment '{seg_id}' in VC3D and pick the detection in the Ink Detection panel")


if __name__ == "__main__":
    main()
