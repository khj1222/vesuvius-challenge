#!/usr/bin/env python3
"""Arm B of docs/18: test-time entropy minimisation on the normalisation affines.

The cross-scroll gap measured in docs/15 is what this tries to close *without
any label on the target scroll*. The architecture leaves exactly one cheap
adaptation surface -- the affine parameters of its normalisation layers, 27,712
of 34.5M -- because there are no running statistics to recompute (docs/18 s2).
This is TENT: freeze everything else, minimise the mean binary entropy of the
prediction over target patches, and checkpoint often, because the objective
degenerates if it is run to convergence.

Honesty rules, taken from docs/18 s1 and unchanged here:

* Adaptation sees the target scroll's **images only**. The supervision mask, the
  labels and the annotated area never enter -- not as a loss mask, not as a
  sampling prior, not for choosing patches. Patches come from the render's valid
  area, which is what a real unlabelled scroll offers.
* Nothing is selected on target labels. Checkpoints are written at fixed steps
  chosen before the run, and the trajectory of the *unsupervised* objective is
  recorded here so a label-free stopping rule can be evaluated afterwards.

The output is a checkpoint in the same format the trainer writes, so
`koine_machines.inference.infer` consumes it with no special flag.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn


NORM_TYPES = (
    nn.InstanceNorm1d, nn.InstanceNorm2d, nn.InstanceNorm3d,
    nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d,
    nn.GroupNorm, nn.LayerNorm,
)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint", type=Path, help="LOSO checkpoint to adapt")
    parser.add_argument("out_dir", type=Path, help="directory for the adapted checkpoints")
    parser.add_argument("--volumes", nargs="+", required=True, type=Path,
                        help="target surface volumes (zarr); images only")
    parser.add_argument("--code-root", type=Path, default=Path("D:/vw2/ink-detection"),
                        help="checkout that provides koine_machines")
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--save-at", type=int, nargs="+", default=[50, 100, 200, 400])
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-occupancy", type=float, default=0.5,
                        help="minimum non-empty fraction of a patch footprint in the "
                             "occupancy scan; the render's valid area")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--block-cache", type=Path, default=None,
                        help="directory for cached per-volume block lists")
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--log-every", type=int, default=10)
    return parser.parse_args(argv)


def log(message: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


def occupancy_blocks(infer, zarr, volume: Path, patch: int, stride: int,
                     min_occupancy: float):
    """Blocks whose footprint is at least `min_occupancy` non-empty.

    infer.iter_blocks keeps a block if *any* low-resolution cell under it is
    non-zero, which is right for inference -- every scrap of sheet gets a
    prediction -- but wrong for adaptation, where a batch of mostly-empty
    patches would spend the objective on padding. The threshold is on the
    image's own occupancy scan, so no label is consulted.
    """
    root = infer.open_zarr_readonly(volume)
    array = root if isinstance(root, zarr.Array) else root["0"]
    shape = tuple(int(v) for v in array.shape)
    depth_first = int(np.argmin(shape)) == 0
    depth, height, width = shape if depth_first else (shape[2], shape[0], shape[1])

    if isinstance(root, zarr.Group) and "3" in root:
        mask_lowres, scale, level = infer.build_lowres_block_mask(
            root, height=height, width=width, user_mask=None)
    else:
        # These prepared volumes ship a single level, and infer's occupancy scan
        # then reads the whole array -- 7.4 GB for the largest Paris4 segment.
        # One z plane answers the same question: the non-empty area is the
        # rendered sheet, which does not move with depth.
        plane = array[depth // 2] if depth_first else array[:, :, depth // 2]
        mask_lowres = np.asarray(plane) != 0
        scale, level = (1, 1), "0 (single mid-depth plane)"
    blocks = infer.iter_blocks(image_shape=(height, width), patch_size=patch,
                              stride=stride, mask_lowres=mask_lowres,
                              occupancy_scale=scale)
    if mask_lowres is None:
        return blocks, (depth, height, width), len(blocks), level

    scale_y, scale_x = scale
    kept = []
    for block in blocks:
        low_y0 = block.y0 // scale_y
        low_x0 = block.x0 // scale_x
        low_y1 = max(low_y0 + 1, math.ceil((block.y0 + block.valid_h) / scale_y))
        low_x1 = max(low_x0 + 1, math.ceil((block.x0 + block.valid_w) / scale_x))
        footprint = mask_lowres[low_y0:low_y1, low_x0:low_x1]
        if footprint.size and float(footprint.mean()) >= min_occupancy:
            kept.append(block)
    return kept, (depth, height, width), len(blocks), level


def cached_blocks(infer, zarr, volume: Path, patch: int, min_occupancy: float,
                  cache_dir: Path | None):
    """Block lists are seed-independent, so the second seed reuses the first's."""
    key = f"{volume.name}_p{patch}_occ{min_occupancy:g}.json"
    cache = None if cache_dir is None else cache_dir / key
    if cache is not None and cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        blocks = [infer.Block(*row) for row in payload["blocks"]]
        return blocks, tuple(payload["shape"]), payload["before"], payload["level"] + " (cached)"
    blocks, shape, before, level = occupancy_blocks(
        infer, zarr, volume, patch, patch, min_occupancy)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({
            "volume": str(volume).replace("\\", "/"),
            "shape": list(shape), "before": before, "level": level,
            "blocks": [[b.y0, b.x0, b.valid_h, b.valid_w] for b in blocks],
        }), encoding="utf-8")
    return blocks, shape, before, level


