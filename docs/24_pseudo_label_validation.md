# 24 — Does validation on pseudo-labels track the truth?

**Pre-registered 2026-09-05, before any number was computed.** Committed first, as
[docs/18](18_uda_design.md), [docs/20](20_annotation_targeting.md) and
[docs/21](21_snr_augmentation.md)–[docs/23](23_blur_exposure.md) were; two of those four were
stopped by their own calibrations before spending GPU, and the stopping rule below is written
to have the same power here.

## Why

The Vesuvius Challenge open-problems page names **cross-scroll generalization** as a bottleneck
and asks for "multi-scroll training, better labels, **stronger diagnostics**". On the same page:

> One step forward on cross-scroll generalization came from an unusual source: an autonomous
> agent swarm … the system found a configuration that nearly doubled the **validation Dice
> score (computed on pseudo-labels)** on PHerc. 1667 while training only on PHerc. 139 data — a
> genuine cross-scroll generalization improvement.

That is the axis this project measured with withheld human annotations
([docs/15](15_loso_cross_scroll.md), [docs/18](18_uda_design.md)): train on other scrolls,
score on 1667. **The direction and the scroll are the same; the measuring stick is not.**

And this project already holds a result that makes the difference worth checking. On 1667,
pseudo-label self-training bought **nothing** against withheld annotations — arm C never left
the noise floor at any step and **arm D was negative at every step** — where on Paris4 arm D
improved 14 of 14 cells (docs/18). A method that helps by one stick and not the other is
exactly the case where knowing which stick you are holding matters.

**The question is therefore not whose result is right. It is whether the two scorings rank
models the same way.** We can ask it because, for the same segments, we hold both: the
pseudo-label trees (`pseudo1667D_s42/43`, `pseudoT_s42/43`) cover precisely the segments the
committed matrices score against annotation (`r1667_matrix.csv`, `armD_pseudoT_matrix.csv`).

## What this can and cannot claim

- **Cannot**: reproduce or evaluate the swarm's configuration. It is not published, and nothing
  here says their number is wrong.
- **Can**: say whether, in this corpus and on this axis, a score computed against pseudo-labels
  chooses the same model as a score computed against annotations withheld from training.

## Stage 1 — calibration, no GPU

Score each pseudo-label tree **against the withheld annotations of the same segment**, for both
scrolls and both seeds. This measures the quality of the object the other measurement validates
against.

⚠️ **Support, stated before the numbers.** Pseudo-labels cover only the base model's confident
pixels inside the valid render area (built at p ≥ 0.6 positive, p ≤ 0.4 negative, the middle
discarded); annotations cover the annotated regions. **The comparison is made only where both
are defined**, and the intersection's size and positive rate are reported alongside, because a
comparison over a differently shaped support is not the comparison meant here.

Also recorded: the positive rate of each tree, and what fraction of the annotated area the
pseudo-labels have an opinion about at all.

**Stopping rule, committed now.**

| Stage 1 agreement (F1, pseudo vs annotation) | what it means | what happens |
|---|---|---|
| **≥ 0.90 on both scrolls** | validating on pseudo-labels ≈ validating on truth | **STOP.** Report the calibration as a null result; spend no GPU. |
| **0.50 – 0.90** | the proxy is mid-quality, so a score against it is agreement with a proxy of that quality | Stage 2 is warranted |
| **< 0.50** | the proxy is poor | Stage 2 is warranted, but any ranking conclusion is *weaker*, not stronger, and must be reported that way |

## Stage 2 — the ranking test (≈ 2 GPU hours, only if Stage 1 warrants)

Re-infer arm D's 1667 checkpoints — 3 steps × 2 seeds × 5 segments = **30 inferences** — and
score **each prediction twice**: once against the pseudo-labels, once against the withheld
annotations. One inference serves both, so the two sticks measure the identical prediction.

Reported: rank correlation between the two scorings; whether pseudo-label validation selects
the same step as truth; and whether the pseudo score rises where truth falls.

**Reading rule, committed now.**

- **"They disagree"** = the step chosen by pseudo-label validation is worse *in truth*, by more
  than **0.03 F1** (this project's noise floor, established over four evaluations of one config
  in July), than the step truth chooses — **and this holds in both seeds**.
- **"They agree"** = the selections match, or differ by less than 0.03.
- Anything else is **reported as not captured.** No spinning a split result.

## Predictions, written before computing

- **Stage 1**: pseudo-vs-annotation F1 of **0.55 – 0.80 on 1667** and **0.70 – 0.90 on Paris4**
  — the trees keep only the base model's confident pixels, and the base is the better model on
  Paris4 (docs/18).
- **Stage 2**: I expect **disagreement on 1667**, because docs/18 already shows arm D's true F1
  falling at every step there while self-training, by construction, moves the model toward its
  own pseudo-labels.

⚠️ **And the failure mode that would make Stage 2 uninteresting, named in advance.** The
pseudo-labels are frozen — built once from the base model — so an adapted model drifting toward
them raises the pseudo score *trivially*. **A rising pseudo score therefore shows nothing on its
own.** The result is only interesting if the two scorings **rank the checkpoints differently**.
If the pseudo score rises monotonically and the ranking still agrees with truth, that is a
finding *for* the practice, and it is reported as such.
