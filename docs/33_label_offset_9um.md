# 33 — Do 9 µm models learn the ~7 px offset in labels moved from 2.4 µm maps? (pre-registered)

**Status: DRAFT pre-registration, not yet committed.** Once committed, it is committed before any Stage 1
measurement below is run. Results will be appended under a separate heading; nothing above it changes
afterwards.

## Why

villa #2243 (evilaliv3) reports that a mesh regridded from a 9.362 µm scan to a finer one puts node j at source
parameter (j + 0.5)/k − 0.5 instead of j/k. A map drawn on the finer segment's canvas and resized by area onto the
9 µm canvas therefore lands g = 10(1 − 1/k) px off on both axes (k ≈ 3.89, g ≈ 7.4 px ≈ 70 µm). Labels made that
way include KLAVIS's Reader v2 labels (70 native segments, `domenicor046/reader-v2-labels`: "the team's ink map …
resampled onto the native surface volume's canvas"), which Reader v2 and Reader V3 were trained on.

We checked the canvas offset itself before writing this (rules fixed locally before any pixel was read,
2026-10-29). Each segment's < 3 µm surface volume was resized by area onto its 9 µm canvas and phase-correlated
against the 9 µm surface volume. 6 of 7 judged segments sit at +7.0 to +8.1 px on both axes against a predicted
7.2 to 7.6 (PHerc0139, 0500P2, 0009B, 0343P). The seventh, a PHerc0009B segment, was off on one axis (4.5 px).
That replicates #2243 on the canvases. It says nothing about models.

