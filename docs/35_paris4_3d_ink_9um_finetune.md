# 35 — Can the Paris4 3D ink model be fine-tuned to read other scrolls at 9.6 µm? (pre-registered)

**Status: pre-registration**, committed before any fine-tuned model is run on a test segment. Results will be appended under a separate heading; nothing above it changes afterwards.

## Why

docs/34 ran the team's Paris4 3D ink model (`scrollprize/ink_paris4_3d_4.8um_gambiarra`) as released on held-out,
human-labelled segments of three other scrolls. It transferred partly: AUC 0.64–0.86 on four segments, with the
positive control at 0.91. It was below the 2.5D `ink_9um` model on three of four. On 2026-10-25 a maintainer said
in the project Discord that the model could probably be fine-tuned at 9 µm. Most scrolls that are still unread
have 9 µm scans only.

This document asks the next question. Start from the released 3D weights, fine-tune on human ink labels from the
four `ink_9um` training scrolls with 9.6 µm CT as input. Does the result read scrolls it never saw? Does it match
`ink_9um`, which learned from the same labels? Does the Paris4 3D starting point matter? The held-out labels and
segments are the same as in docs/27–34.

## Data

- **Model start:** the released `model.safetensors` (Hub revision `4c71198`, 98,016,588 bytes, sha256
  `a3986efb…`, as in docs/34). The network is the branch's student U-Net (`c9ca2dc52`). It is fully
  convolutional; the released model reads 64³ inputs at 4.8 µm.
- **Input here:** level 2 of each scroll's public 2.4 µm CT pyramid (9.6 µm voxels, uint8, 128³ chunks, no
  compressor; checked for all seven CTs below). A 64³ level-2 crop is normalised to [0, 1] by the p1/p99 of its
  128³ level-2 parent, the same 2× parent rule as the released preprocessing, and fed to the network without the
  2× pooling. The released model was never shown this scale.
- **Training labels:** the 24 `aligned-scrollprizeorg-21slices` segments of the `ink_9um` label set: PHerc0139 (9),
  PHerc1667 (6), PHercParis4 (8), PHerc0814 (1). The labels sit on the level-2 grid of each segment's 2.4 µm
  canvas, at Z = 10. Each segment has a tifxyz mesh on its scroll's 2.4 µm CT (`<id>-on-<ct>-2.399um` or
  `-2.4um`). CTs: PHerc0139 `20260102150214`, PHerc1667 `20251217075048`, PHercParis4 `20260411134726`, PHerc0814
  `20260309142202`. The five `native9` segments are not used (a different scan, no 2.4 µm CT).
- **Held out inside the training scrolls:** the `_validation_mask` regions of pherc0139-w016, pherc0814-46527 and
  pherc1667-w029 (the regions on which the released `ink_9um` checkpoints report validation). No training pixel
  lies within 64 level-2 px of them.
- **Training area cap:** sampling is balanced by scroll, so the area per scroll is capped. Each training segment's
  canvas is cut into 256 × 256 level-2 tiles. A tile is eligible if at least 10% of it is supervised and it is
  more than 64 px from a validation region. Tiles are drawn per scroll with seed 0, in round-robin over that
  scroll's segments, until the scroll reaches 3,000,000 supervised px, or until its tiles run out (PHerc0814 has
  0.27 M). The tiles are chosen from labels only.
- **Test segments:** as in docs/34, with their whole supervised area, not three windows.
  - Primary (judged): PHerc0841 w00, ag144, ag174 and PHerc0009B ag055.
  - Secondary (reported, not judged): PHerc0500P2 s1.
  - Labels: the `openlabels9` level-2 arrays.
- **What the test scrolls saw before:**
  - No ink labels from the test scrolls are used anywhere: not in the released 3D model (Paris4 clicks only),
    not in this fine-tune, and not in `ink_9um`.
  - The DINO backbone that taught the released model was self-supervised on CT from 11 scrolls. They include
    PHerc0009B and PHerc0500P2, but not PHerc0841. Its card names no label loss.
  - The student's unlabelled pool is Paris4 CT only.

## Arms

