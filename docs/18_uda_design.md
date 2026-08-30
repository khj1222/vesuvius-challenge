# Unsupervised domain adaptation across scrolls: a pre-registered design (2026-08-29)

[docs/16](16_first_letters_render.md) ends at a wall. The render path to an
unseen scroll works, the released checkpoints run on it, and nothing readable
comes out — as [docs/15](15_loso_cross_scroll.md) predicted from a cross-scroll
margin of +0.06 to +0.17 over the trivial baseline. The playbook's answer was
"annotate one segment and fine-tune", which closes 82% of the gap in seven GPU
minutes. But on a scroll with no ground truth, **the prediction cannot say where
to annotate**, so that step has no entry point.

What is missing is adaptation that uses the target scroll's **images only**.
This document fixes the design, the predictions and the decision rules **before
running anything**, the way [docs/15 appendix 2](15_loso_cross_scroll.md) was
pre-registered — so a negative result stays interpretable instead of becoming a
search for a framing that works.

## 1. The measurement frame

The obstacle to studying adaptation on an unlabelled scroll is that an
unlabelled scroll cannot be scored. So the study does not run there. It runs
where labels exist and are withheld:

- **target domain** = one scroll's images, used without labels;
- **model** = the leave-one-scroll-out arm from docs/15 that never saw that
  scroll;
- **score** = that scroll's full annotation, held out throughout.

Both bounds are already measured, on the same segments, with the same scoring
rules:

| target scroll | trivial floor margin | LOSO direct transfer | one labelled segment, fine-tuned |
|---|---|---|---|
| **Paris4** (8 segments) | +0.060 | **0.487** | **0.822** (7 segments the FT never saw) |
| 1667 (6 segments) | +0.131 | 0.546 | not run |
| 0139 (14 reps) | +0.169 | 0.678 | not run |

**Paris4 is the primary testbed**, because it is the only scroll with both
bounds and because it is the hardest target — if something works there it should
work elsewhere. The headline metric is the one docs/15 part 4b already uses:

> **share of the gap closed** = (adapted − LOSO) / (fine-tuned − LOSO)

with 0% being direct transfer and 100% being what one labelled segment buys.
Anything reported is the mean over the same seven segments as the fine-tune
matrix, at both seeds.

### The rule that keeps it honest

On a genuinely unlabelled scroll you do not know **which pixels are annotated**,
only which are on the sheet. So adaptation may use the render's valid area and
nothing else. **The target's supervision mask must not enter the adaptation** —
not as a loss mask, not as a sampling prior, not for choosing patches. It is
used only for scoring, afterwards. Any variant that breaks this rule gets
reported separately and labelled optimistic.

## 2. What this architecture rules out before we start

Two of the standard cheap moves are unavailable or already done here, which is
worth knowing in advance rather than discovering by running them.

- **AdaBN does not apply.** The model (`vesuvius_unet_3d_stem_2d`, a 3D stem
  feeding a 2D UNet) contains 62 `InstanceNorm2d` and 2 `InstanceNorm3d` layers
  and **zero running-statistics buffers**. There are no batch statistics to
  recompute on the target.
- **Global intensity alignment is largely redundant.** Inputs are normalised
  **per patch** by a robust median/MAD over the 1st to 99th percentile, and then
  InstanceNorm normalises again per sample and channel. A histogram or CDF match
  between scrolls mostly re-does what these two already do.

That leaves 27,712 affine parameters in the normalisation layers — 0.080% of the
model's 34.5M — as the natural cheap adaptation surface, and it leaves
input-space work that changes something **other than intensity**.

## 3. The ladder

Three arms, cheapest first, each with its prediction committed here.

### A. Input-space: match the resolution and noise spectrum, not the intensity

**Motivation.** docs/15 appendix 2 found that the aligned representation beats
the native one by +0.03 to +0.07 F1 on the *same physical segments*, and that
the advantage survives training on both families — so it is representation
quality, not family match. Aligned is a 2.399 um acquisition pooled 4x in z;
native is a single 9.362 um acquisition. The difference that matters is
therefore in the noise and blur spectrum, which per-patch intensity
normalisation does not touch.

**Arm.** Estimate the source corpus's mean radial power spectrum over training
patches, estimate the target's, and apply the matching filter to the target
render before inference. No training at all — re-inference only.

**Prediction.** This is the arm most likely to produce a cheap, immediately
usable result, and also the one whose effect is most likely to be small. I
expect **0 to 20% of the gap**. Above 20% would be a genuinely useful finding
for anyone rendering an unseen scroll, because it costs one filter.

### B. Test-time entropy minimisation on the normalisation affines

**Motivation.** The only adaptation surface the architecture leaves, and the
classical one (TENT). Confident predictions on the target are encouraged without
any label.

**Arm.** Freeze everything but the 27,712 norm affine parameters. Minimise the
mean binary entropy of the sigmoid output over target patches drawn from the
valid render area. Small learning rate, a few hundred steps, checkpoint often —
entropy minimisation degenerates if run too long, which is a known failure mode
and must be reported if it happens rather than tuned away.

**Prediction.** **10 to 40% of the gap.** Entropy minimisation sharpens a
decision boundary that is already roughly in the right place; docs/15 says the
boundary here is systematically displaced, so sharpening it should help less
than usual. If it collapses to a constant prediction, the best threshold pins at
an extreme and the score falls to the trivial floor — that is the signature to
watch for.

### C. Confidence-thresholded pseudo-label self-training

**Motivation.** The obvious method, and the one people will ask about.

**Arm.** Run the LOSO model on the target, keep predictions above and below
symmetric confidence thresholds as positive and negative pseudo-labels, discard
the middle, and fine-tune with the official recipe for 2,500 steps — the point
where supervised fine-tuning saturates.

**Prediction — I expect this to fail, and the reason is already measured.**
docs/15 part 4a found the cross-scroll gap is **bias, not variance**: two
independent seeds averaged together recover only +0.005 to +0.009, and seeds
differ by 0.011 to 0.032 where in-scroll seeds differ by 0.22. Two models that
are wrong in the same way will produce confident pseudo-labels that are wrong in
the same way, and training on them reinforces the error. I predict **−10% to
+15% of the gap**, i.e. indistinguishable from doing nothing, or worse.

If C nonetheless works well, that falsifies the bias reading and is the more
interesting outcome — which is exactly why it is worth running and why the
prediction is committed now.

## 4. Decision rules, fixed in advance

- The noise floor is the one this project has used throughout: **differences
  under ~0.03 F1 are noise**. On the Paris4 scale that is about 9% of the gap,
  so **any arm below 9% is reported as "no effect"**, whatever its sign.
- Every arm runs at **both seeds (42 and 43)** and is scored on **all seven
  segments**. A result that holds on fewer than 5 of 7 segments is reported as
  inconsistent regardless of its mean.
- Arms are compared at a **fixed step**, not best-of-grid, since a real
  deployment has no held-out set to select on. Best-of-grid numbers are reported
  alongside as an upper bound.
- If an arm needs a hyperparameter chosen on target labels, it is disqualified
  from the headline and reported as an oracle variant.

## 5. Cost

| arm | GPU | notes |
|---|---|---|
| A, spectrum matching | ~0 for adaptation, ~30 min re-inference per seed | filter estimation is CPU |
| B, entropy minimisation | ~10 min per seed, plus ~30 min scoring | a few hundred steps on 0.08% of the parameters |
| C, pseudo-label self-training | ~7 min per seed, plus ~30 min scoring | same shape as the docs/15 fine-tune |

Roughly **4 to 5 GPU hours** for the whole ladder at two seeds, which is less
than one LOSO arm cost to train. The expensive part is scoring, not adapting.

## 6. Threats to validity

- **One target scroll for the headline.** Paris4 has both bounds, but docs/15
  showed the transfer margin varies more than twofold by target. Anything that
  works on Paris4 should be checked on 1667 before being called general.
