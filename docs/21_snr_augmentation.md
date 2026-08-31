# Can noise augmentation close the aligned-over-native gap? A pre-registered test

**Written and committed before the calibration was measured and before any training ran.**
As in [docs/18](18_uda_design.md) and [docs/20](20_annotation_targeting.md), the design, the
decision rule and the predictions are fixed first so the result can only be read one way.

## The gap this targets

On the four PHerc0139 segments that exist in **both** representations, a model that never saw
that scroll scores consistently better on the aligned input than on the native one
([docs/15](15_loso_cross_scroll.md), `no0139_matrix.csv`):

| segment | aligned | native | gap |
|---|---|---|---|
| w035 | 0.7399 | 0.6789 | 0.0610 |
| w039 | 0.6544 | 0.5848 | 0.0696 |
| w040 | 0.7033 | 0.6519 | 0.0514 |
| w041 | 0.7340 | 0.7025 | 0.0315 |
| **mean** | **0.7079** | **0.6545** | **0.0534** |

The same physical sheet, two renderings, one of them worth 0.05 F1 more. We refuted the first
explanation ourselves — it is not domain match with the training corpus, which a
pre-registered arm ruled out in August — and the mechanism that survives is sampling density:
the published pyramids are 2×2 means and the preparer averages four z-planes on top, so **one
aligned voxel is the mean of 64 acquired voxels while a native voxel is one**
([docs/15](15_loso_cross_scroll.md) appendix 3).

If that is the whole story, the aligned advantage is an SNR advantage, and a model trained to
tolerate single-acquisition noise should lose less of it on native input.

## Why this is not arm A again

[docs/18](18_uda_design.md)'s arm A attacked the same gap from the other end: filter the
native input at test time so its radial power spectrum matches aligned. It did nothing —
+0.005 F1, median 9.1% of the gap, judged "no effect" by its own pre-registered rule. That
tested whether the *input* can be repaired. This tests whether the *model* can be made
indifferent, which is a different intervention with a different failure mode.

One fact that raises the bar and that we did not know when arm A was designed: **the recipe
already trains with Gaussian noise.** `create_training_transforms` applies
`GaussianNoiseTransform(noise_variance=(0.0124, 0.0277))` with probability 0.2, inside a
`OneOfTransform` with a blur. So the null hypothesis is not "noise augmentation is untried";
it is "the noise the recipe already uses is not enough, and more of it, calibrated to the
measured difference, would help". If that is wrong the honest conclusion is that the gap is
not an SNR effect the model can be trained out of.

## The arm

One training arm, differing from the published leave-0139-out LOSO configuration in a single
value: the Gaussian-noise variance range used during training.

- **base**: the existing `ink9um_loso_no0139_s{42,43}` runs, already scored. No new run.
- **new**: the same configuration and the same two seeds, with the noise variance raised to a
  level calibrated (below) to the measured difference between the two representations.

Everything else is held: recipe, corpus, iterations, schedule, seeds, scoring protocol.

## Calibration, fixed as a procedure before it is run

The augmentation acts on the patch **after** the trainer's robust-MAD normalisation, so the
calibration is measured there too:

1. for each of the four paired segments, take matched samples of both representations;
2. normalise each the way the trainer does (`robust_mad`, percentiles 1/99);
3. estimate a noise proxy as the standard deviation of the high-frequency residual — the
   image minus a 3x3 Gaussian blur of itself — which is dominated by per-voxel noise rather
   than by sheet structure;
4. take `sigma_extra = sqrt(max(0, sigma_native^2 - sigma_aligned^2))`, the noise that has to
   be added to an aligned patch for its high-frequency energy to match a native one;
5. set the arm's noise variance range to bracket that value, and record the measured numbers
   in this document before training starts.

If step 4 returns a value inside the range the recipe already uses, the arm is not worth
running and this document will say so instead of running it anyway.

## Scoring

Identical to the published matrix, so the numbers sit beside it:

- score at **step 20,000**, where the published leave-0139-out curve peaks (0.6542 against
  0.6274 at 10,000 and 0.6236 at 75,000);
- the four paired segments, **both representations**, both seeds;
- the same threshold sweep and best-F1 selection.

## Decision rule

Let **native gain** = (new native mean) − (base native mean) over the four segments, averaged
over the two seeds, and **aligned cost** = (new aligned mean) − (base aligned mean).