The open question is whether it matters. A convolutional model trained on labels that sit 7 px from the ink
evidence can learn to draw ink 7 px away from it. If it does, its maps are displaced on every scroll. Shifting the
output back would then be a free fix, and retraining on corrected labels a better one. If it does not (the labels
are blobby and a 9 µm model's maps are smooth), the offset is harmless and should be said so. Nobody has
published either.

## Stage 1 — is a learned shift visible in existing models? (no training)

**Data.** The five open-label segments used since docs/27: PHerc0841 w00, ag144, ag174, PHerc0009B ag055 and
PHerc0500P2 s1. Inputs are the level-2 renders of each segment's 2.4 µm surface volume (`openlabels9`); human
labels and supervision masks are on the same canvas. None of the five is in the ink_9um corpus, the Reader v2
label manifest, or Reader V3's `train_config.json`. Checked: ag055 (`20250919125754…`), s1 (`20250825181859--1`)
and PHerc0841 are absent from both. The labels' level 2 is a nearest-neighbour sample, the volumes' a 4×4 mean,
which puts a constant 0.375 px between them that the relative shift below cancels.

**Models.**
- ink_9um `hybrid_3d2d` seed43 step-075000 (reference) and seed42 step-075000. Trained on labels that share
  the input canvas, so no learned shift is expected. Predictions already exist (docs/27).
- Reader V3 (KLAVIS, weights `aee1d64`, local re-save) and Reader v2 (`reader-v2-step040000.pth`, 138 MB, to be
  downloaded and re-saved without unpickling as in [`convert_thirdparty_ckpts.py`](../tools/convert_thirdparty_ckpts.py)).
  Trained partly on the resized labels, so a shift is expected if models learn it. Inference uses the same
  command and settings as the existing predictions.
- KLAVIS ink9um-dense all7 and its manual-label control, and Nieuwlaar dense-native (predictions exist,
  docs/29). The first two were trained on labels on their input canvas (no shift expected). How Nieuwlaar's
  labels were transferred is not documented, so it is reported, not judged.

**Measurement.** For a prediction P and labels L on the same canvas, AUC(d) is the AUC over supervised pixels of
L(y, x) against P(y + dy, x + dx), for integer d in [−12, 12]² (pixels whose shifted position leaves the canvas
are dropped; 256-bin histogram AUC). The model's shift ŝ is the argmax of AUC(d), refined by a parabola through
the argmax and its two neighbours on each axis. ŝ is where the prediction draws ink relative to the labels. A
positive ŝ means it is displaced towards larger row and column indices. Because the human labels may carry their
own canvas offset, the quantity judged is the relative shift Δ = ŝ(model) − ŝ(ink_9um seed43), per segment.

**Rule.**
- **Learned shift present:** for Reader V3, Δ lies in [+4, +10] px on both axes in at least 4 of 5 segments, and
  for ink_9um seed42 |Δ| ≤ 2 on both axes in at least 4 of 5 (the control does not move).
- **Absent:** for Reader V3, |Δ| ≤ 2 on both axes in at least 4 of 5.
- Otherwise **unclear**. Reader v2 is judged by the same rule, separately. If its download is not approved,
  Stage 1 runs without it.
- **Post-hoc fix (secondary, a fixed correction, not the argmax):** ΔAUC = AUC(Δ̄) − AUC(0), where Δ̄ is the
  rounded mean of the ink_9um seed43 shift plus (7, 7). It is reported for every model per segment.
  For Reader V3 it counts as a useful fix if the mean over the five segments is ≥ +0.005 and positive in at least
  4 of 5.

**Predictions (written before running).** ink_9um seed42 and the two KLAVIS dense models: |Δ| ≤ 2. Reader V3 and
Reader v2: learned shift present, Δ ≈ +5 to +8 (partly diluted, because both also trained on the ink_9um corpus,
whose labels are not shifted). Post-hoc fix for Reader V3: a gain of at least +0.005 on the mean, which is a
guess with little behind it.

**Method check, before Stage 1.** Shift an ink_9um seed43 prediction by a known (+5, −3) and recover it within
0.5 px with the same code. Compute AUC(0) for ink_9um seed43 on each segment with
`sklearn.metrics.roc_auc_score` over the same supervised pixels. It must agree with the histogram AUC to 0.002,
or the measurement does not run.

## Stage 2 — retraining on corrected labels (outline; fixed in an addendum before it starts)

Only if Stage 1 says "present", or if the user decides to run it anyway after an "absent" result (a null result
would then be its point).
- Arms: **P**, the published Reader v2 labels. **C**, the same labels and supervision masks shifted by −g per
  segment (g from the canvas ratio; sub-pixel bilinear shift of the 0/255 masks, then ≥ 128; PHerc0172's
  same-scan labels unchanged). Optional **D**, shifted by a further +g, as a dose control.
- Recipe: Reader v2's `train_config.json` as published (init `reader-v2-init-ft12k.pth`, 40k iterations, the
  ink_9um corpus included). Two seeds per arm. The same five open-label segments, scored as in Stage 1 at d = 0.
- Rule (to be fixed): C − P mean AUC ≥ +0.01 with the same sign in both seeds means the correction helps;
  |C − P| < 0.01 means no detectable effect. KLAVIS gives checkpoint noise on the PHerc0841 mean of about 0.01.
- Cost, to be measured before fixing: the native surface volumes of 70 segments plus the label tar (download
  size by HEAD requests), and about 4 runs × 3–5 h on one RTX 5090.

## Limits

- Five evaluation segments on three scrolls, human labels on all five; the shift search is integer plus a
  parabola.
- A shift found in Stage 1 is consistent with the label offset but not proof of it. Stage 2 is the test.
- The canvas check above used one surface volume per segment and the middle layers only.

## Credits

The offset and its formula are evilaliv3's (villa #2243, #2245). Reader v2, Reader V3, ink9um-dense and their
labels are KLAVIS's (Domenico Russo); ink_9um, the teacher maps and the open labels are the Vesuvius Challenge
team's; the dense-native model is Erwin Nieuwlaar's.

AI disclosure: the design, code, runs and this text were produced by Claude (Anthropic) via Claude Code, directed
by Hyojun Kwon (khj1222), who chose the problem, the data and the decisions.