- **The LOSO models are ours, not the released ones.** They were trained on the
  same recipe and their online validation matched the released band (docs/15
  part 1, point 5), but they are not the same weights.
- **The fine-tune ceiling is generous.** Its denominator is the reference
  model's *training-pixel* score, so "share of the gap closed" is measured
  against a bar that no honest model reaches.
- **Adaptation on the target scroll is not adaptation on an unseen scroll.**
  Paris4's images come from the same acquisition family as most of the training
  corpus. A method that only survives that similarity would not transfer to
  PHerc1447, whose scan is 8.640 um from a different session. Whatever survives
  the ladder gets run on the docs/16 render as the final, unscoreable check —
  and judged by eye, stated as such.

## 7. What gets published either way

If an arm closes a meaningful share of the gap, the deliverable is the method,
the tool and the number. If none does, the deliverable is a measured statement
that **cheap unsupervised adaptation does not close the cross-scroll gap on this
corpus**, with three methods, their predictions, and their pre-registration
timestamps — which is the honest answer to "why not just adapt?" and closes the
loop docs/16 opened.

---

# Addendum: how arm A's testbed was chosen (same day, after the design was committed)

The design above was committed at `ecd6a41`, 2026-08-29 11:05. Everything in
this section happened after that and before any F1 was computed, and it is
recorded here because the arm-A testbed described below is **better than the one
the design specified**, and a reader is entitled to know that it was picked with
some measurements already in hand.

## What was measured in between

`tools/spectrum_match.py` was written and committed (`02f8e98`, 11:09), and used
to measure radial power profiles. Two things came out of it.

**The two representations separate cleanly.** Every `aligned` volume measured
sits at a spectral centroid of 0.0278 or above; every `native` one at 0.0262 or
below. Averaged over the LOSO-no0139 arm's six training volumes the source sits
at 0.0318, against 0.0254 for the four native targets, with no overlap between
the groups. That is a property of the representation rather than of any segment
or scroll — which is what makes one corpus-level filter the right shape.

**The PHerc1447 render is spectrally a native-class input.** It measures 0.0248,
with 1.8% of its power in the 0.1-0.25 band and 0.0% above 0.25 — indistinguishable
from native (0.0244, 1.7%, 0.0%) and below every aligned volume. So the unseen
scroll that read nothing in [docs/16](16_first_letters_render.md) is, in input
terms, the class that docs/15 appendix 2 already measured as the worse of the
two. And the guidance appendix 2 issued — *render in the aligned family* —
**cannot be followed on PHerc1447**, because that scroll has only an 8.640 um
acquisition and there is no higher-resolution scan to pool from. The deficit is
in the data, not in the render settings.

That is what makes arm A worth running properly rather than as a formality: if a
filter can make a native-class input behave like an aligned-class one, the
guidance becomes followable on scrolls that have no high-resolution scan.

## What changed, and what did not

**Changed — the testbed.** The design said "estimate the source spectrum,
estimate the target spectrum, apply the matching filter, re-infer". It did not
say where. The obvious reading was to run it on the Paris4 LOSO arm like
everything else. Instead arm A runs on **0139's w035, w039, w040 and w041**, the
only segments in this corpus that exist in *both* representations, because there
the thing being corrected has a measured size: docs/15 part 3 puts the aligned
margin ahead of the native one by +0.057, +0.066, +0.048 and +0.028 F1
respectively. The filter's job is to recover part of a gap that was measured
before this study existed, on segments with ground truth on both sides.

**Not changed — the prediction.** Arm A's committed interval is **0 to 20% of
the gap**, and it stays. Nothing measured in between says anything about F1: the
spectral distance closed by the filter (38% at the patch level) is a statement
about inputs, not about what the model does with them.

**Added — one honesty constraint the design implied but did not spell out.** The
source profile is estimated from the no0139 arm's *training* corpus only — six
aligned volumes across 1667, Paris4 and 0814. **0139's own aligned volumes are
excluded from the filter entirely**, even though they sit on the same disk,
because a real target scroll would not have an aligned twin and using one would
hand the arm the answer it is supposed to reach without labels. The target
profile comes from the native volumes' images alone.

## Why this is a strengthening rather than a degree of freedom

The risk in choosing a testbed after seeing data is that the choice quietly
selects for a result. Three things bound that here:

1. **The comparison target predates the choice.** The +0.028 to +0.066 margins
   were measured on 2026-08-24 and published in docs/15 and on villa #1582.
   Arm A cannot move them.
2. **The prediction interval was fixed first**, and it was fixed before any
   inference on a filtered volume existed.
3. **The scoring rules come from the design** — fixed step, both seeds, all four
   segments, the ~0.03 F1 noise floor, and "consistent on fewer than 5 of 7" (here
   3 of 4) reported as inconsistent whatever the mean.

What this testbed cannot do is stand in for the Paris4 arm. It measures whether
a filter recovers a **representation** gap between two renders of the same
sheet, not whether it recovers a **scroll** gap. Those are different quantities,
and if arm A works here it still has to be run on the Paris4 arm before any
claim about cross-scroll adaptation.

---

# Result — arm A: spectrum matching does not buy F1 (2026-08-29, same day)

Run on the testbed the addendum describes: 0139's w035, w039, w040 and w041, each present
as both an `aligned` and a `native` render, with the LOSO-no0139 checkpoints at steps 10k,
20k and 30k and both seeds. The filter comes from the training corpus's aligned profile and
the targets' native images, with 0139's own aligned volumes excluded. 48 cells;
`runs/ink9um_scorecard/armA_specmatch_matrix.csv` and `armA_specmatch_summary.json`.

| quantity | value |
|---|---|
| mean Δ F1, filtered minus raw | **+0.0052** |
| range | −0.0184 … +0.0398 |
| cells where the filter wins | 17 of 24 |
| share of the aligned-versus-native gap recovered | **median 9.1%** |
| per-segment mean Δ | w035 +0.0002 · w039 **+0.0193** · w040 +0.0022 · w041 −0.0009 |

## Verdict, by the rules fixed in section 4

**No effect.** The mean gain of +0.0052 is a sixth of the ~0.03 noise floor, which section 4
says is reported as no effect whatever its sign. Three of the four segments move by less
than ±0.002; only w039 shifts materially (+0.019), and one segment in four does not meet the
consistency requirement. The direction is right — 17 of 24 cells improve — but the size is
not there.

The pre-registered prediction was **0 to 20% of the gap**, and the median recovery is 9.1%.
The prediction holds.

⚠️ Do not quote the *mean* recovery share. On w041 seed 42 at 10k the aligned-native gap is
only 0.0015, so a −0.010 change divides to −673% and drags the mean to −8.4%. The median,
9.1%, is the usable statistic.

⚠️ **These two share statistics were recomputed on 2026-08-30.** The first version of
`armA_specmatch_summary.json` recorded a median of 8.4% and a mean of −19.2%, and neither
could be reproduced from the matrix under any denominator I could identify; the summary now
stores the definition it uses — per cell, `(filtered − raw) / (aligned − raw)` at the same
segment, seed and step — along with every cell it is computed from. Everything else in this
section (mean Δ, the range, 17 of 24, the per-segment means) reproduces exactly, and the
verdict does not move: 9.1% is inside the same pre-registered interval.

## What it means

The spectral difference is real and measurable — aligned and native separate with no
overlap, and `spectrum_match.py` closes 38% of that distance at the patch level — mean over
the four filtered volumes of the drop in total variation against the source profile, 27.6% to
54.1% by volume, 35.7% if the four are pooled first
(`runs/spectra/filter_effect_native0139.json`). Closing it moves F1 by nothing. **So the aligned representation's advantage is not carried by the
radial power spectrum we measured.** Matching second-order statistics is not enough; whatever
makes the aligned render better lives somewhere else — phase structure, information along z,
or something the 4x z pooling produces that a radial profile does not see.

