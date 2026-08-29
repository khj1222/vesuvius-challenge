# Auditing the ink_9um held-out masks (2026-08-29)

July's contribution to this project was a held-out harness, built on the
observation that a validation split which cuts through a letter does not
measure generalisation: at a 256 px patch the model trains on one half of a
stroke and is scored on the other. That harness has since been used to judge our
own work — the depth-label matrix (docs/12), the cross-scroll study (docs/15).
This document turns it on the corpus itself.

The `ink_9um` release ships 29 segments. **Three of them carry a
`_validation_mask`**; the other 26 carry none, so on those the only measurable
number is performance on training pixels. Every honest number anyone has
published on this corpus — including our own scorecard, docs/14 — rests on those
three masks. So it is worth asking whether they hold out what they appear to.

## What the three masks look like

In this corpus a `_validation_mask` is **disjoint from the supervision mask**:
the two together are the segment's whole annotation, and the split was made when
the corpus was built. `tools/audit_holdout_masks.py` reconstructs the union,
counts the annotated regions that contain both kinds of pixel, and measures how
far each held-out pixel sits from the nearest supervised one.

| segment | annotation | regions | held out | regions holding **both** | held-out pixels within one 128 px patch | within two |
|---|---|---|---|---|---|---|
| pherc0139-w016 | 593,824 px | 3 | 175,222 (29.5%) | **2 of 3** | **58.6%** | 99.1% |
| pherc0814-46527 | 590,044 px | **1** | 161,051 (27.3%) | **1 of 1** | 45.0% | 87.8% |
| pherc1667-w029 | 1,595,268 px | 8 | 382,353 (24.0%) | 1 of 8 | 23.2% | 45.4% |

Distances from held-out pixels to the nearest training pixel:

| segment | min | p25 | median | p75 | max |
|---|---|---|---|---|---|
| pherc0139-w016 | 1 | 55 | 108 | 166 | 275 |
| pherc0814-46527 | 1 | 72 | 142 | 214 | 319 |
| pherc1667-w029 | 1 | 138 | 283 | 690 | 986 |

Three things follow directly, before any model is involved.

1. **All three splits cut through annotated regions.** On w016 two of the three
   regions carry both training and held-out pixels; on 0814 the whole annotation
   is a single connected region split internally.
2. **w016 has no leak-free held-out at all.** 99.1% of its held-out pixels lie
   within two patches of a training pixel, and the 1,595 px that lie beyond
   contain **no ink** — so there is no distance threshold at which a clean F1
   can even be computed on that segment.
3. **w029 is the only one with real separation**, and even there a quarter of
   the held-out pixels sit within one patch.

This is not a claim that the corpus authors did anything unreasonable. With
three annotated regions — or one — a region-aware split of the kind
`make_validation_mask.py` produces is arithmetically impossible: our own planner,
asked for w016's official 29.5%, can only offer 40.8% because there are just two
groups to choose from. The structure of the annotation, not the split, is what
constrains this.

## Does the adjacency actually pay?

Adjacency only matters if the model exploits it. Measuring that needs no new
training, because two model families already exist for these segments:

- **released** — the public `ink_9um` checkpoints, which trained on the
  segment's supervision regions;
- **control** — our leave-one-scroll-out arms from docs/15, which never saw the
  scroll at all.

Held-out pixels were split into distance strata and both families scored in
each, at every one of the 7 released steps x 2 seeds. Raw per-stratum F1 is not
comparable across strata — they differ sharply in ink density — so the quantity
that means something is **how much the trained model's advantage over the
control grows as held-out pixels get closer to training pixels**. The control
measures each stratum's intrinsic difficulty; anything beyond that is adjacency.

### pherc0139-w016 (mean best-F1 over 14 checkpoints)

| stratum | px | ink density | released | control | gain |
|---|---|---|---|---|---|
| <64 | 51,311 | 0.1278 | 0.7609 | 0.5356 | **+0.2253** |
| 64-128 | 51,400 | 0.2808 | 0.6650 | 0.5399 | +0.1250 |
| 128-256 | 70,916 | 0.2851 | 0.6664 | 0.5786 | **+0.0878** |
| >=256 | 1,595 | 0.0000 | — | — | no ink, F1 undefined |

**Excess gain of the nearest stratum over the farthest scorable one: +0.1375 F1.**

The control is nearly flat across the three strata (0.5356 / 0.5399 / 0.5786)
and, if anything, finds the *nearest* stratum hardest — which is what one would
expect from its ink density of 0.128 against 0.285. So the strata are not
intrinsically easier near training pixels. Only the model that trained next door
does better there.

### pherc1667-w029

| stratum | px | ink density | released | control | gain |
|---|---|---|---|---|---|
| <64 | 44,574 | 0.1190 | 0.7405 | 0.4767 | **+0.2638** |
| 64-128 | 43,985 | 0.0000 | — | — | no ink, F1 undefined |
| 128-256 | 85,215 | 0.3160 | 0.7781 | 0.6427 | +0.1354 |
| >=256 | 208,579 | 0.2675 | 0.7010 | 0.5105 | **+0.1905** |

