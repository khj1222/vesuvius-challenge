# September 2026 Progress Prize — submission package (DRAFT)

**Form:** https://forms.gle/xoF5C3QsYutKP97x7
**Deadline:** 2026-09-30 23:59 PT
**Status:** DRAFT (2026-08-23) — the centerpiece (LOSO cross-scroll study, docs/15) is
finished and committed; this file is ready except for the open items in the notes:
①a September-specific PR for the field-6 checkbox ②fold in whatever lands during
September (0139-out arm, render-path work, upstream replies) ③push before submitting.
August's own submission (2026-08 file) must go in first and stays separate — its
scorecard paragraph is groundwork here, cited as such, not re-claimed.

---

## Step 1 — the pull request ⚠ OPEN ITEM

Candidates, in preference order (decide when one actually exists):
1. **Harness/eval upstreaming to villa** — e.g. a cross-scroll evaluation script or a
   measured-baselines table for `ink-detection/configs/README.md` (the model card and
   configs README ship no numbers; ours are the first). Read `villa/CONTRIBUTING.md` on
   `main` first (the #1434 lesson), include the human "why this matters to me" paragraph.
2. **scrollprize.org community-projects entry update** on top of merged
   [#1249](https://github.com/ScrollPrize/villa/pull/1249) — add the cross-scroll study
   line next to the harness entry (small, safe, same pattern as July).
3. Fallback: if [#1535](https://github.com/ScrollPrize/villa/pull/1535) is still open and
   unreviewed it technically satisfies "submitted", but it is August's story — prefer 1/2.

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
Result writeup (cross-scroll study): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/15_loso_cross_scroll.md
Groundwork (first scorecard of the released ink_9um models): https://github.com/khj1222/vesuvius-challenge/blob/main/docs/14_ink9um_scorecard.md
Arm generator: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/make_ink9um_config.py
Raw numbers (392 scored cells): https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink9um_scorecard
Dataset and models measured: https://huggingface.co/scrollprize/ink_9um (models), hf://buckets/scrollprize/datasets/ink_9um (labels)
Open problem addressed: https://scrollprize.org/2026_open_problems (#7, cross-scroll ink generalization)
```

**5. Short description of how your contributions substantially increase the probability of reading complete scrolls**

```
Reading a complete scroll means running an ink model on a scroll nobody has labeled.
Open problem #7 asks how well today's models survive that jump; until now there was no
systematic number — the official 9 µm models released on 2026-08-14 ship with no
evaluation at all. I measured both halves of the question on that release, with the
held-out methodology that won July's Progress Prize and settled villa #192 in August.

First, a scorecard of what the released checkpoints actually do (docs/14): scoring all
14 hybrid_3d2d checkpoints on the three segments that ship validation masks puts the
honest within-scroll ceiling at F1 0.74–0.77, while the same checkpoints reach 0.98+ on
their training pixels — a 0.22–0.45 memorisation gap at the final step, no step that is
best everywhere, and two released seeds that disagree by 0.22 F1 at step 75k on the same
held-out region.

Then the September centerpiece (docs/15): leave-one-scroll-out. I retrained the exact
released recipe four times — the only change being one scroll removed and the per-batch
scroll quotas renormalised — and scored each pair of runs on every annotated pixel of
the held-out scroll, against the released checkpoints for which those same pixels are
training data. Two arms: leave-Paris4-out (2 seeds × 78,125 steps, scored on 8 segments)
and leave-1667-out (2 seeds, 6 segments). 392 scored cells, every inference reduced by a
full threshold sweep, and every segment reported against its all-positive F1 floor
(2p/(1+p)) so ink-fraction artifacts cannot masquerade as transfer.

The numbers: models that never saw the target scroll reach best-of-grid F1 0.487
(Paris4) and 0.546 (1667) where the released models reach 0.89–0.98 on the same pixels —
and the margin over the trivial all-positive classifier averages just +0.06 toward
Paris4 and +0.13 toward 1667. The gap is universal but its size is scroll-dependent
(Paris4, with transferred labels, is the hardest target by 2×). It is structural, not
seed luck: the two independent seeds agree to |ΔF1| ≈ 0.01 on held-out scrolls, versus
the 0.22 seed spread within scrolls. And cross-scroll performance peaks at 10–20k steps
in all four runs — no held-out axis, within-scroll or across, justifies the released
75k schedule.

Why this raises the probability of reading complete scrolls: the First Letters targets
have no labels, so cross-scroll transfer is the deployment condition, and +0.06..+0.13
over a trivial baseline is now the measured starting point — the number domain
adaptation has to beat, on an apparatus where anyone can test a proposed fix in a day
(one config line generates an arm; training is ~3 h on one consumer GPU; the scorer and
floors are in the repo). The same measurements yield immediate practical guidance:
checkpoint selection at 10–20k rather than 75k, per-seed disagreement as a cheap
uncertainty signal, and per-segment floors as the honest yardstick for any published
score. Everything is MIT, documented end to end (docs/14–15), and continuous with the
July harness and the August #192 verdict — one apparatus, three months of answered
questions.
```

**6. Pull Request Submission** → check "Pull request submitted!" (see step 1 — OPEN)

**7. Terms and conditions** → "Yes, I agree"
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Evidence backing the claims above

| claim | source |
|---|---|
| within-scroll honest ceiling 0.74–0.77; memorisation gap 0.22–0.45; seed spread 0.22 @75k | `runs/ink9um_scorecard/scorecard.csv` (+`summary.json`), `docs/14` |
| LOSO→Paris4 per-segment bests, mean 0.487, floor margin +0.060 | `runs/ink9um_scorecard/paris4_matrix.csv` (+`paris4_matrix_summary.json`) |
| LOSO→1667 per-segment bests, mean 0.546, floor margin +0.131 | `runs/ink9um_scorecard/no1667_matrix.csv` (+`no1667_matrix_summary.json`) |
| ref arms 0.89–0.98 on the same pixels | same two matrix CSVs, `ref42`/`ref43` rows |
| honest-to-honest drops −0.26 (Paris4) / −0.17 (w029 0.758→0.589) | `docs/14` ceiling vs matrix CSVs |
| seed agreement \|ΔF1\| mean 0.011 / 0.015 | `*_matrix_summary.json`, `loso_seed_abs_diff_*` |
| LOSO peak at 10–20k, decline to 75k | `stepwise_mean_loso` in both summary JSONs |
| all-positive floor 2p/(1+p) per segment | `floors` in both summary JSONs |
| recipe fidelity (quota renormalisation, 21/23 reps) | `configs/ink9um_loso_*.json`, generated by `tools/make_ink9um_config.py` |
| reproduction validity (online val 0.69–0.77 on official masks) | `runs/ink9um_loso_*/validation_metrics.jsonl` |

(Checkpoints and prediction TIFFs stay untracked; the six committed CSV/JSON files
reproduce every quoted figure.)

---

## Notes for whoever finalises this

* **Do not re-claim the scorecard as September work if August's form went in with its
  scorecard paragraph** — here it is framed as groundwork ("August" sentence in field 5).
  If August was submitted WITHOUT that paragraph, promote docs/14 freely.
* **Field-6 PR is the one genuinely open item** — see step 1. Whichever lands, add its
  URL to field 4 and a half-sentence to field 5's last paragraph.
* **Fold in September events before submitting**: ①leave-0139-out arm if run (separates
  target difficulty from source composition) ②render-path/domain-adaptation work if the
  WSL2/Docker install happened (docs/13 §6) ③any upstream replies (#1231, #192
  stantheman scoring, #1535 review) that touch the framing.
* **Push before submitting** — docs/14, docs/15, tools, configs, and the six evidence
  files are local-only until pushed; every field-4 link must resolve publicly.
* Timing: judging is monthly after the round closes, so early submission buys nothing;
  same submit-when-something-moves logic as August, backstop the last weekend (09-26/27).
