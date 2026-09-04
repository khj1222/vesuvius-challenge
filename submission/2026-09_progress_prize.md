# September 2026 Progress Prize — submission package (DRAFT)

**Form:** TBD — each round has its own Google Form and the previous one closes.
Fetch September's from https://scrollprize.org/prizes when the round opens
(August's was https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform).
**Deadline:** 2026-09-30 23:59 PT
**Status:** DRAFT v12 (2026-08-31, trimmed). Arm D — the transductive variant of arm C, pre-registered
at commit `923895d` before it ran — landed at **14.3% of the gap**, and was then pointed at
PHerc1447 itself under criteria fixed at `1da7685`, where it met none of them. Then the whole
Paris4 comparison was replicated on 1667 (pre-registered at `cd07b16`, step curve at
`5468ac5`) and **three of its four commitments were refuted**: the annotation buys 24% there
rather than 82%, and the label-free arms do not cross. All three results are in the ladder
and repair-price paragraphs and the evidence table. v8 was the full pre-submission audit. The adaptation ladder
is finished: arms B and C were pre-registered and run, so the PHerc1447 paragraph reports
three closed routes rather than one. Also folded in: the pyramid-pooling measurement that
settles the mechanism behind the domain-match retraction (docs/15 appendix 3), prompted by a
reviewer's question on villa #1582.

**Audit, 2026-08-30 — every artifact-backed number in field 5 was re-derived from the
committed CSV/JSON.** All reproduce except two, both now fixed at source rather than in the
prose: arm A's recovery share (the old summary's median 8.4% / mean −19.2% could not be
reproduced under any denominator; recomputed to **9.1% / −8.4%** with the definition and all
24 cells written into `armA_specmatch_summary.json`), and the "38% of the spectral distance"
figure (had no artifact; re-derived and stored as `runs/spectra/filter_effect_native0139.json`
— 37.7% mean per volume, so the text stands). The docs/14 ceiling is now given exactly
(0.755 / 0.758 / 0.765) as well as as a band.

**Form checked 2026-08-30:** scrollprize.org/prizes still carries August's form and the
08-31 deadline, as expected — September's link should appear once the round turns over.

