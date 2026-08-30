# Reply to nerln on villa issue #1582

**Post as:** a comment on https://github.com/ScrollPrize/villa/issues/1582
**Status:** drafted 2026-08-30, awaiting the user posting it.
**Backing:** `tools/check_pyramid_pooling.py` + `runs/pyramid/*_pooling.json` in
khj1222/vesuvius-challenge, written up as docs/15 appendix 3.

---

You flagged the one assumption your mechanism rests on — whether the published pyramids were
built by averaging or by decimation — and said the argument weakens if it is decimation. That
is checkable from the published data, so I checked it, and it comes out on your side by a
wide margin.

**Method.** Read small windows straight out of the published surface volumes over anonymous
https and compare each pyramid level against the level below it, pooled two ways: as a 2×2
mean, and as a 2×2 decimation. Three scrolls (Paris4 w01, 1667 w013, 0139 w035), both level
transitions (0→1 and 1→2), three 64×64 windows at three z planes each — 18 window-level
comparisons.

| model | max abs difference | exact after rounding | correlation |
|---|---|---|---|
| 2×2 **mean** | **0.50 in every one of the 18** | 86.9–88.0% | 0.99994+ |
| 2×2 decimation | 16–98 | — | 0.975–0.998 |

0.50 is exactly the rounding bound for the mean of uint8 values, and ~87% is the share of
blocks whose average lands on an integer. **Every level is a plain 2×2 mean.** Your factor
stands.

**One correction, in your favour.** The published pyramid is **XY-only** — the volumes' own
OME metadata gives the scales as `[2.4, 2.4, 2.4]` → `[2.4, 4.8, 4.8]` → `[2.4, 9.6, 9.6]`,
so z is never downsampled. That makes `prepare_9um_isotropic_input`'s `POOL_Z = 4` an
*independent* second averaging rather than a re-count of the same one: it pools four planes
that are still 2.399 µm apart. So per output voxel:

- level 2 pixel = mean of a 4×4 block of acquired pixels = 16 samples;
- output voxel = mean of 4 such planes = **64 acquired 2.399 µm voxels**, spanning 9.596 µm
  on each axis;
- the native voxel covering that same space is **one** 9.362 µm acquisition.

Under the independence assumption you stated, that is a factor of eight, not four. I am not
claiming the eight: I did not measure whether the noise is independent between neighbouring
2.399 µm voxels, and that is the assumption doing the work. What I can say is that the field
being averaged is not flat — the standard deviation inside the 2×2 blocks each level averages
runs 1.7 to 5.8 grey levels across the 18 windows — so the pooling is acting on real
variation rather than reproducing a constant.

**A second piece of evidence that fits sampling density and does not fit anything else I can
think of.** Before your comment I ran a pre-registered arm on the input-space version of this
question: estimate the source corpus's mean radial power spectrum and the target's, apply the
matching filter to the native render, re-infer. Aligned and native separate cleanly in that
statistic (every aligned volume at spectral centroid ≥ 0.0278, every native ≤ 0.0262) and the
filter closes 38% of the distance at the patch level — mean over the four filtered volumes of
the drop in total variation against the source profile. The F1 effect was **+0.005 mean,
median 9.1% of the aligned-native gap, 17 of 24 cells improving** — no effect by the noise
floor I had fixed in advance. (That median is per cell, `(filtered − raw) / (aligned − raw)`
at the same segment, seed and step; the mean of that ratio is useless here because one cell
has an aligned-native gap of 0.0015.) That is what a sample-count account predicts: a filter can reshape a
spectrum, but it cannot restore measurements that were never taken. It is not what a
"different but equivalent representation" account predicts.

**On the reference arms** — agreed, and I would not cite them either. You put the reason
better than I did: with 90.7–96.8% of the available headroom already spent on training pixels
there is 0.014–0.036 of room for a ±0.05 effect to appear in, so the ordering there is
uninformative in both directions.

**On your bullet 3, I agree with your stronger form.** Report the family; never refuse on it.
A preflight check that enforced family match would refuse the better-sampled input on the
authority of a check, and the corpus makes that concrete: 24 of 29 representations are
aligned, and all five native ones belong to a single scroll, so "match the family" and "use
the worse input" coincide exactly where it would bite.

And your remaining open item is the one I would keep too: absence of provenance being the de
facto marker of the native family is a publishing accident, not a declaration, and it breaks
silently the first time someone publishes either kind the other way round. That stands on its
own without needing the transfer result.

Tool and raw reports: [`tools/check_pyramid_pooling.py`](https://github.com/khj1222/vesuvius-challenge/blob/main/tools/check_pyramid_pooling.py),
[`runs/pyramid/`](https://github.com/khj1222/vesuvius-challenge/tree/main/runs/pyramid),
write-up in [docs/15 appendix 3](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/15_loso_cross_scroll.md).

- [x] The pooling figures above were produced today by the linked tool against the published
      volumes; the 64-voxel count follows from them plus `POOL_Z = 4` in
      `scripts/prepare_9um_isotropic_input.py`.
