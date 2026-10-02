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

---

# Results (2026-10-02, run after commit 1b5917e)

Tool: [`tools/score_label_free_threshold.py`](../tools/score_label_free_threshold.py) (`collect` reads each
saved prediction once into 256-bin histograms, `score` applies the rules to those histograms only).
Raw: [`labelfree_summary.json`](../runs/ink9um_scorecard/labelfree_summary.json),
[`labelfree_cells.csv`](../runs/ink9um_scorecard/labelfree_cells.csv) (one row per cell),
[`labelfree_hists.npz`](../runs/ink9um_scorecard/labelfree_hists.npz) (every histogram, so the rules can be
re-audited without the 18 GB of TIFFs).

**Reproduction check: 322 of 322 cells reproduce the committed matrices** (threshold exact, F1 within
0.0001). No cell is excluded. As an independent check on the sheet definition, Paris4 w00's sheet is
85,866,396 px, the same count docs/18 reports for that segment's valid render area.

## Primary (steps 10k and 20k)

Mean regret (oracle F1 − F1 at the rule's threshold); in brackets, cells under 0.03 and the range
of thresholds the rule chose. Mean oracle F1 is 0.473 (Paris4), 0.536 (1667), 0.654 (0139).

| rule | Paris4 (32 cells) | 1667 (24) | 0139 (36) | verdict |
|---|---|---|---|---|
| R0 default 128 | 0.113 (2/32) | 0.056 (5/24) | 0.145 (5/36) | — |
| **R1 value transfer** | **0.014** (27/32; 86–92) | **0.007** (24/24; 84–86) | **0.016** (30/36; 85–90) | **passes** |
| R2 Otsu | 0.050 (12/32; 104–116) | 0.022 (19/24; 107–118) | 0.055 (15/36; 98–114) | fails (1 of 3) |
| **R3 quantile transfer** | **0.025** (20/32; 92–111) | **0.002** (24/24; 78–109) | **0.020** (25/36; 72–85) | **passes** |

**The prediction failed, in the useful direction.** Two rules pass on every scroll, R1 by the wider
margin. The parts that held: R0 is the worst rule on every scroll, and Otsu is poor.

What the numbers say in plain terms:

- **128 is the wrong default for these models.** On the unseen scroll it costs 0.06–0.14 F1 — two to
  five times the noise floor — and is within the floor in only 12 of 92 cells. The optimum is below
  128 in 90 of the 92 cells (the two exceptions are 0139 w017 at step 20k, 131 and 137).
- **The other scrolls' optimum transfers.** R1 lands at 84–92 in every cell and leaves 0.007–0.016,
  under half the floor. Because it barely moves, the operational content is close to "these
  recipe models want about 85–90, not 128" — but that value was taken from other scrolls each time, never
  from the scroll being scored, which is the whole test.
- **Quantile transfer also passes but is less safe:** its worst cell on Paris4 loses 0.120.
- **Otsu does not work** here: its median threshold sits 20–26 grey levels above the optimum on every
  scroll (worst cell +111). A likely reason, not tested: the sheet histogram has no separate ink mode
  for Otsu to split off.

## Secondary (descriptive, not tested)

- **All seven steps (10k–75k):** R1 still passes (0.016 / 0.007 / 0.024). R3 does not: Paris4 rises
  to 0.032. The longer-trained checkpoints are where quantile transfer starts to slip.
- **Counting each pixel once vs the matrices' per-box counting** changes no verdict and no mean by more
  than 0.0015.
- **Adaptation moves the optimum, so the transferred value must not be carried across.** Oracle
  thresholds from the committed matrices (min / per-seed medians / max): Paris4 fine-tune
  74 / 90–100 / 131, 1667 fine-tune 98 / 109 / 120, arm C 63–97 (medians 68–73), arm D 65–121,
  TENT collapses to 0–69.
  A threshold transferred from unadapted LOSO models describes unadapted LOSO models.
- For scale: on its own (different, adapted) cells, docs/24's pseudo-label threshold cost 0.066 F1.

## Deviations and limits

- One detail was not fixed in advance: R1's median of an even number of donor thresholds is rounded
  half-up. Any effect is at most one grey level.
- Three scrolls, one recipe (the ink_9um LOSO models, aligned 9.6 µm representations). The pass is a
  recommendation for that setting. Public checkpoints trained on every scroll, Hecate, native renders
  and adapted models are untested, and the last of these is shown above to move the optimum.
- Cells within a scroll share a model and neighbouring segments; the counts above are not independent
  samples.

## What to do with it

For an ink_9um-recipe model run on a scroll nobody has annotated: **do not binarize at 128.** Take the
threshold that was F1-optimal on held-out scrolls you do have labels for (here 84–92) and use it
unchanged. If you fine-tune or self-train on the new scroll, that value no longer applies; re-derive it
on held-out data of the adapted model.