For PHerc1447 that tightens docs/16 rather than loosening it. Its render really is a
native-class input, and there is no higher-resolution scan to build an aligned-class one
from — **and now we also know a filter will not stand in for one.** The conclusion that
unsupervised adaptation has to come first survives, with one cheap alternative eliminated.

## What is left of the ladder

Arms B (entropy minimisation on the 27,712 normalisation affines, predicted 10–40%) and C
(pseudo-label self-training, predicted to fail) were unrun when this was written, and arm A's
result does not bear on either prediction: it says the input-space route is closed, not that
the parameter-space route is. Both were run on 2026-08-30 and their results are the sections
below.

---

# Arm B operating parameters, fixed before any score exists (2026-08-30)

Section 3B fixed the method and the prediction; it did not fix the knobs. These
are written down here, and committed, **before a single adapted checkpoint has
been scored** — the adaptation runs themselves produce no F1, only an entropy
curve, so nothing below was chosen with a result in view.

Exact ordering, since it is the only thing that makes a pre-registration worth
anything. This section is commit `3bff82f`, **07:43:18**. The adaptation driver
was still building its patch pool then; its first optimisation step ran at
07:50:06, the last checkpoint was written at 07:53, scoring started at 07:54 and
the first F1 landed at 07:56:45. So neither the entropy curve nor any score
existed when the knobs below were fixed. The headline step is the round middle of
section 3B's "a few hundred steps"; the full trajectory is in
`runs/ink9um_tent_s{42,43}/tent_trajectory.json` for anyone who wants to see what
it would have suggested instead.

**Base.** The leave-Paris4-out arm at `ckpt_020000`, both seeds — the same
checkpoint the docs/15 part 4 fine-tune started from. Direct transfer, one
labelled segment, and entropy minimisation are then three treatments of one
model, and the gap denominator is the one already published.

**Adaptation surface.** The affine parameters of every normalisation layer:
**27,712 in 64 layers, 0.080% of 34,546,498** — measured by the tool, and equal
to the count section 2 derived. Every other parameter has `requires_grad`
cleared. The model stays in `eval()`; InstanceNorm has no running statistics, so
this changes nothing for it, and it keeps dropout out of the objective.

**Target pool — images only.** All eight Paris4 aligned volumes, w00 included:
adaptation is unsupervised, so the segment the fine-tune spent its labels on is
just more unlabelled sheet here. Patches are the non-overlapping 128px grid,
kept when at least **50% of the patch footprint is non-empty** in the volume's
own mid-depth plane. That threshold is the render's valid area and is computed
from the image alone — the supervision mask, the labels and the annotated area
are not opened by `tools/tent_adapt.py` at any point.

**Objective.** Mean binary entropy of the sigmoid of the z-max-reduced
prediction — the same surface `infer` writes and `eval_validation` scores, not an
internal one.

**Schedule.** Adam, lr 1e-4, batch 16, gradient clipping 1.0, **1,600 steps**,
checkpoints at **50, 100, 200, 400, 800, 1,600**. Section 3B says a few hundred
steps and warns that the objective degenerates if run to convergence; the grid
runs past that on purpose so the degeneration is measured rather than assumed.

**What gets scored, and how it is labelled.**

- **Headline: step 200**, chosen here and not from any score, on all seven
  segments the docs/15 fine-tune never saw, both seeds. This is the number the
  section 4 rules apply to.
- **Trajectory probe:** every checkpoint on **w01 and w05**, both seeds — the
  middle and the weakest of the seven under direct transfer. This shows the shape
  and is where a collapse would first be visible.
- If the probe's best step is not 200, that step is scored on the remaining five
  segments and reported **as an oracle upper bound**, explicitly labelled: it is
  chosen on target labels, which a real deployment does not have.
- The entropy trajectory is recorded for every step, so a label-free stopping
  rule can be evaluated after the fact and reported as what it is.

**Collapse signature**, from section 3B: mean predicted probability drifts to 0
or 1, the best threshold pins at an extreme, and F1 falls to the segment's
all-positive floor. If that happens it is the result, not a tuning failure.

Prediction unchanged: **10 to 40% of the gap**.

---

# Arm C: the pre-registered rule turns out to be empty, and what replaces it (2026-08-30)

Section 3C says to keep predictions "above and below symmetric confidence
thresholds as positive and negative pseudo-labels". The obvious reading of
"confident" is 0.9 and 0.1. **On this target that rule selects nothing at all**,
and the measurement that says so uses no label, so it is reported here before any
arm-C checkpoint exists.

Running the base model (leave-Paris4-out, `ckpt_020000`, seed 42) over the valid
render area of all eight Paris4 segments:

| segment | sheet pixels | min p | max p | positives at p>=0.6 | share of supervised | supervised share of sheet |
|---|---|---|---|---|---|---|
| w00 | 85,866,396 | 0.19 | 0.89 | 4,510,179 | 6.4% | 81.8% |
| w01 | 99,074,525 | 0.19 | 0.88 | 5,920,686 | 7.4% | 80.4% |
| w02 | 78,909,235 | 0.19 | 0.86 | 3,506,138 | 5.4% | 82.1% |
| w03 | 98,146,109 | 0.18 | 0.88 | 5,046,466 | 6.3% | 81.9% |
| w05 | 213,085,492 | 0.18 | 0.89 | 12,446,899 | 7.2% | 80.7% |
| w06 | 109,890,114 | 0.18 | 0.89 | 6,211,284 | 7.0% | 80.9% |
| w07 | 305,671,435 | 0.17 | 0.89 | 15,917,346 | 6.1% | 84.8% |
| w09 | 130,950,271 | 0.18 | 0.89 | 10,929,574 | 10.6% | 78.5% |

**The model's entire output range on an unseen scroll is 0.17 to 0.89.** Not one
pixel of 1.3 billion reaches 0.9, and not one falls to 0.1 — on any of the eight
segments. That is worth stating on its own: cross-scroll failure is not the model
being confidently wrong, it is the model never being confident.

## The replacement rule, fixed before any training

Symmetric about the model's **own** decision point rather than about the ends of
the scale:

- **positive** where p >= 0.6, **negative** where p <= 0.4, middle discarded;
- restricted to the render's valid area, taken from one mid-depth plane of the
  image — the same image-only criterion arm B uses;
- built for **all eight** Paris4 segments, including the seven that get scored.
  Self-training is transductive by nature and a deployment would do exactly this;
  giving the arm the favourable condition is deliberate, because the prediction
  is that it fails.

That yields 78-85% of each sheet supervised with positives at 5.4-10.6% of it —
both classes non-empty, and a positive rate in the range a real annotation has.

Everything else is unchanged from section 3C and section 4: the same base
checkpoint at both seeds, the released recipe, **2,500 steps** (where supervised
fine-tuning saturates, docs/15 part 4), the same seven scored segments, the same
inference and scoring flags, the same ~0.03 F1 noise floor and 5-of-7 consistency
requirement.

**Prediction unchanged: -10% to +15% of the gap.** The reason stands as written —
docs/15 part 4a measured the gap as bias rather than variance, and a confident
wrong pseudo-label trains the next model to be wrong in the same place. If it
works anyway, that reading is what breaks, which is the more interesting outcome.

The pseudo-labels are built by `tools/make_pseudo_labels.py` into the corpus's own
label contract, so the released recipe consumes them unmodified. The target's real
annotation is opened only afterwards, to score.

## Deviation, recorded before any arm-C score exists (2026-08-30, 10:15)