| Arm | Start | Fine-tune | Seeds |
|---|---|---|---|
| A0 | released weights | none (zero-shot at 9.6 µm) | — |
| A1 | released weights | yes | 0, 1 |
| A2 | random init (the branch's `build_network`, seed 27 + seed) | yes, same data and loss | 0, 1 |

**Fine-tune.**
- **Batch.** One update is 16 crops of 64³ level-2 voxels, in microbatches of 8, with bf16 autocast.
- **Optimiser.** AdamW, weight decay 0.01, gradient-norm clip 1.
  - A1 uses the authors' student-stage-2 rate: warmup 50, then constant 3e-5.
  - A2 uses their student-stage-1 rate: warmup 50, then 3e-4 cosine to 3e-5.
- **Crops.** Each crop is centred on a surface point of a supervised pixel, offset by up to ±16 voxels per axis.
  The scroll is drawn uniformly, then the segment by area, then the pixel with ink and non-ink equally likely.
- **Loss.** Class-balanced BCE between the 2D label and the band maximum of the 3D logits, on up to 512 supervised
  pixels per crop whose band lies at least 8 voxels inside the crop.
  - The band maximum is the maximum over t ∈ {−3, −2.5, …, +3} level-2 voxels along the mesh normal (±29 µm,
    the band of docs/34), read trilinearly.
  - This is the same operator the test uses.
- **Augmentation.** Flips and axis permutations, applied to the crop and the points together. Contrast and gamma
  changes as the student used.
- **Length.** The number of updates N is fixed by a 200-update smoke run of A1 before any other training: N =
  10,000 if 10,000 updates take at most 3 h, else 5,000. N and the measured rate are written in an addendum
  before any test inference. No checkpoint is selected; the last one is scored.

## Measurement

1. **Inference.** The network runs on 64³ level-2 crops on a global stride-32 grid around each test segment's
   band. Overlaps are blended with a Gaussian window (σ = 8 voxels) in float64. This is the branch's rule, here
   without pooling, written by us.
2. **Surface sampling.** The method is that of docs/34, at level 2. For each supervised level-2 label pixel
   (i, j), the point p and normal n come from the tifxyz at node (4i, 4j)·0.05. The canvas convention is fixed by
   the CT check below. The map value is the band maximum over t ∈ {−3, …, +3} in steps of 0.5. t = 0 and the band
   mean are secondary.
3. **Score.** AUC over each segment's supervised pixels, from a 256-bin histogram, checked against
   `roc_auc_score`.
4. **Baselines on the same pixels**, already computed in docs/33 (whole-segment AUC at zero shift):

   | Segment | ink_9um seed43 step-075000 | Reader V3 |
   |---|---|---|
   | 0841 w00 | 0.891 | 0.930 |
   | 0841 ag144 | 0.800 | 0.859 |
   | 0841 ag174 | 0.820 | 0.862 |
   | 0009B ag055 | 0.860 | 0.954 |
   | 0500P2 s1 | 0.857 | 0.919 |

   On docs/34's 18 windows, A1 is also compared with the released model at 4.8 µm (docs/34's numbers).

## Rules

- **Pipeline valid** only if both of these hold:
  - (a) Our inference loop, fed level 0 pooled by 2 as the branch does, reproduces the branch's `infer_volume`
    codes on one docs/34 positive-control window. At least 99% of voxels must be identical and none may differ by
    more than 1 code. That window's CT is still on disk.
  - (b) Both A1 seeds reach AUC ≥ 0.75 on the three held-out validation regions, pooled.

  If either fails, no test verdict is given.
- A1's AUC on a segment is the mean of its two seeds. Per-seed values and the seed gap are reported.
- **Reads held-out scrolls:** A1 AUC ≥ 0.80 on at least 3 of the 4 primary segments.
- **Does not:** A1 AUC ≤ 0.65 on at least 3 of 4.
- Otherwise **partial**.
- **Against ink_9um (secondary):** "competitive" if A1 ≥ ink_9um − 0.02 on at least 3 of 4; "better" if
  A1 ≥ ink_9um + 0.02 on at least 3 of 4.
