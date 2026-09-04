# F4 against `main`: a patch cache that notices a label changed under it

The same defect as [#1661](https://github.com/ScrollPrize/villa/pull/1661), rewritten where
`main` keeps this code. On `merge-ink-pipelines` the cache identity is spread across three
files (`common/common.py`, `data/ink_dataset.py`, `data/segment.py`); on `main` it is one
module, `vesuvius/src/vesuvius/ink_detection/data/patch_cache.py`, so the fix fits inside it
and **the `Segment` type is not touched at all**.

Branch: `khj1222:fix/patch-cache-fingerprints-labels` (`596e865`), one commit on top of `main`
(`5479453`), 2 files, +131 −1. PR body draft: `submission/pr_f4_main_patch_cache.md`.

## The defect

`load_patch_cache` matches records to segments on
`(dataset_idx, segment_relpath, scale, inklabels_path, supervision_mask_path,
validation_mask_path)` — all **paths**. Pointing a run at a different tree is caught.
Regenerating a mask in place is not: the split is reused against labels it no longer
describes, with the old patch count and the old bounding boxes, so nothing looks wrong while
training continues over supervision that has been deleted.

## The fix

Fingerprint each label asset by the relative names and sizes of its files, carry it in the
record and in the lookup key, and let the rejection path that already exists do the work. No
new invalidation logic, and no change to `Segment`.

## Measured here

| | |
|---|---|
| real w00 label assets | 12,619 files (3,459 ink labels + 9,160 supervision mask) |
| fingerprint, 5 runs | **22.5 – 32.4 ms** |
| the same on `Path.stat()` | **187.4 – 270.5 ms** |
| digest | stable across calls, independent of argument order |

`os.scandir` carries the size along on Windows and Linux alike, which is the whole reason the
cheap version is cheap. No chunk contents are read.

## Evidence

| file | what |
|---|---|
| `pytest.txt` | four tests: the repository's own cache round-trip test, unmodified, plus the three added |
| `real_fingerprint_cost.json` | the cost measurement above, five repeats, on the real label trees |
| `real_cost.py` | the script that produced it |
| `patch_f4_main_fingerprint.patch` | the commit |
| `pytest_conftest_stub.py` | how the tests were run here (see the F3 note — `import vesuvius` pulls `nrrd`) |

## Limits, stated rather than discovered later

Two different labels that compress to identical sizes under identical names are
indistinguishable, because no chunk contents are read. A byte-identical copy of a tree
fingerprints the same as its source, which is the wanted behaviour. And a cache written
before this change carries no fingerprint, so it misses once and is rebuilt.

## The original failure this comes from

On a real segment, 1,266 patches were found; the supervision mask was then halved in place;
rerunning against the same `out_dir` still reported **1,266** with identical bounding boxes,
while the truth in a fresh directory was **1,162**. 104 patches kept training on supervision
that no longer existed. That reproduction is in `runs/f4_patch_cache/` from the
`merge-ink-pipelines` version; the defect and the fix are the same here.