The rule above said pseudo-labels for **all eight** Paris4 segments, including the
seven that get scored, on the grounds that self-training is transductive and the
favourable condition should be granted. That run was started and **stopped after
13 minutes**, before a single training step: with 78–85% of every sheet
supervised, the trainer's patch discovery took 13 minutes for the first segment
and projected **1h32m for the remaining seven**, at 10.2 GB resident and climbing,
per seed. Two seeds of that plus scoring does not fit the day, and a run that has
to be killed halfway is worth less than a smaller one that finishes.

**What it was changed to: `phercparis4-w00` only.** The pseudo-label trees for the
other seven are built and stay in the repository, unused by this arm.

This makes arm C the **direct counterpart of the docs/15 part 4 fine-tune**: same
base checkpoint, same single segment, same recipe, same seven scored segments,
same 2,500 steps — the config differs from the supervised arm in exactly three
keys (`datasets`, `description`, `out_dir`). The only variable left is where the
labels on w00 came from: a human annotator, or the model's own confident
predictions. That is a cleaner isolation than the eight-segment version offered,
and it is the comparison the result section reports.

**What was given up, stated plainly.** The eight-segment version would also have
let the model adapt on the very sheets it is then scored on. This one does not, so
a null result here does **not** rule out that transductive self-training — pseudo-
labelling the target segments themselves — would do better. That variant is
untested and is named as untested.

The prediction is unchanged: **−10% to +15% of the gap**. No F1 for any arm-C
checkpoint existed when this was written; the run that was stopped never reached
its first optimisation step.


---

# Result — arm B: entropy minimisation makes it worse, and the objective never says so (2026-08-30)

Run exactly as the addendum above fixed it: the leave-Paris4-out arm at
`ckpt_020000`, both seeds, adapted on all eight Paris4 segments' **images only**,
scored at the pre-registered step 200 on the seven segments the docs/15 part 4
fine-tune never saw. 14 headline cells;
`runs/ink9um_scorecard/armB_tent_matrix.csv` and `armB_tent_summary.json`.

The adaptation touched what it was supposed to touch and nothing else: the
adapted checkpoint differs from its base in 252 of 508 state-dict entries, and
those 252 are aliases of the **128 parameter tensors of its 64 normalisation
layers** (62 `InstanceNorm2d` and 2 `InstanceNorm3d`; the model exposes most norm
modules under two names, so they appear twice) — **27,712 unique parameters,
maximum change 0.025**. Every convolution is byte-identical.

## Headline

| segment | trivial floor | LOSO base (s42 / s43) | TENT s42 | TENT s43 | mean delta | fine-tune bound |
|---|---|---|---|---|---|---|
| w01 | 0.4148 | 0.4607 / 0.4621 | 0.4318 | 0.4198 | **-0.0356** | 0.8573 |
| w02 | 0.3791 | 0.4096 / 0.4174 | 0.3857 | 0.3819 | **-0.0297** | 0.8122 |
| w03 | 0.5124 | 0.5233 / 0.5331 | 0.5124 | 0.5124 | **-0.0158** | 0.8143 |
| w05 | 0.3485 | 0.3861 / 0.3971 | 0.3589 | 0.3488 | **-0.0377** | 0.7620 |
| w06 | 0.4743 | 0.5013 / 0.4985 | 0.4771 | 0.4743 | **-0.0242** | 0.7880 |
| w07 | 0.4778 | 0.5522 / 0.5551 | 0.4843 | 0.4893 | **-0.0668** | 0.7846 |
| w09 | 0.4424 | 0.5875 / 0.5981 | 0.4959 | 0.5334 | **-0.0781** | 0.7947 |

Mean over the 14 cells: **0.4916 to 0.4504, a change of -0.0412**, against a
fine-tune bound of 0.8118. **Not one cell of fourteen improved**, and all seven
segments are worse at both seeds.

## Verdict, by the rules fixed in section 4

**It harms, consistently.** -0.0412 is past the ~0.03 noise floor, so this is not
the "no effect" arm A returned; it is a measured cost, and the consistency
requirement is met in the wrong direction — 7 of 7 segments, 14 of 14 cells.

**The pre-registered prediction was 10 to 40% of the gap, and the result is
-12.9%.** The interval does not contain the outcome and the sign is wrong. I
expected sharpening a displaced boundary to help less than usual; it does not
help at all, it hurts. That is the prediction failing, and it is the reason the
number was committed in advance.

## What actually happens: the collapse the design said to watch for

Section 3B named the signature — "if it collapses to a constant prediction, the
best threshold pins at an extreme and the score falls to the trivial floor". That
is what the numbers are.

- **The fraction of the batch above 0.5 reaches zero by step 100–200** and stays
  there, while the mean predicted probability falls from 0.39 to 0.20.
- **Four of the fourteen cells land on their segment's all-positive floor to
  within 0.002** (w03 at both seeds, w05 and w06 at seed 43), and the median cell
  clears its floor by only **+0.006**. After 200 steps of adaptation the model is
  worth almost exactly as much as answering "ink" everywhere.
- The best threshold moves from **72–112 at the base to 30–66 after adaptation**,
  which is the signature of a prediction squashed downward, not of a sharper
  boundary.

## The trajectory: neutral at 50 steps, on the floor by 400

Every checkpoint scored on the two probe segments, both seeds — the schedule the
addendum fixed.

| probe | LOSO base | 50 | 100 | 200 | 400 | 800 | 1600 |
|---|---|---|---|---|---|---|---|
| w01 s42 | 0.4607 | 0.4680 @68 | 0.4606 @63 | 0.4318 @59 | 0.4148 @18 | 0.4148 @0 | 0.4148 @0 |
| w01 s43 | 0.4621 | 0.4741 @69 | 0.4558 @66 | 0.4198 @64 | 0.4148 @0 | 0.4148 @5 | 0.4148 @1 |
| w05 s42 | 0.3861 | 0.3889 @68 | 0.3802 @62 | 0.3589 @59 | 0.3485 @18 | 0.3485 @0 | 0.3485 @0 |
| w05 s43 | 0.3971 | 0.3978 @69 | 0.3762 @66 | 0.3488 @63 | 0.3485 @0 | 0.3485 @0 | 0.3485 @0 |

Four probes, one shape. At **50 steps** the arm is neutral — +0.003 to +0.012,
inside the noise floor, and positive in all four. By **100** it is level or below,
by **200** it has cost 0.03 to 0.05, and from **400 onwards every cell sits exactly
on its segment's all-positive floor with the best threshold pinned at 0 to 18**.
The collapse is complete before a quarter of the budget section 3B called "a few
hundred steps" has been spent.

The best-of-grid number, which section 4 says to report as an upper bound: taking
each probe's best checkpoint **on the target's own labels** gives **+0.0057**
mean (+0.0007 to +0.0120) — still inside the noise floor, and unavailable to
anyone who does not have those labels.

## It is not the 8-bit write — the ranking is what degrades

The obvious alternative explanation is quantisation: every score in this project
comes from `round(255 * p)`, and a squashed output loses grey levels, so F1 could
fall while the model's ordering of pixels stayed intact.
`tools/float_rank_check.py` re-runs the model in float over the annotated area and
settles it.

| segment / seed | checkpoint | AUC | best F1 float | best F1 uint8 | p25–p75 |
|---|---|---|---|---|---|
| w01 s42 | LOSO base | 0.6593 | 0.4544 | 0.4545 | 0.287–0.442 |
| w01 s42 | TENT 200 | 0.5905 | 0.4226 | 0.4237 | 0.228–0.243 |
| w01 s42 | TENT 1600 | 0.4787 | 0.4148 | 0.4148 | 0.192–0.216 |
| w01 s43 | LOSO base | 0.6562 | 0.4541 | 0.4546 | 0.276–0.431 |
| w01 s43 | TENT 200 | 0.5960 | 0.4171 | 0.4193 | 0.248–0.263 |
| w01 s43 | TENT 1600 | 0.5494 | 0.4148 | 0.4148 | 0.206–0.223 |
| w05 s42 | LOSO base | 0.6200 | 0.3764 | 0.3765 | 0.282–0.423 |
| w05 s42 | TENT 200 | 0.5677 | 0.3529 | 0.3539 | 0.228–0.243 |
| w05 s42 | TENT 1600 | 0.4881 | 0.3485 | 0.3485 | 0.192–0.216 |