- **Does the Paris4 3D start matter (secondary):** "yes" if A1 − A2 ≥ +0.02 on at least 3 of 4, and the sign is
  the same in both seed pairs (A1 s0 vs A2 s0, A1 s1 vs A2 s1) on those segments. "No" if |A1 − A2| < 0.02 on
  at least 3 of 4. Otherwise unclear.
- **Fine-tune vs zero-shot (reported):** A1 − A0 per segment.
- **Negative control (reported):** A1's map scored against labels shifted by half the segment's height along the
  rows, wrapped. Expected near 0.5.

**Predictions (written before running).**
- A0 is weak, AUC 0.55–0.70: the network has never seen 9.6 µm voxels.
- The pipeline is valid.
- A1 is partial, leaning towards reading: around 0.75–0.85.
- A1 is not competitive with ink_9um on at least 2 of 4. ink_9um learned from all 124 M supervised px of these
  aligned labels, plus the native9 set, for 75,000 steps; A1 sees at most 9.3 M px for at most 10,000.
- The Paris4 start matters (A1 > A2).
- On ag144, the 3D model is again at least level with ink_9um. That is where docs/33 found every 2D model shifted
  4–8 px from the labels.

## Method checks, before training

1. **CT alignment at level 2.** For each training and test segment, the CT is sampled at level 2 along the mesh
   with each canvas convention. The result is phase-correlated with the middle layer of the segment's 9.6 µm
   surface volume (`aligned9` / `openlabels9`). The convention with |d| ≤ 1 px on both axes is used. A segment
   that fails is dropped and named. A training scroll that loses more than half its segments stops the run.
2. **Labels.** The level-2 labels read for the test segments are identical to `openlabels9`. The training tiles
   contain no validation-region pixel.
3. **Pyramid (reported).** For one chunk per scroll, level 2 is compared with the mean of the 4 × 4 × 4 level-0
   blocks. We report whether the pyramid is a mean; the run does not depend on it.
4. **Inference loop.** Rule (a) above.

## Cost and data

- **Measured from the test meshes:** the test segments' supervised area needs 2,517 level-2 CT chunks (4.9 GiB)
  for crops and their parents.
- **Estimated by area:** training needs about 0.53 GiB per million supervised px, so about 5 GiB for 9.3 M px.
- **Training meshes:** about 1.3 GB.
- **Total:** about 11 GB, read with HTTP Range requests and kept only for the run. If the computed chunk list
  exceeds 25 GiB, the download stops and the user is asked first.
- **GPU:** four fine-tunes of at most 3 h each, plus five whole-segment inferences per test segment, on one
  RTX 5090.
- **Environment:** the branch package as in docs/34, in villa's ink-detection environment (Python 3.12).

## Limits

- The 9.6 µm input is the 2.4 µm scan's pyramid, not a native 9 µm scan. A native scan differs in blur and noise.
  So a pass here shows that the model reads coarse voxels of the same scan. It does not show that it reads
  native 9 µm scrolls.
- Four primary segments on two scrolls, as in docs/34. The training labels are about 7% of what `ink_9um` used,
  and there are four training scrolls. The comparison with `ink_9um` is therefore against a model trained on far
  more of the same labels.
- The loss and the band maximum are our choices, not the authors'. The authors trained on 3D clicks with teacher
  distillation.
- Two seeds per arm.

## Credits

- The 3D model, its code, the DINO backbone and the 2.4 µm volumes are the Vesuvius Challenge team's. The branch
  commit is by erdpx; the remark about fine-tuning at 9 µm was made in the project Discord.
- The ink labels (`ink_9um`, `openlabels9` sources) and `ink_9um` are the team's.
- Reader V3 is KLAVIS's (Domenico Russo).

AI disclosure: the design, code, runs and this text were produced by Claude (Anthropic) via Claude Code, directed
by Hyojun Kwon (khj1222), who chose the problem, the data and the decisions.

---

## Addendum before training (2026-10-30, written before any fine-tune or test-segment inference)

- **Length: N = 10,000.** The 200-update smoke run of A1 seed 0 ran at 0.19 s per update after the first 20
  (10,000 updates ≈ 32 min ≤ 3 h). Its loss fell from 1.13 to 0.57. The smoke weights are not used.
