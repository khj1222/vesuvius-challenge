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
