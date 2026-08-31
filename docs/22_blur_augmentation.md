# Can a calibrated blur close the aligned-over-native gap? A pre-registered test

**Written and committed before the calibration was computed and before any training ran.**
Third in the series after [docs/18](18_uda_design.md) and [docs/20](20_annotation_targeting.md);
the design, the decision rule and the predictions are fixed first.

## Why this arm exists, and why it is not docs/21

[docs/21](21_snr_augmentation.md) proposed training with extra **noise** so a model would
tolerate the native rendering. Its calibration killed it before any GPU time: after the
trainer's own normalisation the native input carries *less* high-frequency energy than the
aligned one — 24 of 24 cells, ratio 0.37 to 0.77, never above 1. Adding noise would move an
aligned patch away from native, not towards it.

That measurement points at the opposite operation. If the native rendering is the **smoother**
of the two, then the augmentation that would make a model indifferent between them is a
**blur**, applied to the aligned inputs it trains on.

This is a new hypothesis derived from a measurement, not a rescue of the old one, so it gets
its own pre-registration with its own numbers committed in advance.

## The gap, unchanged

The four PHerc0139 segments that exist in both representations, scored by the published
leave-0139-out model ([docs/15](15_loso_cross_scroll.md), `no0139_matrix.csv`):

| segment | aligned | native | gap |
|---|---|---|---|
| w035 | 0.7399 | 0.6789 | 0.0610 |
| w039 | 0.6544 | 0.5848 | 0.0696 |
| w040 | 0.7033 | 0.6519 | 0.0514 |
| w041 | 0.7340 | 0.7025 | 0.0315 |
| **mean** | **0.7079** | **0.6545** | **0.0534** |

The leave-0139-out training corpus contains **no native representations at all** — the five
native rows in the contract are exactly the 0139 segments being held out — so the model has
never seen native-like statistics. A calibrated blur is the only way to show it some without
giving it the held-out scroll.

## What raises the bar

The recipe already blurs. `create_training_transforms` applies
`GaussianBlurTransform(blur_sigma=(0.5, 3.0))` inside a `OneOfTransform` with the noise
transform, at `apply_probability=0.2` — so roughly one patch in ten is blurred, at a sigma
drawn from a wide range that was not chosen with this gap in mind. The hypothesis is
therefore **"blurred more often, at a sigma calibrated to the measured difference"**, not
"blur is untried". If that fails, the honest conclusion is that the aligned advantage is not
a smoothness difference the model can be trained out of.

## The arm

One training arm, differing from the published leave-0139-out configuration in one thing: a
dedicated blur applied to the input with a calibrated sigma and a fixed probability.

- **base**: the existing `ink9um_loso_no0139_s{42,43}` runs, already scored. No new run.
- **new**: the same configuration and the same two seeds, plus
  `RandomTransform(GaussianBlurTransform(blur_sigma=(sigma_lo, sigma_hi)), apply_probability=0.5)`,
  with the sigma range set by the calibration below.

`apply_probability` is fixed at **0.5** in advance, and not tuned: half the patches keep their
native sharpness so the model is not simply retrained on blurred data, which would trade the
aligned score away. Everything else is held — recipe, corpus, seeds, schedule, iterations.

## Calibration, fixed as a procedure before it is computed

Using the same measurement as docs/21, on the same four paired segments, after the same
robust-MAD normalisation:

1. for each aligned sample, find the Gaussian sigma at which its high-frequency residual
   standard deviation drops to the median value measured on the native samples of that
   segment;
2. take the median of those sigmas across segments as the centre of the range;
3. set `sigma_lo`, `sigma_hi` to bracket it at +/- 50%, so the model sees a spread rather than
   one constant;
4. record every number here before training starts.

**Exit condition.** If the calibrated centre lands inside the range the recipe already uses
(0.5 to 3.0) *and* below its midpoint, the arm is not worth running as a sigma change alone,
and this document will say so — the only remaining variable would be the probability, which
is a weaker hypothesis than the one being tested.

## Scoring

Identical to the published matrix so the numbers sit beside it:

- **step 20,000**, where the published leave-0139-out curve peaks (0.6542, against 0.6274 at
  10,000 and 0.6236 at 75,000);
- the four paired segments, **both representations**, both seeds;
- the same threshold sweep and best-F1 selection.