- **Training tiles** (seed 0, labels only): PHerc0139 91 tiles / 3.02 M supervised px, PHerc1667 78 / 3.01 M,
  PHercParis4 73 / 3.05 M, PHerc0814 8 / 0.33 M; 9.41 M px in all. No tile holds a validation-region pixel.
- **Method checks.**
  - CT alignment: all 29 segments (24 training, 5 test) pass under convention A, with |d| ≤ 0.15 px on both axes;
    convention B is off by about 2.5 px.
  - Labels: the five test label sets equal `openlabels9`.
  - Pyramid: level 2 equals the 4×4×4 mean of level 0 to within 1 grey level, mean absolute difference 0.26, on
    all seven CTs. It is a mean, not a stride.
  - Rule (a) passes. Our loop with pooling, on the docs/34 control window, matches the branch's `infer_volume`
    codes at 200,000 sampled voxels: 100% identical, maximum difference 0.
- **Data.** 11,425 level-2 chunks, 22.3 GiB, against about 11 GB estimated. The estimate counted ±64 voxels around
  each surface point. A crop's 128³ parent reaches ±92 voxels around a training point and ±108 around a scored
  point. That is within the 25 GiB stop rule. 75 chunks are absent on the bucket (outside the scroll mask) and
  read as zeros.
- **Two code corrections, made before any validation or test inference.**
  - The validation regions are disjoint from the supervision masks. The released pipeline uses the validation mask
    in place of the supervision mask (koine_machines `supervision_mask_override`). The validation AUC is therefore
    computed over every validation-mask pixel, with the ink labels. Our first code took supervised ∩ validation,
    which is empty.
  - A JSON-writing bug was fixed.
- **Inference implementation.**
  - Our loop computes blended logits only at the voxels the band samples read. It covers all crops of the global
    grid that contain one of them, in lexicographic order, with float64 accumulators.
  - On synthetic volumes, a dense brute-force blend over every crop agrees with it to 3 × 10⁻¹⁶ (pooled and
    unpooled).

Nothing else changes.

---

## Results (2026-10-30, run after `80411bb` and the addendum `8fc17c5`)

**Verdict: pipeline failure under rule (b), so no test verdict.** Rule (a) passed. Rule (b) failed: the two A1
seeds reach only 0.572 and 0.602 AUC on the pooled validation regions, against the 0.75 required. Everything below
is reported as measured, but the judged rules give no verdict on "reads held-out scrolls".

**Whole-segment AUC (band maximum).** The A1 and A2 columns are means of two seeds.

| Segment | A0 (zero-shot) | A1 s0 / s1 | A1 | A2 s0 / s1 | A2 | ink_9um s43 | Reader V3 |
|---|---|---|---|---|---|---|---|
| 0841 w00 | 0.715 | 0.731 / 0.714 | 0.722 | 0.622 / 0.645 | 0.633 | 0.891 | 0.930 |
| 0841 ag144 | 0.783 | 0.757 / 0.741 | 0.749 | 0.676 / 0.678 | 0.677 | 0.800 | 0.859 |
| 0841 ag174 | 0.664 | 0.697 / 0.685 | 0.691 | 0.603 / 0.610 | 0.607 | 0.820 | 0.862 |
| 0009B ag055 | 0.688 | 0.648 / 0.614 | 0.631 | 0.651 / 0.668 | 0.660 | 0.860 | 0.954 |
| 0500P2 s1 (secondary) | 0.604 | 0.680 / 0.683 | 0.682 | 0.583 / 0.606 | 0.595 | 0.857 | 0.919 |
| Validation regions, pooled | 0.502 | 0.572 / 0.602 | — | 0.534 / 0.517 | — | 0.913 (post hoc) | — |

What the measurements say, with the caveat that the run is invalid by its own rule:
- **Not competitive with ink_9um.** A1 is below ink_9um by 0.05 to 0.23 on all four primary segments.
- **Fine-tuning barely moved the test numbers.** A1 − A0 is −0.057 to +0.027. The released model read 9.6 µm CT
  zero-shot about as well as after 10,000 fine-tuning updates: 0.66–0.78 against a predicted 0.55–0.70.
