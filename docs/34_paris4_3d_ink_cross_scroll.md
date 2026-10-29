# 34 — Does the Paris4 3D ink model read other scrolls? (pre-registered)

**Status: DRAFT pre-registration, not yet committed.** Once committed, it is committed before the 3D model is run
on any test segment. Results will be appended under a separate heading; nothing above it changes afterwards.

## Why

The team released a 3D ink model on 2026-10-20: `scrollprize/ink_paris4_3d_4.8um_gambiarra`, MIT, villa branch
`ink-paris4-3d-gambiarra` at `c9ca2dc52`. It is a residual 3D U-Net that reads 2.4 µm CT, pools it to 4.8 µm, and
predicts an ink logit per voxel. It was trained only on click labels in PHercParis4. On 2026-10-25 a maintainer
said in the project Discord that it had not been run on other scrolls, and that it could probably be fine-tuned
at 9 µm. 3D ink conditioned on the surface is one of the two directions the team named that day.

This document asks the first question that suggestion raises: run as released on scrolls it never saw, does it
find ink where people labelled ink? We use the same held-out human labels as docs/27–33.

## Data

- **Test segments (primary, judged):** PHerc0841 w00, ag144, ag174 (CT `20260319124803`, 2.403 µm, 77 keV), and
  PHerc0009B ag055 (`20250919125754…`, CT `20250820154339`, 2.401 µm, 77 keV). Each has open human ink labels on
  its 2.4 µm segment canvas (label set `20260918`) and a tifxyz mesh on that CT (scale 0.05, i.e. 20 canvas px per
  node).
- **Secondary (reported, not judged):** PHerc0500P2 s1 (`20250825181859--1`). Its CT is 2.215 µm, 8% finer than
  what the model was trained on. It is fed as is.
- **Positive control:** a PHercParis4 segment with open human labels on the CT the model was trained on
  (`20260411134726`, 2.4 µm). It is the first of the eight listed in the open-data metadata that has a tifxyz on
  that CT (`20230702185753`, or the next one). The model's training clicks may lie on this segment. That is the
  point: it shows the pipeline below can recover ink where the model is known to work.
- **Windows:** the label canvas at level 2 (9.6 µm px, the `openlabels9` grid), cut into non-overlapping
  256 × 256 tiles. Per segment we take the three tiles with the most supervised pixels, among tiles where ink and
  non-ink are each at least 10% of supervised pixels. Ties go to the lowest row, then column. Windows are chosen
  from labels only.

## Measurement

1. **3D inference.** The released `model.safetensors` (Hub revision `4c71198`, 98,016,588 bytes, sha256
   `a3986efb…`) runs through the branch's own
   `infer_volume` with `--ct` set to the scroll's level-0 array and `--box` set to the 4.8 µm bounding box of each
   window's surface, padded by 32 output voxels. Settings are otherwise the defaults (64³ crops, 50% overlap,
   Gaussian blend).
2. **Surface sampling.** For each level-2 label pixel (i, j), the 3D point p is the bilinear interpolation of the
   tifxyz x/y/z at the node coordinate of canvas pixel (4i, 4j). The normal n comes from the grid's two tangent
   derivatives. The map value is the **maximum decoded logit over offsets t ∈ {−12, …, +12} level-0 voxels along n**
   (±29 µm), read trilinearly from the 4.8 µm grid (level-0 q = 2·q₁ + 0.5). The maximum over a symmetric band
   removes the sign of the normal and small mesh-height errors. The value at t = 0 and the band mean are reported
   as secondary.
3. **Canvas convention, fixed before any ink is sampled.** Whether canvas pixel u maps to node u·0.05 or
   (u + 0.5)·0.05 − 0.5 is decided per segment by sampling the CT itself (not the model) along the mesh. That CT
   image is phase-correlated with the middle layer of the segment's published 2.4 µm surface volume (as in our
   2026-10-29 canvas check). The convention with |d| ≤ 1 px on both axes is used. If neither gets there, the
   segment is reported as "mapping failed" and not judged.
4. **Score.** AUC over supervised pixels of the three windows pooled, per segment, using the level-2 labels
   (`openlabels9`). The baselines are scored on the same windows from existing predictions (docs/33):
   ink_9um seed43 step-075000 (reference) and Reader V3.

## Rules

- **Pipeline valid** only if the positive control gives AUC ≥ 0.80. If it does not, no test verdict is given.
  The result is "pipeline or protocol failure", with whatever was learned.
- **Transfers:** AUC ≥ 0.70 on at least 3 of the 4 primary segments.
- **Does not transfer:** AUC ≤ 0.60 on at least 3 of the 4.
- Otherwise **partial**.
- **Against ink_9um (secondary):** "competitive" if 3D AUC ≥ ink_9um AUC − 0.02 on at least 3 of 4; "better" if
  it is at least +0.02 on at least 3 of 4.
- **Negative control (reported):** the same 3D map scored against labels displaced by half a window (128 px) along
  the rows, wrapped inside the window. Expected near 0.5.

**Predictions (written before running).** The positive control passes. Transfer is partial, leaning towards not
transferring. A community member running 3D ink on other scrolls wrote on 2026-10-29 that it so far works only on
Paris4, though it is not clear that this was this model. PHerc0841's scan protocol (2.403 µm, 77 keV) is close to Paris4's (2.400 µm,
78 keV), so if anything transfers it is PHerc0841. Not competitive with ink_9um, whose AUC on these windows will be
around 0.80–0.89.

## Method checks, before the test segments

1. The level-2 labels read for the windows equal `openlabels9` (identical arrays).
2. On the positive-control segment, the CT-alignment step (Measurement 3) passes.
3. The branch's inference reproduces itself: one positive-control unit run twice gives the same codes.
   The model card warns that a crop's logits can depend on the batch slot; any difference is reported.

## Cost and data

Every CT is uncompressed zarr with 128³ chunks, read with HTTP Range requests and cached only for the run. That is
about 1–2 GB per window, about 25 GB for 18 windows. Nothing is kept except the small 3D outputs of the windows
and the scores. The model is a 98 MB download. The branch asks for Python 3.14. If it does not run on this
machine as is, the student network is loaded with the branch's own `student.load_weights` in another environment.
That is recorded, and the rules do not change.

## Limits

- Four primary segments on two scrolls, three windows each. This is a first look, not a benchmark.
- The model is applied as released, with no fine-tuning. A negative result says nothing about a 9 µm or
  fine-tuned version.
- Surface sampling (band maximum along the normal) is our choice, not the model authors'. Their own use is
  full-volume inference.

## Credits

The 3D model, its training code and the 2.4 µm volumes are the Vesuvius Challenge team's (the branch commit is by
erdpx). The open human ink labels are the team's. ink_9um is the team's; Reader V3 is KLAVIS's
(Domenico Russo).

AI disclosure: the design, code, runs and this text were produced by Claude (Anthropic) via Claude Code, directed
by Hyojun Kwon (khj1222), who chose the problem, the data and the decisions.
