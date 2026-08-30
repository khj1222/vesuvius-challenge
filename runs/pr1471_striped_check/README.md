# Odd-extent check of villa PR #1471 (striped-TIFF streaming)

Run on request from the PR author, who asked for the striped masks this repository's
harness produces to be pointed at their branch, "particularly the odd-extent cases".
The reply built from these artifacts is `submission/pr1471_reply_jaideepsaipadhi.md`.

## Trees compared

| name | commit | what it does with a striped TIFF |
|---|---|---|
| `head` | [`6cec011`](https://github.com/ScrollPrize/villa/pull/1471) | streams strips (the PR) |
| `base` | `aab644c` (the PR's parent; `create_label_zarrs.py` and `label_zarr.py` are identical on `main` tip `5479453`) | loads the whole image, builds the pyramid in memory |
| `head+fix` | `head` + the one-row-strip fix quoted in the reply | streams strips |
| `head+fullwidth` | `head+fix` + full-width write blocks | streams strips, one decode per strip |
| `merge-ink-pipelines` | `external/villa` at `fc6d9a7` (our merged [#1234](https://github.com/ScrollPrize/villa/pull/1234)) | streams strips, derives levels from a 2D pyramid in memory |

## Findings

1. **Correctness: 42/42 identical.** Every variant that ran on both trees matches at all six
   pyramid levels — 252 level comparisons, 9,661,092,220 voxels, zero mismatches. Covers eight
   extents (odd/odd, coprime, parity-flipping, tall, wide, tiny), five layouts, both downsample
   modes, uint8/uint16, and four codecs plus a JPEG fallback.
2. **A crash the PR introduces: a strip of exactly one row.** `page.decode()` returns
   `(depth, rows, columns, samples)`; when `rows == 1`, `_normalize_to_2d`'s `np.squeeze` drops
   the row axis and the 2D guard rejects the result. Triggered by `rowsperstrip == 1` or by
   `height % rowsperstrip == 1`. 13 of the 55 matrix variants, and 25 of the 27 in the targeted
   re-run. Tiles cannot hit it (TIFF tile heights are multiples of 16), which is why the
   `is_tiled` gate hid it.
3. **The fix is verified**, and does not touch the pre-existing failure of 1×N / N×1 / 1×1
   images, which fail on both trees in `_normalized_2d_shape`.
4. **Cost measured on a real 32249×51380 mask** (re-encoded striped; the harness writes tiled
   today): correctness holds at real scale, the striped input costs +37% wall over tiled
   because each strip is decoded once per horizontal block, and the PR's read-back design
   trades 3.0x wall for 2.2x peak RSS against the merged copy.

## Files

| file | what |
|---|---|
| `results_matrix.json` | the 55-variant matrix: per-variant geometry, timings, and full per-level comparisons |
| `results_onerow_fix.json` | the 27-variant targeted re-run across base / head / head+fix |
| `probe_decode_shapes.jsonl` | raw `page.decode()` shapes for first and last strips, per layout |
| `real_inputs.json` | geometry of the real mask re-encoded into each layout |
| `real_timings.jsonl` | wall time and sampled peak RSS for the four real-file runs |
| `real_equality.jsonl` | per-level equality of the real striped outputs against the tiled one |
| `pytest_pr_suite.txt` | the PR's own 14 tests, on `head` and on `head+fix` |
| `verify_numbers.py` | re-derives every figure quoted in the reply and asserts it appears there |

## Reproducing

`drive.py` builds the matrix and runs both trees; `drive_fix.py` does the targeted re-run;
`convert_many.py` and `real_run.py` are the in-tree workers (the latter samples peak RSS);
`compare_zarr.py` and `compare_real.py` are the comparators; `summarize.py` prints the matrix
table. The tree paths at the top of the drivers are local worktrees and need editing to run
elsewhere.

One methodological note that cost an hour: **zarr chunk payloads are not reproducible across
processes**, so byte-comparing the stores reports differences that do not exist in the data.
Every verdict here is decoded-array equality; `compare_zarr.py` hashes first only as a fast
path and falls back to a numeric comparison whenever the hashes disagree, which was always.
