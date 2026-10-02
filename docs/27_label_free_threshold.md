# 27 — Choosing an ink threshold on a scroll with no labels (pre-registration)

**Status: pre-registered, not yet run.** This file is committed before any rule below has
been scored. The results section is appended after the run; nothing above it changes.

## The gap

Every honest F1 in this repository picks its threshold with labels. docs/14–18 report
the F1-optimal threshold per cell (an oracle). docs/26 freezes a threshold, but chooses it
on a second annotated segment of the same scroll. Someone running a model on a scroll
nobody has annotated has neither.

The only label-free method we have measured is worse than a fixed guess would need to be.
Pseudo-labels pick thresholds **+45 grey levels** above the true optimum in 30 of 30 cells and
cost **0.066 F1** (docs/24, an observation made after its test, not a test). Without labels the
usual fallback is a fixed 0.5 (= 128 of 255); #1924's probe, for instance, counts pixels above 0.5.

**Question.** On a scroll the model never saw, can a threshold chosen without that scroll's
labels come within the noise floor (0.03 F1) of the oracle?

## Data (all already on disk, no training, no inference)

- **Predictions**: the leave-one-scroll-out (LOSO) models of docs/15, scored on the scroll
  they left out. Paris4: 8 segments, 1667: 6, 0139: 9 (aligned 9.6 µm representations).
  Two seeds (42, 43) × seven steps (10k–75k) each. Saved TIFFs, uint8.
- **Truth**: each segment's `_inklabels` inside its `_supervision_mask` (middle slice), exactly
  as in `no0139_matrix.csv`, `no1667_matrix.csv`, `paris4_matrix.csv` (rows `loso42`/`loso43`;
  for 0139 only the nine `pherc0139-*` aligned segments, not the native `w035`… rows). The oracle F1 and
  oracle threshold of every cell must reproduce those files — threshold exactly, F1 within 0.0001
  (the files keep four decimals). This check runs first; any cell that fails it is reported and
  excluded from every rule alike.
- **Sheet**: pixels where the middle layer of the segment's aligned surface volume is non-zero.
  Shapes match the predictions exactly (checked on three segments before writing this).
  This is the only region label-free rules may read; it does not use where anyone annotated.
  Fallback if a volume is missing: prediction > 0. The number of fallback cells is reported.

A cell = (held-out scroll, segment, seed, step). Positive means `score >= threshold`,
thresholds are integers 0–255, as in `tools/eval_validation.py`.

## Rules (fixed now)

| rule | threshold | uses |
|---|---|---|
| **R0 default** | 128 | nothing |
| **R1 value transfer** | median oracle threshold over the *other two* scrolls' cells at the same step (both seeds; for 0139 the nine aligned segments only) | other scrolls' labels |
| **R2 Otsu** | Otsu on this cell's sheet histogram: k in 1–255 maximising between-class variance of {< k} vs {≥ k} | this cell's predictions only |
| **R3 quantile transfer** | the threshold at which this cell's sheet has fraction *q* of pixels at or above it, *q* = median over the other two scrolls' cells at the same step of (sheet fraction ≥ that cell's oracle threshold) | other scrolls' labels + this cell's predictions |

R1 and R3 are transfer rules: the labels exist, but on other scrolls (the same cell set as above).
Each borrows from the other scrolls' LOSO models, i.e. from a model that also never saw the scroll
it was scored on — the situation a held-out validation scroll gives a real user. R2 uses nothing but the
prediction. Ties in R3 resolve to the lowest threshold reaching *q*.

## Measure and decision

**Regret** = oracle F1 − F1 at the rule's threshold, per cell.

- **Primary**: steps 10,000 and 20,000 (where docs/15 found LOSO models peak), both seeds, all
  segments. Mean regret per held-out scroll (every cell weighted equally within a scroll), each
  scroll weighted equally in any pooled figure.
- **Secondary** (descriptive only): all seven steps; regret of docs/26's labelled-calibration
  approach where it overlaps; how far adapted models (fine-tune, arm C/D, label budget) move
  the oracle threshold.

A rule **passes** if its mean regret is **< 0.03 on every one of the three scrolls** and lower
than R0's on each.

| outcome | what we report and do |
|---|---|
| ≥ 1 rule passes | publish it as the label-free default, with a small tool that prints the threshold for a prediction TIFF |
| a rule passes on 1–2 scrolls | report it as scroll-specific; no default is recommended |
| no rule passes | report the guidance "annotate one calibration segment", priced by the regret each rule leaves, and by R0's |

The noise floor 0.03 is the same-config spread from docs/09 (four evaluations, 0.823–0.854).
Cells from one scroll are correlated (shared model, neighbouring segments); counts of cells are
not independent samples and no significance test is run.

## What we already know (disclosed so it cannot be mistaken for a finding)

- The oracle thresholds of the LOSO rows span **0–147** (0139 62–147, 1667 67–116, Paris4 0–112;
  the single 0 is Paris4 w03, seed 43, step 10k, where the best F1 is the trivial all-ink
  classifier). We have seen those columns; we have not computed any rule's threshold or regret.
- The rules were chosen from the literature-standard options (fixed default, transfer,
  Otsu, quantile) before looking at any sheet histogram.

## Prediction

No rule passes on all three scrolls. R0 has the largest regret on at least one scroll. R2
(Otsu) does poorly, because docs/18 found the leave-Paris4-out model is not confident on Paris4
(its raw outputs span only 0.17–0.89), so sheet histograms are unlikely to be bimodal. R3 does best of the
four. If R3 passes everywhere, that prediction failed in the useful direction.

## How it can go wrong

- The sheet includes padding or damaged areas that dominate the histogram: R2/R3 are then
  measuring the render, not the ink. Reported via the sheet's pixel count per cell.
- Three scrolls is a small base for "transfer". A pass is a recommendation for these
  representations and this recipe, not a law.
- Aligned representations only. Native renders (docs/15 appendix 2) are out of scope.
