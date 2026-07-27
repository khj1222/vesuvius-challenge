#!/usr/bin/env python3
"""make_3d_labels.py -- turn the one-plane ink annotation into a measured 3D label.

The published annotation has no depth. `<segment>_inklabels.zarr` is a
`(65, H, W)` array in which exactly one z plane -- the middle -- is populated;
the other 64 are empty. Anything that needs a 3D target manufactures one, and
today that means `full_3d` projecting the plane along the surface normal with a
constant half-thickness of 1.0 voxel, centered on the fitted surface by
construction. [villa #192](https://github.com/ScrollPrize/villa/issues/192) asks
for real 3D labels instead.

This tool estimates, across the annotated area, *where along z* the ink evidence
sits and *how thick* it is, and writes the resulting band as a 3D label on the
same grid as the surface volume.

How the depth is estimated
--------------------------
By occlusion, on the trained model: blank a band of z slices and see how much
the ink logit falls. `tools/depth_profile.py` measures that in aggregate; here
it is measured **per cell of a coarse grid** (64 px by default), the band center
is the centroid of the positive part of each cell's profile, and the resulting
depth surface is median-filtered across cells before any label is written.

Both of those choices are corrections, not refinements. Measured on this
segment:

* estimating **per pixel** (9 px smoothing) put neighbouring patches of one
  letter stroke ±12 voxels apart -- geometry a papyrus sheet cannot have;
* estimating per cell but taking the **argmax** band still left a ±17 voxel
  spread inside a single region, and put two regions 28 voxels apart. An argmax
  over sixteen small differences is decided by whichever band the noise favours.

The centroid over the same cells cut the within-region spread roughly in half
and brought the regions into agreement with each other and with the aggregate
measurement. The width still comes from the profile's half-maximum: a
variance-based width sat at the clamp, because occlusion sensitivity has long
tails and the second moment describes those rather than the band.

Two findings from `docs/10_depth_localization.md` shaped the rest:

* **Raw intensity cannot be thresholded into a label.** A single voxel separates
  ink from background at AUC <= 0.55 anywhere along z, so any depth estimate has
  to come from a learned response -- which is also why an experiment built on
  these labels needs a control arm before it can claim the labels caused a gain.
* **A single global band is the wrong shape for the answer.** Per-region depth
  varied (medians 25-39 of 64), so depth is estimated locally, with a region's
  own median as the fallback where the annotation is too sparse to measure.

The label is always a *subset* of the annotated column: a pixel the annotator
did not call ink never becomes ink. This tool only narrows the label in depth,
which keeps a comparison against the current behaviour honest.

Outputs (in SEGMENT_DIR, next to the assets they mirror)
    <segment>_inklabels3d.zarr   the 3D label, OME-Zarr pyramid, same grid/chunks
                                 as _inklabels.zarr
    <segment>_inkdepth.zarr      band center and half-width per pixel (2D float32,
                                 NaN outside the annotation) -- the compact form,
                                 for a projection-based pipeline that wants a
                                 measured thickness instead of a constant
    <segment>_inklabels3d.json   parameters, per-region statistics, coverage
    <segment>_inklabels3d_qc.png y-z cross sections through each region: the CT
                                 with the label band drawn on it

Usage
-----
    uv run --project external/villa/ink-detection python tools/make_3d_labels.py \
        data/ink-dataset/phercparis4/w00_20231016151002 \
        external/villa/ink-detection/runs/ink_holdout_20k/ckpt_020000.pth

    ... --limit-blocks 12 --dry-run     # measure a few blocks, write nothing
    ... --cell 32 --regularize 5        # finer grid, stronger continuity

Dependencies: numpy, torch, zarr, scipy, Pillow -- all in the ink-detection uv
environment.

License: MIT.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


PEAK_QUANTUM = 0.01        # logit units per bin of the reported peak-response histogram
PROMINENCE_QUANTUM = 0.05  # std units per bin of the reported prominence histogram


# --------------------------------------------------------------------------- #
# Segment IO  (kept local: the tools in this folder are self-contained)
# --------------------------------------------------------------------------- #
def open_pyramid(segment_dir: Path, kind: str):
    import zarr

    suffix = f"_{kind}" if kind else ""
    path = segment_dir / f"{segment_dir.name}{suffix}.zarr"
    if not path.exists():
        sys.exit(f"error: missing {path}")
    return zarr.open(str(path), mode="r")


def labeled_plane_index(group) -> int:
    """The one z plane the 2D annotation lives on: the middle of the volume."""
    return int(group["0"].shape[0] // 2)


def coarse_plane(group, *, level: int = 3) -> np.ndarray:
    array = group[str(level)]
    return np.asarray(array[array.shape[0] // 2]) > 0


def region_boxes(group, *, level: int = 3) -> list[dict]:
    """Full-resolution boxes of the connected annotated areas."""
    from scipy import ndimage

    plane = coarse_plane(group, level=level)
    if not plane.any():
        sys.exit(f"error: mask is empty at level {level}")

    full = group["0"]
    scale_y = full.shape[1] / plane.shape[0]
    scale_x = full.shape[2] / plane.shape[1]

    labels, _ = ndimage.label(plane)
    regions = []
    for index, box in enumerate(ndimage.find_objects(labels), start=1):
        y0 = max(0, int(np.floor(box[0].start * scale_y)) - 1)
        y1 = min(int(full.shape[1]), int(np.ceil(box[0].stop * scale_y)) + 1)
        x0 = max(0, int(np.floor(box[1].start * scale_x)) - 1)
        x1 = min(int(full.shape[2]), int(np.ceil(box[1].stop * scale_x)) + 1)
        regions.append({"region": index, "bbox": (y0, y1, x0, x1)})
    return regions


# --------------------------------------------------------------------------- #
# Depth estimation
# --------------------------------------------------------------------------- #
def estimate_depth(
    sensitivity: np.ndarray,
    band_centers: np.ndarray,
    *,
    band_width: float,
    half_width_fraction: float,
    min_response: float,
    min_prominence: float,
    min_half_width: float,
    max_half_width: float,
    estimator: str = "centroid",
):
    """Band center, half-width and confidence from a stack of occlusion maps.

    ``sensitivity`` is [band, ...]: how much the ink logit falls when that band
    is blanked. Each location's profile is centered on its own mean first,
    because something that reacts to *every* band is reporting its overall
    sensitivity, not a depth.

    The center is the peak refined by a parabolic fit against its neighbours, so
    it is not quantized to the band grid. The half-width comes from how many
    bands stay above ``half_width_fraction`` of the peak, a FWHM in band units.

    Returns center, half-width, a confidence mask, the peak response and its
    prominence -- the last two so a run can report what the thresholds are
    actually cutting instead of leaving them to guesswork.
    """
    profile = sensitivity - sensitivity.mean(axis=0, keepdims=True)
    band_count = profile.shape[0]
    peak_index = np.argmax(profile, axis=0)

    def gather(indices):
        return np.take_along_axis(profile, indices[None], axis=0)[0]

    peak_value = gather(peak_index)

    # Width from the half-maximum of the profile either way. The second moment
    # of the positive part was tried first and came back at the clamp: occlusion
    # sensitivity has long tails, so a variance-based width describes the tails
    # rather than the band.
    above = profile >= (peak_value * float(half_width_fraction))[None]
    half_width = np.clip(
        above.sum(axis=0) * band_width / 2.0,
        float(min_half_width),
        float(max_half_width),
    )

    # Two conditions, because either alone lets junk through: the peak has to be
    # large in logit terms *and* stand out from the location's own profile.
    # Something reacting equally to every band has no depth to report, however
    # strongly it reacts.
    spread = profile.std(axis=0)
    prominence = peak_value / np.maximum(spread, 1e-6)
    confident = (peak_value >= float(min_response)) & (prominence >= float(min_prominence))

    if estimator == "centroid":
        # An argmax over 16 small differences is decided by whichever band the
        # noise favours -- measured, it moved the per-cell center by ±17 voxels
        # inside a single letter. The centroid of the positive part of the
        # profile uses every band and cut that spread roughly in half.
        weights = np.clip(profile, 0.0, None)
        total = np.maximum(weights.sum(axis=0), 1e-6)
        shaped = band_centers.reshape((-1,) + (1,) * (profile.ndim - 1))
        center = (weights * shaped).sum(axis=0) / total
    else:
        # Argmax with a parabolic fit against its neighbours, so the estimate is
        # not quantized to the band grid.
        left = gather(np.clip(peak_index - 1, 0, band_count - 1))
        right = gather(np.clip(peak_index + 1, 0, band_count - 1))
        denominator = left - 2.0 * peak_value + right
        usable = np.abs(denominator) > 1e-9
        shift = np.clip(
            np.where(usable, 0.5 * (left - right) / np.where(usable, denominator, 1.0), 0.0),
            -0.5, 0.5)
        shift = np.where((peak_index == 0) | (peak_index == band_count - 1), 0.0, shift)
        center = band_centers[peak_index] + shift * band_width

    return (center.astype(np.float32), half_width.astype(np.float32), confident,
            peak_value.astype(np.float32), prominence.astype(np.float32))


def sample_grid(grid: np.ndarray, *, y0: int, x0: int, height: int, width: int, cell: int) -> np.ndarray:
    """Bilinearly sample a coarse per-cell map at full resolution.

    Cell (i, j) is centered at pixel ((i + 0.5) * cell - 0.5, ...), so a block
    lands on the same interpolated surface as its neighbours and the depth does
    not step at block boundaries.
    """
    from scipy import ndimage

    rows = (np.arange(y0, y0 + height, dtype=np.float32) + 0.5) / cell - 0.5
    cols = (np.arange(x0, x0 + width, dtype=np.float32) + 0.5) / cell - 0.5
    coordinates = np.stack(np.meshgrid(rows, cols, indexing="ij"))
    return ndimage.map_coordinates(grid, coordinates, order=1, mode="nearest")


# --------------------------------------------------------------------------- #
# Zarr output
# --------------------------------------------------------------------------- #
def multiscale_attrs(name: str, levels: int) -> dict:
    """The OME-Zarr 0.4 metadata the label pyramids in this dataset carry."""
    return {
        "multiscales": [{
            "axes": [{"name": "z", "type": "space"},
                     {"name": "y", "type": "space"},
                     {"name": "x", "type": "space"}],
            "datasets": [
                {"path": str(level),
                 "coordinateTransformations": [
                     {"type": "scale", "scale": [1.0, float(2 ** level), float(2 ** level)]}]}
                for level in range(levels)
            ],
            "name": name,
            "version": "0.4",
        }]
    }


def create_label_pyramid(path: Path, reference_group, name: str):
    """An empty pyramid matching the reference label zarr level for level."""
    import zarr

    root = zarr.open(str(path), mode="w")
    levels = sorted((key for key in reference_group.array_keys()), key=int)
    arrays = {}
    for key in levels:
        reference = reference_group[key]
        array = root.create_dataset(
            key,
            shape=tuple(int(v) for v in reference.shape),
            chunks=tuple(int(v) for v in reference.chunks),
            dtype="uint8",
            compressor=reference.compressor,
            overwrite=True,
        )
        array.attrs["_ARRAY_DIMENSIONS"] = ["z", "y", "x"]
        arrays[int(key)] = array
    root.attrs.update(multiscale_attrs(name, len(levels)))
    return arrays


def downsample_block(block: np.ndarray, factor: int) -> np.ndarray:
    """Max-pool in plane only; z is not downsampled in these pyramids."""
    if factor == 1:
        return block
    depth, height, width = block.shape
    pad_y = (-height) % factor
    pad_x = (-width) % factor
    if pad_y or pad_x:
        block = np.pad(block, ((0, 0), (0, pad_y), (0, pad_x)))
    block = block.reshape(depth, block.shape[1] // factor, factor, block.shape[2] // factor, factor)
    return block.max(axis=(2, 4))


# --------------------------------------------------------------------------- #
# QC rendering
# --------------------------------------------------------------------------- #
def draw_cross_sections(path: Path, sections: list[dict], *, scale: int = 3) -> None:
    """One y-z slice per region: the CT column, with the label band on top.

    A depth label is the one thing a plan-view preview cannot show. Each strip is
    x across, z down, so a band that tracks the sheet reads as a ribbon and a
    band chasing noise reads as confetti.
    """
    from PIL import Image, ImageDraw

    if not sections:
        return
    strips = []
    for section in sections:
        ct = section["ct"]
        band = section["band"]
        lo, hi = np.percentile(ct, (1.0, 99.0))
        scaled = np.clip((ct - lo) / max(1e-6, hi - lo), 0.0, 1.0)
        canvas = np.repeat((scaled * 255).astype(np.uint8)[..., None], 3, axis=2)
        canvas[band] = (0.35 * canvas[band] + np.array([200, 40, 30]) * 0.65).astype(np.uint8)
        strips.append((section["region"], canvas))

    gap = 12
    height = sum(strip.shape[0] * scale + gap for _, strip in strips) + 14
    width = max(strip.shape[1] for _, strip in strips)
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    y = 12
    for region, strip in strips:
        tile = Image.fromarray(strip).resize((strip.shape[1], strip.shape[0] * scale), Image.NEAREST)
        image.paste(tile, (0, y))
        draw.text((2, y - 11), f"region {region}", fill=(60, 60, 60))
        y += strip.shape[0] * scale + gap
    image.save(path)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a measured 3D ink label from the one-plane annotation.",
    )
    parser.add_argument("segment_dir", type=Path, help="Segment folder (volume + label pyramids)")
    parser.add_argument("checkpoint", type=Path, help="Training checkpoint the depth is measured with")
    parser.add_argument("--occlude-width", type=int, default=4, help="Occlusion band thickness. Default: 4")
    parser.add_argument("--cell", type=int, default=64,
                        help="Depth is estimated per cell of this many px. Default: 64")
    parser.add_argument("--regularize", type=int, default=3,
                        help="Median filter over the cell grid, in cells. 0 disables. Default: 3")
    parser.add_argument("--min-cell-ink", type=int, default=64,
                        help="A cell needs this many annotated px to be measured. Default: 64")
    parser.add_argument("--estimator", choices=("centroid", "peak"), default="centroid",
                        help="How the band is read off a profile: centroid uses the whole positive "
                             "profile and its second moment, peak takes the argmax and a FWHM. "
                             "Default: centroid")
    parser.add_argument("--half-width-fraction", type=float, default=0.5,
                        help="Thickness = width of the profile above this fraction of its peak. Default: 0.5")
    parser.add_argument("--min-half-width", type=float, default=2.0, help="Clamp, in z voxels. Default: 2")
    parser.add_argument("--max-half-width", type=float, default=16.0, help="Clamp, in z voxels. Default: 16")
    parser.add_argument("--min-response", type=float, default=0.2,
                        help="Peak sensitivity below this falls back to the region median. Default: 0.2")
    parser.add_argument("--min-prominence", type=float, default=1.5,
                        help="Peak must exceed this many std of the cell's own profile. Default: 1.5")
    parser.add_argument("--batch-size", type=int, default=8, help="Variants per forward pass. Default: 8")
    parser.add_argument("--limit-blocks", type=int, default=None, help="Measure only the first N blocks.")
    parser.add_argument("--dry-run", action="store_true", help="Measure and report, write nothing.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing 3D label outputs.")
    parser.add_argument("--device", default=None, help="Torch device. Default: cuda when available.")
    args = parser.parse_args(argv)

    import torch
    import zarr
    from scipy import ndimage
    from tqdm.auto import tqdm
    from vesuvius.image_proc.intensity.normalization import normalize_robust

    from koine_machines.inference.infer import (
        OmeZarrPatchReader,
        build_repo_training_model_bundle,
        iter_blocks,
        load_checkpoint_payload,
    )

    segment_dir = args.segment_dir.resolve()
    if not segment_dir.is_dir():
        sys.exit(f"error: not a directory: {segment_dir}")
    if not args.checkpoint.exists():
        sys.exit(f"error: no such checkpoint: {args.checkpoint}")

    label_path = segment_dir / f"{segment_dir.name}_inklabels3d.zarr"
    depth_path = segment_dir / f"{segment_dir.name}_inkdepth.zarr"
    if not args.dry_run and label_path.exists() and not args.force:
        sys.exit(f"error: {label_path.name} exists (use --force to overwrite)")

    payload = load_checkpoint_payload(args.checkpoint)
    bundle = build_repo_training_model_bundle(payload, args.checkpoint)
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model = bundle.model.to(device).eval()
    patch_size = int(bundle.roi_size)
    model_depth = int(bundle.in_chans)

    cell = max(1, int(args.cell))
    if patch_size % cell:
        sys.exit(f"error: --cell {cell} must divide the model's patch size ({patch_size})")

    volume_group = open_pyramid(segment_dir, "")
    inklabels = open_pyramid(segment_dir, "inklabels")
    supervision = open_pyramid(segment_dir, "supervision_mask")
    volume_depth, height, width = (int(v) for v in volume_group["0"].shape)
    label_z = labeled_plane_index(inklabels)
    ink_array = inklabels["0"]

    layer_indices = np.arange(0, volume_depth, dtype=np.int64)
    if layer_indices.size > model_depth:
        offset = (layer_indices.size - model_depth) // 2
        layer_indices = layer_indices[offset:offset + model_depth]

    reader = OmeZarrPatchReader(
        input_path=segment_dir / f"{segment_dir.name}.zarr",
        resolution="0",
        depth_axis_first=True,
        height=height,
        width=width,
        layer_indices=layer_indices,
        preprocessing=bundle.preprocessing,
    )

    coarse = coarse_plane(inklabels)
    scale_y = max(1, int(round(height / coarse.shape[0])))
    scale_x = max(1, int(round(width / coarse.shape[1])))
    blocks = iter_blocks((height, width), patch_size, patch_size, coarse, (scale_y, scale_x))
    if args.limit_blocks is not None:
        blocks = blocks[: int(args.limit_blocks)]
    if not blocks:
        sys.exit("error: no annotated blocks")

    regions = region_boxes(supervision)
    band_starts = list(range(0, model_depth, max(1, args.occlude_width)))
    band_centers = np.array(
        [0.5 * (start + min(model_depth, start + args.occlude_width)) for start in band_starts],
        dtype=np.float32,
    )
    blank_indices = [
        torch.arange(start, min(model_depth, start + args.occlude_width), device=device)
        for start in band_starts
    ]

    grid_h = (height + cell - 1) // cell
    grid_w = (width + cell - 1) // cell
    cells_per_block = patch_size // cell

    print(f"segment      : {segment_dir.name}")
    print(f"checkpoint   : {args.checkpoint.name}")
    print(f"annotation   : plane z {label_z} of {volume_depth}")
    print(f"blocks       : {len(blocks)} of {patch_size}x{patch_size}  ({len(regions)} region(s))")
    print(f"bands        : {len(band_starts)} x {args.occlude_width} z voxels")
    print(f"cells        : {cell} px  ->  {grid_h} x {grid_w} grid")
    print(f"device       : {device}")

    # ---- pass 1: measure the occlusion profile of every cell -------------- #
    cell_sum = np.zeros((len(band_starts), grid_h, grid_w), dtype=np.float32)
    cell_weight = np.zeros((grid_h, grid_w), dtype=np.float32)
    ink_pixels = 0

    with torch.inference_mode():
        for block in tqdm(blocks, desc="Measure", unit="block"):
            y0, x0 = int(block.y0), int(block.x0)
            valid_h, valid_w = int(block.valid_h), int(block.valid_w)

            truth = np.zeros((patch_size, patch_size), dtype=bool)
            truth[:valid_h, :valid_w] = np.asarray(
                ink_array[label_z, y0:y0 + valid_h, x0:x0 + valid_w]) > 0
            if not truth.any():
                continue
            ink_pixels += int(truth.sum())

            patch = reader.read(y0, x0, patch_size, patch_size)
            patch = np.ascontiguousarray(np.moveaxis(patch, -1, 0))
            patch = normalize_robust(patch)
            patch_t = torch.from_numpy(np.ascontiguousarray(patch, dtype=np.float32)).to(device)

            logits = torch.empty((len(band_starts) + 1, patch_size, patch_size),
                                 dtype=torch.float32, device=device)
            for start in range(0, len(band_starts) + 1, max(1, args.batch_size)):
                chunk = range(start, min(len(band_starts) + 1, start + max(1, args.batch_size)))
                batch = patch_t.unsqueeze(0).repeat(len(chunk), 1, 1, 1).clone()
                for row, index in enumerate(chunk):
                    if index > 0:
                        batch[row, blank_indices[index - 1]] = 0.0
                with torch.autocast(device_type=device.type, dtype=torch.float16,
                                    enabled=device.type == "cuda"):
                    output = model(batch.unsqueeze(1))
                output = output.float()[:, 0]
                if output.shape[-2:] != (patch_size, patch_size):
                    output = torch.nn.functional.interpolate(
                        output.unsqueeze(1), size=(patch_size, patch_size),
                        mode="bilinear", align_corners=False).squeeze(1)
                logits[start:start + output.shape[0]] = output

            sensitivity = (logits[0].unsqueeze(0) - logits[1:]).cpu().numpy()

            # Ink-weighted cell sums: the depth we want is the depth of the ink's
            # evidence, so unannotated pixels do not get a say.
            weight = truth.astype(np.float32)
            weighted = sensitivity * weight[None]
            block_sum = weighted.reshape(
                len(band_starts), cells_per_block, cell, cells_per_block, cell).sum(axis=(2, 4))
            block_weight = weight.reshape(
                cells_per_block, cell, cells_per_block, cell).sum(axis=(1, 3))

            cy0, cx0 = y0 // cell, x0 // cell
            cy1 = min(grid_h, cy0 + cells_per_block)
            cx1 = min(grid_w, cx0 + cells_per_block)
            cell_sum[:, cy0:cy1, cx0:cx1] += block_sum[:, :cy1 - cy0, :cx1 - cx0]
            cell_weight[cy0:cy1, cx0:cx1] += block_weight[:cy1 - cy0, :cx1 - cx0]

    if not cell_weight.any():
        sys.exit("error: no annotated pixels in the selected blocks")

    # ---- estimate on the grid, then enforce continuity -------------------- #
    mean_sensitivity = cell_sum / np.maximum(cell_weight, 1e-6)[None]
    center, half_width, confident, peak_value, prominence = estimate_depth(
        mean_sensitivity,
        band_centers,
        band_width=float(args.occlude_width),
        half_width_fraction=args.half_width_fraction,
        min_response=args.min_response,
        min_prominence=args.min_prominence,
        min_half_width=args.min_half_width,
        max_half_width=args.max_half_width,
        estimator=args.estimator,
    )
    measurable = cell_weight >= float(args.min_cell_ink)
    confident &= measurable

    region_lookup = {region["region"]: region["bbox"] for region in regions}
    region_of_cell = np.zeros((grid_h, grid_w), dtype=np.int32)
    for region_id, (ry0, ry1, rx0, rx1) in region_lookup.items():
        region_of_cell[ry0 // cell:(ry1 + cell - 1) // cell,
                       rx0 // cell:(rx1 + cell - 1) // cell] = region_id

    def weighted_median(values: np.ndarray, weights: np.ndarray) -> float | None:
        if not len(values) or weights.sum() <= 0:
            return None
        order = np.argsort(values)
        values, weights = values[order], weights[order]
        cumulative = np.cumsum(weights)
        return float(values[int(np.searchsorted(cumulative, cumulative[-1] / 2.0))])

    region_center: dict[int, float | None] = {}
    region_width: dict[int, float | None] = {}
    for region_id in region_lookup:
        selected = confident & (region_of_cell == region_id)
        region_center[region_id] = weighted_median(center[selected], cell_weight[selected])
        region_width[region_id] = weighted_median(half_width[selected], cell_weight[selected])
    global_center = weighted_median(center[confident], cell_weight[confident]) or float(model_depth) / 2.0
    global_width = weighted_median(half_width[confident], cell_weight[confident]) or 4.0

    # Unmeasured or unconvincing cells inherit their region, so the interpolated
    # surface stays defined everywhere the label needs it.
    filled_center = center.copy()
    filled_width = half_width.copy()
    for region_id in region_lookup:
        mask = (region_of_cell == region_id) & ~confident
        filled_center[mask] = region_center[region_id] if region_center[region_id] is not None else global_center
        filled_width[mask] = region_width[region_id] if region_width[region_id] is not None else global_width
    outside = ~confident & (region_of_cell == 0)
    filled_center[outside] = global_center
    filled_width[outside] = global_width

    if args.regularize > 1:
        size = int(args.regularize)
        filled_center = ndimage.median_filter(filled_center, size=size, mode="nearest")
        filled_width = ndimage.median_filter(filled_width, size=size, mode="nearest")

    measured_cells = int(confident.sum())
    measured_ink = float(cell_weight[confident].sum())
    print(f"\nink px       : {ink_pixels:,}  (in cells with a measured depth: "
          f"{measured_ink / max(1.0, cell_weight.sum()) * 100:.1f}%)")
    print(f"cells        : {measured_cells:,} measured of {int(measurable.sum()):,} annotated")

    def quantile_line(values: np.ndarray, weights: np.ndarray, label: str, threshold) -> None:
        if not len(values):
            return
        order = np.argsort(values)
        values, weights = values[order], weights[order]
        cumulative = np.cumsum(weights) / weights.sum()
        parts = "  ".join(f"p{int(q * 100)} {float(values[int(np.searchsorted(cumulative, q))]):.2f}"
                          for q in (0.05, 0.25, 0.5, 0.75, 0.95))
        print(f"{label}: {parts}   (cut at {threshold})")

    quantile_line(peak_value[measurable], cell_weight[measurable], "peak logit  ", args.min_response)
    quantile_line(prominence[measurable], cell_weight[measurable], "prominence  ", args.min_prominence)
    print(f"segment median: center z {global_center:.2f}  half-width {global_width:.2f}")

    print("\nper region (measured cells only):")
    print(f"  {'region':>6}  {'cells':>6}  {'center z':>9}  {'spread':>7}  {'half-width':>11}")
    region_report = []
    for region_id in sorted(region_lookup):
        selected = confident & (region_of_cell == region_id)
        if not selected.any():
            continue
        spread = float(np.std(center[selected]))
        print(f"  {region_id:>6}  {int(selected.sum()):>6}  {region_center[region_id]:>9.2f}  "
              f"{spread:>7.2f}  {region_width[region_id]:>11.2f}")
        region_report.append({
            "region": region_id,
            "bbox": list(region_lookup[region_id]),
            "measured_cells": int(selected.sum()),
            "median_center": region_center[region_id],
            "center_spread": spread,
            "median_half_width": region_width[region_id],
        })

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    # ---- pass 2: write the label ------------------------------------------ #
    label_arrays = create_label_pyramid(label_path, inklabels, f"{segment_dir.name}_inklabels3d")
    depth_root = zarr.open(str(depth_path), mode="w")
    depth_arrays = {}
    for field in ("center", "half_width"):
        array = depth_root.create_dataset(
            field, shape=(height, width), chunks=(128, 128), dtype="float32",
            fill_value=float("nan"), compressor=inklabels["0"].compressor, overwrite=True)
        array.attrs["_ARRAY_DIMENSIONS"] = ["y", "x"]
        depth_arrays[field] = array
    depth_root.attrs.update({
        "description": "ink band along the surface volume's z axis, in voxels",
        "segment": segment_dir.name,
        "checkpoint": str(args.checkpoint),
        "cell": cell,
    })

    z_axis = np.arange(volume_depth, dtype=np.float32)[:, None, None]
    labeled_voxels = 0
    thickness_histogram = np.zeros(256, dtype=np.int64)
    sections: dict[int, dict] = {}

    for block in tqdm(blocks, desc="Write", unit="block"):
        y0, x0 = int(block.y0), int(block.x0)
        valid_h, valid_w = int(block.valid_h), int(block.valid_w)
        ink = np.asarray(ink_array[label_z, y0:y0 + valid_h, x0:x0 + valid_w]) > 0
        if not ink.any():
            continue

        block_center = sample_grid(filled_center, y0=y0, x0=x0, height=valid_h, width=valid_w, cell=cell)
        block_width = sample_grid(filled_width, y0=y0, x0=x0, height=valid_h, width=valid_w, cell=cell)

        band = (np.abs(z_axis - block_center[None]) <= block_width[None]) & ink[None]
        block_label = np.where(band, np.uint8(255), np.uint8(0))
        labeled_voxels += int(band.sum())
        thickness_histogram += np.bincount(np.clip(band.sum(axis=0)[ink], 0, 255), minlength=256)

        for level, array in label_arrays.items():
            factor = 2 ** level
            reduced = downsample_block(block_label, factor)
            ly0, lx0 = y0 // factor, x0 // factor
            ly1 = min(int(array.shape[1]), ly0 + reduced.shape[1])
            lx1 = min(int(array.shape[2]), lx0 + reduced.shape[2])
            if ly1 <= ly0 or lx1 <= lx0:
                continue
            existing = np.asarray(array[:, ly0:ly1, lx0:lx1])
            array[:, ly0:ly1, lx0:lx1] = np.maximum(existing, reduced[:, :ly1 - ly0, :lx1 - lx0])

        depth_arrays["center"][y0:y0 + valid_h, x0:x0 + valid_w] = np.where(
            ink, block_center, np.float32("nan"))
        depth_arrays["half_width"][y0:y0 + valid_h, x0:x0 + valid_w] = np.where(
            ink, block_width, np.float32("nan"))

        region_id = int(region_of_cell[min(grid_h - 1, y0 // cell), min(grid_w - 1, x0 // cell)])
        if region_id and region_id not in sections:
            row = int(np.argmax(ink.sum(axis=1)))
            sections[region_id] = {
                "region": region_id,
                "ct": np.asarray(volume_group["0"][:, y0 + row, x0:x0 + valid_w], dtype=np.float32),
                "band": band[:, row, :],
            }

    thickness_mean = float((np.arange(256) * thickness_histogram).sum() / max(1, thickness_histogram.sum()))
    print(f"\nlabeled voxels: {labeled_voxels:,}  "
          f"(mean thickness {thickness_mean:.2f} z voxels per annotated pixel)")
    print(f"label   -> {label_path}")
    print(f"depth   -> {depth_path}")

    report = {
        "segment": segment_dir.name,
        "checkpoint": str(args.checkpoint),
        "annotation_plane": label_z,
        "volume_depth": volume_depth,
        "blocks": len(blocks),
        "ink_pixels": ink_pixels,
        "measured_cells": measured_cells,
        "annotated_cells": int(measurable.sum()),
        "labeled_voxels": labeled_voxels,
        "mean_thickness": thickness_mean,
        "parameters": {
            "occlude_width": args.occlude_width,
            "cell": cell,
            "regularize": args.regularize,
            "min_cell_ink": args.min_cell_ink,
            "estimator": args.estimator,
            "half_width_fraction": args.half_width_fraction,
            "min_half_width": args.min_half_width,
            "max_half_width": args.max_half_width,
            "min_response": args.min_response,
            "min_prominence": args.min_prominence,
        },
        "segment_median": {"center": global_center, "half_width": global_width},
        "regions": region_report,
        "thickness_histogram": [int(v) for v in thickness_histogram],
    }
    report_path = segment_dir / f"{segment_dir.name}_inklabels3d.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report  -> {report_path}")

    if sections:
        qc_path = segment_dir / f"{segment_dir.name}_inklabels3d_qc.png"
        draw_cross_sections(qc_path, [sections[key] for key in sorted(sections)])
        print(f"qc      -> {qc_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
