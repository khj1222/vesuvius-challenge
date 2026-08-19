# August 2026 Progress Prize — submission package

**Form:** https://forms.gle/xoF5C3QsYutKP97x7
**Deadline:** 2026-08-31 23:59 PT
**Status:** READY TO SUBMIT (2026-08-16 — field 5 gained a robustness paragraph: 30k
extension holds the gap at 0.036, and the full pipeline replicated on w02 widens it to
0.098; evidence table updated to match. PR [#1434](https://github.com/ScrollPrize/villa/pull/1434)
in fields 4 and 5 satisfies the required checkbox;
[#1234](https://github.com/ScrollPrize/villa/pull/1234) merged 2026-08-14 and relabelled).
Not submitted yet. Remaining pre-submit check: relabel #1434 if it moves before submission
day (see notes).

---

## Step 1 — the pull request ✅ done

**[#1434](https://github.com/ScrollPrize/villa/pull/1434) opened 2026-08-13** — *this
round's* PR: `flat_depth_targets` (base `merge-ink-pipelines`, 3 files +129 −13, mergeable;
title/body archive = [`villa-pr-flat-depth-targets.md`](villa-pr-flat-depth-targets.md)).
Vercel bot pending team authorization, same code-unrelated check as on #1234.
Also: [#1234](https://github.com/ScrollPrize/villa/pull/1234) (July's PR, review addressed
2026-08-09) **merged by erdpx on 2026-08-14** — second merged upstream PR after
[#1249](https://github.com/ScrollPrize/villa/pull/1249). Fallback never needed:
community-projects entry update on top of merged #1249.

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
Upstream PR (this round, flat_depth_targets): https://github.com/ScrollPrize/villa/pull/1434
Upstream PR (merged 2026-08-14): https://github.com/ScrollPrize/villa/pull/1234
Upstream issue: https://github.com/ScrollPrize/villa/issues/1231
Community projects listing (merged): https://github.com/ScrollPrize/villa/pull/1249
```

**5. Short description of how your contributions substantially increase the probability of reading complete scrolls**

```
villa #192 asks for accurate 3D ink labels, on the reasoning that a label drawn as one
plane and projected through depth teaches the model surface texture rather than ink. It has
been open since April 2025. Both attempts at it this year shipped a way to build such
labels and were closed without anyone training on them (#923 called itself a sketch; #1295
was closed on 2026-08-06 for want of validated depths). Training on them is the question I
answered — with the held-out harness that won July's Progress Prize, so every number below
stands against a measured ~0.03 F1 noise floor rather than a hunch.

The experiment first had to become expressible: in flat mode the trainer max-pools the
label over z immediately before the loss, so a depth-resolved label and the published plane
produce byte-identical targets. A config-gated change (flat_depth_targets) keeps the
volume, computes the loss volume-to-volume against the supervision mask, and adds an
inference flag that reduces the prediction back to the ordinary 2D TIFF — one yardstick for
every arm, old or new.

I then trained three label versions that differ only in band geometry — the published plane
(1 voxel), a constant band at the segment's median depth (8 voxels), and a per-pixel band
measured from where the model and the raw CT independently place the ink evidence (8.01
voxels) — across the same three folds, same seed, same schedule.

The measured band came last on every fold: 0.8098 mean F1 against 0.8478 for the constant
band, a 0.038 gap. The plane and the constant band tie (0.8441 vs 0.8478), so thickness is
not the variable — moving the band per pixel is what costs. The constant band reproduces
the 2D baseline (0.8478 vs 0.8472), so depth-resolved training is not itself harmful. And
circularity ran in the measured band's favour — it was read out of a model trained on the
depthless annotation, so self-distillation should have flattered it — yet it still lost.

Two robustness checks hardened the verdict. Extending all six depth runs to 30k steps
moves the gap from 0.038 to 0.036 — the measured band was not "stopped too early". And
rerunning the entire pipeline unchanged on a second segment (w02) replicates the ordering
with a wider margin: 0.8263 constant against 0.7287 measured, every measured fold below
every constant fold, while the constant band again lands on that segment's own 2D baseline
(0.8263 vs 0.8235 — itself within 0.001 of w00's, on a segment the harness had never seen).

A negative result, but a load-bearing one: the obvious route to #192 — read depth out of a
2D-trained model and follow the sheet per pixel — loses to simply fixing the band at one
depth, and anyone with a better route can now test it in a day on the same apparatus. I
also documented a trap that silently invalidates any such attempt: a depth-target model
must be scored over the supervised z column only, because outside it ink and background
both saturate and a full-volume max reports that noise. Same checkpoint, same pixels:
F1 0.535 against 0.802. My own first pass fell into it and looked like catastrophic label
failure.

Everything is MIT and documented end to end (docs/10–12 in the repo). The result went
upstream to #192 as soon as the matrix finished rather than waiting for this form, the
harness it stands on has been on the scrollprize.org community tools list since #1249
merged, and the villa-side change is one config-gated patch, submitted upstream as PR
#1434, that leaves existing paths untouched.
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
| 30k extension: gap 0.038 → 0.036 | `runs/ink_depth_ext30k_summary.json`, `docs/12` |
| w02 replication: 0.8263 vs 0.7287 (+0.098), w02 2D baseline 0.8235 | `runs/ink_w02_{v3,v4}_fold_cv_summary.json`, `runs/ink_w02_holdout_20k/validation/summary.csv`, `docs/12` |

(Run artifacts live under the gitignored `external/villa/ink-detection/`; every number is
reproduced in `docs/12_depth_training.md`.)

---

## Notes for whoever finalises this

* **Pre-submit swaps** — 1 and 2 done 2026-08-13 (PR #1434 in fields 4 and 5); 3 done
  2026-08-14 ([#1234](https://github.com/ScrollPrize/villa/pull/1234) merged by erdpx,
  field-4 label changed to "merged"). Remaining:
  4. **#1434 was closed unmerged by erdpx on 2026-08-18** (asked for CONTRIBUTING.md
     compliance, and for evidence before shipping `--z-reduce mean`). Revision ready
     2026-08-19: `mean` dropped (`8922c5e`, +112 −13), body rewritten with a real-data
     before/after figure — see
     [`villa-pr-flat-depth-targets.md`](villa-pr-flat-depth-targets.md). **Step 1 above
     and field 5 both still describe it as open and must be relabelled before the form
     goes in**, to whatever it actually is that day: reopened-and-under-review, merged,
     or closed-with-a-revision-pending. Do not leave "opened 2026-08-13 ... mergeable"
     standing — it is no longer true.
  5. Tick the checkbox, submit, then sync this file to match what was actually sent
     (the July file is kept submission-identical; do the same here).
* **Update if #192 gets a reply.** If a maintainer says the `flat_depth_targets` route is
  wanted, say so in field 5 and open the PR. If they say internal 3D labels already exist,
  the framing in the first paragraph has to change.
  * 2026-08-13 activity so far changes nothing in the text: stantheman0128 (not a
    maintainer) offered independent D/FWHM scoring of our v4 band against the 1.129um
    scan (reply draft = [`issue192_reply_stantheman.md`](issue192_reply_stantheman.md));
    pmh47 pushed back on their method. If their scoring of our band produces a result
    before submission day, consider one sentence in field 5 — geometry-invalid band
    supports "the estimator was wrong", geometry-valid supports the stronger reading
    that even accurate per-pixel bands don't help this training setup.
* **Do not quote a single `v2` fold.** Its spread is 0.0308; fold 0 alone reads as "the plane
  wins outright", which fold 1 contradicts.
* **Keep the headline claim v4-vs-v3.** The 08-09 draft said the measured band is "worse
  than doing nothing" — that is the v4-vs-v2 comparison, whose fold-1 gap is only 0.0067.
  Reworded 08-10 to "loses to simply fixing the band at one depth" (v4 vs v3: over the
  noise floor on every fold). Don't strengthen it back.
* **Do not compare v4's 0.8098 to July's 0.8472 as if it were the finding.** Those differ in
  training mode as well as label. The finding is v4 against v3.
