# Is the recipe's blur too *rare* rather than too weak? A pre-registered test

**Written and committed before the arm was built or run.** Fourth in the series after
[docs/18](18_uda_design.md), [docs/20](20_annotation_targeting.md) and
[docs/22](22_blur_augmentation.md).

## This is the weaker hypothesis, run under its own name

[docs/22](22_blur_augmentation.md) asked whether the recipe blurs at the *wrong strength*, and
its calibration answered no: the sigma this gap calls for is 0.776, and the recipe already
samples `blur_sigma` from 0.5 to 3.0. Its exit clause stopped the arm and said what remained —
exposure — was "a weaker hypothesis than the one being tested", and that running it under the
stronger one's name would be the wrong thing to do.

So it gets its own document. **This is the weaker hypothesis, and it is labelled as such
before it runs.** If it fires, the claim it supports is narrow: not "blur fixes the gap", but
"the recipe already had the right tool and applied it too rarely".

## The one number that motivates it

| | share of training patches |
|---|---|
| blurred at all by the recipe (`OneOf` with the noise transform, `apply_probability=0.2`) | 10% |
| of the recipe's sigma range that falls inside the calibrated band 0.39–1.16 | 26.6% |
| **seeing a calibrated-strength blur today** | **2.7%** |
| this arm | **50%** |

A factor of nineteen in exposure is a condition nobody has tested. That is the whole argument
for spending the GPU time, and it is not a strong one.

## The arm

One training arm, differing from the published leave-0139-out configuration by one added
transform:

```
RandomTransform(GaussianBlurTransform(blur_sigma=(0.39, 1.16)), apply_probability=0.5)
```

- **base**: the existing `ink9um_loso_no0139_s{42,43}` runs, already scored. No new run.
- **new**: the same configuration, the same two seeds, plus that transform, gated behind a new
  config key so the default behaviour is untouched.

The sigma range is **fixed at docs/22's calibration** and is not tuned here; the probability is
fixed at **0.5** and is not tuned either. Half the patches keep their sharpness, so the model
is not simply retrained on blurred data.

## Scoring

Identical to the published matrix:

- **step 20,000**, where the published leave-0139-out curve peaks (0.6542, against 0.6274 at
  10,000 and 0.6236 at 75,000);
- the four paired PHerc0139 segments — w035, w039, w040, w041 — in **both representations**,
  both seeds;
- the same threshold sweep and best-F1 selection.

`num_iterations` stays at the recipe's 78,125 so the learning-rate schedule matches the
baseline exactly, and each run is stopped once `ckpt_020000` is written: with the same seed,
schedule and data order, that checkpoint is what the full run would have produced at that
step, and everything past it is beyond the peak and not scored.

## Decision rule

Let **native gain** = (new native mean) − (base native mean) over the four segments, averaged
over both seeds, and **aligned cost** = (new aligned mean) − (base aligned mean). Baselines:
native 0.6545, aligned 0.7079, gap 0.0534.

- **native gain >= 0.03 and positive in both seeds** → the recipe had the right tool and used
  it too rarely. Report the fraction of the gap recovered and the aligned cost beside it.
- **native gain < 0.03** → no effect. Combined with arm A, docs/21 and docs/22 the conclusion
  is that this gap does not move without labels, and docs/15's instruction stands: render the
  target in the aligned family.
- **aligned cost <= −0.03** → report as a trade, not a win, whatever native does. The corpus is
  24/29 aligned.

0.03 F1 is the noise floor used throughout docs/12, 15, 18, 20, 21 and 22.

## Predictions, committed

- native gain: **0.00 to 0.03**;
- probability the rule fires: **25%** — lower than docs/22's 35%, because the strength question
  was answered and what is left is exposure, and because three attempts on this gap have
  already returned nothing;
- aligned cost: **0.00 to −0.03**. Half the patches blurred is a real change to the training
  distribution and sharpness is presumably where the ink signal lives.

Two failure modes worth naming in advance so they are not read as success:

- if native gains and aligned loses by a similar amount, that is the model trading one
  representation for the other, not learning to be indifferent — the aligned-cost clause
  catches it;
- if both move by less than 0.03, that is noise, and the seed spread on this corpus
  (0.011–0.032 in docs/15) is large enough to produce it.

## What gets published

The config, the augmentation patch, the per-segment and per-representation cells as CSV, and
the summary with the verdict — under `configs/`, `submission/` and
`runs/ink9um_scorecard/`.