Float and uint8 agree to 0.001 everywhere, so the 8-bit write costs nothing. What
moves is **AUC**, which is rank-only and immune to any rescaling: 0.66 at the
base, 0.59 after 200 steps, **0.48 after 1,600** — below chance on w01 seed 42.
The ordering itself is being destroyed, and at 1,600 steps the float best-F1 sits
on the segment's all-positive floor to four decimals (0.4148, 0.3485).

(Absolute numbers here run slightly below the matrix because this is a single
non-overlapping pass rather than the blended inference `infer` performs. The
comparison between checkpoints is under identical conditions.)

## The objective is anti-correlated with the thing it stands in for

This is the part worth carrying to anyone else who tries test-time adaptation on
this corpus.

| step | 1 | 50 | 100 | 200 | 400 | 800 | 1600 |
|---|---|---|---|---|---|---|---|
| entropy, seed 42 | 0.6244 | 0.5982 | 0.5786 | 0.5436 | 0.5303 | 0.5163 | 0.5001 |
| mean p, seed 42 | 0.388 | 0.297 | 0.275 | 0.234 | 0.223 | 0.213 | 0.201 |
| entropy, seed 43 | 0.6220 | 0.5958 | 0.5776 | 0.5696 | 0.5605 | 0.5486 | 0.5174 |
| AUC, w01 s42 | 0.659 | | | 0.591 | | | 0.479 |

**The objective improves monotonically the whole way down while the model gets
monotonically worse.** So there is no label-free early stop that rescues this: the
entropy curve has no minimum to stop at, and a practitioner watching the only
thing an unlabelled scroll lets them watch would keep going and arrive at chance.
The one step that would have been chosen correctly is step zero.

## Why it fails here, offered as a reading rather than a measurement

Entropy minimisation assumes the decision boundary is roughly right and needs
sharpening. docs/15 part 4a measured the opposite: the cross-scroll gap is
**bias**, a boundary in the wrong place. On this target most pixels sit below 0.5,
so the cheapest way to lower mean entropy is to push everything down, and nothing
in the objective objects. The architecture makes that easier rather than harder —
the only trainable surface is the normalisation affines, which act as gains and
offsets, so the manoeuvre most available to the optimiser is close to a global
squash.

## Limits

One target scroll, one learning rate, one batch size. A smaller learning rate
would move more slowly, but the trajectory degrades monotonically from the first
scored checkpoint, so it postpones rather than avoids. Entropy minimisation with a
diversity or class-balance regulariser is a different arm and is not tested here;
anyone running it has these numbers as the baseline to beat, and the bar is
0.4916, not zero.

---

# Result — arm C: the only rung that helps, and it is worth a tenth of the annotation (2026-08-30)

Run as the deviation note above fixed it: the leave-Paris4-out arm at `ckpt_020000`
fine-tuned on **pseudo-labels for `phercparis4-w00` alone**, derived from its own
predictions on that segment, at both seeds, for 2,500 steps of the released
recipe, scored on the seven segments the supervised fine-tune never saw. 18 cells;
`runs/ink9um_scorecard/armC_pseudo_matrix.csv` and `armC_pseudo_summary.json`.

The config differs from the docs/15 part 4 fine-tune in exactly three keys —
`datasets`, `description`, `out_dir` — so the comparison isolates one thing: where
w00's labels came from.

## Headline

| segment | trivial floor | LOSO base (s42 / s43) | arm C s42 | arm C s43 | mean delta | supervised bound |
|---|---|---|---|---|---|---|
| w01 | 0.4148 | 0.4607 / 0.4621 | 0.5027 | 0.5383 | **+0.0591** | 0.8573 |
| w02 | 0.3791 | 0.4096 / 0.4174 | 0.4520 | 0.4628 | **+0.0439** | 0.8122 |
| w03 | 0.5124 | 0.5233 / 0.5331 | 0.5322 | 0.5444 | **+0.0101** | 0.8143 |
| w05 | 0.3485 | 0.3861 / 0.3971 | 0.3983 | 0.4331 | **+0.0241** | 0.7620 |
| w06 | 0.4743 | 0.5013 / 0.4985 | 0.5020 | 0.5181 | **+0.0101** | 0.7880 |
| w07 | 0.4778 | 0.5522 / 0.5551 | 0.5598 | 0.5949 | **+0.0237** | 0.7846 |
| w09 | 0.4424 | 0.5875 / 0.5981 | 0.6217 | 0.6458 | **+0.0410** | 0.7947 |

Mean over the 14 cells: **0.4916 to 0.5219, a change of +0.0303**. **Every cell of
fourteen improves**, and every segment improves at both seeds. Per-seed means are
+0.0211 (s42) and +0.0394 (s43); per-cell shares of the gap run +0.2% to +20.9%.

## Verdict, by the rules fixed in section 4

**It improves, consistently — and by about the width of the noise floor.** +0.0303
against a floor of ~0.03 is the smallest effect this project would call an effect
at all; what makes it one is the consistency, 14 of 14 cells and 7 of 7 segments
at both seeds, which a 0.03 coin-flip does not produce.

**The pre-registered prediction was −10% to +15% of the gap; the result is +9.5%.**
That is inside the interval. The reasoning behind it — the cross-scroll gap is bias
(docs/15 part 4a), so a model's confident errors are its own errors and training on
them reinforces them — survives in its quantitative form: self-training recovers a
tenth of the gap, not the gap.

## The number this arm exists to produce

Same base checkpoint, same segment, same recipe, same 2,500 steps, one variable:

| labels on w00 | mean gain on the seven unseen segments | share of the gap |
|---|---|---|
| a human annotator's (docs/15 part 4) | **+0.3202** | 82% |
| the model's own confident predictions | **+0.0303** | 9.5% |

**The annotation is worth about ten times what the model's own confident guesses
are worth.** That is the honest reply to "can we not just bootstrap it?", and it is
measured on the same seven segments with the same scoring rules rather than
argued.

## It is a real change in ranking, not a re-calibration

`tools/float_rank_check.py` on w01, seed 42, over the annotated area:

| checkpoint | AUC | best F1 float | best F1 uint8 | p25–p75 |
|---|---|---|---|---|
| LOSO base | 0.6593 | 0.4544 | 0.4545 | 0.287–0.442 |
| arm C, 2,500 | **0.7002** | 0.4873 | 0.4879 | 0.245–0.301 |
| arm C, 5,000 | **0.7102** | 0.4996 | 0.4999 | 0.245–0.302 |

AUC is rank-only, so the +0.04 it gains is the model ordering pixels better, not
the same ordering written on a nicer scale. That is the opposite of arm B, whose
AUC fell to 0.48 — two methods that both chase confidence, one destroying the
ordering and one improving it. The difference is that arm C's confidence is
converted into **hard targets on the target scroll's own geometry and then trained
with the supervised loss**, while arm B's is a direct objective on the output with
nothing to hold it in place.

The best threshold moves from 72–112 at the base to **63–97**, a much smaller shift
than arm B's collapse to 30–66, and no cell lands anywhere near its trivial floor
(the closest clears it by +0.020, the median by +0.083).

## Does it want more steps? The seeds disagree

The supervised fine-tune peaks at 2,500 and declines after, which is why 2,500 was
the pre-registered step here. Scoring 5,000 on the two probe segments does not
settle whether that was the right choice — it splits by seed:

