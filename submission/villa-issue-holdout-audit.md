# villa issue draft — the three shipped ink_9um validation masks are cut through annotated regions

**To post:** https://github.com/ScrollPrize/villa/issues/new (tick the checkbox)
**Related:** our [#1231](https://github.com/ScrollPrize/villa/issues/1231) (missing
`_validation_mask` on published segments; triaged to `erdpx`, no reply yet). Post a one-line
pointer comment there afterwards.
**Backing document:** [docs/17](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/17_holdout_audit.md)

Paste everything below the `---` only.

---

## Title

```
ink_9um: all three shipped _validation_mask splits cut through annotated regions, and w016 admits no leak-free held-out at all
```

## Body

**In one sentence:** All three `ink_9um` segments that ship a `_validation_mask` split their
annotation *within* connected regions rather than by whole regions, so 23% to 59% of their
held-out pixels sit within one training patch of pixels the model trained on — and on the two segments
where a control model exists, that adjacency is worth an extra +0.14 and +0.07 F1.

**Why I looked:** I have been using these three masks as the only honest yardstick on this
corpus — they are what my scorecard of the released checkpoints is measured on, and what the
"honest ceiling of F1 0.74–0.77" in that scorecard means. Before leaning on that number further
I wanted to check that the masks hold out what they appear to.

**Data:** `ink_9um` labels — 24 segments in `aligned-scrollprizeorg-21slices` and 5 in
`native9-scrollprizeorg-21slices`. Of those 29, exactly three ship a `_validation_mask`:
`pherc0139-w016`, `pherc0814-46527` and `pherc1667-w029`. The other 26 do not. In this corpus the validation mask is disjoint from the supervision mask, so the two
together are the segment's whole annotation.

### 1. Geometry — the splits are internal to regions

| segment | annotation | connected regions | held out | regions holding **both** kinds of pixel | held-out px within one 128 px patch of a training px | within two |
|---|---|---|---|---|---|---|
| `pherc0139-w016` | 593,824 px | 3 | 175,222 (29.5%) | **2 of 3** | **58.6%** | 99.1% |
| `pherc0814-46527` | 590,044 px | **1** | 161,051 (27.3%) | **1 of 1** | 45.0% | 87.8% |
| `pherc1667-w029` | 1,595,268 px | 8 | 382,353 (24.0%) | 1 of 8 | 23.2% | 45.4% |

Distance from each held-out pixel to the nearest supervised pixel:

| segment | min | p25 | median | p75 | max |
|---|---|---|---|---|---|
| `pherc0139-w016` | 1 | 55 | 108 | 166 | 275 |
| `pherc0814-46527` | 1 | 72 | 142 | 214 | 319 |
| `pherc1667-w029` | 1 | 138 | 283 | 690 | 986 |

Two consequences that do not depend on any model:

- **`pherc0139-w016` has no leak-free held-out subset at all.** 99.1% of its held-out pixels lie
  within two patches of a training pixel, and the 1,595 px beyond that contain **no ink**, so
  there is no distance threshold at which a clean F1 can even be computed there.
- **`pherc0814-46527`'s entire annotation is one connected region**, split internally.

I do not think this reflects a mistake in how the split was made. With three annotated regions —
or one — a region-aware split is arithmetically impossible: asked for w016's official 29.5%, a
whole-region planner can only offer 40.8%, because there are two groups to choose between. The
constraint is the annotation geometry, not the split.

### 2. Does the adjacency pay? (no new training needed)

Two model families already exist for these segments:

- **released** — the public `ink_9um` checkpoints, which trained on the segment's supervision;
- **control** — leave-one-scroll-out arms I trained for a cross-scroll study
  ([write-up](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/15_loso_cross_scroll.md)),
  which never saw the scroll at all.

Raw per-stratum F1 is not comparable across distance strata (they differ sharply in ink
density), so the control is what makes the comparison mean something: it measures each stratum's
intrinsic difficulty, and anything beyond that is adjacency. Mean best-F1 over all 14 released
checkpoints (7 steps × 2 seeds):

