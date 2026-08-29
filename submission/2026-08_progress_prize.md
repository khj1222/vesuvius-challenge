# August 2026 Progress Prize — submission package

**Form:** https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform
("August 2026 Progress Prizes" — **the July form at https://forms.gle/xoF5C3QsYutKP97x7 is closed**;
the form URL is round-specific and is re-published each month on
https://scrollprize.org/prizes, so re-fetch it there rather than reusing last month's.)
**Deadline:** 2026-08-31 23:59 PT
**Status:** ✅ **SUBMITTED 2026-08-29** (deadline was 08-31 23:59 PT). Sent by the user
through the August form, https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform,
as Hyojun Kwon / bluekgssk@gmail.com, individually. **Fields 4 and 5 below are byte-identical
to what was sent** (field 5 sha256 `b2910b90c6a573c767a07d49b9b4138daffe87f265e4a43cd72ac27d34d117d0`,
70 lines / 5,101 chars, dashes and en-dashes intact) — keep this file that way, as the July
one is kept, so it stays the record if the judges ask.

Final pre-submit check, 2026-08-29: [#1535](https://github.com/ScrollPrize/villa/pull/1535)
still open and mergeable with zero human comments and no reviewer, unchanged since 08-19 (its
only comment is the Vercel authorization bot), so no label to update;
[#1231](https://github.com/ScrollPrize/villa/issues/1231) unchanged (0 comments, erdpx still
assigned); [#192](https://github.com/ScrollPrize/villa/issues/192) had nothing after
stantheman0128's 08-25 scoring; all ten field-4 links returned HTTP 200 on the day; every
field-5 number was re-derived from the run artifacts. Four things were fixed that morning:
the independent band check was written into `docs/12` (field 4's result writeup, where a
judge following the link would otherwise not have found it); the smoothness caveat from that
scoring was carried into field 5; the w02 comparison now names which w00 baseline it means
(0.8232, the single split — not the 0.8472 three-fold mean quoted two sentences earlier); and
three evidence rows were repointed to the fold-CV JSONs because the 30k extension re-swept
those CSVs onto odd-thousand steps.

⚠️ **The form URL is round-specific.** July's form (`forms.gle/xoF5C3QsYutKP97x7`) had stopped
accepting responses by 08-29; August's is the separate one linked above, published on
https://scrollprize.org/prizes. It also has **six questions, not seven** — the standalone
"Pull request submitted!" checkbox is gone, so the PR is evidenced through field 4 alone. Get
September's link from the prizes page rather than reusing this one.

---

## Step 1 — the pull request ✅ done

**[#1535](https://github.com/ScrollPrize/villa/pull/1535) opened 2026-08-19** — *this
round's* PR: `flat_depth_targets` (base `merge-ink-pipelines`, 3 files +112 −13, mergeable;
title/body archive = [`villa-pr-flat-depth-targets.md`](villa-pr-flat-depth-targets.md)).
It replaces [#1434](https://github.com/ScrollPrize/villa/pull/1434), opened 2026-08-13 and
closed by `erdpx` on 08-18 asking for `CONTRIBUTING.md` compliance and for evidence before
shipping `--z-reduce mean`. Both were addressed — `mean` dropped, description rewritten
with a before/after figure on real scroll data — and since the PR turned out not to be
reopenable, the revision went up as a new one from the same branch.
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
Upstream PR (this round, flat_depth_targets): https://github.com/ScrollPrize/villa/pull/1535
Upstream PR (merged 2026-08-14): https://github.com/ScrollPrize/villa/pull/1234
Upstream issue: https://github.com/ScrollPrize/villa/issues/1231
Community projects listing (merged): https://github.com/ScrollPrize/villa/pull/1249
First scorecard of the released ink_9um models: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/14_ink9um_scorecard.md
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
(0.8263 vs 0.8235 — itself within 0.001 of w00's own single-split baseline, 0.8232, on a
segment the harness had never seen).

A third check came from outside the project. stantheman0128 offered on #192 to score the
exported band against an independently acquired 1.129 um scan of the same segment, and
posted the result on 2026-08-25: of the 164 annotation cells that scan reaches, 157 could
be scored — all inside one of the 15 annotated regions, the only one it covers — and the
band's per-pixel centre sits a median 2.0 voxels from the independently observed surface,
118 of the 157 within 3 voxels. They are careful about what that does not show: it is
geometry and not ink identity, and the band's local smoothness comes out as weak evidence
either way — neighbouring cells differ in distance about as much as random pairs do — so the
check speaks to where the band sits, not to whether it follows the sheet. It still points the
verdict the harder way: the per-pixel band is not obviously misplaced, and it loses anyway to
one held flat.

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
#1535, that leaves existing paths untouched.

The same harness also produced this month's first numbers for the official ink_9um
release (2026-08-14): scoring all 14 released hybrid_3d2d checkpoints on the three
segments that ship validation masks shows honest held-out F1 tops out at 0.74–0.77
while the same checkpoints reach 0.98+ on their training pixels — a 0.22–0.45
memorisation gap at the final step, no step that is best everywhere, and two released
seeds that disagree by 0.22 F1 at step 75k on the same held-out region. The model card
ships no numbers, so this is the first measured baseline anyone can compare against
(docs/14 in the repo).
```

**6. Terms and Conditions** → check "Yes, I agree"
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Evidence backing the claims above

| claim | source |
|---|---|
| 3-arm × 3-fold means 0.8441 / 0.8478 / 0.8098 | `runs/ink_depth_v{2,3,4}_fold_cv_summary*.json` |
| per-fold v3 0.8455 / 0.8452 / 0.8528 | `runs/ink_depth_v3_fold_cv_summary.json` (the per-fold CSVs were re-swept by the 30k extension and no longer carry the even-thousand rows) |
| per-fold v4 0.7997 / 0.8192 / 0.8104 | `runs/ink_depth_v4_fold_cv_summary_z16_48.json` (same re-sweep caveat) |
| per-fold v2 0.8567 / 0.8259 / 0.8496 | `runs/ink_depth_v2_fold_cv_summary.json` |
| July 2D baseline 0.8472 on the same folds | `runs/ink_fold_cv_summary.json` |
| noise floor ~0.03 F1 | July: one unchanged config scored four times, 0.823–0.854 |
| label voxels 1.00 / 8.00 / 8.01 per ink pixel | `make_label_version.py` output, `docs/12` |
| measured centre 29.3–40.3 per region | `_inklabels3d.json`, `docs/11` |
| model-free CT contrast AUC ≤ 0.55, peak 0.546 @ z24 | `runs/depth_contrast/`, `docs/10` |
| reduction trap: F1 0.535 (z0–64) vs 0.802 (z16–48) | `docs/12`, "The reduction has to match the supervision" |
| late-training gain +0.0075 (v3) / +0.0068 (v4) | step 17000 vs 20000 rows of the summaries above |
| 30k extension: gap 0.038 → 0.036 | `runs/ink_depth_ext30k_summary.json`, `docs/12` |
| w02 replication: 0.8263 vs 0.7287 (+0.098), w02 2D baseline 0.8235 | `runs/ink_w02_{v3,v4}_fold_cv_summary.json`, `runs/ink_w02_holdout_20k/validation/summary.csv`, `docs/12` |
| independent band check: median D 2.0 voxels, 118/157 within 3 (region 15 only) | stantheman0128 on villa #192, 2026-08-25; anchors from `submission/depth_anchors/`; recorded in `docs/12`, "Independent check" |

(Run artifacts live under the gitignored `external/villa/ink-detection/`; every number is
reproduced in `docs/12_depth_training.md`.)

---

## Notes for whoever finalises this

* **Pre-submit swaps** — 1 and 2 done 2026-08-13 (PR #1434 in fields 4 and 5); 3 done
  2026-08-14 ([#1234](https://github.com/ScrollPrize/villa/pull/1234) merged by erdpx,
  field-4 label changed to "merged"). Remaining:
  4. **#1434 was closed unmerged by erdpx on 2026-08-18**; the revision went up as
     **[#1535](https://github.com/ScrollPrize/villa/pull/1535)** on 08-19 and every
     mention above now points there. If #1535 moves (reviewed, merged, closed) before
     the form goes in, relabel it the same way — and check that the "Why this matters
     to me" paragraph is in place, since a PR body that fails CONTRIBUTING.md is what
     cost the first attempt.
  5. ✅ Done 2026-08-29 — agreed to the terms, submitted, and this file now matches what
     was actually sent (verified by diff and sha256 before sending, not after).
  6. **ink_9um scorecard paragraph — KEEP (decided 2026-08-24)**: the last paragraph of
     field 5 and the docs/14 link in field 4 both stay in. It is deliberately one
     paragraph — the headline stays #192 — and September cites docs/14 only as already
     submitted groundwork, so this is not double-claiming. Repo is pushed; docs/10, 11,
     12 and 14 all verified reachable 2026-08-24. **Do NOT fold the LOSO / cross-scroll
     results into this form even if they finish before the deadline** — they are the
     September submission's centerpiece (docs/13 A안, judged monthly; splitting wins
     two rounds).
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
    **Resolved 2026-08-28: they posted on 08-25 and the band is geometry-valid** (157
    evaluable cells, median distance to the independent surface 2.0 voxels, 118 within 3,
    median FWHM 2.71; coverage is region 15 alone, and they state plainly that this is
    geometry and not ink identity, and that it does not explain why v4 loses). Field 5 now
    carries it as the third check, worded to keep both caveats. If they post more before
    submission day, the numbers to update are in that paragraph and in the evidence table.
* **Do not quote a single `v2` fold.** Its spread is 0.0308; fold 0 alone reads as "the plane
  wins outright", which fold 1 contradicts.
* **Keep the headline claim v4-vs-v3.** The 08-09 draft said the measured band is "worse
  than doing nothing" — that is the v4-vs-v2 comparison, whose fold-1 gap is only 0.0067.
  Reworded 08-10 to "loses to simply fixing the band at one depth" (v4 vs v3: over the
  noise floor on every fold). Don't strengthen it back.
* **Do not compare v4's 0.8098 to July's 0.8472 as if it were the finding.** Those differ in
  training mode as well as label. The finding is v4 against v3.
