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
| [`depth_profile.py`](depth_profile.py) | Ask a trained model *where along z* it takes its ink evidence |
| [`depth_contrast.py`](depth_contrast.py) | Ask the raw CT the same question, with no model in the loop |
| [`make_3d_labels.py`](make_3d_labels.py) | Turn the one-plane ink annotation into a measured 3D label |

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

# `depth_profile` — where along z does the model read the ink?

Ink labels on these segments are drawn in 2D and stored on a single z plane of
65 — depth is manufactured downstream, by projecting that plane along the
surface normal with a constant thickness
([villa #192](https://github.com/ScrollPrize/villa/issues/192)).
A model trained on them can score well while keying on surface texture instead
of ink, and nothing in the pipeline says which it is doing. This asks the model,
by perturbing the input volume it is given:

| variant | what it does | reads as |
|---|---|---|
| `occlude` | blanks a band of z slices | how far the ink response falls = **necessity** |
| `window` | blanks everything *except* a band | how much response survives = **sufficiency** |

Both are measured on ink-labeled pixels **and** on the labeled background inside
the same supervision mask. That control is the point: blanking slices moves the
model's output on its own, so only the ink-minus-background separation is
evidence about ink.

```bash
python tools/depth_profile.py SEGMENT_DIR RUN_DIR/ckpt_020000.pth
python tools/depth_profile.py SEGMENT_DIR CKPT --mask validation_mask --limit-blocks 8
```

Outputs `depth_profile.{json,csv}`, `depth_curve.png`, and two per-region depth
maps — `depth_map_occlusion.png` (the band each ink pixel needs most; measured
against that pixel's own unperturbed logit) and `depth_map_window.png` (the band
that alone scores it highest).

Blanking fills with `0.0` **after** the per-patch robust normalization, which is
that patch's median — so a blanked slice leaks nothing about what it replaced.
Reading, normalization and z-window selection are imported from
`koine_machines.inference.infer`, so the volume profiled is the volume the model
sees at inference time.

`--mask {supervision_mask,validation_mask}` · `--occlude-width 4` ·
`--window-width 8 --window-stride 4` · `--batch-size N` (variants per forward) ·
`--min-ink-pixels N` (blocks with no ink are skipped; the background control
then rides on the same blocks as the ink) · `--limit-blocks N` ·
`--no-depth-map` · `--depth-map-downsample N`

### `depth_contrast.py`

The profile above is a statement about a checkpoint trained against a depthless
label — circular by construction. This one is not: it averages the raw
(robust-normalized) CT intensity per z layer over ink pixels and over background
pixels, and reports the difference. No checkpoint, no torch, no GPU.

```bash
python tools/depth_contrast.py SEGMENT_DIR
```

`--mask {supervision_mask,validation_mask}` · `--block 256` · `--limit-blocks N` ·
`--min-ink-pixels N` · `--raw` (skip normalization, average uint8 instead)

Emits `depth_contrast.{json,csv,png}`; the plot's second panel draws one gray
line per annotated region over the segment-wide average, which is where the
interesting disagreement shows up.

**Two things not to over-read.** A window's *absolute* logit is not comparable
to the baseline — blanking 56 of 64 slices is far off the training distribution,
and the background response rises with it. And with `z_projection_mode: max` the
curve carries a sawtooth from the network's z-pooling grid, so read the trend
and the ink-vs-background gap, not individual points. Full write-up:
[`docs/10_depth_localization.md`](../docs/10_depth_localization.md).

### `make_3d_labels.py`

Uses the occlusion measurement to give the annotated area a band — a center and
a half-width along z — and writes it out as a real 3D label on the surface
volume's own grid. Depth is estimated per 64 px cell (centroid of the cell's
occlusion profile), then median-filtered across cells and bilinearly sampled
back to full resolution, so the band is continuous across block boundaries.

```bash
python tools/make_3d_labels.py SEGMENT_DIR RUN_DIR/ckpt_020000.pth
python tools/make_3d_labels.py SEGMENT_DIR CKPT --limit-blocks 12 --dry-run
```

| output | what it is |
|---|---|
| `<seg>_inklabels3d.zarr` | the 3D label: OME-Zarr pyramid, same grid, chunks and compressor as `_inklabels.zarr` |
| `<seg>_inkdepth.zarr` | `center` and `half_width` per pixel (2D float32, NaN outside the annotation) — the compact form for a pipeline that projects along normals and wants a measured thickness instead of a constant |
| `<seg>_inklabels3d.json` | parameters, per-region medians, coverage, thickness histogram |
| `<seg>_inklabels3d_qc.png` | a y–z cross section per region: the CT with the band drawn on it |

A pixel the annotator did not call ink never becomes ink — the tool only narrows
the label in depth. Cells whose profile is too flat to localize fall back to
their region's median band rather than inventing one; the run prints the peak and
prominence distributions so `--min-response` / `--min-prominence` can be set from
data instead of guessed, and a per-region center **spread** so you can see how
much the depth surface actually moves inside one letter.

`--cell 64` · `--regularize 3` (median filter, in cells) · `--min-cell-ink 64` ·
`--estimator centroid|peak` · `--occlude-width 4` · `--half-width-fraction 0.5` ·
`--min-half-width 2 --max-half-width 16` · `--min-response 0.2 --min-prominence 1.5` ·
`--batch-size N` · `--limit-blocks N` · `--dry-run` · `--force`

Two estimators that did **not** survive QC on this segment, kept in the docs so
nobody repeats them: per-pixel depth (±12 voxels between neighbouring patches of
one stroke) and per-cell argmax (±17 voxels inside a region, two regions 28
apart). `--estimator peak` still exposes the second if you want to see it.

⚠️ Nothing upstream reads a 3D label asset yet: `flat` collapses z with a maximum
and trains on a 2D target, and `full_3d` builds its own target by projecting the
annotated plane with a constant half-thickness. Consuming this needs a training
change — which is the point of measuring first. Full write-up, including what the
first two estimators got wrong:
[`docs/11_measured_3d_labels.md`](../docs/11_measured_3d_labels.md).

---

MIT-licensed. Part of the [Vesuvius Challenge walkthrough](../docs/08_windows_reproduction.md).
