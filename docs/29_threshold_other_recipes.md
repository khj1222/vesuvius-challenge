# 29 — Does the label-free threshold rule hold for checkpoints trained on other labels? (pre-registered)

**Status: pre-registration, committed before any of the checkpoints below was run on these scrolls.**
Results will be appended under a separate heading; nothing above it changes afterwards.

## Why

[docs/27](27_label_free_threshold.md) tested one way of choosing an ink threshold without labels on the
scroll being read: take the F1-optimal threshold that the **same checkpoint** reaches on other scrolls you
can score (rule R1b). It passed twice, but both times on one recipe: the `ink_9um` models, trained on the
team's sparse manual labels. Its stated limit is "one recipe". `tools/borrow_threshold.py` and villa
[#2012](https://github.com/ScrollPrize/villa/pull/2012) now offer it to anyone, including people who train
on different labels, so the limit is worth testing.

Two public groups of 9 µm checkpoints use the same architecture and inference command but **different
training labels**, and none of them trained on the three open-label scrolls docs/27 used:

- **KLAVIS `ink9um-dense`** ([HF `domenicor046/ink9um-dense`](https://huggingface.co/domenicor046/ink9um-dense),
  revision `3e5e7ed44e`, MIT): the `aligned21_hybrid_3d2d` recipe on the same 29-representation corpus
  (PHerc0139, 1667, Paris 4, 0814), with dense pseudo-labels from a 2.4 µm teacher instead of the manual
  labels. Four checkpoints, including a matched manual-label control.
- **Nieuwlaar `ink9um-dense-native`** ([HF `Nieuwlaar/ink9um-dense-native`](https://huggingface.co/Nieuwlaar/ink9um-dense-native),
  revision `b894a0493a`, MIT): initialised from KLAVIS's dense model, then 20k steps adding native
  113 keV PHerc0139 renders with dense teacher labels (`train_dense_native.json`: quotas 0139, 1667,
  Paris 4, 0814, 0139-native). `dense_native_016000`.

Not testable with the labels available (recorded so the choice is visible): **Reader v2** (KLAVIS,
September) trained on PHerc0009B and 0500P2, so only PHerc0841 is new to it and nothing is left to borrow
from. **v8-in** (YoussefNader) trained on 0500P2 and reads 24-layer native renders, not these inputs.

## Data (all already on disk except the checkpoints)

- Inputs and labels: exactly the docs/27 replication's five segments: PHerc0841 w00, ag144, ag174;
  PHerc0009B ag055; PHerc0500P2 s1 (2.4 µm volumes pooled to the recipe's 21-slice ~9.6 µm grid; level 2
  of the open-data `inklabels` / `supervision` pyramids; scored inside `supervision`). PHerc0500P2 is
  8.86 µm on this grid, as before.
- Checkpoints: five. They are third-party pickles, so they are not unpickled as such: each KLAVIS `.pth`
  was read with `torch.load(weights_only=True)` and re-saved; Nieuwlaar's safetensors (sha256
  `d3d95dc4…6fc6d`, equal to its `VERIFY.md`) was wrapped with its published training config. All five
  have the released `ink_9um` key set and tensor shapes.

| name | source file | labels it was trained on | group |
|---|---|---|---|
| `K_ex016_75k` | `dense9um-w016excluded-step075000.pth` (KLAVIS's recommended) | dense | primary |
| `K_ex016_60k` | `dense9um-w016excluded-step060000-best.pth` | dense | primary |
| `K_all7_75k` | `dense9um-all7-step075000.pth` | dense | primary |
| `N_native_16k` | `dense_native_016000.safetensors` | dense + native dense | primary |
| `K_control_75k` | `control-manuallabels-step075000.pth` | manual (the released recipe, retrained) | control |

- Inference: unchanged from the replication: `koine_machines.inference.infer`, `--overlap 0.5
  --blend-mode hann --batch-size 4 --no-compile`, the `D:/vw2` tree. 25 predictions. Driver:
  [`tools/run_other_recipes_threshold.py`](../tools/run_other_recipes_threshold.py).

A cell = (segment, checkpoint). Positive means `score >= threshold`, integers 0–255.

## Rules (identical to the docs/27 replication)

| rule | threshold |
|---|---|
| **R0** | 128 |
| **R1b** | median oracle threshold of the other two scrolls' cells, **same checkpoint**, rounded half up |
| **R2** | Otsu on this cell's sheet histogram (descriptive) |
| **R3** | the threshold marking the fraction *q* of this cell's sheet, *q* = median over the other two scrolls' cells (same checkpoint) of the sheet fraction at their oracle |

R1a (the withdrawn fixed value 87) is not run.

## Measure and decision

**Regret** = oracle F1 − F1 at the rule's threshold. Per scroll, mean over cells (PHerc0841 has three
segments, the other two one each). Noise floor 0.03 (docs/09).

- **Reading gate, applied first:** for each checkpoint × scroll, mean oracle F1 must beat the trivial
  all-ink F1 by ≥ 0.05. A pair that fails is reported as not reading and dropped from every rule alike.
- **Primary:** the four dense checkpoints pooled (PHerc0841 12 cells, 0009B 4, 0500P2 4).
- **Control:** `K_control_75k` alone (5 cells), compared with the released checkpoints in docs/27.
- Per checkpoint: descriptive.

| outcome (primary) | what it means for the tool |
|---|---|
| R1b < 0.03 on all three scrolls | the rule carries to a second label recipe; docs/27's "one recipe" limit is narrowed to "one architecture" |
| R1b ≥ 0.03 on one or more scrolls | the rule is recipe-specific; the tool's docs and #2012 say so |
| R0 < 0.03 on all three | 128 is also fine for dense checkpoints (as for the released ones) |
| R0 ≥ 0.03 on one or more | 128 is not safe for this recipe; borrowing is what a user of these checkpoints needs |

## What we already know (disclosed)

- On these scrolls the released checkpoints' optima were 98–141, R0 lost 0.006–0.027 and R1b 0.003–0.009
  (docs/27 replication).
- Reader v2's README reports AUC for `ink9um-dense` on PHerc0841 (0.769 against the team's 2.4 µm map,
  0.771 against human labels). AUC says nothing about where the optimum sits. No prediction of these
  checkpoints on these segments has been looked at.
- KLAVIS's card scores his checkpoints by balanced accuracy at 0.5, on the `ink_9um` validation masks.

## Prediction

1. R1b passes on all three scrolls (mean regret ≤ 0.02).
2. The dense checkpoints' optima sit lower than the released ones' (median below 110). Dense labels supervise
   much more background than manual labels, which lowers the ink prior the model learns.
3. Because of 2, R0 loses ≥ 0.03 on at least one scroll.
4. The control behaves like the released checkpoints: optimum within 98–141, R0 under 0.03 on all three.

## How it can go wrong

- A checkpoint expects a different depth order or window and does not read these inputs: the reading gate
  catches it, and it is reported, not tuned.
- The four primary checkpoints are not independent (three are one KLAVIS run family; Nieuwlaar starts from
  KLAVIS's dense model). "A second recipe" means one more label recipe, not four.
- One scroll each for PHerc0009B and 0500P2: a per-scroll mean there is one segment.

---

# Results (2026-10-09, run after commit a2a187c)

25 predictions, all completed (0.4–0.8 min each). Raw:
[`otherrecipes_summary.json`](../runs/ink9um_scorecard/otherrecipes_summary.json),
[`otherrecipes_cells.csv`](../runs/ink9um_scorecard/otherrecipes_cells.csv) (one row per cell),
[`otherrecipes_hists.npz`](../runs/ink9um_scorecard/otherrecipes_hists.npz) (every histogram),
[`otherrecipes_infer.log`](../runs/ink9um_scorecard/otherrecipes_infer.log).

**Reading gate: all 15 checkpoint × scroll pairs read** (oracle F1 above the all-ink F1 by 0.26–0.38
for the dense checkpoints, 0.22–0.31 for the control). Nothing was dropped.

## Primary: the four dense checkpoints (mean F1 lost against each cell's own optimum)

| rule | PHerc0841 (12 cells) | PHerc0009B (4) | PHerc0500P2 (4) | under 0.03 on all three |
|---|---|---|---|---|
| R0 = 128 | 0.003 | 0.001 | **0.062** | no |
| **R1b** borrow the value | 0.011 | 0.002 | **0.062** | **no** |
| R2 Otsu | 0.009 | 0.005 | 0.014 | yes |
| R3 borrow the quantile | 0.010 | 0.004 | 0.003 | yes |

Optima: PHerc0841 115–137, PHerc0009B 121–136, **PHerc0500P2 94–106**. R1b gave PHerc0500P2 123–133,
taken from the other two scrolls, and lost 0.047–0.071 on each of the four checkpoints. The worst R1b cell
elsewhere was 0.0296, just under the floor (PHerc0841 w00, `K_ex016_75k`).

## Control: KLAVIS's manual-label run (the released recipe, retrained)

| rule | PHerc0841 (3) | PHerc0009B (1) | PHerc0500P2 (1) |
|---|---|---|---|
| R0 = 128 | 0.014 | 0.002 | 0.032 |
| R1b | 0.003 | 0.002 | 0.012 |
| R2 | 0.002 | 0.001 | 0.005 |
| R3 | 0.016 | 0.007 | 0.005 |

Optima 95–120. R1b stays under the floor on all three, as it did for the released checkpoints.

## Predictions, scored

1. *R1b passes on all three (≤ 0.02).* **Failed:** 0.062 on PHerc0500P2.
2. *Dense optima below the released ones (median below 110).* **Failed:** they sit at or above the
   released ones on PHerc0841 and 0009B (median 126.5), and below only on PHerc0500P2.
3. *R0 loses ≥ 0.03 on at least one scroll.* Held (PHerc0500P2, 0.062), but not for the reason given in 2.
4. *The control behaves like the released checkpoints (optimum within 98–141, R0 under 0.03 everywhere).*
   **Failed narrowly:** one optimum is 95 and R0 loses 0.032 on PHerc0500P2.

## What it means

- **Borrowing a value is not safe for every recipe.** For the dense checkpoints, PHerc0500P2's optimum is
  about 25 grey levels below the other two scrolls', and taking the value from them costs twice the noise
  floor. On the same inputs, the released checkpoints and the manual-label control lost about 0.01 there
  (0.008 and 0.012). So docs/27's rule R1b passes for the manual-label recipe three times and fails once for a dense-label
  recipe.
- **Borrowing the quantile held.** R3 (take the fraction of the sheet the other scrolls' optima mark, and
  cut this prediction where it marks the same fraction) stayed under 0.03 on all three scrolls for both
  groups, here and in docs/27's replication. It was the secondary rule there; across the three tests it is
  the one that never failed.
- **The tool's own check catches this case.** `calibrate` with these three scrolls scores each one at the
  other two's value; for each dense checkpoint it prints a 0.05–0.07 loss on PHerc0500P2, so a user would see
  the problem before applying the value. It does not tell them what to use instead.

**Not tested, observed after the fact:** PHerc0500P2 is the one input on a different grid (8.86 µm,
listed as a known deviation before the run). Its optimum was also the lowest of the three for the released
checkpoints (median 107.5 vs 117), but the gap was about 10 grey levels, not 25. Whether the grid, the
scroll or the dense labels make the gap larger is not separated here.

## Follow-ups

- docs/27, `tools/borrow_threshold.py` and the README point here instead of saying "one recipe".
  `tools/borrow_threshold.py apply --rule quantile` already implements R3; villa #2012 implements only
  R1b, and this result belongs in its thread.

## Checks (added after the results, 2026-10-09)

Run because the result was a first failure for a rule that had passed twice. Script:
[`check_otherrecipes.py`](../tools/check_otherrecipes.py); outputs:
[`otherrecipes_checks.json`](../runs/ink9um_scorecard/otherrecipes_checks.json),
[`otherrecipes_villa_crosscheck.txt`](../runs/ink9um_scorecard/otherrecipes_villa_crosscheck.txt).

- **Scoring.** All 25 cells recounted pixel by pixel from the prediction TIFFs (F1 at the oracle, at 128
  and at the R1b threshold): largest difference from `otherrecipes_cells.csv` 4.9e-7. Villa #2012's
  `threshold calibrate`, an independent implementation, run per checkpoint: borrowed thresholds and both
  losses equal docs/29's for all 15 checkpoint × scroll pairs.
- **The checkpoints are the published ones.** The five converted files are tensor-for-tensor identical to
  their sources.
- **Positive control (the models run as their author ran them).** KLAVIS's card publishes balanced accuracy
  at 0.5 and AUC on the three `ink_9um` validation masks for `K_ex016_75k` and the control. The same
  converted checkpoints and inference path reproduce all six AUCs within 0.0007 (w016 exactly) and the
  balanced accuracies within 0.003; the small differences are on the two segments where his inputs were
  rebuilt by his own script. No published number on these inputs exists for Nieuwlaar's checkpoint; its
  check is weaker: sha256 equal to its `VERIFY.md`, and on these segments it reads at the level of KLAVIS's
  (oracle F1 0.72–0.74 on PHerc0009B and 0500P2).

| checkpoint | segment | AUC here / published | balanced accuracy at 0.5 here / published |
|---|---|---|---|
| `K_ex016_75k` | pherc0814-46527 | 0.9300 / 0.9298 | 0.8356 / 0.8329 |
| `K_ex016_75k` | pherc0139-w016 | 0.9070 / 0.9070 | 0.7495 / 0.7496 |
| `K_ex016_75k` | pherc1667-w029 | 0.8852 / 0.8853 | 0.7873 / 0.7882 |
| `K_control_75k` | pherc0139-w016 | 0.8707 / 0.8707 | 0.7016 / 0.7016 |
| `K_control_75k` | pherc0814-46527 | 0.8316 / 0.8323 | 0.7546 / 0.7539 |
| `K_control_75k` | pherc1667-w029 | 0.8946 / 0.8945 | 0.7800 / 0.7814 |

The PHerc0500P2 failure is therefore not a scoring or loading error. Its inputs and labels are the ones on
which the released checkpoints and the control lost about 0.01, so it is not a broken segment either.
