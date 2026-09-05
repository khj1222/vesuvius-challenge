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

---

# Stage 1 result (2026-09-05) — the proxy is worse than I predicted, on both scrolls, and the ordering is reversed

24 cells: two scrolls × two seeds × their scored segments, each pseudo-label tree scored against
the annotation withheld from the run that consumed it, on the intersection of the two
supervision masks. Raw numbers: `runs/ink9um_scorecard/pseudo_quality_{1667,paris4}_s4{2,3}.json`.

| scroll | mean F1 | mean trivial floor | mean margin | cells below the floor |
|---|---|---|---|---|
| PHerc. 1667 | 0.4347 | 0.3421 | **+0.093** | 1 / 10 |
| PHerc. Paris 4 | 0.3958 | 0.4101 | **−0.014** | **10 / 14** |

**Both predictions missed, both downward, and the order between the scrolls is inverted.** I
wrote 0.55–0.80 for 1667 and 0.70–0.90 for Paris 4, reasoning that the base model is stronger on
Paris 4 so its confident pixels should be better. The measured values are 0.406–0.464 and
0.390–0.402: lower on both, and **lower on the scroll I expected to be higher**. Eleven of the
24 cells do not beat marking every pixel as ink.

**The failure has a shape: precision 0.33–0.93 against recall 0.007–0.587.** Restricted to
pixels the pseudo-labeller had an opinion about, it is reasonably right when it says *ink* and
badly wrong when it says *background* — it confidently labels most of the ink as empty. That is
not an artifact of the sparse support, which this comparison already excludes by scoring only
where both masks are defined.

**Seed instability on the same segment.** `pherc1667-w023` scores **0.3475 under seed 42 and
0.0144 under seed 43** — a spread of 0.333, from two seeds of the same released base model, with
recall collapsing to 0.007. Which segment's pseudo-labels are usable is not a property of the
segment.

## The thing worth carrying out of Stage 1

These are not arbitrary label trees. `pseudoT_s42/43` are **exactly** the labels of arm D on
Paris 4 (`armD_pseudoT_matrix.csv`, same seven segments, 14 cells), and arm D **improved 14 of
14 cells** against withheld annotation, recovering 14.3% of the cross-scroll gap (docs/18).

So on Paris 4: **training on labels that lose to a trivial classifier in 10 of 14 cells still
improved the model against the truth in 14 of 14.** Whatever makes a pseudo-label *useful for
training* is not what F1 against the annotation measures. The two uses of the same object come
apart, and that is the finding:

- as **training signal**, these labels work — measured, twice, on two scrolls (docs/18);
- as a **yardstick**, they agree with the truth at roughly the level of guessing.

A validation score computed against them is therefore agreement with an object of that quality.
This says nothing about whether any particular configuration found that way is good — only that
the measurement cannot distinguish that case from its opposite without the annotation it
replaces.

## What the pre-registered rule now requires

Both means are below 0.50, which is the band the pre-registration marked **"the proxy is poor —
Stage 2 is warranted, but any ranking conclusion is *weaker*, not stronger, and must be reported
that way."** That constraint is binding and carried forward: if Stage 2 finds the two scorings
choosing different checkpoints, the honest reading is *this proxy, at this quality, misranks* —
not *pseudo-label validation misranks in general*.

⚠️ **The caveat that survives regardless of Stage 2**: this is our pseudo-label recipe (p ≥ 0.6
positive, p ≤ 0.4 negative, middle discarded, from the released base) on this corpus. A
different construction — different thresholds, iterated rounds, a stronger base — could produce
a better proxy. Nothing here measures the swarm's labels, which are not published.

---

# Stage 2 result (2026-09-05) — the registered prediction is refuted, and the test that refuted it had little power

30 cells: arm D's 1667 checkpoints at three steps, two seeds, five segments, each prediction
scored **twice from one inference**. Raw numbers: `runs/ink9um_scorecard/pseudo_rank_matrix.csv`
(60 rows), verdict `pseudo_rank_summary.json`.

