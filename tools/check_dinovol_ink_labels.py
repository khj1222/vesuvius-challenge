"""List which open-data ink labels a dinovol checkpoint could have seen during pretraining.

The released dinovol checkpoints were pretrained with an object/ink contrastive term
(`object_points.use_metadata_meshes`, `ink_weight` 0.1). Their loader,
`dinovol_2/dataset/object_labels.py::load_or_build_volume_meshes`, builds the mesh segments of
each training volume from the open-data `metadata.json`, and attaches a segment's `ink-labels`
(inklabels.zarr + supervision.zarr, level 4) whenever that segment can be placed on the volume:
  - it has a `tifxyz-transformed` representation whose `target_volume` is the training volume, or
  - its `original_volume_id` is the training volume, or one with a `volume_transforms` matrix to it.
This script replays exactly that rule for every `volume_path` in the checkpoint's own saved config
and reports, per ink-labelled segment, whether it reaches pretraining and by which route. It reads
the checkpoint (weights_only) and a local copy of `metadata.json`; nothing else is downloaded.

Before scoring a dinovol-based ink model on "unseen" segments, drop every segment this lists as used.
Limit: it replays today's metadata.json; the copy cached at training time may have differed.

Usage: python tools/check_dinovol_ink_labels.py CHECKPOINT.pt metadata.json [--out report.json]
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

import torch


def walk_values(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            else:
                yield from walk_values(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_values(v, key)


def parse_volume_path(path: str) -> tuple[str | None, str | None]:
    # s3://vesuvius-challenge-open-data/<sample>/volumes/<volume id>-<...>.zarr/
    parts = path.rstrip("/").split("/")
    sample = parts[3] if len(parts) > 3 else None
    volume = parts[parts.index("volumes") + 1].split("-")[0] if "volumes" in parts else None
    return sample, volume


def as_list(x):
    if isinstance(x, dict):
        return list(x.values())
    return list(x or [])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("metadata", type=Path, help="open-data metadata.json (gzip or plain)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, weights_only=True, mmap=True, map_location="cpu")
    cfg = next((ck[k] for k in ("config", "cfg", "args") if isinstance(ck, dict) and k in ck), None)
    if cfg is None:
        raise SystemExit(f"no config in checkpoint; keys: {list(ck)[:20]}")
    volume_paths = [v for v in walk_values(cfg, "volume_path") if isinstance(v, str)]
    flags = {k: list(walk_values(cfg, k)) for k in ("use_metadata_meshes", "ink_weight", "output_dir")}

    raw = args.metadata.read_bytes()
    meta = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
    samples = meta["samples"]

    rows = []
    for vp in volume_paths:
        sample_id, volume_id = parse_volume_path(vp)
        target = samples.get(sample_id) if isinstance(samples, dict) else None
        if target is None:
            target = next((s for s in as_list(samples) if s.get("sample", {}).get("id") == sample_id
                           or any(v.get("id") == volume_id for v in as_list(s.get("volumes")))), None)
        if target is None:
            continue
        transforms = {}
        for vt in target.get("sample", {}).get("properties", {}).get("volume_transforms") or []:
            if vt.get("to_volume_id") == volume_id and "matrix" in vt:
                transforms[str(vt.get("from_volume_id", ""))] = "volume_transform"
            for sub in vt.get("transforms") or []:
                if sub.get("to_volume_id") == volume_id and "matrix" in sub:
                    transforms[str(vt.get("from_volume_id", ""))] = "volume_transform (chained)"
        for seg in as_list(target.get("segments")):
            reps = [r for r in (seg.get("data") or seg.get("representations") or []) if isinstance(r, dict)]
            if not any(r.get("type") == "ink-labels" for r in reps):
                continue
            orig = str(seg.get("original_volume_id", ""))
            route = None
            if any(r.get("type") == "tifxyz-transformed" and (r.get("parameters") or {}).get("target_volume") == volume_id
                   for r in reps):
                route = "tifxyz-transformed"
            elif (orig == volume_id or orig in transforms) and any(r.get("type") in ("tifxyz-normalized", "tifxyz") for r in reps):
                route = "same volume" if orig == volume_id else transforms[orig]
            rows.append({"sample": sample_id, "segment": seg.get("id"), "original_volume": orig,
                         "training_volume": volume_id, "used": route is not None, "route": route})

    print("config:", {k: v[:2] for k, v in flags.items()})
    print(f"training volumes: {len(volume_paths)}")
    per_sample = defaultdict(lambda: [0, 0])
    for r in rows:
        per_sample[r["sample"]][0 if r["used"] else 1] += 1
    print("ink-labelled segments, used / not used:")
    for s, (u, n) in sorted(per_sample.items()):
        print(f"  {s}: {u} / {n}")
    for r in rows:
        if not r["used"]:
            print(f"  not used: {r['sample']} {r['segment']} (original volume {r['original_volume']})")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"checkpoint": args.checkpoint.name, "config": flags,
                                        "training_volumes": volume_paths, "segments": rows}, indent=1))


if __name__ == "__main__":
    main()