**Excess gain of the nearest stratum over the farthest: +0.0733 F1.** Here the
trend is not monotone — the middle stratum sits below the far one — so w029
supports the nearest-stratum effect but not a clean distance gradient.

### How robust is it

Comparing gain(nearest) against gain(farthest) checkpoint by checkpoint, the
nearest stratum wins in **10 of 14** on each segment, 20 of 28 together. The
mean effect is clear (+0.1375 and +0.0733); individual checkpoints are noisy,
with per-checkpoint differences ranging from -0.067 to +0.369 on w016.

pherc0814-46527 is not in this comparison: it belongs to a scroll that no LOSO
arm excluded, so no control model exists for it. Its structural finding — a
single annotated region split internally — stands regardless.

## What this does and does not establish

**It establishes** that the three official held-out masks are cut through
annotated regions rather than taken as whole ones; that on w016 no leak-free
held-out subset exists at all; and that on both segments where a control is
available, a model that trained on the segment gains materially more on
held-out pixels adjacent to its training pixels than on distant ones, by +0.14
and +0.07 F1 on average.

**It does not establish** a precise correction to docs/14's honest ceiling of
0.74-0.77. The strata differ in ink density and size, the released and control
families differ in more than segment exposure (different corpora, different
training lengths), and the per-checkpoint evidence is noisy. The defensible
statement is directional: **0.74-0.77 is an optimistic reading of what these
models generalise to, not a conservative one.**

It also does not say the corpus is wrong. It says the corpus's annotation
geometry does not admit a leak-free split on two of its three masked segments,
which is a property of how much was annotated and where, not of the split.

## What would fix it

1. **Report by distance stratum.** Costs nothing and needs no new data: any
   held-out number on this corpus can be published alongside the share of its
   pixels within a patch of training supervision. `audit_holdout_masks.py` does
   this.
2. **Hold out with a buffer.** When a whole-region split is impossible, delete a
   buffer of at least one patch width from the training supervision around the
   held-out area. This costs training data and buys an honest number.
3. **Annotate for separation.** The deeper fix is upstream of any tool: an
   annotation campaign that produces several separated regions per segment —
   as PHercParis4 w00's 15 letter boxes do — makes region-aware splits possible
   in the first place. w00 supports a 9-group split; w016 supports two groups
   and 0814 supports one.

For the 26 segments that ship no mask at all, `make_validation_mask.py` can
generate one, but the same constraint applies: it can only be leak-free where
the annotation has enough separated regions to allow it. Auditing all 29 for
that property is the obvious next step.

## Reproduce

```bash
# geometry only -- needs just the labels
python tools/audit_holdout_masks.py \
    data/ink_9um/labels/aligned-scrollprizeorg-21slices/pherc0139-w016 \
    --json runs/ink9um_holdout_audit/pherc0139-w016_audit.json

# with a trained model and a control that never saw the scroll
python tools/audit_holdout_masks.py \
    data/ink_9um/labels/aligned-scrollprizeorg-21slices/pherc0139-w016 \
    --prediction runs/ink9um_scorecard/preds/pherc0139-w016_s42_020000.tif \
    --control    runs/ink9um_scorecard/preds/pherc0139-w016_loso0139_42_020000.tif
```

Raw numbers: `runs/ink9um_scorecard/leak_strata.csv` (168 rows: segment, family,
seed, step, stratum) and `runs/ink9um_holdout_audit/*_audit.json`. The control
predictions come from the LOSO arms described in
[docs/15](15_loso_cross_scroll.md); the released-checkpoint predictions are the
ones scored in [docs/14](14_ink9um_scorecard.md).

## Reported upstream

Filed as [villa #1638](https://github.com/ScrollPrize/villa/issues/1638) on 2026-08-29, and
**closed the same day by `pmh47` (Research Team Lead)**:

> "validation mask is disjoint from the supervision mask" — indeed, so there is no actual
> issue. Provided one interprets results carefully in terms of what is intra-segment /
> inter-segment / inter-scroll results (which one always should!), and does not make overly
> broad claims, there is no problem.

**He is right, and the framing was the problem.** Disjoint means those pixels were never
trained on, so there is no label leakage, and an intra-segment held-out number is a
legitimate thing to report — provided it is named that. The issue title said "leak-free",
which presupposes a leak; this document's body already said the corpus is not wrong and kept
the claim directional, but the title outran it.

What the close does not touch is the measured part. His own advice is that intra-segment,
inter-segment and inter-scroll results must be read differently; the strata above put a size
on that difference for this corpus — +0.14 F1 on w016 between adjacent and distant held-out
pixels, against a flat control. So the right reading of docs/14's 0.74–0.77 is **an
intra-segment ceiling**, not a statement about what the released models generalise to. That
distinction is what this document is for, and it survives the close.

The thread was also **locked**, and closed as *not planned*, so there is no reply and this
document is where the concession is recorded instead.

It was filed separately from [#1231](https://github.com/ScrollPrize/villa/issues/1231), which
asks whether the *missing* masks are intended and remains open.

---

MIT-licensed.
