# September 2026 Progress Prize — submission package (evidence follow-up complete, not submitted)

**v28 evidence follow-up, 2026-09-20:** separate-segment fixed-threshold evaluation
is complete using saved predictions. The scoring audit removes duplicated pixel counts
for the new results and preserves the historical comparisons. Public research corrections and evidence were pushed on 2026-09-20 (commit c063ae5); all 14 repository links in the form answers return 200 and the 17 published files match the local commit byte for byte.
The scouting gate remains invalid as a signal-absence test. PR1703 is still a local
follow-up and has not been added as an adopted contribution. No form submission occurred.
See `planning/2026-09-20_fixed_threshold/report.md`.

**Form:** https://docs.google.com/forms/d/e/1FAIpQLScNBMj25FMnphngRG1Ciryv_2_Mkdq2YPJOD9WqPfZExII2iQ/viewform
Verified through https://scrollprize.org/prizes and the live form on 2026-09-20 KST.
**Deadline:** 2026-09-30 23:59 Pacific = 2026-10-01 15:59 KST.
**Current status: SUBMITTED 2026-09-20 (KST) as v30 — form confirmation received; fields 4 and 5 verified in-browser against the recorded hashes before submit. This file is now frozen as the submitted text.** The target/source-size interpretation is now scoped to the confounded comparison. Public evidence remains available at c063ae5, and the published answers are v29 at 186b2db. The v30 answers and record corrections are local, uncommitted and not pushed.
Copy-ready answers: [2026-09_form_answers.md](2026-09_form_answers.md).

The v25 research narrative remains the basis, following the September 18 freeze decision.
The earlier v26 finalization added the September 19 scouting result as agreed: one URL in field 4 and one
sentence after the PHerc1447 paragraph in field 5. It also records #1608's automatic closure
on September 19 (not merged), removes unsupported present-tense claims about what upstream
does not provide, and updates the form prompt/checklist. #1701 remains open, so the conditional
merged-contribution addition is not included. That earlier finalization did not run a new experiment or publish changes; the v28 follow-up is recorded above.

The September small-fix PRs already exist and the recorded scouting run is complete.
The September 20 request reopened October candidate research alongside existing PR follow-up;
see `planning/2026-09-20_october_search/report.md`. This does not add an October result to
this September submission. Earlier revision notes are preserved in the v25 snapshot.

## Step 1 — upstream contribution submitted; PR now closed