⚠️ **villa [#1638](https://github.com/ScrollPrize/villa/issues/1638) was closed the same day it
was filed**, by `pmh47` (Research Team Lead): a disjoint mask is not a leak, and an
intra-segment held-out number is fine provided it is named that. He is right, and the audit
paragraph now says so rather than presenting the issue as a live contribution — a judge will
open the link. What is kept is the measurement, reframed as what it always was: the size of
the intra-versus-inter distinction he says one should always make. Reply draft for the thread:
[`issue1638_reply_pmh47.md`](issue1638_reply_pmh47.md).

**Field 5 is 11,475 characters**, trimmed 2026-08-31 from 12,294 to 9,822 after three results landed
in one day (arm D, PHerc1447, the 1667 replication). Every number survived the trim — 43 key
figures checked — and what went was detail that lives in the linked documents: arm A's
spectral numbers, the pooling method, the #1638 narrative, and the PHerc1447 render's
byte counts. The 1667 replication was deliberately left intact: it is our own headline being
falsified by our own follow-up, which is the strongest thing in the field. If it must shrink
again, the measurement paragraph is the only one with slack left.

On 2026-08-31 the invited check of villa #1471 was added back (+632 characters):
another contributor asked for this harness to be pointed at their PR, and it found a
regression there. It sits in the traction paragraph because that is the claim it
supports — the apparatus is being asked for by name.

⚠️ **The form URL is specific to each round and the previous one closes** — get September's from
https://scrollprize.org/prizes, not from the August link. August's form also dropped the
standalone PR checkbox, leaving six questions.

---

## Step 1 — the pull request ✅ done

**[#1608](https://github.com/ScrollPrize/villa/pull/1608)** — `ink-detection/scripts/make_holdout_config.py`,
opened 2026-08-26 against `merge-ink-pipelines`, 1 file. It is candidate 1 below: the join
that makes the released recipe runnable, plus the `--exclude-scroll` / `--exclude-segment`
flags that turn it into the cross-scroll probe this submission is about. Body follows
`villa/CONTRIBUTING.md` including the human "why this matters to me" paragraph
(`submission/pr1608_body.md`). One round of outside review already closed: Bullo27
reproduced the quota arithmetic, found a crash when `batch_size` is below the surviving
scroll count, and the fix went up as `dc9edb6` two days later
(`submission/pr1608_reply_bullo27.md`).

Kept in reserve if a second PR is wanted:
2. **scrollprize.org community-projects entry update** on top of merged
   [#1249](https://github.com/ScrollPrize/villa/pull/1249) — add the cross-scroll study
   line next to the harness entry (small, safe, same pattern as July).
3. Not [#1535](https://github.com/ScrollPrize/villa/pull/1535) — it is August's story and
   August already cites it, and in any case it is no longer open: a bot closed it on
   2026-09-03 under the repository's 14-day inactivity policy, with no reviewer having
   looked at it.

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
Result writeup (four-part cross-scroll study): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/15_loso_cross_scroll.md
Groundwork (first scorecard of the released ink_9um models): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/14_ink9um_scorecard.md
Arm generator: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/make_ink9um_config.py
Raw numbers (1,720 scored cells, 33 CSV/JSON evidence files): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard
Dataset and models measured: https://huggingface.co/scrollprize/ink_9um (models), hf://buckets/scrollprize/datasets/ink_9um (labels)
Audit of the corpus's own held-out masks: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/17_holdout_audit.md
Audit tool: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/audit_holdout_masks.py
Pre-registered adaptation study, three arms, all run: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/18_uda_design.md
Pre-registered targeting test (where to annotate, and the published curve it corrects): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/20_annotation_targeting.md
Four pre-registered attempts on the aligned-over-native gap, two stopped by their own calibrations: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/23_blur_exposure.md
Adaptation and audit tools written for it: https://github.com/khj1222/vesuvius-challenge/tree/main/tools
Upstream PR (this round, the arm generator): https://github.com/ScrollPrize/villa/pull/1608
Upstream issue (held-out audit; filed and closed by the research lead — the concession is in docs/17): https://github.com/ScrollPrize/villa/issues/1638
Invited check of another contributor's PR (found a crash, verified a fix): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/pr1471_striped_check
Open problem addressed: https://scrollprize.org/2026_open_problems (#7, cross-scroll ink generalization)
```

**5. Short description of how your contributions substantially increase the probability of reading complete scrolls**

```
Reading a complete scroll means running an ink model on a scroll nobody has labeled. Open
problem #7 asks how well today's models survive that jump; until now there was no
systematic number, and the official 9 µm models released on 2026-08-14 ship with no
evaluation at all. I measured the jump, diagnosed why it fails, priced what it costs to
fix, and then checked whether that price holds on a second scroll — all on that release,
with the held-out methodology that won July's Progress Prize and settled villa #192 in
August.

Groundwork first (docs/14): scoring all 14 released hybrid_3d2d checkpoints on the three
segments that ship validation masks puts the honest within-scroll ceiling at F1 0.74–0.77
— the best value any released checkpoint reaches is 0.755, 0.758 and 0.765, one per
segment — against 0.98+ on training pixels: a 0.22–0.45 memorisation gap, no step that is
best everywhere, and two released seeds that disagree by 0.22 F1 at the final step.

That yardstick had to be checked itself, because everything honest here rests on three
masks — and all three split their annotation within connected regions, so 23% to 59% of
their held-out pixels sit inside one training patch of pixels the model trained on. Whether
that adjacency pays needed no new training: the released checkpoints saw those segments and
my leave-one-scroll-out arms never saw the scrolls, so scoring both over the same distance
strata separates proximity from difficulty. The control comes out nearly flat while the
trained model gains +0.14 and +0.07 F1 more on the pixels nearest its training data. I filed
that as villa #1638 and the research lead closed it the same day: the masks are disjoint, and
an intra-segment held-out number is legitimate provided it is named that. He is right, and
the framing was mine to fix — which is why the 0.74–0.77 above is an intra-segment ceiling,
not a claim about generalisation (docs/17).

Then the measurement (docs/15, parts 1–2): leave-one-scroll-out, three times. I retrained
the released recipe six times — the only change being one scroll removed and the per-batch
quotas renormalised — and scored each pair of seeds on every annotated pixel of the held-
out scroll, against the released checkpoints for which those pixels are training data.
Every segment is reported against its all-positive F1 floor so ink-fraction artifacts
cannot masquerade as transfer. Margin over that floor averages +0.06 toward Paris4, +0.13
toward 1667, +0.17 toward 0139 — and the 0139 arm, trained on HALF the corpus, transfers
best, so target identity dominates source size. On the four segments existing in both
representation families, the aligned render wins 4 out of 4. I first published that as
domain match; a reviewer on villa #1580 pointed out the grid contained a control for that
reading, so I pre-registered the test it could not settle, pushing the design and the
reading committed to each outcome before the runs finished. It refuted me: with native
exposure raised from 0% to 16.4% of training batches, the gap came back unchanged at
+0.058 against +0.061. The cause is sampling density, and that is measured rather than
argued — the published pyramids are byte-exact 2x2 means that never touch z, so one
aligned voxel averages 64 acquired 2.399 µm voxels against native's one. Render aligned,
whatever the model trained on.

I then spent four pre-registered attempts trying to make that instruction unnecessary, and
none of them worked. Filtering the native input to match aligned spectra recovered +0.005 F1.
Training with noise calibrated to the difference was stopped by its own calibration: measured
after the trainer's normalisation, the native input carries *less* high-frequency energy than
the aligned one in 24 of 24 cells, so the correction points at blur rather than noise. The
blur version was stopped too -- the sigma the gap calls for, 0.78, is already inside the range
the recipe samples. Only exposure was left, so I raised the share of patches seeing a
calibrated-strength blur from 2.7% to 50% and ran it: native -0.012, the wrong sign, inside
the noise floor, and the two seeds disagreeing by more than the effect. Two attempts ran and
returned nothing; two were stopped by their own calibrations before consuming GPU time. The
advantage the aligned rendering gives you cannot be recovered by anything I can do without
labels, which is what makes "render aligned" an instruction rather than a preference.

The diagnosis (part 3): the gap is bias, not variance. The two seeds of each arm agree
on held-out scrolls to |ΔF1| ≈ 0.01–0.03 (versus 0.22 within scrolls), and averaging
their predictions recovers only +0.005–0.009 F1. Independent runs fail the same way on
the same pixels — no amount of free ensembling closes this.

The repair price (part 4): one labeled segment. Fine-tuning the leave-Paris4-out model on
a single Paris4 segment lifts the seven segments it has never seen from mean F1 0.496 to
0.822 — 82% of the distance to the train-pixel reference — saturating at 2,500 steps,
about seven minutes on one consumer GPU. Cross-scroll performance peaks at 10–20k steps in
all six LOSO runs and fine-tuning at 2.5k: no held-out axis anywhere justifies the
released 75k schedule.

Then I checked whether that 82% is a fact about the method or about Paris4, because a
single-scroll headline is exactly the kind of thing that gets quoted without its scroll.
It is about Paris4. Repeating the whole comparison on 1667 — same recipe, same steps, its
own base and its own annotated segment, 90 scored cells — one annotated segment buys
+0.104 F1 there against Paris4's +0.320, which is 24% of the way to the reference rather
than 82%. I also ran the obvious escape first: every arm had been stopped at 2,500 because
that is where Paris4 saturates, so I extended all six runs to 10,000 and scored 5,000 and
10,000 too. 1667's fine-tune peaks at 2,500 and falls monotonically after, exactly as
Paris4's does — the saturation point replicates, the magnitude does not. So what an
annotation buys varies threefold between two scrolls of the same corpus, and for open
problem #7 that variance is the more useful number than either headline.

And the price has a price curve (part 5). Rebuilding that fine-tune on nested subsets of
the same annotation — 50.3%, 20.7% and 13.5% of the area, regions kept whole — half the
annotation keeps 89% of the benefit for 0.033 F1: above the noise floor on six of seven
segments, so real, but cheap against halving the annotation work. Below that it bends, a
fifth keeping 71% and an eighth 56%, and the smallest arm is the only one that overfits by
step 5,000. So "annotate one segment" now says annotate half of one.

Then a pre-registered follow-up refuted the reading of that curve, including my own
hypothesis for it. Holding the budget at a fifth and changing only *which* regions are
annotated -- four subsets chosen by rules fixed before the runs -- moves the mean by 0.0373
F1, above the noise floor, with the ordering identical in both seeds and one subset best on
all seven scored segments. The rule I expected to win lost: ranking candidate regions by the
model's own disagreement picked the wrong ones in both seeds, so I report uncertainty
sampling as failed. What replaces it is a correction to my own published number: the 71%
above was a property of that subset, not of that budget, and another subset at a slightly
smaller budget retains 82.9% (docs/20).

Why this raises the probability of reading complete scrolls: the First Letters targets
have no labels, so cross-scroll transfer is the deployment condition, and it now has a
measured playbook instead of a hope. Render the target aligned; use direct inference only
to scout for promising surface; annotate one segment; fine-tune for minutes; re-infer.
Every stage carries an expected value measured here, and re-verifying any proposed
improvement costs one config line and about three GPU hours.

I then ran that playbook on a scroll nobody has read. PHerc1447 ships no rendered surface
volume at all, so I rendered its largest segment (7.40 cm²) from the mesh and fed the result
to the released checkpoints unmodified. Nothing readable came out, and it fails the way the
margins predict: the four checkpoints disagree threefold on how much surface is strong ink,
none reaches full confidence, and at full resolution the output is rounded patches rather
than connected strokes. So step two scouts only in the weak sense — it says the model has
nothing, not where to annotate (docs/16).

So I pre-registered the other ways out too — design, prediction and decision rule pushed
publicly before each run. Parameter space: test-time entropy minimisation on the only
surface the architecture leaves, the 27,712 normalisation affines, costs 0.041 F1 across
fourteen cells with not one improving. I predicted +10 to +40%; it is −13%, refuted with the
sign wrong — and its objective improves monotonically the whole way down, so no label-free
stopping rule built on it could have caught this. Label space: self-training on the model's
own confident pixels is the rung that helps, most when it labels the sheets it is about to
read — +0.046 F1, all fourteen cells improving, 14.3% of the gap. That prices the annotation:
base, recipe and step count fixed, a human's labels on one segment buy +0.32 where the
model's own guesses buy +0.046, so A HUMAN ANNOTATION IS WORTH ABOUT SEVEN TIMES the best
label-free method. And because that method needs no labels I pointed it at PHerc1447 itself
under three criteria fixed beforehand; it met none — the patches stay rounded, the seeds
agree no more on where the ink is, the output collapses to one mode. Self-training amplifies
what a model already believes, and there it believes nothing. None of it crosses to the
second scroll either: on 1667 arm C never leaves the noise floor at any step and arm D is
negative at every step, where on Paris4 it improved 14 of 14 cells. What survives the
crossing is the ordering and the saturation point; what does not is any magnitude
(docs/18).

The apparatus went upstream as well as the numbers. The released recipe does not run as
published — its datasets block is a single placeholder while the 29 representations live
in a separate contract file — so the join, and the holdout flags that turn it into this
probe, are villa PR #1608; it regenerates my three arm configs byte-for-byte. Both have
survived outside hands: one contributor pulled the raw 0139 matrix and recomputed every
published figure, confirming the margins hold under four selection rules, and the same
person then reviewed the generator and found a crash on a batch smaller than the surviving
scroll count, fixed two days later. The traffic went the other way too: the author of villa PR #1471 asked for this harness to
be pointed at their striped-TIFF streaming path, at the odd extents their own testing did
not cover. It reproduces their output exactly on 42 of 42 variants and crashes on any image
whose height leaves a strip of exactly one row, which converts fine today; the fix is
verified against the same matrix. Being reproduced, being corrected, and being asked to
check someone else's work are the three things a measurement of an open problem needs.

Everything is MIT, documented end to end (docs/14–18 plus 100 committed evidence
files), and continuous with the July harness and the August #192 verdict — one
apparatus, three months of answered questions.
```

**6. Terms and Conditions** → check "Yes, I agree"

⚠️ **August's form had six questions, not seven** — the standalone "Pull request submitted!"
checkbox is gone, so the PR is evidenced through field 4 alone. Check September's form when it
opens; the layout above assumes August's.
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Step 3 — on submission day

Everything below the fold is already done and verified; this is the short list to run
before pasting.

0. **⚠️ A full read-through is owed, and has not been done since 2026-09-01.** Field 5 grew
   from 9,822 to 11,475 characters in one day as three results landed (the invited #1471
   check, the annotation-targeting arm, and four attempts on the aligned-over-native gap).
   Two trimming passes removed 1,037 characters of restatement and one stale promise, and
   then stopped: what remains would cost claims, not words. Before submitting, read the
   whole field once end to end for order and repetition — it has been edited in five places
   without anyone reading it as a single piece since the 08-31 trim.
1. **Get September's form** from https://scrollprize.org/prizes. Do not reuse August's
   link — each round issues a new form and closes the previous one. Check the question
   count: August had six (email, name, team, URL, description, terms). If September adds
   back the "Pull request submitted!" checkbox, #1608 is the answer.
2. **Check the four upstream links still say what field 4 says they say** — #1608 (open,
   one review round), #1638 (closed and locked, and field 4 labels it as such), #1249
   (merged). If **#1608 merges**, relabel it "merged" in field 4 and in field 5's
   second-to-last paragraph. ⚠️ **This repository auto-closes a PR after 14 days without
   activity** — that is how #1535 died on 2026-09-03, unreviewed — so check the state of
   every PR cited here on the day, not from memory.
3. **`git push`** and confirm `git status` is clean. Every field-4 link must resolve for a
   judge who is not logged in.
4. **Re-run the two verifiers** if anything in `runs/` changed since 2026-08-30:
   they re-derive every artifact-backed number in field 5 from the committed CSV/JSON.
5. **Paste fields 1–5 from the fenced blocks above, tick Terms, submit.** Then sync this
   file to exactly what was submitted and freeze it, as the July and August files were.
6. **Record the field-5 sha256 over the block body plus one trailing newline** — that is
   the convention the August entry uses, and checking it any other way looks like a
   mismatch.

**Timing.** Judging is monthly after the round closes, so submitting early buys nothing.
Submit when something moves upstream, with the last weekend (09-26/27) as the backstop.

**State as of 2026-08-31**: the two replies above were posted on 08-30; the invited #1471 check
was run and added to fields 4 and 5; 100 committed evidence files; every cited path in this
file resolves in the repository (23 of 23), which was not true of the August text until
today — its evidence table pointed at nine `runs/*.json` that lived only in an untracked
tree, and those files are now committed at the cited paths.

**Update 2026-09-04**: `pr1471_reply_jaideepsaipadhi.md` was posted on 08-31. #1535 was
closed by the inactivity bot on 09-03. Five further replies are drafted and unposted —
`pr1471_reply_hendrikschilling.md` (the maintainer is deciding whether to close that PR),
`pr1608_base_branch_question.md`, and the three `pr166x_*_followup.md`.

Field hashes at this revision, over the block body plus one trailing newline — the
convention the August entry uses:

- field 4 — 2,015 chars, `39a669d5c4f87e8afd8ce62f78f590caa4fb60553593dda3750d1f9728acfbac`
- field 5 — 11,475 chars, `ea82e5959e84f0e32be654454c537da10f896c7608ae4012cd144f769ad606cd`

If either field is edited before submitting, recompute these and record the new pair
against what was actually pasted.

---

## Evidence backing the claims above

| claim | source |
|---|---|
| label-efficiency: half the annotation keeps 89% for −0.033 F1; a fifth 71%, an eighth 56% | `runs/ink9um_scorecard/labelbudget_matrix.csv` (84 cells) + `labelbudget_summary.json`, `docs/15` part 5 |
| annotation targeting (pre-registered, 42 cells): at a fifth of the annotation the subset choice moves the mean 0.0373 F1, ordering identical in both seeds, one subset best on 7 of 7 segments; the disagreement rule loses by 0.017/0.024; benefit retained 70.8% → 82.9% at a smaller budget | `runs/ink9um_scorecard/annotarget_matrix.csv` + `annotarget_summary.json` + `annotation_candidates.json`, `docs/20` |
| arm A: spectrum matching gains +0.005 F1, median 9.1% of the aligned gap — no effect by the pre-registered rule | `runs/ink9um_scorecard/armA_specmatch_matrix.csv` (48 cells) + summary, `docs/18` |
| the aligned advantage resists four pre-registered attempts: spectrum matching +0.005; noise stopped by calibration (native smoother in 24 of 24 cells); blur strength stopped (calibrated 0.78 already inside the recipe's 0.5–3.0); blur exposure 2.7% → 50% run and returning −0.012, seeds disagreeing in sign | `runs/ink9um_scorecard/representation_noise.json`, `blur_calibration.json`, `blurexp_matrix.csv` (16 cells) + `blurexp_summary.json`, `docs/21`–`docs/23` |
| arm B: entropy minimisation costs −0.041 F1, 0 of 14 cells improving, four cells on the trivial floor; AUC 0.66 → 0.48–0.55 on the three rank-checked cells while the objective keeps falling | `runs/ink9um_scorecard/armB_tent_matrix.csv` (34 cells) + `armB_tent_summary.json` + `armB_rank_check_*.json`, `docs/18` |
| arm C: self-training gains +0.030 F1, 14 of 14 cells, 9.5% of the gap — against +0.320 for a human annotation on the same segment with everything else fixed | `runs/ink9um_scorecard/armC_pseudo_matrix.csv` (18 cells) + `armC_pseudo_summary.json` + `armC_rank_check_w01_s42.json`, `docs/18` |
| arm D (transductive): +0.046 F1, 14 of 14 cells, 14.3% of the gap, AUC 0.659 → 0.742; pre-registered at +5–30% | `runs/ink9um_scorecard/armD_pseudoT_matrix.csv` (18 cells) + `armD_pseudoT_summary.json` + `armD_rank_check_w01_s42.json`, `docs/18` |
| arm D on PHerc1447 (unscoreable, judged against criteria fixed first): 0 of 3 met — patches not strokes, top-decile seed overlap 0.173 → 0.177, one-mode collapse | `runs/first_letters/pherc1447_armD_compare.json` + `pherc1447_base_on_sheet.json`, `docs/images/pherc1447_armD_before_after.png`, `docs/18` |
| 1667 replication (90 cells, 3 arms x 3 steps): one annotated segment buys +0.104 (24%) against Paris4's +0.320 (82%); arm C inside the noise, arm D negative at every step; fine-tune peaks at 2,500 on both scrolls | `runs/ink9um_scorecard/r1667_matrix.csv` + `r1667_stepcurve_summary.json`, `docs/18` |
| the published pyramids are 2×2 means and never touch z, so one aligned voxel averages 64 acquired voxels | `runs/pyramid/*_pooling.json` (3 scrolls, 18 windows), `docs/15` appendix 3 |
| held-out masks cut through regions: 2 of 3 / 1 of 1 / 1 of 8 regions mixed; 58.6% / 45.0% / 23.2% within one patch | `runs/ink9um_holdout_audit/*_audit.json`, `docs/17`; villa #1638, closed by the research lead — see the note below |
| adjacency excess gain +0.1375 (w016) / +0.0733 (w029), 20 of 28 checkpoints | `runs/ink9um_scorecard/leak_strata.csv` (168 rows), `docs/17` |
| within-scroll honest ceiling 0.74–0.77; memorisation gap 0.22–0.45; seed spread 0.22 @75k | `runs/ink9um_scorecard/scorecard.csv` (+`summary.json`), `docs/14` |
| LOSO→Paris4 mean 0.487, floor margin +0.060 | `paris4_matrix.csv` (+`paris4_matrix_summary.json`) |
| LOSO→1667 mean 0.546, floor margin +0.131 | `no1667_matrix.csv` (+`no1667_matrix_summary.json`) |
| LOSO→0139 mean 0.678, floor margin +0.169; aligned>native 4/4 (+0.03..0.07) | `no0139_matrix.csv` (+`no0139_matrix_summary.json`, `representation_pairs`) |
| domain match refuted: gap +0.058 with native at 16.4% of batches vs +0.061 at 0%; 2/2 at every checkpoint | `segloso_matrix.csv` (+`segloso_matrix_summary.json`), design pre-registered in commit `fb37974` |
| ref arms 0.86–0.99 on the same pixels | `ref42`/`ref43` rows of the three matrix CSVs |
| honest-to-honest drops −0.26 (Paris4) / −0.17 (w029 0.758→0.589) | `docs/14` ceiling vs matrix CSVs |
| seed agreement \|ΔF1\| 0.011 / 0.015 / 0.032 | `loso_seed_abs_diff_*` in the three summary JSONs |
| ensembling recovers +0.005..+0.009 (seed) / ±0.007 (step) | `loso_ensembles.csv` (+`loso_ensembles_summary.json`) |
| one-segment fine-tune: 0.496→0.822 mean, 78–90% closure, saturates @2.5k steps | `ft_paris4_matrix.csv` (+`ft_paris4_summary.json`) |
| LOSO peak at 10–20k, decline to 75k | `stepwise_mean_loso` in the three summary JSONs |
| all-positive floor 2p/(1+p) per segment | `floors` in the summary JSONs |
| recipe fidelity (quota renormalisation, 15/21/23 reps; FT = w00-only + weights-only load) | `configs/ink9um_loso_*.json`, `configs/ink9um_ft_w00_*.json`, generated by `tools/make_ink9um_config.py` |
| reproduction validity (online val 0.69–0.78 on official masks across arms) | `runs/ink9um_loso_*/validation_metrics.jsonl` |
| independent recomputation of the 0139 table, margins hold under 4 selection rules | Bullo27 on villa #1580, 2026-08-24 |
| generator upstreamed, reviewed, crash fixed | villa #1608 (`dc9edb6`), `submission/pr1608_body.md` + `pr1608_reply_bullo27.md` |
| invited check of villa #1471: 42/42 variants identical at six levels (9,661,092,220 voxels); a one-row strip crashes the new path (`rowsperstrip == 1` or `height % rowsperstrip == 1`) and the fix is verified 18/18; on a real 32249×51380 mask the read-back design costs 3.0x wall for 2.2x peak RSS | `runs/pr1471_striped_check/` (matrix, targeted re-run, real-file timings, and `verify_numbers.py` re-deriving all 38 figures), `submission/pr1471_reply_jaideepsaipadhi.md` |

(Checkpoints and prediction TIFFs stay untracked; the committed CSV/JSON files reproduce
every quoted figure.)

---

## Notes for whoever finalises this

* **Do not re-claim the scorecard as September work if August's form went in with its
  scorecard paragraph** — here it is framed as groundwork (second paragraph of field 5).
  If August was submitted WITHOUT that paragraph, promote docs/14 freely.
* ~~**Field-6 PR is the one genuinely open item**~~ — **resolved 2026-08-28**: #1608 is the
  field-6 PR, its URL is in field 4 and field 5's second-to-last paragraph carries the
  review round. If it merges before submitting, relabel it "merged" the way August did
  with #1234.
* **Fold in September events before submitting**: ①✅ done — the render path ran on
  2026-08-26 and its negative result is now the field-5 paragraph after the playbook
  (docs/16); if more segments get rendered before submitting, update the count there
  ②upstream replies that touch the framing — #1231 still silent; **stantheman0128's scoring
  of our depth band landed 2026-08-25 and belongs to August, not here** (it is folded into
  the August form's field 5; do not repeat it); #1535 was auto-closed unreviewed on
  2026-09-03; **two replies were
  drafted 2026-08-30 and are waiting on the user to post them** (`issue1582_reply_nerln.md`,
  `issue1611_reply_bullo27_round2.md`) — if either draws an answer that changes the framing,
  it belongs here ③✅ done — the label-efficiency curve (docs/15 part 5) and the full
  adaptation ladder (docs/18 arms A, B, C) both ran and are in field 5.
* **Honesty guardrails already embedded in the text** — keep them through edits: closure
  percentages use the train-pixel ref as denominator (generous baseline, said as such);
  "one segment" is w00, one of the larger Paris4 annotations; best-of-grid comparisons
  are oracle-selected on both sides.
* **Push before submitting** — docs/14–18, tools, configs and the evidence files must
  resolve publicly; every field-4 link is checked. (As of 2026-08-30 everything is pushed,
  including all three adaptation arms and the pooling reports; all 17 links verified 200.)
* **Do not soften the refutation** — the pre-registered arm that broke our own domain-match
  reading is an asset, not a wound: claim published → outside reviewer presses → falsifiable
  test registered in public before the run → claim dies → retraction posted upstream and in
  docs/15. That chain is the documentation axis. If space is tight elsewhere, cut something
  else.
* Timing: judging is monthly after the round closes, so early submission buys nothing;
  same submit-when-something-moves logic as August, backstop the last weekend (09-26/27).
