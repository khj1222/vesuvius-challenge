<!--
Draft reply to villa PR #1471 "create_label_zarrs: stream striped TIFFs, not just tiled (refs #1231)"
target: https://github.com/ScrollPrize/villa/pull/1471
author of that PR: jaideepsaipadhi. This answers their 2026-08-27 comment, which asked us to
run their branch against the striped masks our harness generates, "particularly the odd-extent
cases", and asked whether maintainers want the two copies of the file converged.

Trees under test:
  head = 6cec0116cd2c6c37f60f20e40e22a2452156a651 (the PR)
  base = aab644c9c065f45aedb8836be479432350a16c6e (its parent; create_label_zarrs.py and
         label_zarr.py are byte-identical between this commit and current main tip 5479453)
Everything below is reproducible from the scripts in scratchpad; raw results are in
work/results.json and work_fix/results_fix.json.

The evidence link in the body resolves only after runs/pr1471_striped_check/ is pushed.
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

Ran it against the harness. Short version: **the streaming path reproduces today's output exactly on every extent I could construct, and it hard-crashes on a class of striped file that converts fine today.** The crash is one line and I have a verified fix for it. The odd-extent case you were least confident about turned out not to be where it breaks.

## What I ran

Your head `6cec011` against its parent `aab644c` (`create_label_zarrs.py` and `label_zarr.py` are byte-identical between that commit and current `main`, so "parent" and "today" are the same thing here). 55 variants, same content through both trees, compared per pyramid level.

One methodological note first, because it nearly cost me the whole run: **equality has to be read off the decoded arrays, not the chunk files.** The blosc payloads are not reproducible across processes — the *same code on the same input* writes different bytes twice — so my first pass flagged all 55 variants as differing and every one of them was compression, not data.

**42 of 42 variants that ran on both trees are identical at all six levels: 252 level comparisons, 9,661,092,220 voxels, zero mismatches.**