def build_dataset(infer, zarr, volume: Path, bundle, args):
    patch = int(bundle.roi_size)
    blocks, (depth, height, width), before, level = cached_blocks(
        infer, zarr, volume, patch, args.min_occupancy, args.block_cache)
    root = infer.open_zarr_readonly(volume)
    resolution = "0"
    array = root if isinstance(root, zarr.Array) else root[resolution]
    shape = tuple(int(v) for v in array.shape)
    depth_first = int(np.argmin(shape)) == 0

    in_chans = int(bundle.in_chans)
    layer_indices = np.arange(0, depth, dtype=np.int64)
    if layer_indices.size > in_chans:
        start = (layer_indices.size - in_chans) // 2
        layer_indices = layer_indices[start:start + in_chans]

    reader = infer.OmeZarrPatchReader(
        input_path=volume, resolution=resolution, depth_axis_first=depth_first,
        height=height, width=width, layer_indices=layer_indices,
        preprocessing=bundle.preprocessing)
    dataset = infer.OmeZarrBlockDataset(reader=reader, blocks=blocks, patch_size=patch,
                                        preprocessing=bundle.preprocessing)
    log(f"  {volume.name}: {len(blocks)} patches kept of {before} non-empty "
        f"(occupancy level {level}, {height}x{width}, z {layer_indices.size})")
    return dataset


def adaptable_parameters(model: nn.Module):
    """The normalisation affines, and nothing else."""
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    chosen = []
    layers = 0
    for module in model.modules():
        if isinstance(module, NORM_TYPES):
            own = list(module.parameters(recurse=False))
            if not own:
                continue
            layers += 1
            for parameter in own:
                parameter.requires_grad_(True)
                chosen.append(parameter)
    return chosen, layers


def binary_entropy(logits: torch.Tensor) -> torch.Tensor:
    probability = torch.sigmoid(logits.float())
    eps = 1e-6
    return -(probability * torch.log(probability + eps)
             + (1.0 - probability) * torch.log(1.0 - probability + eps)).mean()


def save_adapted(payload: dict, base_model: nn.Module, out_path: Path, step: int,
                 meta: dict) -> None:
    adapted = {
        "model": {k: v.detach().cpu().clone() for k, v in base_model.state_dict().items()},
        "config": payload["config"],
        "step": int(step),
        "wandb_run_id": None,
        "tent": meta,
    }
    torch.save(adapted, out_path)


