# September 2026 Progress Prize — submission package (DRAFT)

**Form:** https://forms.gle/xoF5C3QsYutKP97x7
**Deadline:** 2026-09-30 23:59 PT
**Status:** DRAFT v3 (2026-08-28 — field-6 PR resolved to #1608 and its review round folded
into field 5; was v2 of 2026-08-24) — rewritten after the study grew to its full four parts:
①three LOSO arms (Paris4 / 1667 / 0139, the last with the aligned-vs-native
representation control) ②nature-of-the-gap (ensembles ≈ no recovery → bias)
③label-efficiency repair (one segment closes 82%), plus a pre-registered follow-up that
refuted our own reading of ① and is reported as such. Open items in the notes:
a September-specific PR for field 6, September events to fold in, push before submit.
August's own submission goes in first and stays separate — its scorecard paragraph is
groundwork here, cited as such, not re-claimed.

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
Raw numbers (1,000+ scored cells, 9 CSV/JSON evidence files): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard
Dataset and models measured: https://huggingface.co/scrollprize/ink_9um (models), hf://buckets/scrollprize/datasets/ink_9um (labels)
Upstream PR (this round, the arm generator): https://github.com/ScrollPrize/villa/pull/1608
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
segments that ship validation masks puts the honest within-scroll ceiling at F1
0.74–0.77 against 0.98+ on training pixels — a 0.22–0.45 memorisation gap, no step that
is best everywhere, and two released seeds that disagree by 0.22 F1 at the final step.

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
on. A reviewer on villa #1580 pointed out the grid contained a control for that reading,
so I pre-registered the test it could not settle (the same segments held out in BOTH
families, so the model has seen the native one), pushed the design and the reading
committed to each outcome before the runs finished, and it refuted me: the gap came back
unchanged, +0.058 against +0.061, with native exposure raised from 0% to 16.4% of
training batches. The mechanism is not familiarity but quality — aligned renders are
2.399 µm acquisitions pooled 4x in z, against a single 9.362 µm one. Render aligned,
whatever the model trained on. The retraction is in docs/15 appendix 2 and on the
upstream thread.

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

Why this raises the probability of reading complete scrolls: the First Letters targets
have no labels, so cross-scroll transfer is the deployment condition — and it now has a
measured playbook instead of a hope. Render the target aligned; use direct inference
(floor +0.06–0.17) only to scout for promising surface; annotate one segment; fine-tune
for minutes; re-infer everything. Every stage of that recipe carries an expected value
measured here, and the apparatus to re-verify any proposed improvement is one config line
and ~3 hours of training on a consumer GPU.

I then ran that playbook on a scroll that has never been read, to see where it breaks.
PHerc1447 ships fifteen segments and no rendered surface volume for any of them, so I
rendered the largest (7.40 cm²) from its mesh — 0.6 MB of coordinates from the public
bucket, twenty-five minutes of streamed rendering, a 389 MB volume whose pyramid fed the
released checkpoints with no changes at all. The ink predictions are not readable, and
they fail in the way the margins above say they should: the four checkpoints disagree
threefold on how much of the surface is strong ink, none of them reaches full confidence
anywhere on it, and at full resolution the output is rounded patches rather than connected
strokes — the checkpoints agree on coarse layout while differing in detail, which is what
responding to surface geometry looks like. The honest reading is that step two of the
playbook works as scouting only in the weak sense: it tells you the model has nothing,
not where to annotate next. Unsupervised domain adaptation has to come before step three
on a scroll with no labels. I would rather submit that than a paragraph implying the
recipe is ready to point at PHerc0800 tomorrow (docs/16).
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

Everything is MIT, documented end to end (docs/14–15 plus nine committed evidence
files), and continuous with the July harness and the August #192 verdict — one
apparatus, three months of answered questions.
```

**6. Pull Request Submission** → check "Pull request submitted!" (see step 1 — #1608)

**7. Terms and conditions** → "Yes, I agree"
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Evidence backing the claims above

| claim | source |
|---|---|
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
  (docs/16); if more segments get rendered before submitting, update the count there ②upstream replies that touch the framing — #1231
  still silent; **stantheman0128's scoring of our depth band landed 2026-08-25 and belongs
  to August, not here** (it is folded into the August form's field 5; do not repeat it);
  #1535 still unreviewed ③a smaller-annotation label-efficiency point
  (does half a segment still close the gap?) if measured.
* **Honesty guardrails already embedded in the text** — keep them through edits: closure
  percentages use the train-pixel ref as denominator (generous baseline, said as such);
  "one segment" is w00, one of the larger Paris4 annotations; best-of-grid comparisons
  are oracle-selected on both sides.
* **Push before submitting** — docs/14–15, tools, configs and the evidence files must
  resolve publicly; every field-4 link is checked. (As of 2026-08-26 all of it is pushed,
  including the segloso arm.)
* **Do not soften the refutation** — the pre-registered arm that broke our own domain-match
  reading is an asset, not a wound: claim published → outside reviewer presses → falsifiable
  test registered in public before the run → claim dies → retraction posted upstream and in
  docs/15. That chain is the documentation axis. If space is tight elsewhere, cut something
  else.
* Timing: judging is monthly after the round closes, so early submission buys nothing;
  same submit-when-something-moves logic as August, backstop the last weekend (09-26/27).
