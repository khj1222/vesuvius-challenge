"""Run an ink model on one tifxyz segment and put the result where VC3D's Ink Detection panel finds it.

v2 (2026-11): VC3D now keeps surfaces in an object store (villa #2358, 2026-10-29) and its Ink
Detection panel no longer reads ink-detections.json. The store already has a place for ink: a surface
channel, an image whose size is a whole multiple of the point grid ("ink rendered at 20 pixels per
grid step", vc_object_store/docs/README.md). So v2 writes the prediction as a channel, by target:
  store-folder (default)  an importable tifxyz folder <work>/<segment>-store/ with the prediction as an
                          `ink_<name>.tif` sidecar, which ingestion turns into a channel (VC3D: File ->
                          Object Store -> Import from Folder, or `vc_object_ingest --surface`). The
                          published tifxyz meta.json uuid is often not a UUID ("output_tifxyz"), which
                          the store refuses; the folder gets a UUID derived from the segment
                          (uuid5, so re-running gives the same one) and keeps the old value as
                          `segment_ink_source_uuid`.
  store                   add the channel to a surface already in a store
                          (`vc_object_ingest --surface-channel UUID NAME TIFF`, through --ingest-cmd).
  legacy-json             the v0 behaviour below, for VC3D builds from before #2358.
Showing an `ink*` channel in the panel needs a VC3D change that is not in villa main yet (our branch
feat/vc3d-ink-surface-channel); without it the channel is stored and exported but not drawn.

v0 (legacy-json): VC3D (villa main before #2358, apps/VC3D/overlays/InkDetectionOverlayController.cpp) lists, for every segment
folder of the open project, the records in <segment>/ink-detections.json and stretches the image
named by each record's `local_file` over the segment's point grid. A record shows on a segment
when its `segment_id` or `segment_long_id` equals the segment's key: the catalog keys in
meta.json when present, else the folder name (builds before villa #2077: meta.json's uuid; both
are written). So no VC3D change is needed: this tool
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
  python tools/segment_ink.py SEGMENT_DIR --prediction existing_pred.tif --name reader_v3 \
      --target store --store objects.vcobj --store-uuid UUID --ingest-cmd "vc_object_ingest"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid as uuidlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = "segment_ink v2"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
# uuid5 namespace for segments whose meta.json uuid is not a UUID (fixed; changing it renames surfaces).
SEGMENT_NS = uuidlib.UUID("6f0c1d52-3b1e-5e7a-9f43-5e9a1c0b7d21")
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
    """(segment_id, segment_long_id) as VC3D will match them for this folder.

    VC3D since villa #2077 (2026-10-13, in "VC3D Latest") keys a plain segment by its folder name;
    older builds ("VC3D Stable" and earlier) key it by meta.json's uuid. A record shows when either
    field equals the key, so the uuid goes in segment_long_id. Two segments sharing a uuid are
    already indistinguishable to those older builds, so this adds no new collision.
    """
    for key in CATALOG_KEYS:
        value = meta.get(key)
        if isinstance(value, str) and value:
            return value, value
    uuid = meta.get("uuid")
    if isinstance(uuid, str) and uuid and uuid != seg_dir.name:
        return seg_dir.name, uuid
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


def channel_name(stem: str) -> str:
    """`ink_<stem>` in the lowercase form ingestion recognizes as a sidecar channel.

    The VC3D panel change lists exactly `ink` and `ink_*` channels (not `inked`, not `ink9um`)."""
    name = re.sub(r"[^a-z0-9_]+", "_", stem.lower()).strip("_")
    return name if name == "ink" or name.startswith("ink_") else f"ink_{name}"


def check_channel_shape(seg_dir: Path, image: Path) -> tuple[int, int]:
    """The store takes a channel only when each side is a whole multiple of the point grid."""
    import tifffile

    grid = tifffile.TiffFile(seg_dir / "x.tif").pages[0].shape[:2]
    with tifffile.TiffFile(image) as tif:
        if len(tif.pages) != 1:
            sys.exit(f"{image}: {len(tif.pages)} pages; a channel must be a single-page TIFF")
        shape = tif.pages[0].shape[:2]
    if shape[0] % grid[0] or shape[1] % grid[1]:
        sys.exit(f"{image}: {shape} is not a whole multiple of the point grid {grid}")
    return shape[0] // grid[0], shape[1] // grid[1]


def store_uuid(seg_dir: Path, meta: dict) -> str:
    value = meta.get("uuid")
    if isinstance(value, str) and UUID_RE.match(value):
        return value.lower()
    # Not a UUID (published tifxyz say "output_tifxyz"): derive one from the scroll/segment names.
    return str(uuidlib.uuid5(SEGMENT_NS, f"{seg_dir.parent.name}/{seg_dir.name}/{value}"))


def write_store_folder(seg_dir: Path, meta: dict, out: Path, channels: dict[str, Path]) -> str:
    """An importable tifxyz folder: x/y/z (+mask), meta.json with a valid uuid, one sidecar per channel."""
    out.mkdir(parents=True, exist_ok=True)
    for name in ("x.tif", "y.tif", "z.tif", "mask.tif"):
        if (seg_dir / name).is_file():
            shutil.copyfile(seg_dir / name, out / name)
    uid = store_uuid(seg_dir, meta)
    new_meta = dict(meta, uuid=uid)
    if meta.get("uuid") != uid:
        new_meta["segment_ink_source_uuid"] = meta.get("uuid")
    tmp = out / "meta.json.tmp"
    tmp.write_text(json.dumps(new_meta, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, out / "meta.json")
    for name, image in channels.items():
        # The prediction TIFF itself: ingestion keeps exact samples, so no re-encoding.
        shutil.copyfile(image, out / f"{name}.tif")
    return uid


def add_store_channel(ingest_cmd: str, db: str, author: str, uid: str, name: str, image: Path) -> None:
    cmd = shlex.split(ingest_cmd) + [  # POSIX quoting; use forward slashes on Windows
        "--db", db, "--author", author, "--surface-channel", uid, name, image.as_posix()]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        sys.exit(f"vc_object_ingest failed (exit {proc.returncode}): {' '.join(cmd)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("segment", type=Path, help="tifxyz segment folder (meta.json, x/y/z.tif)")
    ap.add_argument("--checkpoint", type=Path, help="ink checkpoint (optional with --prediction)")
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
    ap.add_argument("--prediction", type=Path, help="skip rendering and inference: use this uint8 TIFF")
    ap.add_argument("--prediction-reverse", type=Path, help="with --prediction: the reverse-direction TIFF")
    ap.add_argument("--target", action="append", choices=("store-folder", "store", "legacy-json"),
                    help="where the result goes (repeatable; default store-folder)")
    ap.add_argument("--store", help="object store (.vcobj) for --target store")
    ap.add_argument("--store-uuid", help="surface UUID in --store (default: the uuid store-folder would use)")
    ap.add_argument("--ingest-cmd", default="vc_object_ingest",
                    help="command (with any wrapper prefix) that runs vc_object_ingest")
    ap.add_argument("--author", default=os.environ.get("USER") or os.environ.get("USERNAME") or "segment_ink")
    args = ap.parse_args()
    targets = args.target or ["store-folder"]
    if "store" in targets and not args.store:
        sys.exit("--target store needs --store")

    seg_dir = args.segment.resolve()
    meta = check_segment(seg_dir)
    seg_id, seg_long_id = segment_key(seg_dir, meta)
    if args.segment_key:
        seg_id = args.segment_key
    work = (args.work or seg_dir.parent / "_segment_ink").resolve()
    work.mkdir(parents=True, exist_ok=True)

    ckpt = args.checkpoint.resolve() if args.checkpoint else None
    stem = args.name or (f"{ckpt.parent.name}_{ckpt.stem}" if ckpt else None)
    if not stem:
        sys.exit("give --name when there is no --checkpoint")
    if args.prediction:
        render_zarr = args.render_zarr.resolve() if args.render_zarr else None
        outs, directions = [args.prediction.resolve()], ["forward" if args.direction == "both" else args.direction]
        if args.prediction_reverse:
            outs.append(args.prediction_reverse.resolve())
            directions = ["forward", "reverse"]
    else:
        if not ckpt:
            sys.exit("--checkpoint is required unless --prediction is given")
        if args.render_zarr:
            render_zarr = args.render_zarr.resolve()
        else:
            if not (args.scroll and args.volume):
                sys.exit("give --scroll and --volume to render, or --render-zarr")
            render_zarr = work / f"{seg_dir.name}_render.zarr"
            render(seg_dir, args.scroll, args.volume, render_zarr)
        raw = work / f"{seg_dir.name}_{stem}.tif"
        outs = infer(render_zarr, ckpt, raw, args.direction, args.python, args.villa_src)
        directions = ["forward", "reverse"] if args.direction == "both" else [args.direction]

    channels = {}
    for out, direction in zip(outs, directions):
        scale = check_channel_shape(seg_dir, out)
        name = channel_name(f"{stem}_reverse" if direction == "reverse" else stem)
        channels[name] = out
        print(f"channel {name}: {out.name}, {scale[0]}x{scale[1]} px per grid step")

    if "store-folder" in targets:
        folder = work / f"{seg_dir.name}-store"
        uid = write_store_folder(seg_dir, meta, folder, channels)
        print(f"store folder (surface uuid {uid}): {folder}")
        print("  import it in VC3D (File -> Object Store -> Import from Folder) or with "
              "`vc_object_ingest --db objects.vcobj --author NAME --surface <folder>`")
    if "store" in targets:
        uid = args.store_uuid or store_uuid(seg_dir, meta)
        for name, out in channels.items():
            add_store_channel(args.ingest_cmd, args.store, args.author, uid, name, out)
            print(f"store {args.store}: surface {uid} channel {name}")
    if "legacy-json" not in targets:
        return

    ckpt_sha = sha256(ckpt) if ckpt else ""
    for out, direction in zip(outs, directions):
        record = {
            "label": f"{args.label or stem} ({direction})",
            "segment_id": seg_id,
            "artifact_type": "local-ink-run",
            "checkpoint": ckpt.name if ckpt else "",
            "checkpoint_sha256": ckpt_sha,
            "render": str(render_zarr) if render_zarr else "",
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
