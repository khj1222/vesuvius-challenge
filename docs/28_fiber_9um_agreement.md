# 28 — How much of a 2.4 µm fiber reading survives at 9 µm? (pre-registration)

**Status: pre-registered, not yet run.** This file is committed before any fiber model has been run on
the data below. The results section is appended after the run; nothing above it changes.

## The gap

On 2026-10-01 in #unrolling-vc3d, a question was asked about moving the fiber algorithms to 9 µm
scans. The team answer was that it needs training data and retraining, and that close fibers get
harder to tell apart as resolution drops ("even at 2.4um fibers get squished together").

A 9 µm fiber model already exists. [`Qualzz20/afv_fiber_9um`](https://huggingface.co/Qualzz20/afv_fiber_9um)
(2026-09-30) fine-tunes [`scrollprize/fiber_hz_vt`](https://huggingface.co/scrollprize/fiber_hz_vt) on native
8.64 µm and 9.362 µm scans of ten scrolls. Its labels are automatic pseudo-labels, and its card says it was
"only evaluated on native ~9 µm scans", with no number. `fiber_hz_vt` itself was trained on fibers traced by
hand on the older 7.91 µm scans. Every other public fiber model and every public fiber prediction in the open
data is at 2.4 µm.

So nobody has measured what a 9 µm fiber prediction gets right. We have no human fiber truth on any
9 µm scan. What we do have is a scroll scanned at both resolutions, with the same papyrus surface mapped
into both scans.

**Question.** On a scroll none of the models trained on, how well does a 9 µm fiber prediction agree with a
2.4 µm fiber prediction of the same papyrus surface? Does the 9 µm fine-tune agree better than the model
it started from?

This measures **agreement with a higher-resolution reading**, not accuracy. The reference is itself a
model output (below), and the team's own remark is that fibers merge even at 2.4 µm.

## Data

- **Scroll**: PHerc. 0139. It is not in the training scans of any model used here. `afv_fiber_9um` trained
  on 0125, 0191, 0211, 0257, 0358, 0175A, 0268, 0306B, 0800 and 1447 (0813 validation only).
  `fiber_hz_vt` trained on 7.91 µm Scroll 1 / Scroll 5 traces. The reference trained on PHerc. Paris 4.
- **Scans**: native `20250728140407-9.362um-1.2m-113keV-masked.zarr` (level 0), and
  `20260102150214-2.399um-0.2m-78keV-masked.zarr` (level 0). Both are open data, isotropic.
- **Segments**: w035, w039, w040, w041, w044 (`PHerc0139/segments/<id>/mesh/`). Each has a tifxyz mesh
  on the 9.362 µm scan (`-on-20250728140407-9.362um`) and one on the 2.399 µm scan
  (`-on-20260102150214-2.399um`). Both meshes keep one vertex every 20 voxels of their own scan, so the grids
  differ in size (w035: 291×262 and 1132×1020). Native grid index (i, j) maps to
  (i·(H₂−1)/(H₁−1), j·(W₂−1)/(W₁−1)) on the 2.399 µm grid.

**Correspondence, checked before writing this (no fiber model involved).** On three segments we rendered a
3 mm surface window from each scan at those mapped points (the 2.399 µm scan read at level 2, sampled at
~23 µm). Normalised cross-correlation of the two high-passed images:

| segment | at mapped points | shifted one native vertex (~190 µm), 4 directions | 12 vertices away | nominal ratio 3.9025 |
|---|---|---|---|---|
| w035 | **0.84** | 0.02–0.11 | −0.04 | 0.70 |
| w040 | **0.67** | −0.05–0.16 | 0.03 | 0.33 |
| w044 | **0.61** | 0.03–0.07 | −0.08 | 0.48 |

On a ±2-index grid in 0.5 steps (one step ≈ 24 µm on the papyrus), the peak is at zero shift on all three.
Mapping by grid shape beats the nominal voxel ratio everywhere, so the grid-shape mapping is used. The script
is `tools/fiber9_check.py uv-check`. All five segments are re-checked in gate G1 below.

## Arms

| arm | model | input |
|---|---|---|
| **A** | `scrollprize/fiber_hz_vt` (nnUNet `3d_fullres`, `checkpoint_final.pth`) | native 9.362 µm |
| **B** | `Qualzz20/afv_fiber_9um` (same layout) | native 9.362 µm |
| **R** reference | `scrollprize/fiber_ink_4class_selfdistill`, EMA weights, step 29000 | 2.399 µm |

A and B: nnUNet's own predictor with test-time mirroring on (both cards' default), tile step 0.5, and the
argmax label. Classes are 1 vertical, 2 horizontal, 3 intersection; for presence, 1–3 all count as fiber.

R: villa `scripts/fiber_5class` `NetworkFromConfig` built from the checkpoint's embedded config. Input uses
the trainer's per-crop 1–99 percentile min-max normalisation, on 256³ windows, stride 128, averaged
softmax, then argmax. Its classes are 1 vertical, 2 horizontal/angular, 3 ink. Ink counts as not-fiber.

If a model cannot be run exactly as stated, the deviation is recorded in the results before any score is
looked at.

## Sampling

- **Tiles**: 20 per segment, each 96 × 96 native voxels on the surface (≈0.9 mm square), sampled at one point
  per native voxel along the upsampled mesh grid. Tile centres are drawn with `numpy.random.default_rng(20261003)`
  from native grid positions whose whole tile is valid in both meshes. Tiles may not overlap. 100 tiles in all.
- **Depth**: for each surface point, both scans are sampled along their own mesh normal, over the same
  physical window: **±47 µm primary** (±5 native voxels, ±20 voxels at 2.399 µm), and ±19 µm and
  ±94 µm secondary. A point carries class c if any voxel in its window has label c. A papyrus sheet has
  its two fibre layers at different depths, so a point can be both vertical and horizontal.
- **Crops**: each model sees a crop of its scan around the tile's surface points, with at least 32 voxels
  (A, B) or 64 voxels (R) of context beyond the window on every side.

## Measure

Each tile gives a 96 × 96 binary fiber map from each arm and from R.

- **Primary: presence F1 with a 1-pixel tolerance** (1 native voxel ≈ 9.4 µm). Precision is the fraction of an
  arm's fiber pixels within 1 pixel (8-neighbourhood) of an R fiber pixel. Recall is the converse. F1 is
  computed per tile.
- **Secondary**: tolerance 0 and 2 pixels; the three depth windows; per-class F1 for vertical and for
  horizontal (only if G3 passes).
- **Null**: each arm's map scored against R's map of a *different* tile of the same segment, using a fixed
  derangement drawn with the same seed. This is what the F1 would be with no spatial correspondence, at the
  same fiber densities.

Tiles of one segment are correlated, so the uncertainty is a bootstrap over tiles stratified by segment
(10,000 resamples, seed 20261003, 95% percentile interval). Every result is also given per segment.

## Gates (run first; a failed gate stops or narrows the run, and is reported)

- **G1 correspondence**, per segment: on its central 3 mm window, NCC at the mapped points must be ≥ 0.5, and the
  fine-shift peak must lie within ±1 grid index of zero. A failing segment is dropped from every arm alike.
- **G2 usable reference**: median over tiles of R's fiber fraction in [0.05, 0.95], and R's vertical and
  horizontal fractions each ≥ 0.02. If this fails, nothing is scored and we report "no usable 2.4 µm
  reference on this scroll".
- **G3 class convention**: per-class F1 is reported only if, for arm A, the direct mapping (vertical↔vertical)
  scores higher than the swapped one. `fiber_hz_vt` labels came from hand tracing and R's labels from a
  principal-axis rule (vertical = within 35° of the scan z axis). They might not mean the same thing.

## Hypotheses and decisions

| | claim | decision rule |
|---|---|---|
| **H1** | fiber signal survives at 9 µm | for each arm, mean (F1 − null F1) has a 95% interval above 0 |
| **H2** | the 9 µm fine-tune agrees better on an unseen scroll | mean paired (F1_B − F1_A) interval above 0 **and** same sign in ≥ 4 of 5 segments → "helps"; interval below 0 under the same sign rule → "hurts"; otherwise "no measurable difference" |
| **H3** | crowding costs recall (the team's remark) | Spearman ρ over tiles between R's fiber fraction and arm B's recall, interval below 0 |

## Prediction

- H1 passes for both arms.
- H2: B helps, by at least 0.03 F1.
- H3: ρ < 0.

If H2 comes out "no measurable difference", the fine-tune's benefit is not visible against a 2.4 µm reading
on this scroll. That would be a result for Qual's card, not a verdict on the model.

## What we already know (disclosed)

- The correspondence numbers above. No fiber model has been run on PHerc. 0139, on any scan.
- We have looked at the model cards, the public 2.4 µm fiber direction fields' metadata (not their values),
  and the 2026-10-01/02 Discord discussion.

## How it can go wrong

- **The reference is a Paris 4 model applied to another scroll.** If it is poor on 0139, every agreement
  number is a floor, and H2 can favour whichever arm shares its mistakes. A and B come from a different
  pipeline (hand traces → nnUNet) than R (self-distillation from pseudo-labels).
- **Residual misregistration** between the meshes lowers every F1 alike. That is why the tolerance and the
  null exist, and why H2 is paired.
- **Coverage**: one scroll and five segments of it. A pass describes PHerc. 0139 at 9.362 µm, not 9 µm
  scans in general. In particular, 8.64 µm scans (half of B's training) are not tested.
- **Not tested**: fiber tracing (the neural tracer and VC3D tools), the effect on spiral fitting, and Qual's
  post-processing into fiber volumes. This compares voxel predictions only.
