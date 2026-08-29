# A scorecard for the released ink_9um checkpoints (2026-08-22)

Step 1 of the September track: the **first quantitative scoring** of the public
`scrollprize/ink_9um` models (hybrid_3d2d, seeds 42 and 43 x 7 steps) on the
three segments that ship an official validation mask. The model card carries no
performance numbers at all — this table is the first.

> Read together with [docs/17](17_holdout_audit.md), which audits those three
> official masks and finds that a large share of their held-out pixels sit
> within one training patch of pixels the model trained on. The honest ceiling
> below is therefore an optimistic reading, not a conservative one.

## Method

- Input: the public 2.399 um surface volumes, pooled to ~9.6 um in 21 slices by
  villa's `scripts/prepare_9um_isotropic_input.py` (level-2 XY plus a 4x mean in
  z). It **streams straight from the S3 URLs**, so the 2.4 um originals (tens of
  GB per segment) never have to be downloaded — only the 1-2 GB output per
  segment.
- Inference: villa `koine_machines.inference.infer` with
  `--overlap 0.5 --blend-mode hann` (the contract stated in the README) and
  `--no-compile` (Windows/Triton).
- Scoring: `tools/eval_validation.py` — July's harness — run twice:
  - over the `_validation_mask` regions = **held**, the pixels excluded from the
    public training, i.e. the honest number;
  - with `--region-kind supervision_mask` = **train**, the pixels the model
    trained on.
  - Same prediction image and same threshold sweep both times, so the difference
    between the two is the **memorisation gap**.
- 42 inference runs (14 checkpoints x 3 segments, ~1-2.5 min each) and 84
  scorings. Raw numbers in `runs/ink9um_scorecard/scorecard.csv`, summary in
  `summary.json`.

## Results (best F1, each at its own optimal threshold)

| segment | seed | | 10k | 20k | 30k | 40k | 50k | 60k | 75k |
|---|---|---|---|---|---|---|---|---|---|
| 0139-w016 | 42 | held | 0.673 | **0.743** | 0.577 | 0.630 | 0.575 | 0.574 | 0.531 |
| | | train | 0.725 | 0.895 | 0.946 | 0.962 | 0.972 | 0.981 | 0.984 |
| 0139-w016 | 43 | held | 0.654 | 0.741 | 0.637 | 0.713 | 0.709 | 0.732 | **0.755** |
| | | train | 0.710 | 0.833 | 0.929 | 0.957 | 0.969 | 0.977 | 0.985 |
| 0814-46527 | 42 | held | **0.765** | 0.761 | 0.711 | 0.734 | 0.760 | 0.752 | 0.753 |
| | | train | 0.870 | 0.933 | 0.962 | 0.968 | 0.981 | 0.987 | 0.989 |
| 0814-46527 | 43 | held | **0.762** | 0.752 | 0.750 | 0.750 | 0.759 | 0.755 | 0.740 |
| | | train | 0.840 | 0.928 | 0.953 | 0.971 | 0.977 | 0.983 | 0.988 |
| 1667-w029 | 42 | held | 0.606 | 0.672 | **0.716** | 0.675 | 0.678 | 0.677 | 0.658 |
| | | train | 0.720 | 0.873 | 0.937 | 0.960 | 0.973 | 0.982 | 0.986 |
| 1667-w029 | 43 | held | 0.612 | 0.730 | 0.755 | 0.743 | 0.741 | 0.755 | **0.758** |
| | | train | 0.683 | 0.850 | 0.921 | 0.954 | 0.963 | 0.976 | 0.983 |

## What it says

1. **The honest ceiling is F1 ~0.74-0.77.** Across every segment, seed and step,
   the best held-out values are 0.765 (0814 / s42 / 10k), 0.758 (w029 / s43 /
   75k) and 0.755 (w016 / s43 / 75k). The same checkpoints reach 0.98+ on
   training pixels — a **memorisation gap of 0.22 to 0.45 at the final step**.
2. **No step is best everywhere.** The best held-out step per (segment, seed) is
   20k / 75k / 10k / 10k / 30k / 75k. The model card's "try a few steps" is
   confirmed by measurement — and the choice is worth up to 0.21 F1
   (w016 / s42: 20k 0.743 against 75k 0.531).
3. **The seed matters as much as the step.** On the same recipe and the same
   data, w016 at 75k gives s42 = 0.531 against s43 = 0.755 — a **0.22 gap
   between seeds**. The curves are not merely offset: s42 collapses late while
   s43 peaks late. Picking a step from a single seed's trajectory is a lottery.
4. **All 6 training curves rise monotonically** to 0.98+. That training
   memorises the annotated pixels is not in doubt; what does not follow is the
   held-out score.
5. 0814 is stable on held-out (0.71-0.77; a small segment with a single
   validation region) while w016 and w029 swing — so how a segment's validation
   regions are composed accounts for much of the variance, which is the same
   conclusion July's fold analysis reached.

## Traps worth recording

- `prepare_9um_isotropic_input.py` dies on Windows at the final rename
  (`.partial` to the final name) with a `PermissionError`: a directory rename
  with open handles. **If the tile log says `tiles=N/N` the data is complete** —
  only the rename needs doing by hand, and the driver does it.
- S3 streaming at 24 connections (3 parallel x 8 workers) throws
  `ServerDisconnectedError` often. Run the retry pass at 2 x 6 with three
  attempts.
- The ink_9um aligned label zarrs are **a single level, not a pyramid** (only
  `0`). `eval_validation.py`'s region search assumed level 3 and failed; it now
  falls back to the deepest level present. (The native9 labels have six levels,
  so they take the original path.)

## The Paris4 reference arm (2026-08-22, w00 and w02 x 14 checkpoints)

Paris4 ships no validation mask, so only training pixels (the whole supervision)
can be scored. This becomes the "model that **did** see Paris4" axis of the LOSO
comparison.

| segment | seed | 10k | 20k | 30k | 40k | 50k | 60k | 75k |
|---|---|---|---|---|---|---|---|---|
| w00 | 42 | 0.790 | 0.854 | 0.877 | 0.892 | 0.902 | 0.910 | 0.918 |
| w00 | 43 | 0.778 | 0.848 | 0.875 | 0.891 | 0.903 | 0.909 | 0.915 |
| w02 | 42 | 0.762 | 0.846 | 0.859 | 0.878 | 0.893 | 0.903 | 0.916 |
| w02 | 43 | 0.754 | 0.823 | 0.860 | 0.881 | 0.889 | 0.902 | 0.911 |

Observation: **even on training pixels Paris4 stops at 0.91-0.92**, where other
scrolls reach 0.98+. The four curves nearly coincide across seeds (differences
below 0.012) and rise monotonically. A batch quota of 11/64 and segments three
to four times the area of others give Paris4 low per-pixel exposure, and its
transferred aligned labels are probably noisier as well. That Paris4 is not even
fully memorised has to be kept in mind when reading the LOSO gap — the reference
ceiling is itself only 0.92.

## Next (in progress at the time of writing)

- **LOSO arm**: `configs/ink9um_loso_noParis4_s42.json` — the official recipe
  with only Paris4's eight representations removed (quota renormalised to
  {0139: 35, 1667: 27, 0814: 2}), 78,125 iterations. After training, the whole
  supervision of all eight Paris4 segments becomes honest held-out, giving a
  same-pixel comparison between a model that saw the scroll and one that did
  not — the first systematic numbers for open problem #7, cross-scroll
  generalization. That study is [docs/15](15_loso_cross_scroll.md).

---

MIT-licensed.
