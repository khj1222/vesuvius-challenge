# August 2026 Progress Prize — submission package

**Form:** https://forms.gle/xoF5C3QsYutKP97x7
**Deadline:** 2026-08-31 23:59 PT
**Status:** final draft v3 (2026-08-13 — upstream re-checked: no reply/reaction on the #192
comment, #1234, or #1231 as of 08-13, so the framing stands; every field-5 number re-verified
against `runs/*cv_summary*.json`; the flat_depth_targets branch is rebased, tested, and
pushed — opening the PR is one click). Not submitted.
**Order matters:** the form has a required "Pull request submitted!" checkbox, so settle step 1 first.

---

## Step 1 — the pull request ⚠️ one click left

The checkbox needs a PR. Three candidates, in order of preference:

1. **`flat_depth_targets` upstream PR — READY, not yet opened.** Branch
   `khj1222:feat/flat-depth-targets` (commit `8515746`) was rebased onto the current
   `merge-ink-pipelines` tip (`33c463e`), unit-tested (7 passed), and pushed 2026-08-13.
   **Open it here:** https://github.com/ScrollPrize/villa/compare/merge-ink-pipelines...khj1222:feat/flat-depth-targets
   — title and body are in [`villa-pr-flat-depth-targets.md`](villa-pr-flat-depth-targets.md)
   (an optional pre-open GPU smoke is listed there too). Best fit: it is *this round's*
   contribution, and without it nobody can run a label-depth experiment in flat mode at all.
   The #192 comment already offered it — **open it if a maintainer says yes; if there is
   still no reply by ~2026-08-24, open it unprompted** so CI and a possible review round
   have lead time before 08-31. Opening earlier is now costless and buys review time;
   upstream is actively reworking `infer.py` (the rebase already had to absorb one round of
   it), so sitting on the branch risks another conflict cycle.
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
Upstream PR (this round, flat_depth_targets): <FILL IN once opened — see step 1>
Upstream PR (review addressed): https://github.com/ScrollPrize/villa/pull/1234
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
merged, and the villa-side change is one config-gated patch that leaves existing paths
untouched.
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

* **Pre-submit swaps, in order** (the text is otherwise final):
  1. Open the `flat_depth_targets` PR (step 1) and put its URL into field 4's
     `<FILL IN>` line.
  2. Optionally update field 5's closing sentence "the villa-side change is one
     config-gated patch that leaves existing paths untouched" to "…is one config-gated
     patch, submitted upstream as a PR, that leaves existing paths untouched".
  3. If [#1234](https://github.com/ScrollPrize/villa/pull/1234) has merged by submission
     day, change its field-4 label from "review addressed" to "merged".
  4. Tick the checkbox, submit, then sync this file to match what was actually sent
     (the July file is kept submission-identical; do the same here).
* **Update if #192 gets a reply.** If a maintainer says the `flat_depth_targets` route is
  wanted, say so in field 5 and open the PR. If they say internal 3D labels already exist,
  the framing in the first paragraph has to change.
* **Do not quote a single `v2` fold.** Its spread is 0.0308; fold 0 alone reads as "the plane
  wins outright", which fold 1 contradicts.
* **Keep the headline claim v4-vs-v3.** The 08-09 draft said the measured band is "worse
  than doing nothing" — that is the v4-vs-v2 comparison, whose fold-1 gap is only 0.0067.
  Reworded 08-10 to "loses to simply fixing the band at one depth" (v4 vs v3: over the
  noise floor on every fold). Don't strengthen it back.
* **Do not compare v4's 0.8098 to July's 0.8472 as if it were the finding.** Those differ in
  training mode as well as label. The finding is v4 against v3.
