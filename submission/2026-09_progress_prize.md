# September 2026 Progress Prize — submission package (DRAFT)

**Form:** TBD — each round has its own Google Form and the previous one closes.
Fetch September's from https://scrollprize.org/prizes when the round opens
(August's was https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform).
**Deadline:** 2026-09-30 23:59 PT
**Status:** DRAFT v9 (2026-08-30). Arm D — the transductive variant of arm C, pre-registered
at commit `923895d` before it ran — landed at **14.3% of the gap** and is folded into the
ladder paragraph and the evidence table. v8 was the full pre-submission audit. The adaptation ladder
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

Field 5 is ~10,500 characters, which is long. The measurement paragraph was already tightened
once (2026-08-30) to pay for the adaptation-ladder paragraph. If it has to shrink further, cut
the spectral detail from the ladder paragraph next — arm A's numbers live in docs/18 — and then
the audit paragraph, whose detail is in docs/17.

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
3. Not [#1535](https://github.com/ScrollPrize/villa/pull/1535) — it technically satisfies
   "submitted", but it is August's story and August already cites it.

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
Raw numbers (1,612 scored cells, 27 CSV/JSON evidence files): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard
Dataset and models measured: https://huggingface.co/scrollprize/ink_9um (models), hf://buckets/scrollprize/datasets/ink_9um (labels)
Audit of the corpus's own held-out masks: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/17_holdout_audit.md
Audit tool: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/audit_holdout_masks.py
Pre-registered adaptation study, three arms, all run: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/18_uda_design.md
Adaptation and audit tools written for it: https://github.com/khj1222/vesuvius-challenge/tree/main/tools
Upstream PR (this round, the arm generator): https://github.com/ScrollPrize/villa/pull/1608
Upstream issue (held-out audit; filed and closed by the research lead — the concession is in docs/17): https://github.com/ScrollPrize/villa/issues/1638
Open problem addressed: https://scrollprize.org/2026_open_problems (#7, cross-scroll ink generalization)
```

**5. Short description of how your contributions substantially increase the probability of reading complete scrolls**

```
Reading a complete scroll means running an ink model on a scroll nobody has labeled.
Open problem #7 asks how well today's models survive that jump; until now there was no
systematic number — the official 9 µm models released on 2026-08-14 ship with no
evaluation at all. I measured the jump, diagnosed why it fails, and priced what it costs
to fix — all on that release, with the held-out methodology that won July's Progress
Prize and settled villa #192 in August.

Groundwork first (docs/14): scoring all 14 released hybrid_3d2d checkpoints on the three
segments that ship validation masks puts the honest within-scroll ceiling at F1 0.74–0.77
— the best value any released checkpoint reaches is 0.755, 0.758 and 0.765, one per
segment — against 0.98+ on training pixels: a 0.22–0.45 memorisation gap, no step that is
best everywhere, and two released seeds that disagree by 0.22 F1 at the final step.

That yardstick then had to be checked itself, because everything honest on this corpus rests
on three masks — and all three split their annotation *within* connected regions, so 23% to
59% of their held-out pixels sit inside one 128px training patch of pixels the model trained
on. Whether that adjacency pays needed no new training: the released checkpoints trained on
those segments and my leave-one-scroll-out arms never saw the scrolls, so scoring both over
the same distance strata separates proximity from how hard a stratum is. The control comes
out nearly flat while the trained model gains +0.14 and +0.07 F1 more on the held-out pixels
nearest its training pixels.

I filed that upstream as villa #1638 and the research lead closed it the same day: the masks
are disjoint from supervision, so nothing was trained on, and an intra-segment held-out number
is legitimate provided it is named that and not read as inter-segment or inter-scroll. He is
right, and the framing was mine to fix. What survives the correction is the size — his own
advice is that those three kinds of result must be read differently, and this measures what
that difference is worth here, which is why the 0.74–0.77 above is an intra-segment ceiling
and not a statement about what these models generalise to (docs/17).

Then the measurement (docs/15, parts 1–2): leave-one-scroll-out, three times. I retrained
the exact released recipe six times — the only change being one scroll removed and the
per-batch quotas renormalised — and scored each pair of seeds on every annotated pixel of
the held-out scroll, against the released checkpoints for which those same pixels are
training data. Every segment is reported against its all-positive F1 floor (2p/(1+p)) so
ink-fraction artifacts cannot masquerade as transfer. The spectrum: margin over the
trivial classifier averages +0.06 toward Paris4, +0.13 toward 1667, +0.17 toward 0139 —
and the 0139 arm, trained on HALF the corpus, transfers best, so target-scroll identity
dominates source size. On the four physical segments that exist in both representation
families, transfer to the aligned representation beats the native render 4 out of 4. I
first published that as domain match — models transfer best into the family they trained
on — and a reviewer on villa #1580 pointed out the grid contained a control for that
reading. So I pre-registered the test it could not settle, pushing the design and the
reading committed to each outcome before the runs finished, and it refuted me: with the
same segments held out in both families, native exposure raised from 0% to 16.4% of
training batches, the gap came back unchanged at +0.058 against +0.061. The mechanism is
not familiarity but quality, and the reviewer who proposed why — aligned inputs are
averages of many acquired samples — flagged the assumption it rested on: are the published
pyramids averaged or decimated? Reading them says averaged — byte-exact in all 18 window
comparisons across three scrolls, and another contributor reached the same answer on the
thread the same day; and they never touch z, so
the recipe's 4x z pool multiplies the in-plane 16 again. One aligned voxel is the mean of
64 acquired 2.399 µm voxels where the native voxel covering the same space is a single
9.362 µm acquisition. Render aligned, whatever the model trained on. Retraction in docs/15
appendix 2, pooling measurement in appendix 3, both on the upstream thread.

The diagnosis (part 3): the gap is bias, not variance. The two seeds of each arm agree
on held-out scrolls to |ΔF1| ≈ 0.01–0.03 (versus 0.22 within scrolls), and averaging
their predictions recovers only +0.005–0.009 F1. Independent runs fail the same way on
the same pixels — no amount of free ensembling closes this.

The repair price (part 4): one labeled segment. Fine-tuning the leave-Paris4-out model
on a single Paris4 segment (w00) lifts the seven segments it still has never seen from
mean F1 0.496 to 0.822 — 82% of the distance to the train-pixel reference — and the
adaptation saturates at 2,500 steps, about seven minutes on one consumer GPU. Cross-
scroll performance peaks at 10–20k steps in all six LOSO runs and fine-tuning peaks at
2.5k: no held-out axis anywhere justifies the released 75k schedule.

And the price has a price curve (part 5). That fine-tune used all of w00's annotation, one
of the largest in Paris4, so I rebuilt it on nested subsets — 50.3%, 20.7% and 13.5% of the
annotated area, regions kept whole, configs differing from the full arm in three keys — and
rescored the same seven segments. Half the annotation keeps 89% of the benefit for 0.033 F1,
above the noise floor on six of seven segments: real, but cheap against halving the
annotation work. Below that it bends — a fifth keeps 71%, an eighth 56% — and the smallest
arm is also the only one that overfits by step 5,000. So "annotate one segment" now carries a
number, and the number says annotate half of one. What it does not explain is why the budget
is worth three times as much on one segment as another (w09 keeps 93.5% at half, w07 82.7%),
which the trivial floor does not predict.

Why this raises the probability of reading complete scrolls: the First Letters targets
have no labels, so cross-scroll transfer is the deployment condition — and it now has a
measured playbook instead of a hope. Render the target aligned; use direct inference
(floor +0.06–0.17) only to scout for promising surface; annotate one segment; fine-tune
for minutes; re-infer everything. Every stage of that recipe carries an expected value
measured here, and the apparatus to re-verify any proposed improvement is one config line
and ~3 hours of training on a consumer GPU.

I then ran that playbook on a scroll nobody has read. PHerc1447 ships no rendered surface
volume for any of its fifteen segments, so I rendered the largest (7.40 cm²) from its mesh
in twenty-five minutes of streaming, and the 389 MB result fed the released checkpoints
unmodified. Nothing readable came out, and it fails the way the margins predict: the four
checkpoints disagree threefold on how much surface is strong ink, none reaches full
confidence anywhere, and at full resolution the output is rounded patches rather than
connected strokes. So step two scouts only in the weak sense — it says the model has
nothing, not where to annotate — and unsupervised adaptation has to precede step three on
an unlabeled scroll. I would rather report that than imply the recipe is ready to point at
PHerc0800 tomorrow (docs/16).

So I pre-registered the cheapest ways out — design, prediction and decision rule pushed
publicly before each run — and ran all four. Input space: that render is spectrally a
native-class input, and PHerc1447 has only an 8.640 µm scan, so the "render aligned"
guidance cannot be followed there at all; a matching filter closes 38% of the spectral
distance between the families and buys a median 9.1% of the transfer gap, mean +0.005 F1 —
no effect by the rule I had fixed, inside the 0–20% I predicted. Parameter space: test-
time entropy minimisation on the only surface the architecture leaves — 27,712
normalisation affines, 0.08% of the model — costs 0.041 F1 across fourteen cells with not
one improving, and every checkpoint I scored at 400 steps or beyond sits on its segment's
all-positive floor. I predicted +10 to +40%; it is −13%, so that prediction is refuted
with the sign wrong. A rank check in float shows the loss is the model and not the 8-bit
output — AUC falls from 0.62–0.66 to 0.48–0.55, at or below chance — and that the
adaptation objective improves monotonically the whole way down, so no label-free stopping
rule built on it could have caught this. Label space: self-training on the model's own
confident pixels is the rung that helps, and it helps most when it labels the sheets it is
about to read — +0.046 F1, all fourteen cells improving, 14.3% of the gap, against
+0.030 when the pseudo-labels come from a different segment. Both were pre-registered; the
transductive one was committed at +5% to +30% and landed at 14.3%. That number is the
useful one, because it prices the annotation: with the base checkpoint, the recipe and the
step count held fixed, a human's labels on one segment buy +0.32 where the model's own
confident guesses buy +0.046. A HUMAN ANNOTATION IS WORTH ABOUT SEVEN TIMES the best
label-free method — and since that method needs no labels at all, the 14% is what a
scroll nobody has annotated can have today. Annotate something, and half a segment will do
(docs/18).

The apparatus went upstream as well as the numbers. The released recipe does not run as
published — its `datasets` block is a single `/path/to/` placeholder while the 29
representations live in a separate contract file — so the join, and the holdout flags that
turn it into this probe, are villa PR #1608; it regenerates my three arm configs
byte-for-byte. Both have already survived outside hands: one contributor pulled the raw
0139 matrix and recomputed every published figure from it, confirming the margins hold
under four different checkpoint-selection rules, and the same person then reviewed the
generator and found a crash on a batch smaller than the surviving scroll count, fixed two
days later. Being reproduced and being corrected are the two things a measurement of an
open problem needs.

Everything is MIT, documented end to end (docs/14–18 plus 60 committed evidence
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

1. **Get September's form** from https://scrollprize.org/prizes. Do not reuse August's
   link — each round issues a new form and closes the previous one. Check the question
   count: August had six (email, name, team, URL, description, terms). If September adds
   back the "Pull request submitted!" checkbox, #1608 is the answer.
2. **Check the four upstream links still say what field 4 says they say** — #1608 (open,
   one review round), #1638 (closed and locked, and field 4 labels it as such), #1249
   (merged), #1535 (open, August's story). If **#1608 merges**, relabel it "merged" in
   field 4 and in field 5's second-to-last paragraph.
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

**State as of 2026-08-30** (the audit pass): all 17 links 200; every artifact-backed number
re-derived and passing; 60 committed evidence files; the repo pushed; two upstream replies
drafted and waiting on the user to post (`issue1582_reply_nerln.md`,
`issue1611_reply_bullo27_round2.md`).

Field hashes at this revision, over the block body plus one trailing newline — the
convention the August entry uses:

- field 4 — 1,501 chars, `fff1b5f4ed935f9dcdd9aa425810bee00056111331e58aacb3d971aa803e7ae7`
- field 5 — 10,027 chars, `9ffab5742fa52ce0ea734cf428985ca7060fbbc6ff8b84b08c6ccb9933553d10`

If either field is edited before submitting, recompute these and record the new pair
against what was actually pasted.

---

## Evidence backing the claims above

| claim | source |
|---|---|
| label-efficiency: half the annotation keeps 89% for −0.033 F1; a fifth 71%, an eighth 56% | `runs/ink9um_scorecard/labelbudget_matrix.csv` (84 cells) + `labelbudget_summary.json`, `docs/15` part 5 |
| arm A: spectrum matching gains +0.005 F1, median 9.1% of the aligned gap — no effect by the pre-registered rule | `runs/ink9um_scorecard/armA_specmatch_matrix.csv` (48 cells) + summary, `docs/18` |
| arm B: entropy minimisation costs −0.041 F1, 0 of 14 cells improving, four cells on the trivial floor; AUC 0.66 → 0.48–0.55 on the three rank-checked cells while the objective keeps falling | `runs/ink9um_scorecard/armB_tent_matrix.csv` (34 cells) + `armB_tent_summary.json` + `armB_rank_check_*.json`, `docs/18` |
| arm C: self-training gains +0.030 F1, 14 of 14 cells, 9.5% of the gap — against +0.320 for a human annotation on the same segment with everything else fixed | `runs/ink9um_scorecard/armC_pseudo_matrix.csv` (18 cells) + `armC_pseudo_summary.json` + `armC_rank_check_w01_s42.json`, `docs/18` |
| arm D (transductive): +0.046 F1, 14 of 14 cells, 14.3% of the gap, AUC 0.659 → 0.742; pre-registered at +5–30% | `runs/ink9um_scorecard/armD_pseudoT_matrix.csv` (18 cells) + `armD_pseudoT_summary.json` + `armD_rank_check_w01_s42.json`, `docs/18` |
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
  the August form's field 5; do not repeat it); #1535 still unreviewed; **two replies were
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
