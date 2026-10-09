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