| probe | 2,500 | 5,000 | change |
|---|---|---|---|
| w01 s42 | 0.5027 | 0.5156 | **+0.0129** |
| w05 s42 | 0.3983 | 0.4123 | **+0.0140** |
| w01 s43 | 0.5383 | 0.5179 | **−0.0204** |
| w05 s43 | 0.4331 | 0.4174 | **−0.0157** |

Seed 42 is still climbing at 5,000 and its AUC agrees (0.7002 → 0.7102); seed 43
has turned over. So there is no case for running longer, the pre-registered step
stands, and — worth noting for anyone reading the headline — **which seed you get
matters more than 2,500 versus 5,000 does**: the per-seed means differ by 0.018,
comparable to the whole effect.

## Limits

- **One segment's pseudo-labels, not the target's own sheets.** The transductive
  version — pseudo-labelling the seven scored segments themselves — is the variant
  a deployment would actually run, and it is untested here (see the deviation note).
  It could plausibly do better.
- **The thresholds were not tuned.** 0.5 ± 0.1 was fixed before the run because the
  literal pre-registered rule selected nothing; no other pair was tried, on this or
  any other target.
- **One target scroll**, as with every arm. docs/15 measured the transfer margin
  varying more than twofold by target, so "9.5%" is a Paris4 number.

---

# Arm D — the transductive variant of arm C, pre-registered (2026-08-30)

Arm C's deviation note gave up one thing explicitly:

> The eight-segment version would also have let the model adapt on the very sheets it is
> then scored on. This one does not, so a null result here does **not** rule out that
> transductive self-training — pseudo-labelling the target segments themselves — would do
> better. That variant is untested and is named as untested.

This is that variant, and it is the one a deployment would actually run. It is also **the
only method in this document that needs no annotation at all**, which is why it matters
beyond the ladder: it is the only one that can be pointed at a scroll nobody has labelled.

Written and committed **before any arm-D pseudo-label, checkpoint or score exists**.

## The design

| | arm C (run 2026-08-30) | **arm D (this)** |
|---|---|---|
| pseudo-labelled | `phercparis4-w00` only | **the seven scored segments themselves** |
| scored | the other seven | **the same seven** |
| labels used in adaptation | none | none |
| what a deployment has | the scroll's images | the scroll's images |

