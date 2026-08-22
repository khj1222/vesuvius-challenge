#!/usr/bin/env python3
"""Build an ink_9um training config for one cross-scroll (or cross-segment) arm.

The released recipe -- villa ``configs/aligned21_hybrid_3d2d.json`` plus the
sampling contract in ``aligned21_fixed_scroll_prior.json`` -- trains on all 29
representations across four scrolls, so every annotated pixel of every segment
is training data. Dropping a scroll turns the same recipe into a generalisation
probe: nothing on the held-out scroll is ever seen, which makes its whole
supervision mask honest held-out ground truth for
``tools/eval_validation.py --region-kind supervision_mask``.

Example
-------
    python tools/make_ink9um_config.py --exclude-scroll Paris4 \
        --out configs/ink9um_no_paris4.json --run-dir runs/ink9um_no_paris4

The per-batch scroll quotas are renormalised over the surviving scrolls (the
sampler insists they sum to ``batch_size``), so an arm keeps the recipe's
relative weighting instead of silently reweighting toward the biggest scroll.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALIGNED_FAMILY = "public_2p4_level2_zmean4"
NATIVE_FAMILY = "native_9p362_level0"
LABEL_DIRS = {
    ALIGNED_FAMILY: "labels/aligned-scrollprizeorg-21slices",
    NATIVE_FAMILY: "labels/native9-scrollprizeorg-21slices",
}


def as_posix(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def volume_path(data_root: Path, family: str, segment: str) -> Path:
    """Locate the ~9 um surface volume a representation trains on."""
    if family == ALIGNED_FAMILY:
        return data_root / "surface-volumes/aligned9" / f"{segment}.zarr"
    holder = data_root / "surface-volumes/native9" / segment
    candidates = sorted(holder.glob("*.zarr"))
    if len(candidates) != 1:
        sys.exit(f"error: expected exactly one *.zarr under {holder}, found {len(candidates)}")
    return candidates[0]


def renormalise(quotas: dict, keep: set, batch_size: int) -> dict:
    """Spread the recipe's quotas over the surviving scrolls, summing to batch_size."""
    live = {scroll: value for scroll, value in quotas.items() if scroll in keep}
    if not live:
        sys.exit("error: every scroll was excluded")
    total = sum(live.values())
    exact = {scroll: batch_size * value / total for scroll, value in live.items()}
    out = {scroll: max(1, int(value)) for scroll, value in exact.items()}
    # Largest-remainder top-up so the quotas land exactly on batch_size.
    order = sorted(live, key=lambda s: exact[s] - int(exact[s]), reverse=True)
    index = 0
    while sum(out.values()) < batch_size:
        out[order[index % len(order)]] += 1
        index += 1
    while sum(out.values()) > batch_size:
        victim = max((s for s in order if out[s] > 1), key=lambda s: out[s])
        out[victim] -= 1
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--villa-configs", type=Path, default=Path("D:/vw2/ink-detection/configs"),
                        help="Directory holding aligned21_hybrid_3d2d.json and the sampling contract.")
    parser.add_argument("--data-root", type=Path, default=REPO / "data/ink_9um",
                        help="ink_9um root (labels/, surface-volumes/).")
    parser.add_argument("--exclude-scroll", action="append", default=[],
                        help="Scroll key to hold out entirely (0139, 1667, Paris4, 0814). Repeatable.")
    parser.add_argument("--exclude-segment", action="append", default=[],
                        help="Representation segment name to hold out. Repeatable.")
    parser.add_argument("--out", type=Path, required=True, help="Config path to write.")
    parser.add_argument("--run-dir", type=Path, required=True, help="Training out_dir.")
    parser.add_argument("--iterations", type=int, default=None, help="Override num_iterations.")
    parser.add_argument("--seed", type=int, default=None, help="Override seed (and the sampler seed).")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch_size.")
    parser.add_argument("--save-every", type=int, default=None)
    parser.add_argument("--val-every", type=int, default=None)
    parser.add_argument("--allow-missing", action="store_true",
                        help="Emit the config even if some volumes are not prepared yet.")
    args = parser.parse_args(argv)

    base = json.loads((args.villa_configs / "aligned21_hybrid_3d2d.json").read_text())
    contract = json.loads((args.villa_configs / "aligned21_fixed_scroll_prior.json").read_text())

    excluded_scrolls = set(args.exclude_scroll)
    excluded_segments = set(args.exclude_segment)
    known_scrolls = {rep["scroll"] for rep in contract["representations"]}
    unknown = excluded_scrolls - known_scrolls
    if unknown:
        sys.exit(f"error: unknown scroll(s) {sorted(unknown)}; known: {sorted(known_scrolls)}")

    kept, dropped = [], []
    for rep in contract["representations"]:
        if rep["scroll"] in excluded_scrolls or rep["segment"] in excluded_segments:
            dropped.append(rep)
        else:
            kept.append(rep)
    if not kept:
        sys.exit("error: the exclusions removed every representation")

    groups = OrderedDict()
    missing = []
    for rep in kept:
        family, segment = rep["source_family"], rep["segment"]
        volume = volume_path(args.data_root, family, segment)
        labels = args.data_root / LABEL_DIRS[family] / segment
        if not volume.exists():
            missing.append(str(volume))
        if not (labels / f"{segment}_inklabels.zarr").exists():
            missing.append(str(labels / f"{segment}_inklabels.zarr"))
        entry = groups.setdefault((family, rep["scroll"]), {
            "segments_path": as_posix(args.data_root / LABEL_DIRS[family]),
            "segments": [],
            "surface_volume_paths": {},
            "volume_scale": 0,
            "sampling_scroll": rep["scroll"],
            "sampling_physical_segment_keys": {},
            "sampling_representation_keys": {},
        })
        entry["segments"].append(segment)
        entry["surface_volume_paths"][segment] = as_posix(volume)
        entry["sampling_physical_segment_keys"][segment] = rep["physical_segment_key"]
        entry["sampling_representation_keys"][segment] = rep["representation_key"]

    if missing and not args.allow_missing:
        sys.exit("error: missing inputs:\n  " + "\n  ".join(sorted(set(missing))))

    batch_size = args.batch_size or int(base["batch_size"])
    seed = args.seed if args.seed is not None else int(base["seed"])
    quotas = renormalise(contract["target_batch_counts"],
                         {rep["scroll"] for rep in kept}, batch_size)
    held_out = sorted({rep["segment"] for rep in dropped})

    config = dict(base)
    config["batch_size"] = batch_size
    config["seed"] = seed
    config["fixed_scroll_prior"] = {"seed": seed, "target_batch_counts": quotas}
    config["out_dir"] = as_posix(args.run_dir)
    config["datasets"] = list(groups.values())
    if args.iterations is not None:
        config["num_iterations"] = args.iterations
    if args.save_every is not None:
        config["save_every"] = args.save_every
    if args.val_every is not None:
        config["val_every"] = args.val_every
    arm = f"held out {sorted(excluded_scrolls) or held_out}" if dropped else "all 29 representations"
    config["description"] = (f"{base['description'].split('.')[0]}. Arm: {arm}; "
                             f"{len(kept)} representations, quotas {quotas}.")
    config["held_out_representations"] = held_out

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(config, indent=2) + "\n")
    print(f"wrote {args.out}")
    print(f"  representations : {len(kept)} kept, {len(dropped)} held out")
    if dropped:
        print(f"  held out        : {', '.join(held_out)}")
    print(f"  quotas          : {quotas} (batch {batch_size})")
    print(f"  dataset entries : {len(groups)}")
    if missing:
        print(f"  WARNING         : {len(set(missing))} input(s) not on disk yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