Training keeps `num_iterations` at the recipe's 78,125 so the learning-rate schedule is
identical to the baseline's, and the run is stopped once `ckpt_020000` exists: with the same
seed, schedule and data order that checkpoint is what the full run would have produced at
that step, and the remaining 58,125 iterations are past the peak and not scored.

## Decision rule

Let **native gain** = (new native mean) − (base native mean) over the four segments, averaged
over both seeds, and **aligned cost** = (new aligned mean) − (base aligned mean).

- **native gain >= 0.03 and positive in both seeds** → the gap is partly a smoothness
  difference the model can be trained across. Report the fraction of the 0.0534 gap recovered,
  and report the aligned cost beside it whatever it is.
- **native gain < 0.03** → no effect, reported as arm A and docs/21 were. The conclusion is
  then that neither end of this difference — the input, via filtering, nor the model, via
  augmentation — can be moved without labels, and docs/15's instruction stands: render the
  target in the aligned family.
- **aligned cost <= −0.03** → report as a trade, not a win, whatever native does. The corpus
  is 24/29 aligned and a recipe that reads aligned input worse is not an improvement.

0.03 F1 is the noise floor used throughout docs/12, 15, 18, 20 and 21.

## Predictions, committed

- native gain: **0.00 to 0.04**;
- probability the rule fires: **about 35%** — higher than docs/21's 30% because the direction
  is now measured rather than assumed, lower than even odds because the recipe already blurs
  and because every label-free intervention on this gap so far has returned between nothing
  and a tenth of it;
- aligned cost: **0.00 to −0.03**, and this is the number I expect to be least comfortable
  with: half the training patches will be blurred, and sharpness is presumably where the ink
  signal lives.

## What gets published

The calibration, the per-segment and per-representation cells as CSV, the summary with the
verdict, the config, and the augmentation patch — under `runs/ink9um_scorecard/`, `configs/`
and `submission/`.

---

## Calibration result: the exit condition fired

Computed after this document was committed. Raw numbers:
`runs/ink9um_scorecard/blur_calibration.json`.

The Gaussian sigma at which a normalised aligned patch's high-frequency residual falls to the
native median, per segment:

| segment | native sigma_hf | aligned sigma_hf | calibrated sigma |
|---|---|---|---|
| w035 | 0.1158 | 0.1945 | 0.696 |
| w039 | 0.1249 | 0.2747 | 0.856 |
| w040 | 0.1394 | 0.2266 | 0.649 |
| w041 | 0.1191 | 0.2663 | 0.916 |
| **median** | | | **0.776** |

Bracketed at +/- 50% that is a range of **0.39 to 1.16**. The recipe already samples
`blur_sigma` from **0.5 to 3.0**. The calibrated centre is inside that range and below its
midpoint of 1.75, which is exactly the exit condition written above, so **the arm does not run
as designed.**

### What the exit does and does not settle

It settles the sigma. The blur strength this gap calls for is not exotic — it is at the weak
end of what the recipe already draws from, so "the recipe blurs at the wrong strength" is
false.

It does not settle exposure, and the arithmetic is worth recording because it is the only
live variable left:

| | share of training patches |
|---|---|
| blurred at all by the recipe (`OneOf` with noise at p=0.2) | 10% |
| of the recipe's sigma range that lies inside the calibrated band | 26.6% |
| **seeing a calibrated-strength blur today** | **2.7%** |
| the arm would have made it | 50% |

So a probability-only arm is not vacuous — it would move calibrated-strength exposure by a
factor of nineteen. But it is a weaker hypothesis than the one this document set out to test,
and the exit clause was written precisely so that the weaker hypothesis does not get run under
the stronger one's name. If it is worth spending, it is worth pre-registering separately.

### The pattern this makes

Three pre-registered attempts on the same 0.0534 gap have now stopped:

| | intervention | outcome |
|---|---|---|
| [docs/18](18_uda_design.md) arm A | filter the native input to match aligned spectra | ran; +0.005 F1, no effect |
| [docs/21](21_snr_augmentation.md) | train with noise calibrated to the difference | stopped: the difference has the opposite sign |
| this document | train with blur calibrated to the difference | stopped: the calibrated strength is already in the recipe |

The gap is real, it is reproducible, its mechanism is measured — and it has now resisted one
test-time intervention and two training-time ones, two of which were stopped by their own
calibrations before consuming GPU time. What still moves this number is human annotation:
[docs/18](18_uda_design.md) puts one annotated segment at roughly seven times the best
label-free method on the transfer problem next door.
