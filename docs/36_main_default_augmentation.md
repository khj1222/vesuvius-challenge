# 36 — Does villa main's stronger default augmentation change ink_9um on unseen scrolls? (pre-registered)

**Status: pre-registration, committed before any fine-tuned checkpoint below exists.** Results will be
appended under a separate heading; nothing above it changes afterwards.

## Why

The released `ink_9um` checkpoints were trained with `augmentation_preset: "default"` in the
`koine_machines` ink pipeline (the recipe in the dataset README). When the ink pipeline moved into villa
`main` (2026-08-27, #1625, which added `vesuvius/src/vesuvius/ink_detection/`), the preset of the same name
came with a different, much stronger transform graph. The ink config main ships,
`ink_detection/configs/aligned21_hybrid_3d2d.json`, uses it. Anyone who retrains or fine-tunes the recipe
from main today gets the strong version.

| | released recipe (`koine_machines`) | villa main (`a23ec7c34`, unchanged since 2026-08-27) |
|---|---|---|
| geometry | mirror; rot90 p 0.3 | rot90 p 0.5; in-plane transpose p 0.2 |
| low-resolution simulation | none | scale 0.25–1, p 0.4 |
| gamma | 0.3–0.8, p 0.1 | 0.7–1.5, p 0.4, plus inverted gamma p 0.2 |
| brightness / contrast | additive ±0.2 and contrast 0.8–1.2 together, p 0.1 | contrast or multiplicative 0.75–1.25, p 0.3; additive σ 0.5, p 0.1 |
| blur / noise | one of the two, p 0.2 | blur σ 0.3–1.5 p 0.3; noise p 0.3 |
| other | sharpening p 0.1; inversion p 0.1; slice illumination p 0.3; blank rectangle p 0.1 | sharpening p 0.2; inversion p 0.2; slice illumination p 0.4; brightness gradient p 0.2; smear p 0.3; blank rectangle (mean fill) p 0.1 |

We found no measurement of whether this matters for reading scrolls the model never saw. We searched villa PRs
and issues for ink augmentation; #1625 carries no comparison. A second reason to look: on PHerc0841, the
released seed-43 checkpoint scores AUC 0.891 / 0.800 / 0.820 (w00 / ag144 / ag174) on the 9.6 µm volumes
downsampled from the 2.4 µm scan (docs/30), but 0.772 / 0.681 / 0.756 on surface volumes rendered directly
from the 9.366 µm scan (docs/32). Low-resolution simulation and stronger blur are the kind of
change that might narrow such a gap.

## Question

Fine-tuning a released checkpoint with villa main's default augmentation, against the same fine-tune with the
released recipe's: on scrolls neither saw, does AUC change? And on native 9.366 µm renders?

## Design (fixed now)

- **Arms.** `control`: the released recipe's preset, i.e. the docs/30 control config, trained again.
  `strong`: identical plus `augmentation_preset: "main_default"`. That is a new preset in the fork that copies
  villa main's `create_default_training_transforms` (`ink_detection/data/augmentations.py` at `a23ec7c34`).
  The one edit drops `benchmark=False` from `GaussianBlurTransform`. The fork's transform library
  (`fc6d9a7f4`) has no such argument, and its only blur path is the one `benchmark=False` selects in main.
  Every other transform class it uses is byte-identical between the two library versions (`git diff`).
  Both use `robust_mad` normalization. Main's preset ignores `augmentation_rotation_axes` and takes its
  rotation plane from the patch shape. For 17×128×128 that is the in-plane (y, x) plane, the same one the
  recipe's `[0]` selects. **Not ported:** main's dataset-level crop translation
  (`maybe_translate_crop_bbox`), which is not part of the preset. This study isolates the transform graph,
  not everything main's trainer does differently. Code: villa fork branch `feat/flat-depth-targets`, one
  commit after `47957aee4`; the patch will be committed as `runs/presetab/main_default.patch`.
- **Training.** As docs/30. Both arms start from the released checkpoint of the same seed
  (`hybrid_3d2d-seed42/43`, `step-075000`, weights only). Then 10,000 steps, SGD lr 0.01 with 1,000
  warm-up steps and cosine decay, batch 64, patch 17×128×128, the full 29-representation corpus with the
  recipe's per-scroll quotas, `dataloader_workers` 6, seeds 42 and 43. Four runs. Configs:
  `configs/ink9um_presetab_{control,strong}_s{42,43}.json`. Driver: `tools/run_presetab.py`. The final
  step is evaluated; no checkpoint is chosen.
- **Rerun reference.** The docs/30 control fine-tunes (same config, trained 2026-10-11) are scored
  alongside. The new control against the old one is the run-to-run spread of an identical recipe.
- **Test set T1 (unseen scrolls).** The docs/30 clean renders: PHerc0841 w00, ag144, ag174; PHerc0009B
  ag055; PHerc0500P2 s1. None of these scrolls is in the training corpus. Same inference command and
  flags as docs/27–30.
- **Test set T2 (native renders).** The docs/32 surface volumes of the same three PHerc0841 segments,
  rendered from the 9.366 µm scan (28 slices, `--flip-normals`), forward direction only. The labels are on
  the native grid, exactly as in docs/32. Inference via villa main `e2254ebe0` as in docs/32.
- **Models scored.** `base_s42`, `base_s43`, docs/30 `control_s42/s43`, and the four new fine-tunes, on
  T1 and T2.
- **Measure.** AUC inside the published `supervision` mask (primary); best F1 with an oracle threshold
  alongside.

## Checks before training (fixed now; a failure stops the study and is recorded here)

1. **Port fidelity.** With the same seeds, the fork's `main_default` and main's own function (run from a
   main checkout) give bit-identical outputs on 200 fixed synthetic patches carrying `image`, `inklabels`
   and `supervision_mask`.
2. **Geometry.** On synthetic patches where every depth slice equals the label, the geometric members
   (rot90, transpose) leave image and label still equal.
3. **Active.** In a 200-step smoke run, the strong arm changes intensities on more samples, and by more,
   than the control does. Nothing from the smoke run is evaluated.
4. **Scoring paths.** T1: re-scoring the existing docs/30 control predictions reproduces the docs/30 cell
   values. T2: `base_s43` forward on 0841 w00 reproduces docs/32's AUC 0.7719 within 0.0005.

## Decision (fixed now)

The **contrast** is strong arm minus new control arm, same seed. On T1, PHerc0841's three segments are
averaged first, and each scroll counts once.

| endpoint | set | passes if |
|---|---|---|
| **P1 unseen scrolls** | T1 | contrast ≥ +0.015 averaged over the three scrolls in **both** seeds, positive on ≥ 2 of 3 scrolls in both seeds, and larger than the rerun spread (largest over seeds of \|new control − docs/30 control\|, averaged over the three scrolls) |
| **P2 native renders** | T2 | contrast ≥ +0.03 averaged over the three segments in both seeds, positive on ≥ 2 of 3 segments in both seeds |
| **H harm** | T1 | contrast ≤ −0.015 averaged over the three scrolls in both seeds |

| outcome | what happens |
|---|---|
| P1 passes | report that main's default helps on unseen scrolls at this budget; release the two `strong` fine-tunes |
| P1 fails, P2 passes | report a gain on native renders only; release nothing as a better default |
| H holds | report that main's default costs accuracy on unseen scrolls at this budget, with the numbers, to the ink pipeline's maintainers |
| none | report a measured null: at a 10k-step fine-tune the two presets read these scrolls the same |

Secondary, descriptive: best F1; per-segment tables; fine-tunes against their released starting points;
the T1–T2 gap per model.

## What we already know (disclosed)

- T1 AUC of `base_s42/s43` and docs/30 `control_s42/s43` (docs/30 cells). Scroll means:
  docs/30 control 0.855 (s42) and 0.854 (s43).
- T2 AUC of `base_s43` (docs/32 and above). `base_s42` and every fine-tune on T2 are unscored.
- Nothing from the strong arm exists.

## Prediction

P1 fails: the contrast is within ±0.010. The released checkpoints already reach these scrolls at
AUC 0.80–0.89, and docs/30 showed that 10k-step fine-tunes move T1 by about 0.01. P2 fails narrowly: the
strong arm narrows the native gap by +0.01 to +0.03. H does not hold.

## How it can go wrong

- This is a fine-tune from checkpoints trained 75k steps with the weak preset, not a recipe trained from
  scratch. A null here does not show that the presets are equivalent from scratch.
- Three scrolls on T1 and one scroll on T2. The rerun spread is the only noise control on T1. T2 has none
  beyond the seed rule.
- Only the transform graph is swapped. Main's trainer differs in other ways (crop translation, code
  structure). The result speaks for the preset, not for training with main.
- The strong arm loads the CPU more. Steps are fixed, so this changes run time, not the comparison.

Cost: four fine-tunes (about 45–90 min each on one RTX 5090) and about an hour of inference; no downloads.
