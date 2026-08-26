<!-- Draft comment for https://github.com/ScrollPrize/villa/issues/1582 -->
<!-- Answers the caveat nerln carried over from #1580, qualifies the control, and reports the
     pre-registered segment-holdout arm -- which came out against our own reading. -->

Thanks for splitting this out. Three things: the caveat you carried over from #1580 is
answerable, the control it concerns deserves less weight than the issue body gives it, and I
ran the arm that settles what the control cannot. The last one came out against the reading I
offered you.

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

## I ran it, and it went against me

The arm is the one described in commit
[`fb37974`](https://github.com/khj1222/vesuvius-challenge/commit/fb37974), pushed before
the runs finished, so the design and the reading committed to each outcome are on the record
ahead of the numbers. Both seeds completed 78,125 steps; all 56 cells scored.

**Arm.** w035 and w039 held out in *both* families, 25 representations left in training with
native w040 / w041 / w044 retained. That put the native family at 36.3% of the 0139 patch
pool and **16.4% of training batches**, against 0% in the published LOSO arm.

| seg | aligned F1 (margin) | native F1 (margin) | Δ margin |
|---|---|---|---|
| w035 | 0.791 (+0.311) | 0.757 (+0.281) | **+0.030** |
| w039 | 0.725 (+0.240) | 0.635 (+0.153) | **+0.086** |

Aligned wins 2/2, mean Δ margin **+0.058**. On the same two segments the LOSO arm gave
**+0.061**. Native exposure went from nothing to a sixth of every batch and the gap moved by
**−0.003**.

It is not a selection artifact. Max, mean and median over the grid give +0.058 / +0.055 /
+0.064; seed 42 alone gives +0.048, seed 43 alone +0.058; and aligned wins 2/2 at every one
of the seven checkpoints taken separately, Δ from +0.050 to +0.081.

**By the reading I committed in advance, this is the outcome that argues against me.** A gap
that survives exposure to the native family is better explained by aligned renders simply
being easier to score than by domain match. That is not a surprising thing for them to be —
they are 2.399 µm acquisitions pooled 4× in z, so more of the scan survives into the input
than a single native 9.362 µm acquisition carries. I would not now defend the domain-match
reading on this data, and I will amend the write-up that offered it.

Scroll exposure did what I said it would, symmetrically, which is why it does not rescue the
other reading: every absolute number rose (w035 aligned 0.740 → 0.791, native 0.679 → 0.757;
w039 aligned 0.654 → 0.725, native 0.585 → 0.635) while the difference between families
stayed put.

**What I think this means for your third bullet.** If the aligned family is better rather
than merely familiar, then "does this input match the family the recipe trained on" is the
wrong question to enforce. A model trained mostly on native renders would still, on this
evidence, do better fed an aligned one. Reporting *which* family an input belongs to stays
useful — arguably more useful — but as provenance a reader can act on, not as a mismatch to
refuse. I would be careful about writing a rule that pushes anyone toward the weaker
representation because it happens to be the one a recipe was trained on.

**Limits, stated the same way I stated them before the run.** 16.4% is not balance, and by
the section above this corpus cannot give balance — so "the gap survives native exposure" is
established at that exposure level, not at parity. Two segments, not four. And the arm gains
scroll exposure inseparably from family exposure; it moved both families alike, but I cannot
prove that from two segments alone. What would settle the remaining doubt is a native render
of a segment on some other scroll, which is a data question rather than an analysis one.

One infrastructure note for anyone rerunning this: both seeds first died at step 5000 with a
Windows DataLoader shared-memory failure (error 1455, commitment limit) and were resumed from
that checkpoint with `dataloader_workers` cut from 12 to 6. Nothing else changed; the recipe,
seeds, step count and scoring rule are the published ones.

Both grids, one row per arm × representation × step, if anyone wants to recompute any table
here — `pherc0139-wNNN` rows are aligned, bare `wNNN` are native:

- this arm: https://github.com/khj1222/vesuvius-challenge/blob/main/runs/ink9um_scorecard/segloso_matrix.csv
- the published LOSO arm: https://github.com/khj1222/vesuvius-challenge/blob/main/runs/ink9um_scorecard/no0139_matrix.csv
