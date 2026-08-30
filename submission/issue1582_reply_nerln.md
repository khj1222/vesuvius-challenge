# Reply to nerln (and Bullo27) on villa issue #1582

**Post as:** a comment on https://github.com/ScrollPrize/villa/issues/1582
**Status:** rewritten 2026-08-30 after Bullo27 answered the pooling question first
(their comment of 2026-08-30T01:23Z). The earlier draft presented that measurement as
news; this one credits it and keeps only what is still additive.
**Backing:** `tools/check_pyramid_pooling.py` + `runs/pyramid/*_pooling.json` in
khj1222/vesuvius-challenge, written up as docs/15 appendix 3.

---

@Bullo27 got to the pooling question before me and measured it better, so first: I
reproduce it. On my own windows — three scrolls (Paris4 w01, 1667 w013, 0139 w035), both
level transitions, 18 window comparisons read over anonymous https — modelling the
per-level rounding as round-half-up makes the coarse level **byte-exact**: max |diff| = 0
on 100% of pixels, against 16–98 grey levels for a decimation model. I had first compared
against the *unrounded* mean, seen a residual of exactly 0.50, and written that up as "~87%
exact"; that 0.50 was the rounding I had not modelled, not slack in the pyramid. I had also
missed that `multiscales[0].metadata` says `downsampling_method: "mean"` outright. Both
fixed, and the write-up says so.

**So your assumption holds — and the factor is larger than either of us said.** The part I
think is still missing from the thread is that the pyramid is **XY-only**: the OME scales
go `[2.4, 2.4, 2.4]` → `[2.4, 4.8, 4.8]` → `[2.4, 9.6, 9.6]`, so z is never touched. That
matters because `prepare_9um_isotropic_input` then mean-pools **four z planes**
(`POOL_Z = 4`) which are still 2.399 µm apart. The two averagings are independent, so per
voxel of the prepared aligned input:

- one level-2 pixel = mean of a 4×4 block of acquired pixels = 16 samples;
- one output voxel = mean of 4 such planes = **64 acquired 2.399 µm voxels**, spanning
  9.596 µm on each axis;
- the native voxel covering that same space is **one** 9.362 µm acquisition.

Your comment treats the z step as differing between the families only as their nominal
scales do, which is true of the *acquisitions* but not of the *prepared inputs* — the
aligned one gets a second 4× average that the native one never gets. Under the independence
assumption you stated, that is a factor of eight rather than four. I am not claiming the
eight: like you, and like Bullo27, I have not tested whether the noise is independent
between neighbouring 2.399 µm voxels. What I can say is that the field being averaged is
not flat — inside the 2×2 blocks each level averages, the standard deviation runs 1.7 to
5.8 grey levels across those 18 windows — so the pooling is acting on real variation.

**One piece of F1-side evidence, now that the input side is settled.** Before this thread I
ran a pre-registered arm on the input-space version of the question: estimate the source
corpus's mean radial power spectrum and the target's, apply the matching filter to the
native render, re-infer. The two families separate cleanly in that statistic (every aligned
volume at spectral centroid ≥ 0.0278, every native ≤ 0.0262) and the filter closes 38% of
the distance — mean over four filtered volumes of the drop in total variation against the
source profile. The F1 effect was **+0.005 mean, median 9.1% of the aligned-native gap, 17
of 24 cells improving**: no effect by the noise floor I had fixed in advance. (That median
is per cell, `(filtered − raw) / (aligned − raw)` at the same segment, seed and step; the
mean of that ratio is unusable because one cell has a gap of 0.0015.) That is what a
sample-count account predicts — a filter can reshape a spectrum, it cannot restore
measurements that were never taken — and not what "different but equivalent representation"
predicts.

**On the reference arms** — agreed, and I would not cite them either. You put the reason
better than I did: with 90.7–96.8% of the available headroom already spent on training
pixels, there is 0.014–0.036 of room for a ±0.05 effect to appear in, so the ordering there
is uninformative in both directions.

**On your bullet 3, I agree with your stronger form.** Report the family; never refuse on
it. A preflight check that enforced family match would refuse the better-sampled input on
the authority of a check, and the corpus makes that concrete: 24 of 29 representations are
aligned and all five native ones belong to a single scroll, so "match the family" and "use
the worse input" coincide exactly where it would bite.

And the open item you narrowed to is the one I would keep: absence of provenance being the
de facto marker of the native family is a publishing accident rather than a declaration,
and it breaks silently the first time someone publishes either kind the other way round.
That stands on its own without needing the transfer result.

Tool and raw reports: [`tools/check_pyramid_pooling.py`](https://github.com/khj1222/vesuvius-challenge/blob/main/tools/check_pyramid_pooling.py),
[`runs/pyramid/`](https://github.com/khj1222/vesuvius-challenge/tree/main/runs/pyramid),
write-up in [docs/15 appendix 3](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/15_loso_cross_scroll.md).

- [x] The pooling and spectral figures above were produced on 2026-08-30 by the linked
      tools against the published volumes; the 64-voxel count follows from them plus
      `POOL_Z = 4` in `scripts/prepare_9um_isotropic_input.py`.