**[#1608](https://github.com/ScrollPrize/villa/pull/1608)** — `ink-detection/scripts/make_holdout_config.py`,
opened 2026-08-26 against `merge-ink-pipelines`, 1 file; automatically closed
on 2026-09-19 for 14 days without activity, not merged. The
`--exclude-scroll` / `--exclude-segment` flags, and the quota renormalisation they force,
turn the released recipe into the cross-scroll probe this submission is about. Body follows
`villa/CONTRIBUTING.md` including the human "why this matters to me" paragraph
(`submission/pr1608_body.md`). One round of outside review already closed: Bullo27
reproduced the quota arithmetic, found a crash when `batch_size` is below the surviving
scroll count, and the fix went up as `dc9edb6` two days later
(`submission/pr1608_reply_bullo27.md`).

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

**Discord display name (optional, between team and URL on September's form)**
Use the user's actual server display name if they choose to supply it; otherwise leave blank.
The field-4/field-5 labels below are retained as the document's stable references.

**4. URL to your open source / publicly available contribution**
```
https://github.com/khj1222/vesuvius-challenge
Result writeup (cross-scroll study): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/15_loso_cross_scroll.md
Groundwork (first scorecard of the released ink_9um models): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/14_ink9um_scorecard.md
Arm generator: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/make_ink9um_config.py
Raw numbers (1,838 scored cells, 47 CSV/JSON evidence files): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard
Dataset and models measured: https://huggingface.co/scrollprize/ink_9um (models), hf://buckets/scrollprize/datasets/ink_9um (labels)
Audit of the corpus's own held-out masks: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/17_holdout_audit.md
Audit tool: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/audit_holdout_masks.py
Pre-registered adaptation study, three arms, all run: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/18_uda_design.md
Pre-registered check of the yardstick itself (both stages run): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/24_pseudo_label_validation.md
Pre-registered targeting test (where to annotate, and the published curve it corrects): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/20_annotation_targeting.md
Four pre-registered attempts on the aligned-over-native gap, two stopped by their own calibrations: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/23_blur_exposure.md
Adaptation and audit tools written for it: https://github.com/khj1222/vesuvius-challenge/tree/main/tools
Upstream PR (arm generator; auto-closed 2026-09-19, not merged): https://github.com/ScrollPrize/villa/pull/1608
Upstream issue (held-out audit; filed and closed by the research lead — the concession is in docs/17): https://github.com/ScrollPrize/villa/issues/1638
Invited check of another contributor's PR (found a crash, verified a fix): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/pr1471_striped_check
Author incorporated and credited the one-row-strip fix (2026-09-08; merged into villa main 2026-09-10): https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5586571289
Incorporating commit: https://github.com/ScrollPrize/villa/commit/29d2863878a751e37d6d1d0a02f2847101c8c5a0
Final merge commit: https://github.com/ScrollPrize/villa/commit/43f93f4b5aa2fd093673ac74e8a6d923d2f7833d
Open problem addressed: https://scrollprize.org/2026_open_problems (#7, cross-scroll ink generalization)
Fixed-threshold follow-up and counting audit: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/26_fixed_threshold_finetuning.md
Scouting follow-up (43 public surfaces, 0 candidates; protocol and scorecard): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/25_scouting_eligible_volumes.md
```

**5. What is your contribution?**

The live form asks: (1) Which scroll data did you work on? (2) How does this increase the
probability of reading those scrolls or others? (3) What does it enable? (4) What evidence
have you provided? The answer below addresses all four; field numbering here is stable.

```
Reading a complete scroll means running an ink model on a scroll nobody has labeled. Open
problem #7 asks how well models survive that jump. I measured it against withheld annotation
using the official 9 µm models released on 2026-08-14, investigated the failures, measured
what target-scroll annotation buys, and checked whether that benefit holds on a second scroll.
I used the held-out methodology that won July's Progress Prize and was used in August to
test one proposed depth-label approach to villa #192.

Previously submitted groundwork (August, docs/14): scoring all 14 released hybrid_3d2d
checkpoints on the three segments that ship validation masks puts the honest within-scroll
ceiling at F1 0.74–0.77
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
best in this comparison. Source size alone does not explain the ordering, while source
composition and target identity are confounded. On the four segments existing in both
representation families, the aligned render wins 4 out of 4. I first published that as
domain match; a reviewer on villa #1580 pointed out the grid contained a control for that
reading, so I pre-registered the test it could not settle, pushing the design and the
reading committed to each outcome before the runs finished. It refuted me: with native
exposure raised from 0% to 16.4% of training batches, the gap came back unchanged at
+0.058 against +0.061. Sampling density is a plausible contributor: the published pyramids are byte-exact
2x2 means that never touch z, so one aligned voxel averages 64 acquired 2.399 µm voxels
against native's one. This verifies the construction, not a unique causal explanation;
acquisition and target composition remain confounded. Aligned rendering won on the four
paired segments tested.

I then spent four pre-registered attempts trying to make that instruction unnecessary, and
none of them worked. Filtering the native input to match aligned spectra recovered +0.005 F1.
Training with noise calibrated to the difference was stopped by its own calibration: measured
after the trainer's normalisation, the native input carries *less* high-frequency energy than
the aligned one in 24 of 24 cells, so the correction points at blur rather than noise. The
blur version was stopped too — the sigma the gap calls for, 0.78, is already inside the range
the recipe samples. Only exposure was left, so I raised the share of patches seeing a
calibrated-strength blur from 2.7% to 50% and ran it: native -0.012, the wrong sign, inside
the noise floor, and the two seeds disagreeing by more than the effect. Two attempts ran and
returned nothing; two were stopped by their own calibrations before consuming GPU time. The
advantage of aligned rendering was not recovered by these four attempted interventions;
this does not rule out other methods without labels.

The diagnosis (part 3): the tested averaging schemes recover little of the gap. The two seeds of each arm agree
on held-out scrolls to |ΔF1| ≈ 0.01–0.03 (versus 0.22 within scrolls), and averaging
their predictions recovers only +0.005–0.009 F1. Independent runs fail the same way on
the same pixels, and the tested seed/step ensembles did not close the gap.

The repair price (part 4): one labeled segment. Fine-tuning the leave-Paris4-out model on
a single Paris4 segment lifts the seven segments it has never seen from mean F1 0.496 to
0.822 — 82% of the distance to the train-pixel reference — saturating at 2,500 steps,
about seven minutes on one consumer GPU. Cross-scroll performance peaks at 10–20k steps in
all six LOSO runs and fine-tuning at 2.5k: no held-out axis anywhere justifies the
released 75k schedule.

These F1 values use per-prediction threshold sweeps; the LOSO and fine-tuning summaries also
select the best checkpoint per segment. They measure attainable performance under those rules,
not a fixed-threshold deployment on an unread scroll. The recovery denominator is the
train-pixel reference, not an independent generalisation ceiling (docs/15).

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

A retrospective September 20 follow-up held each arm/seed's threshold fixed after calibration
on one additional labeled segment per scroll (Paris4 w01, 1667 w013). Excluding both
calibration and FT-training segments, same-seed paired means are Paris4 0.485→0.790 F1 (12/12
comparisons improve) and 1667 0.531→0.629 (8/8 improve), with the base at 20k steps for Paris4
and 10k for 1667 and the fine-tune at 2,500 in both. Both arms receive identical calibration
labels. This uses additional annotation and previously inspected data, not label-free
unread-scroll validation. A counting audit found overlapping region boxes in the historical
evaluator; this follow-up counts each labeled pixel once and reproduces the legacy counts
separately (maximum fixed-F1 difference 0.000473; docs/26). Historical headlines retain their
original counting and selection rules.

And the price has a price curve (part 5). Rebuilding that fine-tune on nested subsets of
the same annotation — 50.3%, 20.7% and 13.5% of the area, regions kept whole — half the
annotation keeps 89% of the benefit for 0.033 F1: above the noise floor on six of seven
segments. This halves labeled area; human annotation time was not measured. Below that it bends, a
fifth keeping 71% and an eighth 56%, and the smallest arm is the only one that overfits by
step 5,000. This is a budget result on Paris4, conditional on which regions are kept.

Then a pre-registered follow-up refuted the reading of that curve, including my own
hypothesis for it. Holding the budget at a fifth and changing only *which* regions are
annotated — four subsets chosen by rules fixed before the runs — moves the mean by 0.0373
F1, above the noise floor, with the ordering identical in both seeds and one subset best on
all seven scored segments. The rule I expected to win lost: ranking candidate regions by the
model's own disagreement picked the wrong ones in both seeds, so I report uncertainty
sampling as failed. What replaces it is a correction to my own published number: the 71%
above was a property of that subset, not of that budget, and another subset at a slightly
smaller budget retains 82.9% (docs/20).

Why this raises the probability of reading complete scrolls: the First Letters targets have no
labels, so cross-scroll transfer is the deployment condition, and it now has a measured
playbook instead of a hope. Render the target aligned; use direct inference only to scout for
promising surface; annotate one segment; fine-tune for minutes; re-infer. The labeled-scroll
experiments quantify some of these steps; unread-scroll scouting and fixed-threshold deployment
on an unread scroll still require validation.

I then ran that playbook on a scroll nobody has read. For PHerc1447 I rendered the largest
segment in that experiment (7.40 cm²) from its mesh and fed the result to the released
checkpoints unmodified. Nothing readable came out, and it fails the way the
margins predict: the four checkpoints disagree threefold on how much surface is strong ink,
none reaches full confidence, and at full resolution the output is rounded patches rather
than connected strokes. So step two scouts only in the weak sense — it says the model has
no convincing readable structure in these outputs, not an absence of ink (docs/16).
A September 19 follow-up screened 43 public surfaces across PHerc0800, PHerc1447 and PHerc1203
in both orientations: none passed the seed-agreement gate calibrated on a held-out-scroll
control and registered before target inference, so scouting stopped (docs/25). A later
control audit found that the complete gate can also reject a known ink-positive surface.
The zero is a result of that rule, not evidence of sensitivity or absence of text; the
20 eligible volumes without public meshes were not tested.

So I pre-registered the other ways out too — design, prediction and decision rule pushed
publicly before each run. Parameter space: test-time entropy minimisation on the only
surface the architecture leaves, the 27,712 normalisation affines, costs 0.041 F1 across
fourteen cells with not one improving. I predicted +10 to +40%; it is −13%, refuted with the
sign wrong — and its objective improves monotonically the whole way down, so no label-free
stopping rule built on it could have caught this. Label space: self-training on the model's
own confident pixels is the rung that helps, most when it labels the sheets it is about to
read — +0.046 F1, all fourteen cells improving, 14.3% of the gap. That prices the annotation:
base, recipe and step count fixed, a human's labels on one segment buy +0.32 where the
model's own guesses buy +0.046, so a human annotation is worth about seven times the best
label-free method tested in this experiment.

And because that method needs no labels I pointed it at PHerc1447 itself under three
criteria fixed beforehand; it met none — the patches stay rounded, the seeds agree no more
on where the ink is, the output collapses to one mode. Self-training amplifies what a model
already believes, and there it believes nothing. None of it crosses to the second scroll
either: on 1667 arm C never leaves the noise floor at any step and arm D is negative at
every step, where on Paris4 it improved 14 of 14 cells (docs/18).

The page that names this open problem reports its own step forward as a validation Dice
computed on pseudo-labels, so I measured what that instrument reads (docs/24, pre-registered
before the numbers). Scored against the annotation withheld from the runs that consumed them,
my pseudo-labels agree at F1 0.39–0.46 and lose to marking every pixel as ink in 11 of 24 cells
— while being the very labels that improved 14 of 14 above. Training signal and yardstick are
not the same object. Then, scoring one inference with both sticks across 30 cells, the choices
are equivalent within the registered 0.03 F1 tolerance on all five segments. Exact checkpoint
matches are 6 of 10 seed-by-segment pairs, or 2 of 5 segments when both seeds must match. My
registered disagreement prediction was not supported. This is a weak result: the pseudo score
rises monotonically, so it always answers “the latest”, and truth varies by less than the noise
floor in 9 of 10 cells, leaving little to get wrong. One thing I did not register: the two pick
operating thresholds an average of 45.33 grey levels apart (range 18–71), in the same direction
in all 30 cells. The saved 8-level sweep gives an approximate mean F1 loss of 0.066 at the
pseudo-selected threshold. Accounting conservatively for sweep spacing and rounding bounds the
mean loss between 0.054991 and 0.078671; this is a numerical bound, not a confidence interval.
It is a retrospective observation, not a pre-registered threshold-calibration experiment.

The apparatus went upstream as well as the numbers. I submitted scroll/segment exclusions
and the corresponding per-batch quota renormalisation as villa PR #1608; it regenerates my
three arm configs byte-for-byte. The PR was automatically closed on September 19 for
inactivity and has not merged. Numbers and apparatus have both survived outside hands: one
contributor pulled the raw 0139 matrix and recomputed
every published figure, confirming the margins hold under four selection rules, and the same
person then reviewed the generator and found a crash on a batch smaller than the surviving
scroll count, fixed two days later. The traffic went the other way too: the author of villa
PR #1471 asked for this harness to be pointed at their striped-TIFF streaming path, at the
odd extents their own testing did not cover. On the revision tested in August, 42 of 42
comparable variants matched the parent at all six levels; a strip of exactly one row
crashed the new path, and I supplied a verified fix. On September 8 the author incorporated
that fix as `_decoded_block_to_2d` in commit 29d2863 and explicitly credited this project's
55-variant matrix in the commit and their follow-up comment (linked in field 4). On September
10 the contributor's PR merged into villa `main` as 43f93f4. Its final implementation also
decodes each source chunk once and removed an unenforced memory-budget path after review; I
have not re-tested that final rewrite. The adoption claim is limited to the incorporated
one-row-strip fix and verification, not a pass verdict on every later implementation change.

Everything is MIT, documented end to end (docs/14–18 and docs/20–26, with
public CSV/JSON evidence under runs/), and continuous with the July harness and the
August depth-label study — one apparatus, three months of measured questions. Nothing here asks
the pipeline to change shape around it: pseudo-labels are written to the corpus's own label
contract, adapted checkpoints load in `infer` unmodified, and predictions use the pipeline's
Zarr/TIFF formats, with scores in CSV/JSON. The added tools make the held-out comparisons
and quota-preserving experiment configs reproducible.
```

**6. Terms and Conditions** → check "Yes, I agree"

**September form checked 2026-09-20:** email, name, team, optional Discord display name,
contribution URLs, contribution description, and terms. There is no standalone
"Pull request submitted!" checkbox. Supply the optional Discord name separately if desired.
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Step 3 — research follow-up complete; actual submission remains separate

- [x] Confirm September's live form, current questions and official deadline (2026-09-20 KST).
- [x] Correct the audited v26 claims locally; retain the complete v26 snapshot.
- [x] Complete fixed-threshold evaluation and document unique/legacy counting.
- [x] Publish and verify the corrected research documents and numerical evidence (c063ae5;
      all 17 files independently matched against remote main 186b2db on 2026-09-20).
- [x] Verify #1608 CLOSED, not merged; #1471 MERGED, with the final rewrite not re-tested here.
- [x] Preserve August's submitted file and the 135 existing archived-file deletions.
- [x] Re-read the final answers and record their hashes below.
- [ ] On the actual submission day, recheck the form and cited PR states. If #1701 has merged,
      the prior decision permits one supporting URL; otherwise leave it out.
- [ ] Paste the five fenced answers, optionally supply the actual Discord display name, review
      and accept Terms, and submit. The user performs the final form submission.
- [ ] Save the confirmation/response copy and freeze exactly the submitted answers and hashes.

Public research corrections and evidence were pushed on 2026-09-20 (commit c063ae5); all 14 repository links in the form answers return 200 and the 17 published files match the local commit byte for byte.
The September 27–28 PR follow-up and actual form submission remain separate.

Current field hashes (v30, 2026-09-20), calculated over each fenced block body
with LF line endings and exactly one trailing newline:

- field 4 — 2,879 chars, `2d18df8c5e0af6adc9c710fec57872277aa3b323659746b35aee3c69316e9247`
- field 5 — 15,666 chars, `5e1f95bb86fdc579273e08b7ebb22dbdd2f55e6fb94a6da0991a69d0980f20b9`

If either field is edited before submitting, recompute these against the actual pasted text.
The full v25 document and historical field hashes are preserved in
`planning/2026-09-20_submission_finalization/september_v25.md`.

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
| #1471 author incorporated and credited the one-row-strip fix on 2026-09-08; PR merged into villa `main` on 2026-09-10; final source-chunk-major rewrite not re-tested by this project | [author confirmation](https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5586571289), [commit 29d2863](https://github.com/ScrollPrize/villa/commit/29d2863878a751e37d6d1d0a02f2847101c8c5a0), [merge 43f93f4](https://github.com/ScrollPrize/villa/commit/43f93f4b5aa2fd093673ac74e8a6d923d2f7833d) |
| September 19 scouting: 43 surfaces in 3 scrolls, 0 candidates under the pre-target v2 gate; both orientations scored; 20 mesh-less eligible volumes untested | `docs/25_scouting_eligible_volumes.md`, `runs/scouting/scorecard.json`, `runs/scouting/scores/` |

(Checkpoints and prediction TIFFs stay untracked; the committed CSV/JSON files reproduce
every quoted figure.)

---
