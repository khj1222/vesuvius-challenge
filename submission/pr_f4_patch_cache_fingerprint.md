<!--
Body for a villa PR against `merge-ink-pipelines`.
Branch: khj1222:fix/patch-cache-notices-changed-labels   Worktree: D:/vw8
Base tip when written: 3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e

⚠️ BEFORE OPENING
  1. CONTRIBUTING.md wants human-written commentary on an LLM-assisted PR. The section
     marked "Why this matters to me" is left for the user.
  2. GitHub prefills the body from the commit message; replace it after opening.
  3. Tick the verification checkbox after pasting.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** A run that reuses an `out_dir` after regenerating a mask no longer trains on the previous split without saying so.

**One real example:** Building held-out splits for a label-efficiency study, I regenerated `_supervision_mask.zarr` for a segment and reran training in the same `out_dir`. The run started immediately, found no patches to search for, and trained on the split from before the regeneration.

**Before:** the flat patch cache identifies a segment's labels by *path*. Pointing at a different label tree is caught — the cached paths no longer match any current segment, and the cache is rejected. Regenerating a mask in place is not caught: the paths still match, `flat_patch_finding_cache_token` is built from config knobs only, and the previous split is reused against labels it no longer describes.

**After this PR:** the segment cache key and the cached records carry a digest of the label assets as they are on disk, so an in-place change rejects the cache and the patches are found again.

**Proof:** on a real segment (`phercparis4-w00`, the 21-slice aligned tree), one condition changed at a time:

| step | before this PR | after this PR |
|---|---|---|
| 1. discover patches | 1,266 | 1,266 |
| 2. halve `_supervision_mask.zarr` **in place** | token unchanged | token unchanged |
| 3. rerun, same `out_dir` | **1,266 — byte-identical bounding boxes to step 1** | **1,162** |
| 4. rerun, fresh `out_dir` (the truth) | 1,162 | 1,162 |

So before the change, 104 patches keep training on supervision that no longer exists, and the run looks normal. After it, step 3 returns exactly what step 4 returns, bounding boxes included.

The cache still does its job:

| | first discovery | second, unchanged |
|---|---|---|
| same tree | 3.03 s | **0.02 s** |
| a byte-identical copy of the tree | 3.09 s | **0.02 s** |

61 tests pass across `koine_machines/data`, `common` and `inference`.

**Why / where this is useful:** anyone iterating on held-out splits or on label versions in one `out_dir` — which is what you do when you are measuring what a change to the labels buys. The failure is silent and it points the wrong way: the arm you just changed is scored on the split from the arm before it.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

`Segment.label_fingerprint` hashes, for each of `inklabels` / `supervision_mask` / `validation_mask`, the relative file names and sizes under the asset, and is computed once per segment. It goes into `Segment.cache_key`, into the record written by `save_flat_patch_cache`, and into the tuple `InkDataset` rebuilds when it validates a cache — so the existing "this record matches no current segment → reject the cache" path does the work, and no new invalidation logic is introduced.

Why names and sizes rather than contents: rewriting a zarr changes chunk sizes, and dropping annotation deletes chunks outright when the store does not write empty ones, so the digest moves for the changes that matter. It reads no chunk data, which is what keeps it at 8 ms for a 6,429-file label array — `os.scandir` carries the size on both Windows and Linux, and using `Path.stat()` instead costs 320 ms for the same array.

Two limits I would rather state than have found:

- two different labels that compress to identical sizes under identical names are not distinguished. I could not construct such a case by editing a mask, but it is not impossible, and reading contents would cost the fast path more than the bug costs.
- a tree whose files are rewritten with identical content and identical sizes still fingerprints the same, which is the wanted behaviour: a copied corpus hits the cache, as the table above shows.

**Why this matters to me:** <!-- TO BE WRITTEN BY THE USER before opening: a couple of
sentences on hitting this while iterating on held-out splits, and what the wrong numbers
looked like before the cause was found. -->
