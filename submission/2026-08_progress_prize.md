# August 2026 Progress Prize — submission package

**Form:** https://forms.gle/xoF5C3QsYutKP97x7
**Deadline:** 2026-08-31 23:59 PT
**Status:** draft (2026-08-09). Not submitted.
**Order matters:** the form has a required "Pull request submitted!" checkbox, so settle step 1 first.

---

## Step 1 — the pull request ⚠️ decide

The checkbox needs a PR. Three candidates, in order of preference:

1. **`flat_depth_targets` upstream PR** — the villa-side change this round's experiment
   required (`train.py`, `infer.py`, `test_train.py`;
   `submission/villa-flat-depth-targets.patch`, against `merge-ink-pipelines`). Best fit:
   it is *this round's* contribution, and without it nobody can run a label-depth experiment
   in flat mode at all. The #192 comment already offered it — **open it if a maintainer says
   yes, or open it unprompted a few days before the deadline** rather than submitting without
   a PR of this round's own.
2. **[#1234](https://github.com/ScrollPrize/villa/pull/1234)** — open, review addressed
   2026-08-09, no conflicts. Counts, but it was July's PR.
3. **Community-projects entry update** — extend the `#### ⚙️ Tools` line added by
   [#1249](https://github.com/ScrollPrize/villa/pull/1249) (merged 2026-07-31) to mention the
   depth-label comparison. Cheap and always available as a fallback.

---

## Step 2 — Form answers

**1. Email**
```
bluekgssk@gmail.com
```

**2. Your full name**
```
Hyojun Kwon
```

**3. Team description**
```
Individual submission — no team.
```

**4. URL to your open source / publicly available contribution**
```
https://github.com/khj1222/vesuvius-challenge
Result writeup: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/12_depth_training.md
How the depth was measured: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/10_depth_localization.md
How the 3D label was built: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/11_measured_3d_labels.md
Reported upstream on the issue it answers: https://github.com/ScrollPrize/villa/issues/192
Upstream PR (review addressed): https://github.com/ScrollPrize/villa/pull/1234
Upstream issue: https://github.com/ScrollPrize/villa/issues/1231
Community projects listing (merged): https://github.com/ScrollPrize/villa/pull/1249
```

**5. Short description of how your contributions substantially increase the probability of reading complete scrolls**

```
villa #192 asks for accurate 3D ink labels, on the reasoning that labels drawn as one plane
and projected through depth teach the model surface texture rather than ink. It has been
open since April 2025. Two people proposed ways to build such labels this year; #923 called
itself a sketch, #1295 was closed on 2026-08-06 for want of validated depths. Neither
reported what happens when you train on them. That is the question I answered.

Answering it first required unblocking it. In flat mode the training loop max-pools the
label over z immediately before the loss, so a depth-resolved label and the published
single-plane label produce byte-identical targets — the experiment was not expressible in
the pipeline at all. A config-gated change (flat_depth_targets) keeps the volume, computes
the loss volume-to-volume against the supervision mask, and adds an inference flag that
reduces a volume prediction back to the ordinary 2D TIFF, so old and new models are scored
by one yardstick.

I then built three label versions differing only in band geometry — the published plane
(1 voxel), a constant band at the segment median (8 voxels), and a per-pixel band measured
from where the model and the raw CT independently agree the ink evidence lives (8.01 voxels)
— and trained all three across the same three folds, same seed, same schedule, scored on
last month's held-out harness.

The measured band came last on every fold: 0.8098 mean F1 against 0.8478 for the constant
band, a gap of 0.038 where the measured noise floor is ~0.03. The plane and the constant
band tie (0.8441 vs 0.8478), so thickness is not the variable — moving the band per pixel is
what costs. The constant band reproduces the 2D baseline exactly (0.8478 vs 0.8472), so
depth-resolved training is not itself harmful. And the circularity runs against the
hypothesis: the measured band was read out of a model trained on the depthless annotation,
so self-distillation should have flattered it, and it still lost.

A negative result, but a load-bearing one. It tells anyone working on #192 that the obvious
route — read depth out of a 2D-trained model, follow the sheet per pixel — is worse than
doing nothing, and it hands them the apparatus to test their own route in a day instead of
arguing about it for another fifteen months. I also documented a trap that would silently
invalidate any such attempt: a depth-target model must be scored over the supervised z
column only, because outside it ink and background both saturate and a max over the full
volume reports that noise. Same checkpoint, same pixels: F1 0.535 against 0.802. My own
first pass fell into it and looked like catastrophic label failure.

Everything is MIT, documented end to end, and the villa-side change is one patch that leaves
the existing paths untouched.
```

**6. Pull Request Submission** → check "Pull request submitted!" (see step 1)

**7. Terms and conditions** → "Yes, I agree"
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Evidence backing the claims above

| claim | source |
|---|---|
| 3-arm × 3-fold means 0.8441 / 0.8478 / 0.8098 | `runs/ink_depth_v{2,3,4}_fold_cv_summary*.json` |
| per-fold v3 0.8455 / 0.8452 / 0.8528 | `runs/ink_depth_v3_fold{0,1,2}/validation/summary.csv` |
| per-fold v4 0.7997 / 0.8192 / 0.8104 | `runs/ink_depth_v4_fold{0,1,2}/validation_z16_48/summary.csv` |
| per-fold v2 0.8567 / 0.8259 / 0.8496 | `runs/ink_depth_v2_fold{0,1,2}/validation/summary.csv` |
| July 2D baseline 0.8472 on the same folds | `runs/ink_fold_cv_summary.json` |
| noise floor ~0.03 F1 | July: one unchanged config scored four times, 0.823–0.854 |
| label voxels 1.00 / 8.00 / 8.01 per ink pixel | `make_label_version.py` output, `docs/12` |
| measured centre 29.3–40.3 per region | `_inklabels3d.json`, `docs/11` |
| model-free CT contrast AUC ≤ 0.55, peak 0.546 @ z24 | `runs/depth_contrast/`, `docs/10` |
| reduction trap: F1 0.535 (z0–64) vs 0.802 (z16–48) | `docs/12`, "The reduction has to match the supervision" |
| late-training gain +0.0075 (v3) / +0.0068 (v4) | step 17000 vs 20000 rows of the summaries above |

(Run artifacts live under the gitignored `external/villa/ink-detection/`; every number is
reproduced in `docs/12_depth_training.md`.)

---

## Notes for whoever finalises this

* **Update if #192 gets a reply.** If a maintainer says the `flat_depth_targets` route is
  wanted, say so in field 5 and open the PR. If they say internal 3D labels already exist,
  the framing in the first paragraph has to change.
* **Do not quote a single `v2` fold.** Its spread is 0.0308; fold 0 alone reads as "the plane
  wins outright", which fold 1 contradicts.
* **Do not compare v4's 0.8098 to July's 0.8472 as if it were the finding.** Those differ in
  training mode as well as label. The finding is v4 against v3.