- **The Paris4 start matters** (secondary rule: "yes"). A1 − A2 is +0.073 to +0.089 on the three PHerc0841
  segments, with the same sign in both seed pairs. On 0009B ag055 it is −0.029.
- **The band maximum beats t = 0 on three of four** primary segments for both A1 seeds, by 0.005 to 0.021. On
  0009B ag055, t = 0 is higher, by 0.010 to 0.017. In docs/34 the band maximum won on every segment.
- **The negative control is weak at segment scale.** Rolling the labels by half the segment height gives 0.38–0.65
  where both classes remain. On ag174 and ag055 it is undefined: no ink falls on supervised pixels after the roll,
  because the labels sit in one half. A window-scale roll, as in docs/34, would have been the better null.

**Predictions:** two of six right.
- ✗ A0 weak at 0.55–0.70. It was 0.66–0.78; two of four were above the range.
- ✗ The pipeline is valid. It failed rule (b).
- ✗ A1 partial, around 0.75–0.85. It was 0.63–0.75, and gets no verdict.
- ✔ Not competitive with ink_9um on at least 2 of 4. It is below on 4 of 4.
- ✔ The Paris4 start matters.
- ✗ ag144 at least level with ink_9um. A1 is 0.749 against 0.800, and A0 0.783.

**Checks after the run (not pre-registered).**
- **The validation scoring is right.** ink_9um seed43 on the same validation-mask pixels (`aligned9` input) gives
  AUC 0.937 / 0.863 / 0.930, pooled 0.913. So the labels, masks and AUC code are sound; the 3D model is weak there.
- **The fine-tune fits, but loosely.** Two training tiles and two unused eligible tiles were drawn per training
  segment of PHerc0139, PHerc1667 and Paris4 (seed 7). The scores below are for A1 seed 0; the other two arms are
  given for comparison.

  | Arm | Training tiles | Unused tiles | Validation regions |
  |---|---|---|---|
  | A1 seed 0 | 0.839 | 0.757 | 0.572 |
  | A0 | 0.658 | 0.697 | 0.502 |
  | A2 seed 0 | 0.723 | 0.683 | — |
  | ink_9um, for contrast | 0.9996–0.9998 (training px) | — | 0.913 |

  Within the training scrolls, A1 is 0.18 lower on the validation regions than on unused tiles. We did not find
  why.
- **AUC recheck.** The rank AUC equals `sklearn.metrics.roc_auc_score` to 6 decimals on 15 arm × segment
  checks.
- **Reading.**
  - The CT reads were complete: no lazy fetches, and coverage 1.000 on every scored pixel.
  - On docs/34's 18 windows, A0 at 9.6 µm scores 0.53 / 0.82 / 0.61 / 0.83. The released model at 4.8 µm scored
    0.66 / 0.86 / 0.64 / 0.73 there: means 0.70 against 0.72, per segment −0.13 to +0.10.

**What it means.**
- A short fine-tune of the 3D model, at 9.6 µm on four scrolls' labels with a band-maximum loss, does not produce
  a model that passes our in-distribution check. It does not approach ink_9um on held-out scrolls.
- The run cannot say whether longer training, the full label set, the authors' own distillation recipe, or a
  native 9 µm scan would change this. ink_9um's memorised training pixels (AUC ≈ 1.0) and its 0.91 on the
  validation regions show how far apart the two recipes are in training budget.
- The positive findings are narrow. On average the released 3D model reads 9.6 µm CT zero-shot about as well as
  4.8 µm on these windows (per segment the two differ by up to 0.13), and its Paris4 weights are a better start than random init.

Evidence: `runs/paris4_3d9/` (`summary.json`, `method_check.json`, `pyramid_check.json`, `loopcheck.json`,
`tiles.json`, `chunks.json`, `posthoc_checks.json`, `diag_insample.json`, `train/*/COMPLETE.json` and
`curve.jsonl`; the synthetic loop test `selftest_sparse.py` and the diagnostic `diag_insample.py`). Code:
`tools/paris4_3d_9um_finetune.py`. The fine-tuned weights are not released.
