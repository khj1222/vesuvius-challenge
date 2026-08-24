<!--
Comment for villa PR #1471 "create_label_zarrs: stream striped TIFFs, not just tiled (refs #1231)"
  target: https://github.com/ScrollPrize/villa/pull/1471
  author of that PR: jaideepsaipadhi, opened 2026-08-16, no review yet
  why we are commenting: it cites our issue #1231, and fixes the same bug in the
    OTHER copy of create_label_zarrs. Our #1234 fixed the merge-ink-pipelines copy
    (merged 2026-08-14); main's copy is still unfixed. Verified 2026-08-24.
  status: DRAFT, not posted as of 2026-08-24 — user posts it themselves.

This header is an HTML comment, so the whole file can be pasted as-is —
GitHub renders nothing for it.
-->

Thanks for picking this up — I filed #1231, so this is the fix I was hoping someone would
write. One heads-up that may save you a round: this file exists twice in the repository,
and the same bug was fixed once already on the other copy.

- `merge-ink-pipelines`, `ink-detection/koine_machines/preprocessing/create_label_zarrs.py`
  — fixed in #1234, merged 2026-08-14.
- `main`, `vesuvius/src/vesuvius/ink_detection/preprocessing/create_label_zarrs.py`
  — the file you are patching. I checked it today: still `if not page.is_tiled` on the
  streaming path, still `load_image` → `build_pyramid_with_mode` on the fallback.

So this is not a duplicate of #1234 — the copy you are fixing is still broken, and it is
the more visible of the two.

## The two fixes are not the same fix, and yours is the better half of the level-0 read

Yours streams strips through the chunk API and never holds the whole image. Mine does not
stream strips at all — it reads the image once with `load_image` and then derives the
pyramid in 2D, writing each level straight to `DEFAULT_LABEL_SLICE`. What that avoids is
the *other* allocation on that branch: `build_pyramid_with_mode` embeds every level into a
`(VOLUME_DEPTH, H, W)` volume before writing, 64 of 65 slices zeros. On the real file
behind #1231 that multiplier, not the image itself, is what made the number large.

Measured on that file (32249 × 51380 striped `_validation_mask.tif`): 114.5 s → 66.5 s,
peak RSS 1.99 GiB — which is dominated by holding the level-0 image, exactly the cost your
approach does not pay.

## A data point from the review on the sibling copy, in case it is useful

My first version called `_build_downsample_levels_from_zarr` for the levels, like the tiled
branch does and like yours will after this change. In review, erdpx asked for the opposite:
build the 2D pyramid in memory and write each level straight to the label slice, instead of
reading level *n−1* back out of zarr. That is where the 114.5 s → 66.5 s came from, and the
1.61 → 1.99 GiB peak RSS is what it cost.

I mention it only because the same question may come up here, and on a striped input the
trade reads differently than it did for me: holding the level-0 image to derive the levels
would reintroduce precisely the allocation your streaming avoids. You are better placed than
I am to judge which side that lands on — I just did not want you to meet the question cold,
as I did.

## Your multi-page finding reproduces on the merged copy

Not specific to `main`. The merged copy normalizes the same way:

```python
image = np.squeeze(image)
if image.ndim == 3:
    image = image[..., 0]
```

I ran a `(5, 40, 60)` array through it: comes out `(5, 40)`, identical to what you describe.
Agreed it is out of scope here and deserves its own issue. If you do open one, it may be
worth naming both paths, since a fix to one will not reach the other — and it is your
finding, so I would rather leave that to you than file it myself.

## If it is useful

The verification set I used for #1234 is four synthetic cases — binary and grayscale, even
and odd extents — each requiring byte-identity across all 6 levels between the streamed path
and the in-memory path, plus the real 32249 × 51380 file. The odd-extent cases are the ones
that earn their keep; that is where a block/strip boundary and a downsample step disagree.
Patch copy: https://github.com/khj1222/vesuvius-challenge/blob/main/submission/villa-pr-stream-untiled-labels.patch

Happy to review or test this against the striped masks my harness generates, if that helps
it move.