Everything else is held to arm C: the same base (leave-Paris4-out `ckpt_020000`, both
seeds), the same rule (**p ≥ 0.6 positive, p ≤ 0.4 negative, middle discarded, restricted to
the render's valid area**), the same released recipe, the same **2,500 steps**, the same
inference and scoring flags, the same seven segments.

**Each seed pseudo-labels from its own base.** Seed 42's labels come from the seed-42
checkpoint's predictions, seed 43's from seed 43's — as in arm C — so the two arms are not
sharing a hidden input.

**Adapting on the scored sheets is not scoring on training labels.** The target's annotation
is never opened during adaptation; the pseudo-labels come from the images and the model's own
output, and they cover the whole valid sheet rather than the annotated regions, so the
supervision mask never enters either. Scoring afterwards uses the withheld annotation exactly
as every other arm does.

## One compute concession, stated before the run

Pseudo-labelling a whole sheet puts 78–85% of it under supervision, and that is what made the
eight-segment attempt unaffordable: patch discovery took 13 minutes for the first segment and
projected 1h32m per seed at 10 GB and climbing.

So the supervision is **thinned on a deterministic grid: one 128 px block kept in every 3x3**,
about 1/9 of the confident set. Two things about it:

- **The pseudo-label content is unchanged** — the same pixels are called ink and background by
  the same rule. Only *how many* of them carry supervision changes.
- It lands the supervised area near what a real annotation covers on these segments (w01's
  real annotation is 8.3M of 99M sheet pixels, 8.4%), so the sampler sees a training
  distribution of roughly the shape the recipe was written for, rather than a sheet that is
  supervised nearly everywhere.

If arm D wins, the obvious follow-up is whether the thinning cost it anything. Not tested here.

## Prediction, committed now

**+5% to +30% of the gap** (arm C, non-transductive, returned +9.5%).

Reasoning, so the prediction can be judged and not just scored: adapting on the target sheets
gives the model the exact surface it will be read on, and seven segments of it rather than
one, which should help. But docs/15 part 4a measured the cross-scroll gap as **bias**, and on
these sheets the pseudo-labels *are* the model's own errors on those sheets — the failure
mode self-training is famous for. I expect the first effect to win by a little and the second
to cap it well below what a real annotation buys.

**Second, sharper commitment: it will not exceed 50% of the gap.** One labelled segment buys
82%. If pseudo-labels on seven sheets reach half of that, the bias reading in docs/15 part 4a
is in serious trouble and that is the more interesting outcome — which is why the number is
written down now.

## Decision rules — unchanged from section 4

Differences under **~0.03 F1 are noise**; both seeds; all seven segments; a result holding on
fewer than 5 of 7 is reported as inconsistent whatever its mean; compared at the **fixed
pre-registered step (2,500)**, with best-of-grid reported only as an oracle upper bound.

**The comparison that decides it** is arm D against arm C on the same fourteen cells, since
the only thing that changes between them is which sheets were pseudo-labelled.

## Failure signature to watch for

If self-training entrenches its own errors rather than sharpening them, F1 stays flat or
falls **while the model gets more confident** — mean predicted probability rising with AUC
flat or down. `tools/float_rank_check.py` is run on the probe segment either way, because
that is the measurement that separates "learned something" from "became surer of the same
thing".

---

# Result — arm D: pseudo-labelling the sheets you want to read is better, and still nowhere near an annotation (2026-08-30)

Run exactly as pre-registered above: the leave-Paris4-out arm at `ckpt_020000`, both seeds,
fine-tuned for 2,500 steps on pseudo-labels **for the seven scored segments themselves**,
then scored on those same seven with the withheld annotation. 18 cells;
`runs/ink9um_scorecard/armD_pseudoT_matrix.csv` and `armD_pseudoT_summary.json`.

No annotation entered the adaptation at any point. The pseudo-labels come from the images and
the base model's own predictions, cover the valid sheet rather than the annotated regions, and
the supervision mask is never opened.

## Headline

| segment | trivial floor | LOSO base (s42 / s43) | arm C (w00's labels) | **arm D** (own sheets) | D mean delta | D − C |
|---|---|---|---|---|---|---|
| w01 | 0.4148 | 0.4607 / 0.4621 | 0.5027 / 0.5383 | **0.5444 / 0.5285** | **+0.0750** | +0.0159 |
| w02 | 0.3791 | 0.4096 / 0.4174 | 0.4520 / 0.4628 | **0.4698 / 0.4539** | **+0.0484** | +0.0045 |
| w03 | 0.5124 | 0.5233 / 0.5331 | 0.5322 / 0.5444 | **0.5474 / 0.5449** | **+0.0180** | +0.0079 |
| w05 | 0.3485 | 0.3861 / 0.3971 | 0.3983 / 0.4331 | **0.4445 / 0.4332** | **+0.0472** | +0.0232 |
| w06 | 0.4743 | 0.5013 / 0.4985 | 0.5020 / 0.5181 | **0.5379 / 0.5209** | **+0.0295** | +0.0194 |
| w07 | 0.4778 | 0.5522 / 0.5551 | 0.5598 / 0.5949 | **0.5937 / 0.6031** | **+0.0447** | +0.0211 |
| w09 | 0.4424 | 0.5875 / 0.5981 | 0.6217 / 0.6458 | **0.6600 / 0.6391** | **+0.0568** | +0.0158 |

Mean over the 14 cells: **0.4916 → 0.5372, a change of +0.0457**, against arm C's +0.0303 and
a fine-tune bound of 0.8118. **All 14 cells improve**, all 7 segments at both seeds.

## Verdict, by the rules fixed in section 4

**It improves, consistently, and past the noise floor** — +0.0457 against ~0.03, 14 of 14
cells, 7 of 7 segments. **It recovers 14.3% of the gap** (median per cell 15.2%).

**The pre-registered prediction was +5% to +30%: 14.3% is inside it.** The sharper
commitment — that it would not exceed 50% — also holds, and by a wide margin. Both were
written down before the first pseudo-label existed.

## Against arm C, which is the comparison the arm exists for

Only one thing changed between C and D: which sheets got pseudo-labelled.

- **arm D − arm C = +0.0154 mean**, D better in **11 of 14** cells, range −0.0098 … +0.0462.
- **That difference is below this project's 0.03 noise floor.** The direction is consistent
  and the mechanism is plausible — adapting on the surface you will actually read — but by
  the rule fixed in section 4, **"transductive beats non-transductive" is not established
  here**; what is established is that both beat direct transfer and that D does so past the
  floor while C sat on it.

## It is a ranking gain, and it peaks where the pre-registration said to look

`tools/float_rank_check.py` on w01, seed 42, over the annotated area:

| checkpoint | AUC | best F1 float | best F1 uint8 | p25–p75 |
|---|---|---|---|---|
| LOSO base | 0.6593 | 0.4544 | 0.4545 | 0.287–0.442 |
| arm C, 2,500 | 0.7002 | 0.4873 | 0.4879 | 0.245–0.301 |
| **arm D, 2,500** | **0.7419** | **0.5253** | 0.5254 | 0.251–0.349 |
| arm D, 5,000 | 0.7138 | 0.4992 | 0.4993 | 0.255–0.357 |

**The failure signature did not appear.** Section 3D's entrenchment case was "F1 flat or
falling while the model gets more confident" — instead AUC rises by 0.08 over the base and by
0.04 over arm C, so the model is genuinely ordering pixels better rather than becoming surer
of the same ordering. Self-training on one's own errors is a real failure mode; it is not what
happened at 2,500 steps here.

At 5,000 it starts to come back down on this cell (AUC 0.7419 → 0.7138), and the probe F1
splits by seed exactly as arm C's did:

| probe | LOSO base | 2,500 | 5,000 |
|---|---|---|---|
| w01 s42 | 0.4607 | 0.5444 | 0.5091 |
| w01 s43 | 0.4621 | 0.5285 | 0.5620 |
| w05 s42 | 0.3861 | 0.4445 | 0.4190 |
| w05 s43 | 0.3971 | 0.4332 | 0.4646 |

So 2,500 remains the right stopping point and there is no case for running longer — the same
conclusion arm C reached, from the same split.

## What it costs, and what it still does not buy

Thinning made the arm affordable: patch discovery over seven segments took **2.5 minutes**
against the 13 minutes per segment the unthinned version projected, and each seed trained in
**17–18 minutes**. Supervision after thinning covers 8.8–8.9% of each sheet, next to the 8.4%
a real annotation covers on w01.

And the headline comparison of the whole ladder is unchanged in shape:

| what you give the model on the target scroll | mean gain on the seven segments | share of the gap |
|---|---|---|
| nothing (direct transfer) | — | 0% |
| its own confident pixels on a different segment (arm C) | +0.0303 | 9.5% |
| **its own confident pixels on these segments (arm D)** | **+0.0457** | **14.3%** |
| **one segment annotated by a human** (docs/15 part 4) | **+0.3202** | **82%** |

**A human annotation on one segment is still worth seven times the best label-free method
here.** That is the number to quote when someone asks whether the annotation effort can be
avoided: it cannot, but a seventh of it comes free.

## Limits

- **The D-versus-C difference is inside the noise floor**, as stated above. Establishing it
  would need more segments or more seeds.
- **One target scroll.** Paris4 only, like every other arm; docs/15 measured the transfer
  margin varying more than twofold by target, so 14.3% is a Paris4 number.
- **The thinning is untested as a variable.** It was a compute measure, declared in advance;
  whether keeping all the confident pixels would do better or worse is not known.
- **Two rounds were not tried.** Self-training is usually iterated; this is one round.

---

# Arm D on PHerc1447 — the unscoreable check, written down first (2026-08-30)

Section 6 of this document committed to this before any arm ran:

> Whatever survives the ladder gets run on the docs/16 render as the final, unscoreable
> check — and judged by eye, stated as such.

Arm D survived, and it is the only method here that uses **no labels at all**, so it is the
only one that can be pointed at a scroll nobody has annotated. This is that run. Because
there is nothing to score against, what counts as a result has to be fixed **before looking
at the output**, which is what this section is for.

## What runs

- **Target**: the docs/16 render, PHerc1447 segment `20250703034159-auto_grown_20250703034159599`
  (7.40 cm², the largest on that scroll), `[28, 3700, 5460]`.
- **Base**: the **released** `hybrid_3d2d` checkpoints at step 20000, both seeds — what a
  deployment would actually reach for, and what docs/16 already ran on this render.
- **Pseudo-labels**: the same rule as arm D — p ≥ 0.6 positive, p ≤ 0.4 negative, middle
  discarded, restricted to the render's valid area, supervision thinned one 128px block in
  every 3x3 — computed from **that same base checkpoint's own prediction on this render**,
  which docs/16 already produced.
- **Adaptation**: the same recipe, **2,500 steps**, then re-infer the whole render.
- No label of any kind exists for this scroll, so none is used and none can be used to score.

## What I expect, committed now

**No readable text.** The reasoning is not pessimism, it is what the ladder measured. On
Paris4 arm D recovers 14.3% of a gap whose *starting point already carries real signal* —
direct transfer there scores F1 0.49 against a 0.41 floor, so the confident pixels it
bootstraps from are more often right than wrong. On PHerc1447 docs/16 found the four
signatures of **no signal at all**: the checkpoints disagree threefold on how much surface is
strong ink, none reaches full confidence, the surface is mid-grey rather than bimodal, and at
full resolution the output is rounded patches rather than connected strokes. Self-training
started from that is bootstrapping from noise, and the honest expectation is that it sharpens
noise.

**What would change my mind — fixed here so it cannot be fitted afterwards:**

1. **Connected strokes** at full resolution where the base showed rounded patches — letters
   have joins, corners and consistent stroke width; blobs do not.
2. **The two seeds agreeing on where the strokes are.** They start from different released
   checkpoints and adapt independently; agreement on shape, not just on coarse layout, is
   hard to get from noise.
3. **A bimodal surface distribution** replacing the mid-grey one, i.e. the prediction
   committing rather than hedging.

Any one of those alone is weak. **Two of the three, in the same place, is the bar** for saying
something happened, and even then it is an eye judgement on an unlabelled scroll and gets
reported as exactly that.

**What does not count**, because docs/16 already caught these traps:
- the non-zero share (67.034% on all four base checkpoints) — that is the rendered valid
  area, not a detection rate;
- the `>128` share moving — the base checkpoints already disagree threefold on it;
- the prediction getting *more confident*. Arm B taught this exactly: confidence is not
  correctness, and self-training's known failure mode is becoming certain about its own
  errors. Increased confidence with unchanged structure is the **negative** outcome, not a
  positive one.

## What gets reported either way

The before/after distribution statistics docs/16 used, side by side; full-resolution crops of
the same region from the base and the adapted model, for both seeds; and a plain statement of
which of the three criteria above were met. If none are, this closes the loop docs/16 opened
with a measured negative rather than an open question.

---

# Result — arm D on PHerc1447: none of the three criteria met (2026-08-30)

Run as fixed above: the released `hybrid_3d2d` checkpoints at step 20000, both seeds,
adapted for 2,500 steps on pseudo-labels built from **their own predictions on this render**,
then re-inferred over the whole segment. No label of any kind exists for this scroll, so
nothing below is a score.

## First, a correction to the docs/16 baseline

Measuring the "before" turned up a defect in how docs/16 measured the "after" it never had.
docs/16 computed its statistics over the prediction's **written area**, which is 67.03% of
the canvas, and described that as "the rendered valid area". It is not:

- **The render's valid area is 21.05% of the canvas**, identical at every z.
- **68.9% of the written pixels are off the sheet** — inference schedules blocks from a
  coarse occupancy scan and hann-blends across whole blocks, so it paints well past the
  rendered ribbon, onto zeros.
- The model's output on that padding has almost the same distribution as on the sheet:
  median **86–109 off-sheet against 88–113 on-sheet**.

That last line is a sharper version of docs/16's own conclusion than docs/16 made: **the
model produces the same mid-grey field on zero input as on the scroll**, which is what
"the output is not driven by the data" looks like when you measure it. The four signatures
survive re-derivation on the sheet — `>128` share 10.6–32.3% across the four checkpoints
(still a ~3x disagreement), max 211–237 (still never near 255), median 88–113 (still
mid-grey). Numbers: `runs/first_letters/pherc1447_base_on_sheet.json`.

## What adaptation did

| | seed 42 base | seed 42 arm D | seed 43 base | seed 43 arm D |
|---|---|---|---|---|
| on-sheet `>128` share | 23.04% | **3.71%** | 10.62% | **0.90%** |
| on-sheet median | 100 | **54** | 88 | **58** |
| bottom third of range | 5.2% | **91.3%** | 6.4% | **97.5%** |
| middle third | 79.1% | **6.5%** | 86.5% | **1.8%** |
| top third | 15.8% | 2.3% | 7.1% | 0.7% |
| max | 214 | 237 | 211 | 226 |

**This is one-sided collapse, not commitment.** The pre-registered criterion was a *bimodal*
surface — the prediction committing to ink and not-ink. What happened is that 91–98% of the
sheet moved into the bottom third of the range while the top third shrank. The same shape as
arm B's collapse on Paris4, where it was scoreable and cost 0.04 F1.

⚠️ **A measurement mistake of my own, caught and reported**: the first version of this
comparison scored "bimodality" as the share of mass *outside the middle third*, which a
one-sided pile at the bottom satisfies perfectly — it reported 0.93 and 0.98, i.e. "highly
bimodal", for exactly the collapse above. The three-way split in the table is what the
criterion actually meant.

## The three criteria, judged

**1. Connected strokes where the base showed rounded patches — NOT met.** Matched
full-resolution crops of the 512px window with the *most* above-threshold pixels — the arm's
best case, chosen on the arm's own output — are in
[`pherc1447_armD_before_after.png`](images/pherc1447_armD_before_after.png) (base s42, arm D
s42, base s43, arm D s43). Adaptation raises contrast sharply: the soft mid-grey mush becomes
dark background with bright patches. But the patches are the same rounded, variable-width,
join-free shapes docs/16 described, at a scale far coarser than the papyrus fibre texture
visible in the surface itself ([`pherc1447_armD_surface.png`](images/pherc1447_armD_surface.png)).
Higher contrast, same shapes.

**2. The two seeds agreeing on where the strokes are — NOT met, and the near-miss is
instructive.** Pearson correlation between the seeds' on-sheet predictions rises from
**0.476 to 0.865**, which looks like exactly the agreement the criterion asked for. But the
**top-decile IoU — do they pick the same pixels as most-ink? — is 0.173 before and 0.177
after.** The correlation gain is both seeds collapsing toward the same mostly-dark field; on
*where the ink is*, they agree no more than before. Had the criterion been "correlation goes
up" this would have passed, which is why it was written as "agreeing on where the strokes
are".

**3. A bimodal surface distribution — NOT met.** See the table: unimodal at the bottom.

**Nothing met. The committed expectation — no readable text — holds.**

## What this closes

docs/16 ended by naming unsupervised adaptation as the prerequisite for reading an unlabelled
scroll. That prerequisite now has a measurement rather than a placeholder: **the best
label-free method in this ladder, the one that recovers 14.3% of the cross-scroll gap where
the gap is measurable, changes nothing readable on a scroll where the base model has no
signal to begin with.** Self-training amplifies what the model already believes; on Paris4
that belief is better than chance, and on PHerc1447 docs/16 measured that it is not.

So the honest statement for First Letters is unchanged and now costed at both ends: direct
inference scouts only in the weak sense, unsupervised adaptation does not rescue it, and the
step that works is the one that needs a person — one annotated segment, or half of one
(docs/15 part 5).

**What was not tried**: iterating self-training for more rounds, a different base checkpoint,
or the other fourteen PHerc1447 segments. The first two are cheap and would not change a
"no signal to amplify" diagnosis; the third is ~30 minutes each and docs/16 already argued the
result would be the same.

---

# The ladder, finished (2026-08-30)

| arm | what it does | predicted | measured | verdict |
|---|---|---|---|---|
| **A** — spectrum matching | reshape the target render's radial power spectrum to the source's, then re-infer | 0–20% of the gap | **+0.005 F1**, median 9.1% recovered, 17 of 24 cells | no effect |
| **B** — entropy minimisation | adapt the 27,712 normalisation affines to make the target's predictions confident | 10–40% | **−0.041 F1**, 0 of 14 cells, AUC 0.66 → 0.48 | **harms**; prediction refuted |
| **C** — pseudo-label self-training | fine-tune on the model's own confident pixels for one target segment | −10% to +15% | **+0.030 F1**, 14 of 14 cells, **+9.5%** of the gap | improves, at the noise floor |
| **D** — the same, transductive | pseudo-label the sheets to be read, rather than a different one | +5% to +30%, not above 50% | **+0.046 F1**, 14 of 14 cells, **+14.3%** of the gap | improves, past the floor |

Three cheap routes, each with its design, prediction and decision rule fixed in
public before it ran. Section 7 asked what gets published either way, and the
answer the ladder actually produced is more useful than either branch it
anticipated:

**Unsupervised adaptation on this corpus is not free and is not enough.** The
input-space route buys nothing. The classical test-time route is actively
harmful, and — the part worth carrying elsewhere — **its own objective improves
monotonically while the model degrades, so there is no label-free signal that
would have told anyone to stop.** The route that helps is self-training, and it
helps most when it labels the sheets it is about to read: **14.3% of the gap**,
against **82%** for one segment annotated by a person. Holding the base, the
recipe and the step count fixed, **a human annotation is worth about seven times
the best label-free method measured here.**

So the practical statement for an unlabelled scroll is unchanged in direction and
now quantified: **annotate something.** Half of one segment keeps 89% of the
benefit (docs/15 part 5); the model's own confident guesses on the sheets it will
read keep 14.3%. Between those two numbers is the entire case for spending
annotator time rather than GPU time — and the 14.3% is the part you get for free
on a scroll where annotating is not yet possible.

One prediction of three was wrong, and it was wrong in the direction I did not
consider — I expected entropy minimisation to help a little and it hurts. That is
what the pre-registration was for.

**And it was pointed at a scroll nobody has read.** Arm D on PHerc1447 met **none** of
the three criteria fixed before the run: the patches stay rounded rather than
becoming strokes, the seeds' agreement on *where* the ink is does not move
(top-decile IoU 0.173 → 0.177) even as their overall correlation rises to 0.865,
and the distribution collapses to one mode at the bottom rather than becoming
bimodal. Self-training amplifies what a model already believes, and docs/16
measured that on this scroll it believes nothing.

**Arm D closed the open item, and its prediction held.** The transductive
variant — pseudo-labelling the sheets to be read rather than a different one —
recovers **14.3%** of the gap against arm C's 9.5%, inside the +5% to +30%
committed before it ran and well under the 50% ceiling also committed. It is the
only method in this ladder that needs no annotation at all, so it is the one that
can be pointed at a scroll nobody has labelled; whether that is worth doing is
now a question with a number attached rather than a hope.

---

MIT-licensed. Pre-registered before any arm was run; the git history of this
file is the timestamp.
