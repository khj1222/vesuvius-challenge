# 30 — An ink reader that holds up when the surface is off (pre-registered)

**Status: pre-registration, committed before any fine-tuned checkpoint below exists.** Results will be
appended under a separate heading; nothing above it changes afterwards.

## Why

A 9 µm ink model reads a surface volume rendered around a traced papyrus surface. When the tracing sits a
little off the sheet, the model is fed the wrong depths. The team has named this dependence on segmentation
quality as a problem worth solving (#unrolling-vc3d, 2026-10-10), and the August prize note asked for work
that "quantitatively" improves core pipeline stages, ink models among them.

A feasibility check (commit `12d6d22`, [`tools/check_depth_perturbation.py`](../tools/check_depth_perturbation.py),
[`depth_perturbation.json`](../runs/ink9um_scorecard/depth_perturbation.json); not pre-registered) on two
open-label segments the released `ink_9um` checkpoints never saw:

- shifting the whole surface by ±1–2 slices (≈ ±10–19 µm) moved best F1 by up to 0.08, in one direction for
  the better (the default window is not at this model's best depth on these renders);
- a smooth, spatially varying shift with a mean of under half a slice cost up to 0.04. No global depth window
  can undo that.

The released recipe already moves the whole 17-slice window by up to ±2 slices per training patch
(`flat_z_window_jitter`). Nothing in it shifts depth *within* a patch. This study adds that and asks whether
it buys robustness without costing accuracy on clean renders.

## Question

Fine-tuning a released checkpoint with an in-patch depth wander, against the same fine-tune without it: on
scrolls neither saw, does F1 hold up better on renders whose depth wanders, and stay the same on clean ones?

## Design (fixed now)

- **Arms.** `control`: the released recipe, fine-tuned. `wander`: identical plus `flat_z_local_wander`
  (`enabled`, `max_amplitude` 2.0 slices, `corr_px` [64, 256], `probability` 1.0). Per training patch it draws
  an amplitude uniform in [0, 2] slices and a correlation length uniform in [64, 256] px, builds a smooth
  field (coarse Gaussian grid, bilinear upsampling, peak |1|), adds it to the existing whole-window offset,
  clips the total to the ±2 real layers on either side and resamples the 17-slice window with linear
  interpolation along depth. Labels are unchanged. Code: villa fork branch `feat/flat-depth-targets`
  commit `47957aee4` ([`runs/segrobust/local_wander.patch`](../runs/segrobust/local_wander.patch)), five unit
  tests (zero amplitude reproduces the existing jitter exactly; never reads outside the real layers).
- **Training.** Both arms start from the released checkpoint of the same seed (`hybrid_3d2d-seed42/43`,
  `step-075000`, weights only), 10,000 steps, the recipe's SGD lr 0.01 with 1,000 warm-up steps and cosine
  decay, batch 64, the full 29-representation corpus with the recipe's per-scroll quotas, seeds 42 and 43.
  Four runs. Configs: `configs/ink9um_segrobust_{control,wander}_s{42,43}.json`. Driver:
  [`tools/run_segrobust.py`](../tools/run_segrobust.py). The final step is evaluated; no checkpoint is chosen.
- **Test segments.** The docs/27 replication's five: PHerc0841 w00, ag144, ag174; PHerc0009B ag055;
  PHerc0500P2 s1. None of these scrolls is in the training corpus.
- **Test renders (11 per segment).** `clean`; whole-surface shifts of −2, −1, +1, +2 slices; smooth wander
  with peak 1 and peak 2 slices, three fields each (field seeds 101–103, correlation ≈ 200 px, a different
  generator from the training augmentation: Gaussian-filtered noise rather than a coarse grid). All built
  from the existing 21-slice renders with linear interpolation along depth, clamped at the ends.
- **Models scored.** The two released starting points (`base_s42`, `base_s43`) and the four fine-tunes, on all
  55 renders. Same inference command and flags as docs/27–29.
- **Measure.** Best F1 (oracle threshold) inside the published `supervision` mask, per render; AUC alongside.

## Decision (fixed now)

Per seed and per scroll, take the mean best F1 over a set of renders; the **contrast** is wander arm minus
control arm (same seed). PHerc0841's three segments are averaged first.

| endpoint | renders | passes if |
|---|---|---|
| **P1 robustness** | the six wander renders | contrast ≥ +0.015 averaged over the three scrolls in **both** seeds, positive on ≥ 2 of 3 scrolls in both seeds, and larger than the control arm's own seed-to-seed spread on the same set |
| **P2 no clean cost** | `clean` | contrast ≥ −0.01 averaged over the three scrolls in both seeds |

The study **succeeds** if P1 and P2 both pass.

Secondary, descriptive: the whole-surface shifts; AUC; fine-tunes against their released starting points;
per-segment tables; F1 against mean |shift|.

| outcome | what happens |
|---|---|
| P1 and P2 pass | release the wander checkpoints and the recipe change; offer the augmentation to villa main's `vesuvius.ink_detection` |
| P1 fails | report it as tested and not effective at this amplitude; nothing is released |
| P1 passes, P2 fails | report the trade-off; nothing is released as a default |

## What we already know (disclosed)

- The feasibility numbers above, on two of the five test segments, with the released seed-43 step-20k
  checkpoint (not a model scored here).
- The released checkpoints' clean scores on these segments (docs/27 replication, docs/29).
- A 200-step smoke run of the wander arm completed without error; nothing from it was evaluated.

## Prediction

P1 passes narrowly: the wander arm recovers about half of what wander costs the control (contrast
+0.015 to +0.025). P2 passes (clean contrast within ±0.005). On whole-surface shifts the arms do not
differ, since both already train with whole-window jitter.

## How it can go wrong

- The test wander is synthetic. A real tracing error has other shapes (sheet switches, folds, larger
  offsets), and only ±2 slices fit in these renders. A pass says the model tolerates small smooth depth
  errors, not that it fixes bad segmentation.
- The test fields come from the same broad family as the augmentation, which favours the wander arm. The
  generator differs, the clean and whole-shift renders do not, and both arms see the same corpus for the same
  steps.
- Five segments on three scrolls, one starting checkpoint per seed. The seed spread rule in P1 is the only
  noise control; the 0.03 floor of docs/09 is larger than the effect predicted.

**Deviation recorded before any result (2026-10-11):** the first control run died at the start with Windows
error 1455 (shared-memory mapping failed) while the test renders were being built in parallel. All four
configs were changed from `dataloader_workers` 12 to 6 to leave memory headroom (the earlier ink_9um runs
here used 12, without anything else running).
This changes data-loading parallelism only; both arms get the same change, and nothing had been evaluated.