---

## Deviation recorded during the run (2026-08-31)

`dataloader_workers` was lowered from the baseline's **12 to 6**, for **both** arm seeds.

At 12 the run dies with `WinError 1455` — the Windows commit limit — twice on this box: once
at start-up while the previous seed's process was still tearing down, and once at about
10,200 steps inside a DataLoader worker's shared-memory allocation for collation. It is the
same failure this repository has recorded before on a 12-worker run of this recipe.

It is an I/O parameter and does not change what the model is trained on, but it is not
nothing: worker RNG is seeded per worker, so the augmentation draws differ between a 6-worker
and a 12-worker run. That is why **both** seeds were restarted with 6 rather than only the
one that failed — the two arm seeds stay comparable to each other, and the difference against
the published baseline applies uniformly to the arm rather than to half of it.

Stated here rather than in the result, because it was decided before the arm's numbers
existed.

---

## Result: no effect

16 cells, both seeds, step 20,000. Raw numbers: `runs/ink9um_scorecard/blurexp_matrix.csv`
and `blurexp_summary.json`.

| | arm | baseline @20k | delta |
|---|---|---|---|
| native | 0.6219 | 0.6340 | **−0.0122** |
| aligned | 0.6693 | 0.6857 | −0.0165 |
| **gap** | 0.0474 | 0.0517 | −0.0043 |

**By the pre-registered rule: no effect.** The native gain is **−0.0122** — the wrong sign,
below the 0.03 floor, and not positive in both seeds (**+0.0090** on seed 42, **−0.0333** on
seed 43). The aligned cost, −0.0165, is also inside the floor, so the trade clause does not
fire either. The gap narrowed by 0.0043, and only because the aligned score fell further than
the native one, which is not a way of closing it.

The failure mode named in advance is the one that happened: *"if both move by less than 0.03,
that is noise, and the seed spread on this corpus (0.011–0.032) is large enough to produce
it."* The two seeds disagree in sign on native by 0.042, which is larger than either effect.

### A correction to this document's own baseline

The table at the top of this file quotes the baseline as native 0.6545 and aligned 0.7079.
Those are **best-over-steps** numbers, carried over from docs/15's `representation_pairs`,
while this arm is scored at step 20,000 only. The like-for-like baseline at step 20,000 is
**native 0.6340, aligned 0.6857**, and that is what the table above uses.

The verdict does not depend on which is used — against the best-over-steps baseline the arm
is worse still (native −0.0326, aligned −0.0386) — but quoting a best-of-seven-steps number
as the bar for a single-step arm would have been an unfair comparison in our own favour if
the result had gone the other way, and it is worth fixing rather than leaving.

### Predictions, scored

| committed | outcome |
|---|---|
| native gain 0.00 to 0.03 | **−0.0122** — outside the range, on the low side |
| probability the rule fires: 25% | it did not fire |
| aligned cost 0.00 to −0.03 | **−0.0165** — inside the range |

### Where this leaves the gap

Four pre-registered attempts on the same aligned-over-native difference:

| | intervention | outcome |
|---|---|---|
| [docs/18](18_uda_design.md) arm A | filter the native input to match aligned spectra | ran; +0.005 F1, no effect |
| [docs/21](21_snr_augmentation.md) | train with noise calibrated to the difference | stopped: the difference has the opposite sign |
| [docs/22](22_blur_augmentation.md) | train with blur calibrated to the difference | stopped: that strength is already in the recipe |
| this document | apply that blur to half the patches instead of 2.7% | ran; **−0.012 F1, no effect** |

Two ran and returned nothing; two were stopped by their own calibrations before spending GPU
time. The difference is real, reproducible and mechanically explained, and nothing we can do
without labels moves it. [docs/15](15_loso_cross_scroll.md)'s instruction stands: render the
target in the aligned family. What moves this class of number is human annotation —
[docs/18](18_uda_design.md) measures one annotated segment at roughly seven times the best
label-free method on the transfer problem next door.

### Run notes

The arm cost more wall clock than it should have. Three runs died with `WinError 1455`, the
Windows commit limit, raised by a DataLoader worker while another process on this machine
held the memory — once at start-up, once at 10,200 steps, once at about 6,600. Halving the
workers from 12 to 6 did not prevent it; waiting for free memory before each attempt did. The
driver now waits for 25 GB free before starting a run rather than retrying into a full
machine.
