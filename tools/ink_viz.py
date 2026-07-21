#!/usr/bin/env python3
"""ink_viz.py -- visualize & post-process Vesuvius ink-detection predictions.

The ink-detection inference step (``koine_machines.inference.infer``) emits a
single large, tiled, uint8 GeoTIFF holding raw ink *logits/probabilities* for a
segment's flattened surface. At 32249x51380 that file is impossible to open in a
normal image viewer and, straight out of the model, most of its dynamic range
sits near zero -- so a naive open looks blank even when the letters are there.

``ink_viz`` turns that prediction into images a human can actually read:

    preview   PRED.tif [-o OUT.png] [--downsample N] [--clip LO HI] [--invert]
        Auto-contrast, downscaled grayscale preview of the ink map. This is the
        fastest way to confirm "did the model find anything?".

    overlay   PRED.tif SURFACE.zarr [-o OUT.png] [--level L] [--threshold T] ...
        Ink probability rendered as a colored glow over the raw CT papyrus
        surface read from the source OME-Zarr. A "before/after in one image"
        that shows *what* the model found and *where* on the sheet.

    stats     PRED.tif [--downsample N]
        Distribution stats (min/max/mean, non-zero %, strong-ink %, percentiles).
        Useful for picking a threshold or spotting an all-blank run.

Design notes
------------
* The prediction TIFF is read with a plain full-decode (``tifffile.imread``)
  rather than ``imread(..., aszarr=True)``. The aszarr path pulls in tifffile's
  Zarr store, which requires ``zarr>=3``; the ink-detection environment pins
  ``zarr 2.x`` and would raise ``ValueError: zarr 2.x < 3 is not supported``.
* The source surface volume is an OME-Zarr multiscale pyramid (levels 0..5,
  each 2x smaller in x/y). ``overlay`` reads a downsampled level so it never has
  to touch the ~100 GB level-0 array.

Dependencies: numpy, tifffile, Pillow (preview/stats); plus zarr + numcodecs
for ``overlay``. All are present in the ink-detection ``uv`` environment, so the
simplest way to run this is:

    uv run --directory external/villa/ink-detection python tools/ink_viz.py ...

License: MIT.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np


# --------------------------------------------------------------------------- #
# IO helpers
# --------------------------------------------------------------------------- #
def load_prediction(path: str) -> np.ndarray:
    """Load an ink-prediction TIFF as a 2-D uint8 array.

    Uses a plain full read to sidestep tifffile's aszarr path (needs zarr>=3).
    """
    import tifffile

    arr = tifffile.imread(path)
    if arr.ndim == 3:
        # A stray leading/trailing singleton channel -> squeeze to 2-D.
        arr = np.squeeze(arr)
    if arr.ndim != 2:
        raise ValueError(f"expected a 2-D ink map, got shape {arr.shape}")
    return arr


def read_surface_layer(zarr_path: str, level: int, z_reduce: str) -> np.ndarray:
    """Read one pyramid level of the source OME-Zarr and z-project to 2-D.

    Parameters
    ----------
    level : int
        Multiscale level (0 = full res, each step is 2x smaller in x/y).
    z_reduce : {"mean", "max", "mid"}
        How to collapse the ~65 z-slices into a single surface image.
    """
    import zarr

    grp = zarr.open(zarr_path, mode="r")
    try:
        arr = grp[str(level)]
    except Exception as exc:  # noqa: BLE001 - surface a clear message
        raise SystemExit(
            f"could not open level {level} of {zarr_path}: {exc}\n"
            f"available: {list(getattr(grp, 'array_keys', lambda: [])())}"
        )
    vol = np.asarray(arr[:])  # (z, y, x); a downsampled level fits comfortably
    if vol.ndim == 2:
        return vol
    if z_reduce == "max":
        return vol.max(axis=0)
    if z_reduce == "mid":
        return vol[vol.shape[0] // 2]
    return vol.mean(axis=0).astype(np.float32)


# --------------------------------------------------------------------------- #
# Image ops
# --------------------------------------------------------------------------- #
def downsample(arr: np.ndarray, factor: int) -> np.ndarray:
    """Strided downsample (fast, no interpolation)."""
    if factor <= 1:
        return arr
    return arr[::factor, ::factor]


def autocontrast(arr: np.ndarray, clip=(1.0, 99.5)) -> np.ndarray:
    """Percentile-stretch to full 0..255 uint8."""
    a = arr.astype(np.float32)
    lo, hi = np.percentile(a, clip[0]), np.percentile(a, clip[1])
    if hi <= lo:
        hi = lo + 1.0
    a = np.clip((a - lo) / (hi - lo) * 255.0, 0, 255)
    return a.astype(np.uint8)


# A few small perceptual LUTs (256x3 uint8) built from control points, so we
# don't need matplotlib as a dependency.
_LUT_STOPS = {
    "hot":     [(0, 0, 0), (180, 30, 0), (255, 170, 30), (255, 255, 220)],
    "inferno": [(0, 0, 4), (85, 15, 109), (187, 55, 84), (249, 142, 9), (252, 255, 164)],
    "cyan":    [(0, 0, 0), (0, 130, 170), (60, 230, 240), (225, 255, 255)],
    "lime":    [(0, 0, 0), (30, 120, 0), (140, 230, 30), (235, 255, 200)],
    "magenta": [(0, 0, 0), (150, 0, 120), (240, 60, 200), (255, 220, 245)],
}


def build_lut(name: str) -> np.ndarray:
    stops = _LUT_STOPS.get(name)
    if stops is None:
        raise SystemExit(f"unknown color '{name}'. choices: {', '.join(_LUT_STOPS)}")
    stops = np.asarray(stops, dtype=np.float32)
    xs = np.linspace(0, 255, len(stops))
    grid = np.arange(256, dtype=np.float32)
    lut = np.stack([np.interp(grid, xs, stops[:, c]) for c in range(3)], axis=1)
    return lut.astype(np.uint8)


def apply_lut(intensity_u8: np.ndarray, name: str) -> np.ndarray:
    return build_lut(name)[intensity_u8]


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_preview(args) -> None:
    from PIL import Image

    pred = load_prediction(args.pred)
    ds = downsample(pred, args.downsample)
    img = autocontrast(ds, clip=(args.clip[0], args.clip[1]))
    if args.invert:
        img = 255 - img
    out = args.out or _default_out(args.pred, "_preview.png")
    Image.fromarray(img).save(out)
    print(f"[preview] {pred.shape} -> {img.shape} (down {args.downsample}x)  saved {out}")


def cmd_stats(args) -> None:
    pred = load_prediction(args.pred)
    ds = downsample(pred, args.downsample)
    nz = float((pred > 0).mean()) * 100
    strong = float((pred > 128).mean()) * 100
    print(f"shape={pred.shape} dtype={pred.dtype}")
    print(f"min={int(pred.min())} max={int(pred.max())} mean={float(pred.mean()):.3f}")
    print(f"non-zero={nz:.3f}%  strong-ink(>128)={strong:.3f}%")
    print("percentiles (downsampled):")
    for p in (50, 90, 95, 99, 99.9):
        print(f"  p{p:>4}: {int(np.percentile(ds, p))}")


def cmd_surface(args) -> None:
    from PIL import Image

    surface = read_surface_layer(args.surface, args.level, args.z_reduce)
    img = autocontrast(surface, clip=(args.clip[0], args.clip[1]))
    out = args.out or _default_out(args.surface.rstrip("/\\"), "_surface.png")
    Image.fromarray(img).save(out)
    print(f"[surface] level={args.level} ({2 ** args.level}x)  {img.shape[1]}x{img.shape[0]}"
          f"  z={args.z_reduce}  saved {out}")


def cmd_overlay(args) -> None:
    from PIL import Image

    pred = load_prediction(args.pred)
    # Prediction is at level-0 resolution; a level-L surface is 2**L smaller.
    factor = 2 ** args.level
    pred_ds = downsample(pred, factor)

    surface = read_surface_layer(args.surface, args.level, args.z_reduce)

    # Crop both to the common area (pyramid rounding can differ by 1 px).
    h = min(pred_ds.shape[0], surface.shape[0])
    w = min(pred_ds.shape[1], surface.shape[1])
    pred_ds = pred_ds[:h, :w]
    surface = surface[:h, :w]

    # Background: dimmed grayscale papyrus so the ink pops.
    bg = autocontrast(surface, clip=(1.0, 99.5)).astype(np.float32) * args.bg_gain
    bg_rgb = np.repeat(np.clip(bg, 0, 255)[:, :, None], 3, axis=2)

    # Ink: colored by intensity, alpha ramps in above the threshold.
    p = pred_ds.astype(np.float32) / 255.0
    t = args.threshold / 255.0
    alpha = np.clip((p - t) / max(1e-6, 1.0 - t), 0.0, 1.0) ** args.gamma
    alpha *= args.opacity
    ink_rgb = apply_lut((p * 255).astype(np.uint8), args.color).astype(np.float32)

    out_rgb = bg_rgb * (1 - alpha[:, :, None]) + ink_rgb * alpha[:, :, None]
    out_img = np.clip(out_rgb, 0, 255).astype(np.uint8)

    out = args.out or _default_out(args.pred, "_overlay.png")
    Image.fromarray(out_img).save(out)
    print(
        f"[overlay] level={args.level} ({factor}x)  {out_img.shape[1]}x{out_img.shape[0]}"
        f"  color={args.color} thr={args.threshold}  saved {out}"
    )


# --------------------------------------------------------------------------- #
def _default_out(pred_path: str, suffix: str) -> str:
    import os

    base, _ = os.path.splitext(pred_path)
    return base + suffix


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ink_viz",
        description="Visualize & post-process Vesuvius ink-detection predictions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("preview", help="auto-contrast downscaled grayscale preview")
    pv.add_argument("pred", help="ink-prediction TIFF")
    pv.add_argument("-o", "--out", help="output PNG (default: <pred>_preview.png)")
    pv.add_argument("--downsample", type=int, default=16, help="strided downsample factor")
    pv.add_argument("--clip", type=float, nargs=2, default=(1.0, 99.5),
                    metavar=("LO", "HI"), help="percentile clip for contrast stretch")
    pv.add_argument("--invert", action="store_true", help="dark ink on light background")
    pv.set_defaults(func=cmd_preview)

    st = sub.add_parser("stats", help="print distribution stats")
    st.add_argument("pred", help="ink-prediction TIFF")
    st.add_argument("--downsample", type=int, default=16, help="downsample for percentiles")
    st.set_defaults(func=cmd_stats)

    sf = sub.add_parser("surface", help="grayscale preview of the raw CT surface (the 'before')")
    sf.add_argument("surface", help="source surface OME-Zarr (the <seg>.zarr)")
    sf.add_argument("-o", "--out", help="output PNG (default: <seg>.zarr_surface.png)")
    sf.add_argument("--level", type=int, default=4, help="zarr pyramid level (0=full; 4≈16x)")
    sf.add_argument("--z-reduce", choices=("mean", "max", "mid"), default="mean",
                    help="collapse the z-slices of the surface volume")
    sf.add_argument("--clip", type=float, nargs=2, default=(1.0, 99.5),
                    metavar=("LO", "HI"), help="percentile clip for contrast stretch")
    sf.set_defaults(func=cmd_surface)

    ov = sub.add_parser("overlay", help="ink colored over raw CT papyrus surface")
    ov.add_argument("pred", help="ink-prediction TIFF")
    ov.add_argument("surface", help="source surface OME-Zarr (the <seg>.zarr)")
    ov.add_argument("-o", "--out", help="output PNG (default: <pred>_overlay.png)")
    ov.add_argument("--level", type=int, default=4,
                    help="zarr pyramid level (0=full; 4≈16x, a good screen size)")
    ov.add_argument("--z-reduce", choices=("mean", "max", "mid"), default="mean",
                    help="collapse the z-slices of the surface volume")
    ov.add_argument("--color", default="inferno",
                    help="ink colormap: " + ", ".join(_LUT_STOPS))
    ov.add_argument("--threshold", type=int, default=90,
                    help="ink value (0-255) below which nothing is drawn")
    ov.add_argument("--gamma", type=float, default=1.0, help="alpha ramp shaping")
    ov.add_argument("--opacity", type=float, default=1.0, help="max ink opacity")
    ov.add_argument("--bg-gain", type=float, default=0.7, help="papyrus brightness")
    ov.set_defaults(func=cmd_overlay)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
