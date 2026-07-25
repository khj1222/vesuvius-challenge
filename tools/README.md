# Tools for the Vesuvius ink-detection pipeline

Small, self-contained CLIs that sit next to the official
[`ScrollPrize/villa`](https://github.com/ScrollPrize/villa) `koine_machines`
pipeline. Nothing here forks or patches it — each tool produces or consumes an
artifact the pipeline already understands.

| Tool | What it's for |
|---|---|
| [`ink_viz.py`](ink_viz.py) | Turn a prediction TIFF into images you can actually read |
| [`make_validation_mask.py`](make_validation_mask.py) | Carve a reproducible held-out validation region out of a segment |
| [`eval_validation.py`](eval_validation.py) | Score a prediction inside that region (F1/IoU/balanced acc, DRD, pseudo-F-measure) |
| [`sweep_checkpoints.py`](sweep_checkpoints.py) | Score every checkpoint of a run and plot the curve |
| [`run_cv_folds.py`](run_cv_folds.py) | Run the whole k-fold protocol unattended and report the spread |

## Run them

They need `numpy`, `tifffile`, `Pillow` (+ `zarr`/`numcodecs`, and `scipy`/`opencv`
for the image metrics). All are in the ink-detection `uv` environment, so the
simplest way is to borrow it with `--project` — unlike `--directory`, it leaves
the working directory alone, so relative paths still resolve from the repo root:

```bash
uv run --project external/villa/ink-detection python tools/<tool>.py ...
```

(Or `pip install numpy tifffile pillow zarr numcodecs scipy opencv-contrib-python-headless`
and run with any Python ≥3.9.)

---

# `ink_viz` — read your ink predictions

The inference step emits one large, tiled, uint8 TIFF (`32249 × 51380`, ~700 MB)
of raw ink probability. It's too big for a normal viewer, and most of its range
sits near zero — so a naive open looks **blank** even when the letters are there.

| Command | What it does |
|---------|--------------|
| `stats PRED.tif` | min/max/mean, non-zero %, strong-ink %, percentiles — is there signal? |
| `preview PRED.tif` | auto-contrast, downscaled grayscale preview of the ink map |
| `surface SEG.zarr` | grayscale preview of the raw CT surface (the "before") |
| `overlay PRED.tif SEG.zarr` | ink rendered as a colored glow over the raw papyrus (the "after") |

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

**Useful options** — `preview`: `--downsample N` (default 16), `--clip LO HI`
percentile stretch (default `1 99.5`), `--invert`. `surface`/`overlay`:
`--level L` (0 = full res; **4 ≈ 16×** is a good on-screen size),
`--z-reduce {mean,max,mid}`. `overlay`: `--color {inferno,hot,cyan,lime,magenta}`,
`--threshold 0..255`, `--gamma`, `--opacity`, `--bg-gain`.

**Why a full read (not `aszarr`)** — `tifffile.imread(path, aszarr=True)` raises
`ValueError: zarr 2.x < 3 is not supported` because the ink-detection env pins
zarr 2.x. `ink_viz` uses a plain `tifffile.imread` instead.

---

# The validation harness

The tutorial trains with **no held-out data at all** — the published segments
ship no `_validation_mask`, so `val_every` iterates over an empty set and the
metrics in `koine_machines/evaluation/metrics/` never run. These three tools fix
that without touching the pipeline. Full write-up:
[`docs/09_validation_harness.md`](../docs/09_validation_harness.md).

```bash
# 1. hold out whole annotated regions (deterministic; matches segment ink density)
python tools/make_validation_mask.py SEGMENT_DIR --preview split.png

# 2. convert it with the pipeline's own converter
python -m koine_machines.preprocessing.create_label_zarrs SEGMENT_DIR

# 3. train -- validation now actually runs (use --directory here, not --project,
#    so out_dir lands next to the pipeline; and train into a FRESH out_dir:
#    the patch cache is keyed by asset paths, not contents)
python -m koine_machines.training.train configs/ink_tutorial_val.json

# 4. score a prediction inside the held-out regions
python tools/eval_validation.py PRED.tif SEGMENT_DIR --preview scored.png

# 5. or score every checkpoint at once
python tools/sweep_checkpoints.py RUN_DIR SEGMENT_DIR
```

### `make_validation_mask.py`

Supervision on these segments is **15 disconnected regions** (boxes around
annotated letters), not a continuous ribbon — so this splits by *region*, never
by pixel. A rectangular band would cut letters in half and train on one stroke
while scoring the one next to it. Regions closer to each other than one patch
are merged into an indivisible group first; the held-out subset is then chosen
by exhaustive search for the best match to the segment's ink density. No RNG.
Writes a tiled `_validation_mask.tif` plus a `.json` spec of the split.

`--fraction 0.2` · `--folds K --fold I` (area-balanced k-fold instead) ·
`--min-gap 256` (merge threshold, full-res px) · `--level 3` (planning level) ·
`--dry-run` · `--preview PNG` · `--force`

### `eval_validation.py`

Scores a prediction TIFF inside the held-out regions: a full uint8 threshold
sweep (via cumulative histograms, so the whole curve costs one pass), confusion
metrics at the best-F1 threshold, DRD + pseudo-F-measure through the repo's own
metric classes, and a **per-region breakdown** — with only a few held-out
regions, one average hides which letters actually failed.

`--threshold T` · `--json OUT` · `--preview PNG` (green = hit, red = false
positive, blue = miss) · `--no-image-metrics` (skip the slow part)

### `sweep_checkpoints.py`

Runs each `ckpt_*.pth` through inference restricted to the band — `infer
--mask-path` skips every block outside it, so a checkpoint costs a fraction of a
full-segment pass — then scores it. Emits `summary.csv` and a `curve.png` drawn
with Pillow (no matplotlib needed).

`--every N` · `--batch-size N` · `--compile` (off by default: torch.compile needs
Triton, which has no native Windows build) · `--keep-going` · `--no-image-metrics`

### `run_cv_folds.py`

One held-out split is a handful of letters, and per-region F1 moves by ~0.07 on
its own — so a single number can't settle "did this help?". This driver runs the
protocol unattended: per fold it rebuilds the mask, reconverts the zarr,
retrains into a fresh `out_dir`, sweeps the checkpoints, and at the end reports
the spread across folds and restores the single-split mask.

```bash
python tools/run_cv_folds.py SEGMENT_DIR --folds 3
```

`--folds K` · `--only-fold I` · `--prefix NAME` · `--sweep-every N` ·
`--config PATH` · `--skip-restore`

Budget training-time × K — about 1.7 h per fold for the tutorial config on an
RTX 5090, so 3 folds is an overnight job.

---

MIT-licensed. Part of the [Vesuvius Challenge walkthrough](../docs/08_windows_reproduction.md).
