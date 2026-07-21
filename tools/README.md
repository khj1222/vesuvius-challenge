# `ink_viz` — read your Vesuvius ink predictions

The ink‑detection inference step emits one large, tiled, uint8 TIFF
(`32249 × 51380`, ~700 MB) of raw ink probability. It's too big for a normal
viewer, and most of its range sits near zero — so a naive open looks **blank**
even when the letters are there.

`ink_viz.py` turns that TIFF into images you can actually read.

## Run it

It needs `numpy`, `tifffile`, `Pillow` (+ `zarr`/`numcodecs` for `overlay`/`surface`).
All are in the ink‑detection `uv` environment, so the simplest way is:

```bash
uv run --directory external/villa/ink-detection python tools/ink_viz.py <cmd> ...
```

(Or `pip install numpy tifffile pillow zarr numcodecs` and run with any Python ≥3.9.)

## Commands

| Command | What it does |
|---------|--------------|
| `stats PRED.tif` | min/max/mean, non‑zero %, strong‑ink %, percentiles — is there signal? |
| `preview PRED.tif` | auto‑contrast, downscaled grayscale preview of the ink map |
| `surface SEG.zarr` | grayscale preview of the raw CT surface (the "before") |
| `overlay PRED.tif SEG.zarr` | ink rendered as a colored glow over the raw papyrus (the "after") |

### Examples

```bash
# Quick quality check
ink_viz stats predictions/w00_20231016151002.tif

# Grayscale reading preview (dark background, bright ink)
ink_viz preview predictions/w00_20231016151002.tif -o preview.png

# The money shot: ink over papyrus
ink_viz overlay predictions/w00_20231016151002.tif \
    data/.../w00_20231016151002.zarr \
    -o overlay.png --color inferno --threshold 90
```

## Useful options

- **`preview`** — `--downsample N` (default 16), `--clip LO HI` percentile stretch
  (default `1 99.5`), `--invert` for dark‑ink‑on‑light.
- **`surface` / `overlay`** — `--level L` picks the zarr pyramid level
  (0 = full res; **4 ≈ 16×**, a good on‑screen size); `--z-reduce {mean,max,mid}`
  collapses the ~65 z‑slices.
- **`overlay`** — `--color {inferno,hot,cyan,lime,magenta}`, `--threshold 0..255`
  (hide everything below), `--gamma`, `--opacity`, `--bg-gain` (papyrus brightness).

## Why a full read (not `aszarr`)

Reading the TIFF with `tifffile.imread(path, aszarr=True)` raises
`ValueError: zarr 2.x < 3 is not supported`, because the ink‑detection env pins
zarr 2.x. `ink_viz` uses a plain `tifffile.imread`, which decodes the whole
(~1.6 GB in RAM) array and sidesteps the problem.

MIT‑licensed. Part of the [Vesuvius Challenge walkthrough](../docs/08_windows_reproduction.md).