**Faithfulness check first.** Every truth score reproduces the committed `r1667_matrix.csv` value
to four decimals and the same threshold — e.g. `D,42,pherc1667-w013,002500` gives 0.5685 @ 67
either way. The re-inference is the same experiment, so any difference below is the yardstick.

## The registered verdict: agree, 5 of 5 segments

| segment | seed 42 | seed 43 |
|---|---|---|
| w013 | truth 5,000 / pseudo 10,000, penalty **+0.0017** | same pick, **0.0000** |
| w023 | same pick, 0.0000 | same pick, 0.0000 |
| w028 | truth 2,500 / pseudo 10,000, **+0.0013** | truth 2,500 / pseudo 10,000, **+0.0185** |
| w029 | same pick, 0.0000 | truth 5,000 / pseudo 10,000, **+0.0086** |
| w031 | same pick, 0.0000 | same pick, 0.0000 |

Every penalty is under 0.03. **I predicted disagreement on 1667 and I was wrong.**

## But the failure mode named in advance is exactly what happened

docs/24 said before the run: *"the pseudo-labels are frozen … an adapted model drifting toward
them raises the pseudo score trivially. A rising pseudo score therefore shows nothing on its
own."* Both halves of that are visible in the data:

- **Pseudo picks step 10,000 in 10 of 10 cells**, because its score rises monotonically in every
  cell without exception (0.89 → 0.94 typical). It is not selecting a model; it is reporting how
  far self-training has gone.
- **Truth barely varies across these steps**: spread 0.0027–0.0388, mean **0.0166**, and above
  the 0.03 noise floor in **1 of 10 cells**.

So the two agree because **there was almost nothing to get wrong**. A proxy that always answers
"the last one" is nearly free when the truth curve is flat. The registered verdict stands as a
verdict — it is a finding *for* the practice, as docs/24 committed to reporting — but it is a
weak one, and reading it as "pseudo-label validation selects models correctly" would be reading
more than this design can carry.

## The observation that is not weak, and was not registered

⚠️ **Not part of the pre-registered rule.** It was noticed after the verdict and is reported as
an observation, not a test. Raw numbers: `runs/ink9um_scorecard/pseudo_threshold_cost.json`.

The two yardsticks choose **very different operating thresholds**, and unlike the step choice
this is not close:

| | value |
|---|---|
| pseudo threshold − truth threshold | **+45.3 mean** (min +18, max +71) |
| cells where the gap is positive | **30 / 30** |
| cost in true F1 of adopting pseudo's threshold | **0.066 mean** (0.005 – 0.139) |
| cells where that cost exceeds the 0.03 noise floor | **25 / 30** |

A model agrees with its own pseudo-labels at 0.89–0.97, so the threshold that maximises that
agreement sits far above the one that maximises agreement with the annotation. Someone with no
labels sets the threshold from the only score they have, and pays about **twice the noise floor**
for it — a larger effect than most of the interventions this project has measured.

⚠️ **The cost figure is approximate.** The saved reports carry a 32-point sweep and the
predictions were deleted after scoring, so truth's F1 is read at the nearest sampled threshold
(grid spacing 8) rather than exactly at pseudo's. The bound is the curve's change over four grey
levels; at more than twice the noise floor, the sign and magnitude do not turn on it.

## What Stage 2 leaves standing

- **Which checkpoint**: the two agree here, on a stretch where truth is flat enough that the
  question barely has an answer. Registered, honoured, and weak.
- **Which threshold**: they disagree in every cell, in the same direction, at twice the noise
  floor. Not registered, so it is a hypothesis for someone to test properly, not a result.
- And the Stage 1 constraint still binds everything: this is **our** pseudo-label recipe on
  **this** corpus. Nothing here measures the labels behind the published cross-scroll number.
