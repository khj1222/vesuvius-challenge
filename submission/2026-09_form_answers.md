# 9월 Progress Prize — v30 ✅ **제출 완료 2026-09-20** (이 파일 = 제출본, 동결)

고정 임계값 평가를 완료하고 주석 픽셀 중복 집계 영향을 함께 검증했습니다.
공개 근거 17파일은 c063ae5, 공개 답안 v29는 186b2db에 반영돼 있습니다. 09-20 재검토에서 답안 HTTPS 링크 22/22와 공개 근거·문서 19/19 일치를 확인했습니다.
v30은 스크롤 특성과 학습 데이터 구성의 혼재를 명시하고, 문서 범위·해시·게시 기록을 정리한 로컬 미커밋·미푸시 수정안입니다. 실험 수치는 바꾸지 않았습니다.
**2026-09-20 KST 폼 제출 완료**(Chrome, bluekgssk@gmail.com 로그인 세션, 확인 화면 "Thanks for submitting your open source contributions!" 수신; 응답 사본 메일 자동 발송 설정). 제출 직전 브라우저 안에서 field 4/5 SHA-256이 이 파일·final_audit.json과 일치함을 확인. Discord 표시 이름은 비움. 상세: `planning/2026-09-20_fixed_threshold/report.md`.

## 1. Email

```
bluekgssk@gmail.com
```

## 2. Your full name

```
Hyojun Kwon
```

## 3. Team description

```
Individual submission — no team.
```

## Discord display name (선택)

서버에서 사용하는 실제 표시 이름을 넣거나 비워 두세요.

## 4. URL of your open source / publicly available contribution

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

## 5. What is your contribution?

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

## Terms and Conditions

폼의 약관을 검토한 뒤 동의하면 **Yes, I agree**를 선택하고 직접 제출하세요.
제출 확인 화면이나 응답 사본을 보관하세요. 이 문서는 접수 확인서가 아닙니다.

- field 4: 2,879자 · SHA-256 `2d18df8c5e0af6adc9c710fec57872277aa3b323659746b35aee3c69316e9247`
- field 5: 15,666자 · SHA-256 `5e1f95bb86fdc579273e08b7ebb22dbdd2f55e6fb94a6da0991a69d0980f20b9`
