<!--
Draft reply on villa PR #1471 "create_label_zarrs: stream striped TIFFs, not just tiled (refs #1231)".
target: https://github.com/ScrollPrize/villa/pull/1471
replying to: hendrikschilling, 2026-09-04T09:44:27Z
  https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5538675446
  ("...without some good counter arguments I tend to close this", plus an LLM review with
   two P1 and two P2 items)

Why we are in this thread at all: the PR author asked us in on 2026-08-27 to run their branch
against the striped masks our harness writes, and we posted the result on 08-31:
  https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5478665794

⚠️ This is NOT our PR. The reply supplies measurements that already exist and explicitly
leaves the decision to the maintainer. Do not argue for the PR beyond what was measured.

⚠️ Two honesty points that are deliberately kept in, because they cut against us:
  - our striped test used rowsperstrip=1024, NOT the single-whole-image-strip worst case the
    review describes, so the review's decode count is worse than anything we measured;
  - P2 #4 (multipage) is the PR author's own finding from 08-24, not ours, and it reproduces
    on the copy WE got merged.

All figures below are re-derived from runs/pr1471_striped_check/ (committed and public);
`verify_numbers.py` in that directory re-derives them from the raw artifacts.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

Not my PR and I have no stake in whether it lands — but two of the four review items were
checked against this branch a few days ago, [in this
thread](https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5478665794), and one of
them has a measured answer that I think changes its weight. Raw artifacts and both patches
are in
[`runs/pr1471_striped_check/`](https://github.com/khj1222/vesuvius-challenge/tree/main/runs/pr1471_striped_check).

**P1 #2 (one-row strips) is real, and it is already fixed and verified.** I hit the identical
`ValueError` on 08-31, before this review. The trigger is extent, not content:
`rowsperstrip == 1`, or `height % rowsperstrip == 1` so that only the final strip has one
row. It caught 13 of 55 matrix variants and 25 of 27 in a targeted re-run. `page.decode()`
returns `(depth, rows, columns, samples)` and `np.squeeze` drops the row axis when
`rows == 1`; indexing the axes explicitly (`block[0, :, :, 0]`) fixes it. That patch rescues
16 of the 25 — the other 9 are 1×N / N×1 / 1×1 degenerate extents that fail on the parent
tree too, so they are not this PR's doing — and all 18 outputs that can be compared against
the parent come out identical to it at every level. (`np.atleast_2d` looks like the same fix
and is not: it repairs one-row and silently transposes one-column.) The patch is
`patch_onerow_strip_fix.patch`.

**P1 #1 (re-decoding) is real, and the remedy it asks for is a block-shape change that I
measured.** The review is right that this iterates destination blocks, so a full-width strip
is decoded once per horizontal block — on a real 32249×51380 mask that is 51 decodes per
strip. Making the write blocks full width, which for full-width strips is exactly the
"source-strip-major, decode each strip once" the review asks for:

| tree, same 32249×51380 label image | wall | peak RSS |
|---|---|---|
| this branch, tiled 256 input | 143.27 s | 0.884 GiB |
| this branch, striped input (`rowsperstrip=1024`) | 195.84 s | 0.881 GiB |
| **this branch + one-row fix + full-width write blocks** | **104.38 s** | **0.881 GiB** |
| `merge-ink-pipelines` today (#1234), striped input | 64.62 s | 1.929 GiB |

So after a small patch (`patch_fullwidth_blocks.patch`) the striped path is *faster than this
same branch reading a tiled copy of the same image*, at the same memory. The decode traffic
in P1 #1 is a consequence of the block shape, not of the streaming design.

One caveat that cuts against the PR and in favour of the review: I tested
`rowsperstrip=1024`, **not** the uncompressed `tifffile.imwrite` default of one
whole-image strip. That case is strictly worse than anything in my table, and I did not
measure it.

**On "just convert to tiled beforehand".** That is a legitimate answer and it is cheap for
anyone who knows to do it. The thing worth weighing is what happens to someone who does not:
the in-memory path materialises the full 65-slice pyramid, which for the 16125×25690 label
image referenced in the review is a 25 GiB allocation — that is the failure that produced
#1231. If pre-conversion is the intended workflow, the win is probably mostly captured by
saying so where people hit it, in the docs and in that allocation's error path, and none of
that needs this PR.

**Whatever is decided, it probably wants deciding for both copies.** This function exists
twice: `vesuvius/src/vesuvius/ink_detection/preprocessing/create_label_zarrs.py` on `main`
(585 lines) and `ink-detection/koine_machines/preprocessing/create_label_zarrs.py` on
`merge-ink-pipelines` (840 lines), and they have diverged well past a rename. The
`merge-ink-pipelines` copy already streams untiled labels — that was #1234, mine, merged
2026-08-14 — and it took the *opposite* trade on the pyramid: build the 2D pyramid in memory
rather than reading levels back from zarr, at @erdpx's request during review, for 1.7x the
speed and 1.2x the peak memory. Closing this PR leaves `main` on the in-memory path that
#1231 reported, while the other copy streams. That divergence seems like the more useful
thing to settle than this diff.

**P2 #4 (multipage) is real and is not confined to `main`.** Credit where it is due — that
was @jaideepsaipadhi's finding, which I reproduced on 08-24 on the merged copy: a
`(5, 40, 60)` array comes out `(5, 40)` there too, via the same
`np.squeeze` / `image[..., 0]` normalisation. As far as I know it is still unfiled against
either copy.

Happy to re-run any of the above, or to hand over the patches and the 55-variant matrix if
whoever picks this up wants them. Both patches are small and neither is mine to submit here.
