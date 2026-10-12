# 31 — Wider depth jitter for surface offsets of 3–5 slices (pre-registered)

**Status: pre-registration, committed before any fine-tuned checkpoint below exists.** Results will be
appended under a separate heading; nothing above it changes afterwards.

## Why

docs/30 found the released `ink_9um` recipe already tolerant of surface errors within ±2 slices (≈ ±19 µm):
a smooth wander of that size costs 0.009–0.019 F1, and an in-patch wander augmentation bought nothing. It
also named where the problem probably lives: larger offsets, which the 21-slice renders cannot hold for
training or for testing.

The published 2.4 µm surface volumes have 109 planes (PHerc0500P2: 118). The recipe pools the central 84
into 21 slices; pooling the central 108 gives 27 slices, with the old 21 at positions 3–23. That leaves room
to move the model's 17-slice window by ±5 slices (≈ ±48 µm) on real layers. The wide volumes are built
([`tools/prepare_wide_volumes.py`](../tools/prepare_wide_volumes.py)) and checked: slices 3–23 equal the
existing volumes byte for byte in 28 of 29 (report
[`wide_report.json`](../runs/segrobust/wide_report.json); the one exception, PHerc0139 w016, differs only in
an edge band where the old volume is 0 and the new one has data). The labels are widened the same way, the
old 21 channels copied to 3–23 and zeros in the six new ones
([`tools/prepare_wide_labels.py`](../tools/prepare_wide_labels.py), read back and compared: 0 differing
voxels, [`wide_labels_report.json`](../runs/segrobust/wide_labels_report.json)).

## Question

Fine-tuning a released checkpoint with the recipe's whole-window depth jitter widened from ±2 to ±5 slices,
against the same fine-tune at ±2: on scrolls neither saw, does F1 hold up better when the surface is off by
3–5 slices, and stay the same when it is not?

## Design (fixed now)

- **Data.** Both arms train on the 27-slice volumes and labels. The five native 9.36 µm PHerc0139
  representations of the recipe are dropped from both: they come from a 9 µm volume, which has no wider
  2.4 µm source to pool. The same five physical segments stay in the corpus through their aligned 2.4 µm
  representations. 24 representations, the recipe's per-scroll batch quotas unchanged (0139 29, 1667 22,
  Paris4 11, 0814 2).
- **Arms.** `control`: `flat_z_window_jitter.max_offset` 2, which on the wider volumes draws exactly the
  recipe's window positions (the loader centres the window, then shifts it). `jitter5`: `max_offset` 5.
  Nothing else differs. Configs `configs/ink9um_widejitter_{control,jitter5}_s{42,43}.json`, made from the
  docs/30 control configs by [`tools/run_widejitter.py`](../tools/run_widejitter.py) `configs`.
- **Training.** As docs/30: start from the released checkpoint of the same seed (`hybrid_3d2d-seed42/43`,
  `step-075000`, weights only), 10,000 steps, SGD lr 0.01, 1,000 warm-up steps, cosine decay, batch 64,
  6 data-loader workers, seeds 42 and 43. Four runs. The final step is evaluated; no checkpoint is chosen.
- **Test segments.** The docs/27 replication's five, as in docs/30: PHerc0841 w00, ag144, ag174; PHerc0009B
  ag055; PHerc0500P2 s1. None of these scrolls is in the training corpus.
- **Test renders (17 per segment), built from the 27-slice open-label volumes.** `clean`; whole-surface
  shifts of ±1, ±2, ±3, ±4, ±5 slices; smooth wander with peak 3 and peak 5 slices, three fields each (the
  docs/30 generator and field seeds 101–103, correlation ≈ 200 px). Linear interpolation along depth; the
  model's centred 17-slice window never reaches past the real layers for any of these.
- **Models scored.** The two released starting points and the four fine-tunes, on all 85 renders, with the
  inference command and flags of docs/27–30 (the model reads the centred 17 slices of the 27).
- **Measure.** Best F1 (oracle threshold) inside the published `supervision` mask, per render; AUC alongside.

## Decision (fixed now)

Per seed and per scroll, take the mean best F1 over a set of renders; the **contrast** is `jitter5` minus
`control` (same seed). PHerc0841's three segments are averaged first. **Large** = shifts ±3, ±4, ±5 and the
three peak-5 wander renders (9 renders).

| endpoint | renders | passes if |
|---|---|---|
| **P1 large-offset robustness** | large | contrast ≥ +0.015 averaged over the three scrolls in **both** seeds, positive on ≥ 2 of 3 scrolls in both seeds, and larger than the control arm's own seed-to-seed difference on the same set |
| **P2 no clean cost** | `clean` | contrast ≥ −0.01 averaged over the three scrolls in both seeds |

The study **succeeds** if P1 and P2 both pass. The rules are coded in `run_widejitter.py score`.

Secondary, descriptive: the small set (±1, ±2, peak-3 wander); F1 against shift for every model, including
how much the released checkpoints lose at 3–5 slices; AUC; per-segment tables.

| outcome | what happens |
|---|---|
| P1 and P2 pass | release the `jitter5` checkpoints and the two preparation tools; propose the wider render and jitter for villa main's `vesuvius.ink_detection` |
| P1 fails | report as tested and not effective; nothing is released |
| P1 passes, P2 fails | report the trade-off; nothing is released as a default |

## What we already know (disclosed)

- docs/30's results, on the same five segments: released and fine-tuned models lose 0.009–0.019 F1 to a
  peak-2 wander, and shifting the surface one way costs about 0.02 while the other way gains a little.
- How the released checkpoints do beyond ±2 slices has not been measured on any segment.
- Before this commit, three checks, none of which evaluated a model:
  - building each arm's training set as the trainer does and drawing 200 samples: offsets −2…+2 in
    `control`, −5…+5 in `jitter5`, every crop 17 slices
    ([`widejitter_active_check.json`](../runs/segrobust/widejitter_active_check.json)). The loader places the
    window at `27 // 2 − 17 // 2` = slice 5 before shifting it, the same layers as the recipe's on 21 slices,
    and finds patches on channel `27 // 2` = 13, the annotation channel;
  - a 200-step smoke run of `jitter5` seed 42 completed (7.5 min);
  - its patch counts per representation equal the docs/30 run's for all 24 representations.

## Prediction

The released checkpoints and the `control` fine-tunes lose clearly more at ±4–5 slices than at ±2 (at
least 0.05 F1 at ±5, averaged over shift direction). P1 passes: contrast +0.03 to +0.08 on the large set.
P2 passes, with a small cost (clean contrast between −0.01 and 0). On the small set the arms differ by
less than 0.01.

## How it can go wrong

- Synthetic offsets again. A real tracing error can switch sheets or fold; a whole-surface shift or a smooth
  wander of up to 5 slices does neither. A pass says the model tolerates larger smooth depth errors, not that
  it repairs bad segmentation.
- A window shifted 5 slices still contains the ink layer (the 17-slice window reaches 8 slices either side of
  its centre), so this tests a model finding ink away from the centre of its input, not ink outside it.
- Dropping the native representations changes both arms' corpus relative to the released recipe; the
  contrast is between arms trained the same way, so it does not depend on that, but the `control` arm is not
  the released recipe.
- Five segments on three scrolls, one starting checkpoint per seed; the seed rule in P1 is the only noise
  control.