- **native gain ≥ 0.03 and positive in both seeds** → the gap is partly an SNR effect that
  training can absorb; report the fraction of the 0.0534 gap recovered, and report the
  aligned cost beside it whatever it is.
- **native gain < 0.03** → report no effect, as arm A was reported. The conclusion is then
  that the aligned advantage is not something the model can be trained to ignore, and the
  practical instruction from [docs/15](15_loso_cross_scroll.md) stands unchanged: render the
  target in the aligned family.
- **aligned cost ≤ −0.03** → report as a trade even if native gains, because a recipe that
  reads aligned input worse is not an improvement to a pipeline whose corpus is 24/29 aligned.

0.03 F1 is the noise floor used throughout docs/12, 15, 18 and 20.

## Predictions, committed

- native gain: **0.00 to 0.03**, i.e. most likely no effect by the rule above;
- probability the rule fires: **about 30%**;
- aligned cost: **0.00 to −0.02** — some loss expected, since the model spends capacity on a
  corruption the aligned inputs do not have.

The reason for a low prior despite a clean mechanism: arm A found the spectral difference is
real and closing it changes nothing, the recipe already includes noise augmentation, and
every intervention we have tried on this gap that did not involve human labels has returned
between nothing and a tenth of it.

## What gets published

The calibration measurement, the arm's per-segment and per-representation cells as CSV, the
summary with the verdict, and the config, under `runs/ink9um_scorecard/` and `configs/`.

---

## Calibration result: the arm does not run

The exit written into this document before the measurement was made has fired. Raw numbers:
`runs/ink9um_scorecard/representation_noise.json`.

Measured on the four paired segments, after the trainer's own robust-MAD normalisation, the
noise proxy is **smaller in the native rendering than in the aligned one, in every segment**:

| segment | aligned sigma_hf | native sigma_hf | native / aligned | sigma_extra |
|---|---|---|---|---|
| w035 | 0.1843 | 0.1054 | 0.57 | **0** |
| w039 | 0.2196 | 0.1206 | 0.55 | **0** |
| w040 | 0.2136 | 0.1098 | 0.51 | **0** |
| w041 | 0.2796 | 0.1270 | 0.45 | **0** |

The extra noise an aligned patch needs to look like a native one is zero, because the native
patch is the smoother of the two. Adding noise to aligned inputs would not move them towards
native; it would move them away from both.

**This is not an artefact of the proxy.** Repeating it across two normalisations
(robust-MAD, unit-variance) and three blur scales (0.5, 1.0, 2.0) gives **24 of 24 cells with
the native input smoother**, ratio 0.37 to 0.77, never above 1.

### What this says about the mechanism

[docs/15](15_loso_cross_scroll.md) appendix 3 established a fact of construction: the
published pyramids are 2x2 means and the preparer averages four z-planes, so one aligned voxel
is the mean of 64 acquired voxels. That remains true, and we were careful there not to claim
an SNR ratio, because noise independence was never measured.

This measurement adds the part that matters for anyone trying to act on it: **the difference
the model actually sees is not that native is noisier, it is that native is smoother.** The
native scan is a genuinely coarser acquisition, and averaging a 2.4 µm volume down to 9.6 µm
keeps more fine structure per unit contrast than acquiring at 9.362 µm does. So "aligned wins
because it has less noise" is the wrong shape of explanation to build an intervention on.

### And the intervention this points at is already in the recipe

If the direction is smoothness rather than noise, the augmentation that would make a model
tolerate native input is a **blur**, not added noise. `create_training_transforms` already
applies `GaussianBlurTransform(blur_sigma=(0.5, 3.0))` — in the same `OneOfTransform` as the
noise, at probability 0.2. So the intervention in the correct direction is already present in
the recipe that produced the 0.0534 gap.

That does not prove a stronger blur would not help; it does mean the cheap version of this
idea is already spent, and a blur arm would be a new experiment with its own pre-registration
rather than a rescue of this one.

### Predictions, scored

| committed | outcome |
|---|---|
| native gain 0.00–0.03, rule fires with probability ~30% | **not tested** — the arm was stopped by its own calibration |
| aligned cost 0.00 to −0.02 | not tested |

The design's most useful clause turned out to be the exit condition. It cost about ten GPU
hours to write and nothing to obey.
