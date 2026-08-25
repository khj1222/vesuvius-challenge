<!-- Draft comment for https://github.com/ScrollPrize/villa/issues/1582 -->
<!-- Answers the caveat nerln carried over from #1580, qualifies the control, and pre-registers
     the segment-holdout arm running tonight. Results comment follows tomorrow. -->

Thanks for splitting this out — and the caveat you carried over from the #1580 thread is
answerable, so here it is, along with a correction to how much weight the control deserves.

## What the reference arms trained on: both families

The `ref42` / `ref43` cells are not runs of mine. They are the released
`scrollprize/ink_9um` checkpoints — `hybrid_3d2d`, seeds 42 and 43, the seven published
steps — so what they trained on is the published contract,
`configs/aligned21_fixed_scroll_prior.json`: 29 representations, 24 `public_2p4_level2_zmean4`
and 5 `native_9p362_level0`.

The five native rows are `w035`, `w039`, `w040`, `w041`, `w044` — all PHerc0139, and four of
them are the four segments in the comparison. So the reference arms saw **both families of
exactly those segments**. That is @Bullo27's second branch: the control isolates family
exposure, not merely segment familiarity.

The held-out side is the clean one. `configs/ink9um_loso_no0139_s42.json` keeps 15
representations, all `public_2p4_level2_zmean4`; excluding scroll 0139 dropped its 9 aligned
and 5 native rows in the same operation.

## The control is weaker than its numbers look

Having answered it, I should also say the row does less work than the issue body gives it
credit for. The control was @Bullo27's addition, not mine — I had only used the reference
arms as a legend for the CSV — and now that it is load-bearing it needs a qualification the
recomputation did not cover. The reference arms are scored on pixels they trained on, and
they sit near the ceiling:

| seg | family | floor | ref best F1 | margin | max possible margin | headroom used |
|---|---|---|---|---|---|---|
| w035 | aligned | 0.480 | 0.9764 | +0.4967 | 0.5203 | 95.5% |
| w035 | native | 0.475 | 0.9785 | +0.5030 | 0.5245 | 95.9% |
| w039 | aligned | 0.485 | 0.9802 | +0.4950 | 0.5148 | 96.2% |
| w039 | native | 0.482 | 0.9836 | +0.5019 | 0.5183 | 96.8% |
| w040 | aligned | 0.615 | 0.9641 | +0.3490 | 0.3849 | 90.7% |
| w040 | native | 0.611 | 0.9660 | +0.3545 | 0.3885 | 91.2% |
| w041 | aligned | 0.589 | 0.9857 | +0.3967 | 0.4110 | 96.5% |
| w041 | native | 0.586 | 0.9862 | +0.4003 | 0.4141 | 96.7% |

Between 0.014 and 0.036 of headroom is left. A +0.05 gap has no room to appear there,
whichever reading is true. So the collapse to −0.006 is *consistent with* domain match but
does not establish it, and I would not lean on it. @Bullo27's absolute-margin check answers
the ceiling worry on the margin scale; the ceiling I mean lives on the F1 scale, and on that
scale it is real.

What survives without the control is narrower and still worth stating: one model, one
physical segment, two renderings of it, neither seen in training — and the family matching
the training corpus wins 4/4, +0.028 to +0.066.

## A corpus fact this issue may want on the record

The native family is instantiated on exactly one scroll. All 5 native rows are PHerc0139,
so "hold out a scroll" and "hold out the native family" are the same operation for that
family. None of the three LOSO arms I trained can serve as the missing control: leaving 0139
out removes the entire native family with it, and leaving 0139 in makes these segments
training pixels. Such an arm can be built — I say how below. What cannot be built from this
corpus is a family-*balanced* one, since 24 of the 29 representations are aligned.

That bears on your third bullet. As published, the corpus can measure what a family
mismatch costs on an unseen **scroll**; it cannot measure what it costs on an unseen
**segment**. Those are the two numbers an enforcement decision would want to tell apart.

It also sharpens the legacy-inputs bullet, in a way I ran into from the other side in
#1580: prepared inputs carry the preparer's metadata, and native published volumes carry
nothing, because they never went through the preparer. Right now *absence* of provenance is
the only thing that identifies the native family. That works until something else is
published without provenance for a different reason.

## What I am running tonight

Rather than ask which design you would want and wait, I am running one and stating it
before I see the result.

**Arm.** Hold out two physical 0139 segments in *both* families — `pherc0139-w035` with
`w035`, and `pherc0139-w039` with `w039`. That leaves 25 of the 29 representations in
training, native `w040`, `w041` and `w044` among them, so the model has seen the native
family and has not seen these two segments in either rendering. Seeds 42 and 43, the same
recipe and the same 78,125 steps as the three LOSO arms, scored with the same best-of-grid
rule over 7 checkpoints × 2 seeds. Configs are `configs/ink9um_segloso_w035w039_s{42,43}.json`
in the repo linked below; they are generated, not hand-edited.

**Why two segments and not one or four.** How many I hold out decides how much of the native
family survives in training, because there are only five native representations in existence.
Hold out one and four native rows remain, but there is a single paired comparison to report.
Hold out all four and the comparison matches the published table exactly, but native exposure
collapses to `w044` alone — the model stays effectively aligned-only, and an aligned win
would mean very little. Two is the balance: three native rows retained, two paired
comparisons. I chose w035 and w039 because they carry the largest gaps in the published
table (+0.057 and +0.066), so this is the version of the test with the most to lose.

**What each outcome will mean, committed in advance.**

- *Aligned still wins, by a gap comparable to the LOSO arm* — the advantage survives native
  exposure, which favours the dull reading that aligned renders are simply easier to score
  and weakens the domain-match reading I offered.
- *The gap attenuates or flips* — corpus composition drives it, which is domain match.

Either way, segment familiarity stops being available as an explanation for the paired gap,
which is the part the reference arms could not settle.

**One confound I want on the record before the numbers exist.** This arm also gains scroll
exposure, which for the reason in the section above cannot be separated from family
exposure in this corpus. Scroll
exposure should help both renderings of the same physical sheet about equally, so I will
read the *direction* as the result and treat any change in *magnitude* against the LOSO arm
as suggestive only. If that is the wrong call, I would rather be told now than after I post
a number.

Results tomorrow, win or lose.

Raw grid, one row per arm × representation × step, if anyone wants to recompute either
table: https://github.com/khj1222/vesuvius-challenge/blob/main/runs/ink9um_scorecard/no0139_matrix.csv
(`pherc0139-wNNN` rows are aligned, bare `wNNN` are native.)