**`pherc0139-w016`**

| stratum | px | ink density | released | control | gain |
|---|---|---|---|---|---|
| <64 px | 51,311 | 0.1278 | 0.7609 | 0.5356 | **+0.2253** |
| 64–128 | 51,400 | 0.2808 | 0.6650 | 0.5399 | +0.1250 |
| 128–256 | 70,916 | 0.2851 | 0.6664 | 0.5786 | **+0.0878** |
| ≥256 | 1,595 | 0.0000 | — | — | no ink, F1 undefined |

The control is nearly flat (0.5356 / 0.5399 / 0.5786) and finds the *nearest* stratum hardest,
which matches its ink density of 0.128 against 0.285. Only the model that trained next door does
better there. **Excess gain of the nearest stratum over the farthest scorable one: +0.1375 F1.**

**`pherc1667-w029`**

| stratum | px | ink density | released | control | gain |
|---|---|---|---|---|---|
| <64 px | 44,574 | 0.1190 | 0.7405 | 0.4767 | **+0.2638** |
| 64–128 | 43,985 | 0.0000 | — | — | no ink, F1 undefined |
| 128–256 | 85,215 | 0.3160 | 0.7781 | 0.6427 | +0.1354 |
| ≥256 | 208,579 | 0.2675 | 0.7010 | 0.5105 | **+0.1905** |

**Excess gain +0.0733 F1**, though the trend here is not monotone — the middle stratum sits below
the far one — so w029 supports the nearest-stratum effect but not a clean distance gradient.

`pherc0814-46527` is not in this comparison: no LOSO arm excluded its scroll, so there is no
control for it. Its structural finding stands regardless.

**Robustness.** Comparing gain(nearest) against gain(farthest) checkpoint by checkpoint, the
nearest stratum wins in 10 of 14 on each segment, 20 of 28 together. The mean effect is clear;
individual checkpoints are noisy (per-checkpoint differences on w016 range from −0.067 to
+0.369).

### 3. What I think this does and does not show

**Does**: the three shipped splits are internal to annotated regions; w016 admits no leak-free
held-out at all; and on both segments with a control, a model that trained on the segment gains
materially more on held-out pixels adjacent to its training pixels than on distant ones.

**Does not**: give a precise correction to any published number. The strata differ in ink
density and size, and the released and control families differ in more than segment exposure
(different corpora, different training lengths). What I would claim is only directional — that
held-out scores on these masks read optimistic rather than conservative.

### 4. What would help, cheapest first

1. **Report by distance stratum.** Free, no new data: publish any held-out number alongside the
   share of its pixels within a patch of training supervision.
2. **Hold out with a buffer** where a whole-region split is impossible — drop at least one patch
   width of training supervision around the held-out area. Costs training data, buys an honest
   number.
3. **Annotate for separation.** `PHercParis4 w00` has 15 separated letter boxes and supports a
   9-group split; w016 supports two groups and 0814 supports one. Several separated regions per
   segment is what makes leak-free splits possible in the first place.

### 5. Tool and raw numbers

Everything above comes from one script, MIT-licensed and usable on any segment:

```bash
python tools/audit_holdout_masks.py <segment_dir>                       # geometry only
python tools/audit_holdout_masks.py <segment_dir> \
    --prediction <trained_on_this_segment.tif> \
    --control    <never_saw_this_scroll.tif>                            # does adjacency pay
```

- tool: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/audit_holdout_masks.py
- write-up: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/17_holdout_audit.md
- raw per-stratum scores (168 rows) and the three geometry reports are committed alongside.

**Happy to open a PR** adding the audit script under `ink-detection/scripts/`, or generating
region-aware masks for the 26 segments that ship none — though as above, that can only be
leak-free where the annotation has enough separated regions to allow it. Say which would be
useful and I'll send it.