Scripts, raw per-level results and a checker that re-derives every number quoted here: [`runs/pr1471_striped_check/`](https://github.com/khj1222/vesuvius-challenge/tree/main/runs/pr1471_striped_check).

| axis | covered |
|---|---|
| extents | 2048×2048, 2049×2051, 1025×1027, 1543×2311, 4099×37, 37×4099, 2050×2050 (even, but odd from level 1 down), 63×65 |
| layouts | tiled 256×256; `rowsperstrip` 1, 7, 1024, whole-image |
| downsample mode | `nearest` and `mean` (composite naming), the latter on three extents |
| dtype | uint8 binary, uint8 grayscale, uint16 |
| codecs | none, LZW, deflate, PackBits — plus JPEG, which falls through to the in-memory path on both trees (`streamed_tiled_tiff=false`) and matches |

So the specific risk you named — a strip boundary disagreeing with a downsample step — does not materialise, and I think it structurally cannot. `_write_downsample_block` addresses blocks in the *target* grid and reads `source[:, block_y*2 : ...]`, so every 2×2 window starts on an even source row no matter where strips fall. `rowsperstrip=7`, 1024-row blocks and a 2049-row image agree with the in-memory pyramid exactly, in both modes.

## What does break: a strip of exactly one row

13 of the 55 crash on your tree and convert fine on the parent:

```
ValueError: Expected a 2D image at ...\seg_inklabels.tif, but got shape=(2051,)
```

`page.decode()` returns `(depth, rows, columns, samples)` for a strip exactly as it does for a tile — your reading of the block API holds. But when `rows == 1` the result is `(1, 1, W, 1)`, and `_normalize_to_2d`'s `np.squeeze` drops **both** leading axes, so a single row comes back one-dimensional and the 2D guard rejects it. Decoded shapes, straight out of tifffile 2026.3.3:

| input | strip | `decode()` shape | after `_normalize_to_2d` |
|---|---|---|---|
| 2049×2051, `rowsperstrip=1024` | 0 | `(1, 1024, 2051, 1)` | `(1024, 2051)` |
| 2049×2051, `rowsperstrip=1024` | 2 (last, 1 row) | `(1, 1, 2051, 1)` | **ValueError** |
| 2049×2051, `rowsperstrip=7` | 292 (last, 5 rows) | `(1, 5, 2051, 1)` | `(5, 2051)` |
| 2048×2048, tiled 256 | any | `(1, 256, 256, 1)` | `(256, 256)` |

Two things worth noting. Short strips are *not* padded — a 5-row remainder decodes as 5 rows — so only the exactly-one-row case is affected. And tiles can never hit it, because TIFF tile heights are multiples of 16; that is why the `is_tiled` gate hid this.

The trigger is a property of the extent, not the content:

- `rowsperstrip == 1` — every strip is one row, and this is what a lot of writers emit for uncompressed or small images; or
- `height % rowsperstrip == 1` — only the last strip is, which is roughly a 1-in-`rowsperstrip` accident of image height.

Both are in the matrix: 513×1027 at `rowsperstrip=256`, and 2049×1027 at `rowsperstrip=16`, crash; the same extents tiled do not. This is a regression in the strict sense — those files convert today, slowly, through the in-memory path.

## A fix, verified

`_normalize_to_2d` is right for a whole image and wrong for a decoded block, so index the axes instead of squeezing them:

```python
def _decoded_block_to_2d(decoded: np.ndarray, source_path: Path) -> np.ndarray:
    """Return a decoded tile or strip as 2D without losing a length-1 row axis.

    ``page.decode`` returns ``(depth, rows, columns, samples)`` for a strip
    exactly as it does for a tile. ``_normalize_to_2d`` squeezes, which is
    right for a whole image but drops the row axis of a one-row strip --
    ``(1, 1, width, 1)`` becomes ``(width,)`` -- so index the axes explicitly.
    """
    block = np.asarray(decoded)
    if block.ndim == 4:
        return np.ascontiguousarray(block[0, :, :, 0])
    return _normalize_to_2d(block, source_path)
```

and call it in place of `_normalize_to_2d(decoded, input_path)` in `_write_streamed_tiff_level_zero`. I deliberately did not reach for `np.atleast_2d`: it fixes a one-row strip and silently transposes a one-column image.

Re-ran base / head / head+fix over 27 variants chosen to hit exactly this condition: **head crashes on 25, head+fix crashes on 9, and all 18 comparable outputs are identical to the parent's in-memory output at every level.**

Your own 14 tests pass on both trees, which is to say they don't reach this — a one-row-strip fixture would be the cheapest thing to add.

## Pre-existing, and not yours: degenerate extents

The 9 that still fail with the fix are 1×4099, 4099×1 and 1×1, and they fail on **the parent too**, earlier and in a different place — `_normalized_2d_shape` squeezes the length-1 axis out of the *page* shape and then rejects the result as not 2D. So a whole-image row or column has never converted through either path. I left that alone: it is a separate decision about what `_normalize_to_2d` should mean, and it is worth knowing only so that a squeeze fix here does not accidentally paper over it.

## Real file

Our harness writes `tile=(256, 256)` + LZW today, so I re-encoded a real one rather than claiming to have a striped original: the held-out validation mask for `w00_20231016151002`, 32249×51380 uint8, 19,083,344 ink pixels, odd height. Same pixels, different container. Both runs on your tree, one at a time, no other load:

| input layout | blocks | file | wall | peak RSS |
|---|---|---|---|---|
| tiled 256×256 | 25,326 tiles | 10.49 MB | 143.27 s | 0.884 GiB |
| `rowsperstrip=1024` | 32 strips | 1.36 MB | 195.84 s | 0.881 GiB |

**The two outputs agree at all six levels, zero mismatched pixels** (19,083,344 / 4,773,300 / 1,194,557 / 299,279 / 74,832 / 18,713 non-zero from level 0 down).

The striped run is 37% slower, and the reason is structural rather than alarming: a strip spans the full width, so with 1024-wide write blocks each strip is decoded once per horizontal block — 51 times here. If you want that back, the smallest change is to let the write block span the full width when `page.chunked[1] == 1`; the block then holds one strip's worth of rows (52 MB at this width) instead of a 1024×1024 tile. I measured that variant too — see the table below — but it is an optimisation, not a correctness issue, and the PR stands without it.

One coincidence worth stating: this file misses the crash by luck. 32249 mod 1024 = 505 and 32249 mod 7 = 0. At `rowsperstrip=8` (32249 mod 8 = 1) it would have died on the last strip, after doing all the work.

## The pyramid question, with numbers

You said you would rather measure the level *n*−1 read-back than assert it, and that you did not have striped numbers the way I do. Here they are, same file, same box, same sampler, one run at a time:

| implementation | wall | peak RSS |
|---|---|---|
| this PR — stream level 0, derive levels from zarr | 195.84 s | 0.881 GiB |
| this PR + full-width write blocks | 104.38 s | 0.881 GiB |
| `merge-ink-pipelines` (#1234) — stream level 0, derive levels from a 2D pyramid in memory | 64.62 s | 1.929 GiB |

Both stores use the same chunking `(65, 128, 128)`, the same Blosc(zstd, clevel 3, bitshuffle) and `write_empty_chunks=False`, so the storage side is not what separates them.

**Read that as: your design costs 3.0x the wall clock and gives back 2.2x on peak memory, and most of the time it costs is not the read-back.**

The memory column is the part I would defend. The merged copy's 1.929 GiB is the level-0 image held in memory to derive the pyramid — the exact allocation the streaming path exists to avoid — and it grows with the image, while the read-back's footprint does not. That 1.929 GiB also reproduces #1234's own post-review measurement of 1.99 GiB on this same file, which is a useful check that these two runs measure the same thing.

The time column mostly is not about the read-back. Full-width write blocks — one extra condition on the block iterator — bring your design to 104.38 s at the same 0.881 GiB, closing 70% of the gap, and that output is identical to the tiled one at all six levels too.

**There is one thing you should know before deciding, though, because it is about your PR and not mine.** The pre-review version of #1234 *was* your design — stream level 0, derive the levels by reading level *n*−1 back from zarr — and @erdpx asked me to replace it:

> would you consider building only the 2d pyramid in memory, then writing each level directly to DEFAULT_LABEL_SLICE, instead of rereading the zarr levels from disk? this should be considerably faster while still avoidng materializing the N-slice volumes; the 2d pyramid itself is only ~1.33× the source image size

My numbers at the time, on this same file: 114.5 s / 1.61 GiB before, 66.5 s / 1.99 GiB after. Today's runs reproduce the ordering. So the speed half of that review holds up, and the ~1.33× estimate turns out to be roughly right too (1.929 GiB against a 1.66 GB image).

Where I think your case is still live: 1.33× of *the source image* is unbounded in the image, and the read-back is not — 0.881 GiB here whatever the width — and with full-width blocks the speed gap narrows to 1.6x. That is the argument I would put in front of a reviewer rather than the read-back on its own.

## On converging the two copies

I don't know, and I would rather say so than guess on a maintainer's behalf. What I can offer is that the divergence is not accidental: it is the review above, recorded on one branch, and #1234 was merged by @erdpx on 2026-08-14 in that shape. Whether that preference should propagate to `main`, or `main`'s approach back the other way, needs someone who knows where `merge-ink-pipelines` is going — but at least it is a decision someone made, not two people solving the same problem in ignorance of each other.

For what it's worth I agree with your instinct on scope: whichever way it goes, converging the files is a separate change from this one, and holding this PR for it would be the wrong trade.
