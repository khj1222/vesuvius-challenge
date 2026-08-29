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

MIT-licensed. Pre-registered before any arm was run; the git history of this
file is the timestamp.