def main(argv=None) -> int:
    args = parse_args(argv)
    sys.path.insert(0, str(args.code_root))
    from koine_machines.inference import infer  # noqa: E402
    import zarr  # noqa: E402

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    payload = infer.load_checkpoint_payload(args.checkpoint)
    bundle = infer.build_repo_training_model_bundle(payload, args.checkpoint)
    model = bundle.model.to(device)
    # InstanceNorm has no running statistics, so eval() and train() behave the
    # same for it, and eval() keeps any dropout out of the objective.
    model.eval()

    parameters, layers = adaptable_parameters(model)
    count = sum(p.numel() for p in parameters)
    total = sum(p.numel() for p in model.parameters())
    log(f"adapting {count} parameters in {layers} normalisation layers "
        f"({100.0 * count / max(1, total):.3f}% of {total})")

    log(f"building the target patch pool from {len(args.volumes)} volumes")
    datasets = [build_dataset(infer, zarr, volume, bundle, args) for volume in args.volumes]
    pool = torch.utils.data.ConcatDataset(datasets)
    log(f"target pool: {len(pool)} patches")

    generator = torch.Generator()
    generator.manual_seed(args.seed)
    loader_kwargs = dict(batch_size=args.batch_size, shuffle=True, drop_last=True,
                         num_workers=args.workers, generator=generator)
    if args.workers > 0:
        loader_kwargs.update(persistent_workers=True, prefetch_factor=2)
    loader = torch.utils.data.DataLoader(pool, **loader_kwargs)

    optimizer = torch.optim.Adam(parameters, lr=args.lr)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    save_at = sorted(set(int(s) for s in args.save_at))
    trajectory = []
    step = 0
    started = time.time()

    log(f"adapting for {args.steps} steps, saving at {save_at}")
    while step < args.steps:
        for image, _meta in loader:
            if step >= args.steps:
                break
            image = image.to(device, non_blocking=True)
            logits = model(image)
            loss = binary_entropy(logits)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if args.grad_clip:
                torch.nn.utils.clip_grad_norm_(parameters, args.grad_clip)
            optimizer.step()
            step += 1

            with torch.no_grad():
                probability = torch.sigmoid(logits.float())
                record = {
                    "step": step,
                    "entropy": float(loss.detach()),
                    "mean_p": float(probability.mean()),
                    "frac_above_half": float((probability > 0.5).float().mean()),
                }
            trajectory.append(record)
            if step % args.log_every == 0 or step == 1:
                log(f"  step {step:4d}  entropy {record['entropy']:.4f}  "
                    f"mean p {record['mean_p']:.4f}  p>0.5 {record['frac_above_half']:.4f}")
            if step in save_at:
                out_path = args.out_dir / f"tent_{step:06d}.pth"
                save_adapted(payload, model.model, out_path, step, {
                    "base_checkpoint": str(args.checkpoint).replace("\\", "/"),
                    "volumes": [str(v).replace("\\", "/") for v in args.volumes],
                    "lr": args.lr, "batch_size": args.batch_size, "seed": args.seed,
                    "min_occupancy": args.min_occupancy,
                    "adapted_parameters": count, "normalisation_layers": layers,
                    "entropy": record["entropy"], "mean_p": record["mean_p"],
                })
                log(f"  saved {out_path.name}")

    summary = {
        "checkpoint": str(args.checkpoint).replace("\\", "/"),
        "volumes": [str(v).replace("\\", "/") for v in args.volumes],
        "patches": len(pool),
        "steps": args.steps,
        "save_at": save_at,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "min_occupancy": args.min_occupancy,
        "adapted_parameters": count,
        "normalisation_layers": layers,
        "minutes": (time.time() - started) / 60.0,
        "trajectory": trajectory,
    }
    (args.out_dir / "tent_trajectory.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log(f"done in {summary['minutes']:.1f} min -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
