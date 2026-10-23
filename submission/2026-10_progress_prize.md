# October 2026 Progress Prize — submission package

**Form:** https://docs.google.com/forms/d/e/1FAIpQLSc4flEfgK2nyjoczz2_U_XrIGMlgrnSknWatLqrFPnbtKfZwg/viewform
("October 2026 Progress Prizes", taken from https://scrollprize.org/prizes; the form URL is round-specific.)
**Deadline:** 2026-10-31 23:59 Pacific = 2026-11-01 15:59 KST.
**Status:** prepared 2026-10-23 (KST), not yet submitted. The user performs the form submission.
Fields 4 and 5 below are the final text; their hashes are recorded at the end.

Final pre-submit check, 2026-10-23: fields 4 and 5 read through; all 37 field-4 links returned
HTTP 200; the evidence files they point to exist on `main`; villa
[#2012](https://github.com/ScrollPrize/villa/pull/2012) is closed unmerged (2026-10-21) and field 4
says so; [#1796](https://github.com/ScrollPrize/villa/pull/1796) and
[#1703](https://github.com/ScrollPrize/villa/pull/1703) are merged; #1703 merged after the
September submission and was not part of it.

## Form answers

**Your full name**
```
Hyojun Kwon
```

**Team description**
```
Individual submission — no team.
```

**Discord display name**
```
jamiolrangmalrang4936
```

**4. URL of your open source / publicly available contribution**
```
https://github.com/khj1222/vesuvius-challenge
Label-free ink threshold, pre-registered twice (writeup with both results): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/27_label_free_threshold.md
  Pre-registration 1, committed before scoring: https://github.com/khj1222/vesuvius-challenge/commit/1b5917e1112a3efc3b6b78619513c56f7611742c
  Pre-registration 2 (released checkpoints, three new scrolls), committed before inference: https://github.com/khj1222/vesuvius-challenge/commit/72c7679ee062f9742681822e1ce92018872e11f6
  Tool to use it (calibrate on labelled segments, apply to an unlabelled scroll): https://github.com/khj1222/vesuvius-challenge/blob/main/tools/borrow_threshold.py
  The same tool offered upstream as a villa command (vesuvius.ink_detection.inference.threshold), closed unmerged on 2026-10-21 (the maintainers do not recommend binarizing ink predictions): https://github.com/ScrollPrize/villa/pull/2012
  Tool check against the replication (70 cells, 14 checkpoints): https://github.com/khj1222/vesuvius-challenge/blob/main/runs/ink9um_scorecard/borrow_threshold_check.txt
  Scorer: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/score_label_free_threshold.py
  Replication driver and input preparation: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/run_open_label_replication.py , https://github.com/khj1222/vesuvius-challenge/blob/main/tools/prepare_open_label_segments.py
  Raw results (per-cell CSV, summaries, every histogram): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard (labelfree_*, openlabels_*)
Third test, on public checkpoints trained with dense pseudo-labels (KLAVIS, Nieuwlaar): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/29_threshold_other_recipes.md
  Pre-registration, committed before inference: https://github.com/khj1222/vesuvius-challenge/commit/a2a187ca025569437b6ccee8c3ba3052b75038a0
  Raw results and checks (KLAVIS's published validation numbers reproduced): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard (otherrecipes_*)
Ink reader trained against surface offsets (in-patch depth wander), pre-registered, negative: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/30_surface_offset_robust_ink.md
  Pre-registration, committed before any fine-tune: https://github.com/khj1222/vesuvius-challenge/commit/8b6aefc55e6de22c35621cfcdad1d50fe1ddc7fa
  Raw results and checks: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard (segrobust_*) , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/segrobust
Larger surface offsets (3–5 slices) on wider 27-slice inputs, wider depth jitter, pre-registered, negative: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/31_wide_depth_jitter.md
  Pre-registration, committed before any fine-tune: https://github.com/khj1222/vesuvius-challenge/commit/987b77806acf40f2d3c4c2b69c46d9d3ba4bac68
  Tools (27-slice volumes and labels from the published 2.4 µm volumes, run driver): https://github.com/khj1222/vesuvius-challenge/blob/main/tools/prepare_wide_volumes.py , https://github.com/khj1222/vesuvius-challenge/blob/main/tools/prepare_wide_labels.py , https://github.com/khj1222/vesuvius-challenge/blob/main/tools/run_widejitter.py
  Raw results: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard (widejitter_*)
Fiber maps at 9 µm vs a 2.4 µm reading of the same surface, pre-registered: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/28_fiber_9um_agreement.md
  Pre-registration, committed before any fiber model was run: https://github.com/khj1222/vesuvius-challenge/commit/735404fbdad7527fe40f707a9059fd7eb1f5938d
  Tool: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/fiber9_check.py
  Raw results (gates, per-tile scores, every scored map): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/fiber9
Discord #robots posts: https://discord.com/channels/1079907749569237093/1555465594969661440 (threshold, with the correction) , https://discord.com/channels/1079907749569237093/1556159405211521176 (fiber) , https://discord.com/channels/1079907749569237093/1559894798830272512 (surface offsets)
Data used: PHerc0139, PHerc1667, PHercParis4 (ink_9um labels); PHerc0841, PHerc0009B, PHerc0500P2 (open-data reviewed ink labels, 2026-09-22); PHerc0139 9.362 µm and 2.399 µm scans with tifxyz meshes on both
Models measured: https://huggingface.co/scrollprize/ink_9um (14 checkpoints), https://huggingface.co/scrollprize/fiber_hz_vt , https://huggingface.co/Qualzz20/afv_fiber_9um , https://huggingface.co/scrollprize/fiber_ink_4class_selfdistill
Merged upstream fixes:
  Copy-model test-time augmentation now transports the direction-prior vectors with the volume: https://github.com/ScrollPrize/villa/pull/1796 (merged 2026-10-08, https://github.com/ScrollPrize/villa/commit/12f21236a2c3bb362a69c1b562a63b6a138a673e) , evidence: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/tta_main
  Inference falls back to eager at the first forward when torch.compile cannot run, e.g. Windows without Triton: https://github.com/ScrollPrize/villa/pull/1703 (merged 2026-09-28, after my September submission, https://github.com/ScrollPrize/villa/commit/795ca2ba82ff62ee1365b78d65d2688ba7c6f42e)
```

**5. What is your contribution?**
```
Pre-registered measurements of three questions that come up as soon as a released model is run on a
scroll nobody has labelled: which threshold to use when an ink prediction is binarized, how much of a fiber
reading survives at 9 µm, and how much a traced surface that sits off the sheet costs an ink model
and whether training can buy it back. Each was committed to git with its rules, decision table and my
prediction before anything was scored. Each refuted part of what I predicted, and the write-ups say
where.

(1) Which scroll data

Threshold (docs/27). Study 1: the ink_9um aligned representations of PHerc. Paris 4 (8 segments),
PHerc. 1667 (6) and PHerc. 0139 (9), predicted by leave-one-scroll-out models that never saw the
scroll being scored: 322 cells (segment × seed × checkpoint). Study 2: the reviewed ink labels the team
published in the open-data bucket on 2026-09-22 for three scrolls absent from the ink_9um training
set, PHerc. 0841 (3 segments), PHerc. 0009B (1) and PHerc. 0500P2 (1), predicted by all 14 released
ink_9um checkpoints: 70 predictions, scored against labels nobody in this project had looked at.
Test 3 (docs/29): the same five segments, predicted by four public checkpoints trained on dense
pseudo-labels (KLAVIS's ink9um-dense, three; Nieuwlaar's dense-native, one) and KLAVIS's matched
manual-label control: 25 predictions. None of these checkpoints trained on the three scrolls.

Surface offsets (docs/30): the released checkpoints fine-tuned 10,000 steps with and without an
in-patch depth wander, two seeds, scored on the same five segments under 11 renders each (clean,
whole-surface shifts of ±1–2 slices, six smoothly wandering ones): 330 predictions. Larger offsets
(docs/31): the 2.4 µm surface volumes re-pooled to 27 slices instead of 21, so shifts up to ±5 slices
read real data; the same fine-tune with the depth jitter widened from ±2 to ±5 slices, two seeds, the
same five segments under 17 renders each: 510 predictions.

Fiber (docs/28). PHerc. 0139, scanned at 9.362 µm (20250728140407) and 2.399 µm (20260102150214), on
five segments (w035, w039, w040, w041, w044) that have a tifxyz mesh on each scan: 100 tiles of
0.9 mm. None of the three models used was trained on this scroll.

(2) How it raises the chance of reading these scrolls or others

The villa maintainers do not recommend binarizing ink predictions (said when closing villa #2012),
and nothing here argues otherwise. The threshold results apply where a binary mask is made anyway:
scoring F1 or IoU against labels, measuring ink area, or comparing two models' masks, as recent
community reports do at p > 0.5. Without labels the usual choice is 0.5 (128 of 255). On the
leave-one-scroll-out models that costs 0.06–0.14 F1 on the unseen scroll, two to five times the
0.03 noise floor. The one label-free method measured before (pseudo-labels, docs/24) cost 0.066.
Taking the optimum that the same model reaches on held-out scrolls you can score, and using it
unchanged, lost 0.007–0.016 there and 0.003–0.009 on the three new scrolls: at most about half the
noise floor, with no labels on the scroll being read. It is not safe for every model: for checkpoints
trained on dense pseudo-labels it lost 0.062 on one of the three scrolls, where borrowing the
fraction of the sheet that the optimum marks (the quantile rule) lost 0.003.

A traced surface that sits off the sheet feeds the ink model the wrong depths. Within ±2 slices
(about ±19 µm) the released recipe already tolerates it: a smoothly wandering surface costs every
model only 0.009–0.019 F1. Beyond that it does not, and asymmetrically: with the surface 5 slices
(about 48 µm) off one way the released reader loses 0.14–0.17 F1, the other way 0.03–0.04, and 0.06–0.08
already at 3 slices. Training with the window shifted that far does not buy it back. For anyone
tracing surfaces for ink, that is a measured error budget: a few tens of micrometres on the wrong side
cost at least as much as the worst threshold choice above.

The fiber question matters because fiber tracing is being used as a constraint for unrolling, and
the public fiber predictions are at 2.4 µm while most scrolls have 9 µm scans. On PHerc. 0139 a
9.362 µm fiber map agrees with a 2.399 µm reading of the same papyrus at F1 0.69
(0.45 with the spatial correspondence removed). About four fifths of what the 9 µm models mark is
within a pixel of reference fiber, and they miss about two fifths of it. Whoever moves fiber work to
9 µm now knows the loss is mostly recall, and that on this scroll fine-tuning on 9 µm pseudo-labels
did not change it.

(3) What it enables that was not possible before

When a mask is needed, a threshold for an unlabelled scroll, chosen with a measured cost, using only
the labelled scrolls a user already has. tools/borrow_threshold.py does it in two commands:
`calibrate` reads predictions of labelled segments made with the model you will run, and also scores each of your scrolls with a
threshold borrowed from the others, so you see what borrowing costs for that model before relying
on it. `apply` then binarizes the unlabelled scroll, at the borrowed value or, with `--rule
quantile`, where it marks the same fraction of the sheet as the other scrolls' optima did. On the
replication data it reproduces every cell's optimum and each scroll's thresholds and losses, for all
14 released checkpoints. Before this, honest scores (including all of ours in docs/14–26) picked the
threshold with the scored scroll's own labels, and 128 was used without a measured cost. The study
also settled a practical point for the released checkpoints: on three scrolls they never saw, their
optimum is 98–141 and 128 stays within the noise floor (0.006–0.027), so users of those checkpoints
can keep 128. The leave-one-scroll-out models could not: they wanted 84–92. That difference is the
withdrawal described under (4).

For surface offsets: 27-slice inputs built from the published 2.4 µm surface volumes and their labels
(tools/prepare_wide_volumes.py, prepare_wide_labels.py), so an ink reader can be tested or trained
with the surface up to ±5 slices off on real data. The 21-slice renders capped every such test at ±2
slices, which is why docs/30 could not see the loss reported above.

For fiber: a number for a 9 µm fiber model on an unseen scroll. Qual's afv_fiber_9um card states
that no independent test accuracy is claimed, and I found no published measurement. The protocol is reusable on any scroll scanned twice:
the same surface is located in both scans through the two tifxyz meshes, a correspondence gate must
pass first (NCC 0.60–0.84 on all five segments, peak at zero shift), and every score is compared
with a null that keeps fiber densities but breaks the spatial match.

(4) Evidence

- Pre-registration commits precede every result (threshold 1b5917e → 93c5f50, 72c7679 → 393ab46,
  a2a187c → cff3061; fiber 735404f → 1b781bf; surface offsets 8b6aefc → bc87201, 987b778 → 4a7e797),
  with links in field 4.
- The tool's output matches the replication on all 14 checkpoints (log linked in field 4).
- The third test's failure was checked after the result for loading and scoring errors: the same
  checkpoint files and inference path reproduce KLAVIS's six published validation AUCs within
  0.0007, and the villa tool, a separate implementation, gives the same losses.
- The wider 27-slice inputs contain the old 21 slices byte for byte (28 of 29 volumes; the exception
  differs only in an edge band the old volume left empty), and the released checkpoints' clean scores
  on them equal docs/30's exactly.
- Study 1 first reproduced all 322 committed scores (threshold exact, F1 within 0.0001) before
  applying any rule. The fiber scoring is deterministic: a second run wrote a byte-identical summary.
- The raw files allow re-auditing without the original predictions: every threshold cell's 256-bin
  histograms, and every scored fiber map bit-packed.
- What failed, as written in the documents:
  - Threshold study 1: I predicted no rule would pass. Two passed.
  - Threshold study 2: I predicted the value study 1 recommended (87) would carry to the released
    checkpoints on at least two of the three new scrolls. It failed on all three (0.095–0.118 lost).
    I withdrew the number and the advice against 128 in a correction banner on
    docs/27, in the README and in a correction on the #robots thread. Only the method (borrow the same model's
    optimum) passed twice.
  - Threshold test 3 (docs/29): on four public checkpoints trained with dense pseudo-labels, I
    predicted the borrowed value would hold on all three scrolls. It failed on PHerc0500P2 (0.062
    lost; its optimum sits about 25 grey levels below the other two), while borrowing the quantile
    held everywhere. Three of my four predictions failed. The tool's own check prints that loss.
  - Surface offsets (docs/30): I predicted that training with an in-patch depth wander would recover
    at least 0.015 F1 on wandering renders. It recovered nothing (−0.005 and −0.006 in the two seeds).
    The controls show why: the released recipe already jitters the depth window by ±2 slices, and every
    model loses only 0.009–0.019 to a 2-slice wander. I checked that the augmentation ran (40 of 40
    sampled patches) before reporting this.
  - Larger offsets (docs/31): I predicted the ±5 jitter would recover 0.03–0.08 F1 on 3–5 slice
    offsets. It recovered +0.001 and +0.007. The explanation I first wrote for the one-sided loss (the
    ink signal leaving the window) did not fit the per-scroll numbers. A later update, after sean's reply on
    #robots, explains the direction (the trace lies on the sheet's front surface, so one way reads into
    the sheet) but not the size, which the document leaves open.
  - Fiber: I predicted the 9 µm fine-tune would agree better by at least 0.03. The difference was
    −0.005 [−0.021, +0.009]. My crowding hypothesis also failed, and docs/28 explains why a presence
    map cannot test crowding at all.

Limits: the threshold results say which cut to make, not whether to make one, and they are scored as
F1 against labels, not as legibility. As stated in the documents, the threshold rules were tested on
six scrolls. Borrowing the value held for every manual-label set of checkpoints and failed on one scroll for dense-label ones;
borrowing the quantile has held in all three tests. A threshold borrowed from unadapted models does
not carry over to a model fine-tuned on the new scroll (adaptation moves the optimum, measured in docs/27). The
offset results use synthetic shifts on five segments of three scrolls; a real tracing error can also
switch sheets or fold. The fiber result is one scroll, measured against a model-made reference. That is
agreement, not accuracy, and says nothing about fiber tracing or Qual's fiber volumes.

Integration: everything reads the open data directly (OME-Zarr scans, tifxyz meshes, the published
ink label pyramids), predictions come from the unmodified villa inference command and nnUNet's own
predictor, and results are CSV/JSON. Tools are MIT-licensed.

Also this month, two fixes merged upstream. villa #1796 (merged 2026-10-08): Copy-model test-time
augmentation flipped and rotated the input volume but left the two direction-prior vectors
unchanged, so every augmented variant was given a prior pointing the wrong way. The fix transports
the vector components with the volume; a model that returns its own priors now gets them back (max
error 6.08 before, 3.6e-7 after, mirror mode). On six manually labelled PHerc. Paris 4 cubes the
effect on tracing was mixed, so I claim correctness, not a gain. villa #1703 makes inference fall
back to eager mode at the first forward pass when torch.compile cannot run (for example Windows
without Triton), instead of failing. It merged on 2026-09-28 after review, after my September
submission of 2026-09-20, so it was not part of that submission.
```

**Terms and Conditions:** read and accepted by the user on the form.

## Checklist

- [x] Re-check the live form and deadline on https://scrollprize.org/prizes (2026-10-06).
- [x] Read fields 4 and 5 straight through; check every field-4 link (2026-10-23).
- [ ] Paste the fenced answers, accept the Terms, and submit (user).
- [ ] Compare the submitted text with this file and mark it submitted.

## Field hashes

Calculated over each fenced block body with LF line endings and exactly one trailing newline:

- field 4 — 5,332 chars, `bc1edb9aa570b11f48847a24dfceb47d59cae04288603ec93c7eb7bc410ea185`
- field 5 — 11,970 chars, `a6da802ce27edd0cf4c617d914c4c4b524c8cd2a8531037c918be4321567460b`

If either field is edited before submitting, recompute these against the actual pasted text.
