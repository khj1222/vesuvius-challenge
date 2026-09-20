# 26 — Fine-tuning with a separately calibrated, fixed threshold

**2026-09-20 retrospective follow-up.** Previously inspected segments and saved models
are reused. This is not an independently held-out new dataset or a prospectively
registered public experiment. No new training or inference was needed.

## Result

Thresholds were chosen on one calibration segment per scroll and then frozen for every
other evaluated segment, separately for each arm and seed. Both seeds are averaged;
no checkpoint or seed is selected using evaluation performance.

| Scroll | Base → FT steps | Evaluation segments | Base F1 | FT F1 | Delta | Improved seed–segment pairs |
|---|---|---|---|---|---|---|
| Paris4 | 20,000 → 2,500 | 6 | 0.485284 | 0.789778 | +0.304494 | 12/12 |
| 1667 | 10,000 → 2,500 | 4 | 0.530602 | 0.629321 | +0.098719 | 8/8 |

1667 FT actually starts from the 10k base; Paris4 starts from 20k. The declared 1667
20k-base sensitivity gives 0.532342 → 0.629321
(+0.096980, 8/8 improved). It is a different
base comparison, not the initialization used to produce that FT checkpoint.

Per-seed primary deltas: Paris4 seed 42 +0.300529, seed 43 +0.308459;
1667 seed 42 +0.106174, seed 43 +0.091265.
Seeds and segments from the same scroll are correlated; pair counts are not independent
sample sizes or significance tests.

## Calibration budget and exclusions

| Scroll | Calibration segment | Unique labeled pixels | Base threshold 42 / 43 | FT threshold 42 / 43 |
|---|---|---|---|---|
| Paris4 | phercparis4-w01 | 8,268,843 | 85 / 83 | 129 / 112 |
| 1667 | pherc1667-w013 | 3,358,647 | 89 / 96 | 107 / 117 |

The threshold is the lowest exact maximizer of pooled calibration F1 over integer 0–255,
where a positive prediction is score≥threshold. Both arms receive exactly the same
calibration annotation. FT training w00/w018 and calibration w01/w013 are excluded from
evaluation. The remaining segments are Paris4 w02/w03/w05/w06/w07/w09 and 1667
w023/w028/w029/w031. This requires **an additional labeled calibration segment** beyond
the segment used for FT; it is not label-free or a one-annotation deployment result.
Different scrolls have different annotation budgets and evaluation populations.

## Counting audit

The old evaluator finds connected regions and sums masks inside their bounding boxes.
Overlapping boxes can count the same valid pixel more than once. The first evaluation
guard caught this on Paris4 w02: 4,647,609 unique pixels versus 4,653,221 old counts.
The new primary score visits each valid pixel once. Legacy histograms are also computed
and must reproduce every old count and oracle F1 (CSV rounding tolerance 0.000051).
Positive and negative legacy histogram bins must each be at least their unique counts.

Affected evaluation segments and extra counts: {"phercparis4-w02": 5612}.
Across 48 evaluation cells, the largest absolute fixed-F1 change from removing duplicated
counts is **0.000472715**. The paired gain using legacy
counts is Paris4 +0.304441, 1667 +0.098719.
The primary conclusion is therefore reported alongside this scoring sensitivity.
All 10 calibration cells already match unique counts; their frozen thresholds did not
change after finding this issue. A synthetic ring/center test reproduces 25 unique pixels
versus 26 legacy counts. The historical evaluator and reports are retained, not silently
rewritten; those old numbers use their original counting and selection rules.

## What this supports

Fine-tuning gains persist here when the threshold is calibrated on a separate segment
instead of optimized on each evaluated prediction. This strengthens that limited claim.
It does not establish unread-scroll legibility, independent generalization to a new
dataset, or a guaranteed recovery percentage. The older 82%/24% headlines use oracle
selection and a train-pixel reference; these new means do not replace their denominators.

## Reproduction

Full histograms, per-pair values, exact supports and hashes are in
[`runs/september_evidence_audit`](../runs/september_evidence_audit/README.md).
The portable manifest names all 58 archived predictions (10 calibration, 48 evaluation).
Run `python tools/verify_september_evidence.py` for an independent standard-library
check of threshold selection, F1, pixel supports and the pseudo-threshold loss bounds.
Binary-input rescoring commands and dependencies are listed in that directory's README.
Two synthetic regression tests pass with the installed Python 3.12/numpy/zarr2 environment.
