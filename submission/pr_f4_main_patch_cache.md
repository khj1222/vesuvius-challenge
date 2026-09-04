<!--
PR body draft — F4 rewritten against `main`.

  head:  khj1222:fix/patch-cache-fingerprints-labels  (596e865, pushed)
  base:  main   ← NOT merge-ink-pipelines
  diff:  2 files, +131 −1

⚠️ Before opening:

1. **"Why this matters to me" is left blank on purpose.** villa/CONTRIBUTING.md asks for
   human commentary on an LLM-assisted PR, and #1434 was closed partly over it.

2. **This supersedes our own #1661** (same defect, three files, on merge-ink-pipelines).
   #1661 is currently our only *non-draft* PR besides #1608 and #1662.

3. **Open it as a DRAFT** unless a slot has come free — GitHub caps open non-draft PRs per
   author at three (#1608, #1661, #1662 today).

⚠️ GitHub prefills a new PR body from the commit message plus the template. Overwrite it
   after opening, and keep the template's checkbox line.

Evidence: runs/f4_main/. Timings are ranges over five runs, not single measurements — the
first run measured 23.7 ms and a repeat measured 23.0, which is why the body quotes a band.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

- [x] I personally encountered or reproduced this, and the change is verified rather than assumed.

`load_patch_cache` matches a cached record to a segment on
`(dataset_idx, segment_relpath, scale, inklabels_path, supervision_mask_path,
validation_mask_path)` — all **paths**. So pointing a run at a different label tree is
caught, and regenerating a mask in place is not.

That second case is not hypothetical; it is what a held-out split looks like while it is
being built. On a real segment: 1,266 patches found, the supervision mask then halved in
place, and a rerun against the same `out_dir` reported **1,266 again with identical bounding
boxes**, where the truth in a fresh directory was **1,162**. 104 patches went on training
against supervision that no longer existed, and nothing in the run looked wrong — the count
matched, so the natural reading was that the mask edit had not taken.

**The change.** Fingerprint each label asset by the relative names and sizes of the files
under it, carry that in the record and in the lookup key, and let the rejection path that
already exists do the work. There is no new invalidation logic, and `Segment` is untouched —
on this branch the whole cache identity lives in `data/patch_cache.py`, so the change fits
inside it.

Names and sizes rather than contents, because that is what moves for the changes that matter:
rewriting a zarr changes chunk sizes, and dropping annotation deletes chunks outright when
the store does not write empty ones.

**The cost, which is the part worth checking.** No chunk data is read, so it is one directory
walk. On this repository's real w00 label assets — 12,619 files across the ink labels and the
supervision mask — the fingerprint takes **22.5–32.4 ms** over five runs. The same thing
written on `Path.stat()` takes **187.4–270.5 ms**: `os.scandir` hands back the size as it
walks, and that is the entire difference.

**Tests**: three added beside the existing round-trip test, which passes unmodified. A mask
regenerated in place is rejected — both when a chunk disappears and when one is rewritten to
a different size under the same name; an untouched tree keeps hitting the cache; and the
fingerprint is stable, order-independent, sensitive to each asset, and defined for a missing
path.

**Limits, stated rather than found later.** Two different labels that compress to identical
sizes under identical names are indistinguishable. A byte-identical copy of a tree
fingerprints the same as its source, which is the behaviour I want. And a cache written
before this change carries no fingerprint, so it misses once and is rebuilt — no migration.

**This supersedes [#1661](https://github.com/ScrollPrize/villa/pull/1661)**, which does the
same thing across three files on `merge-ink-pipelines`, where this identity is not yet in one
place. I will close that one if you take this. Same question as on
[#1608](https://github.com/ScrollPrize/villa/pull/1608): if ink-detection work should be
targeting `main` now, this is that version.

## Why this matters to me

<!-- USER WRITES THIS PARAGRAPH. Do not draft it. Suggested substance, in your own words:
     the day lost to a validation split that looked right and was not, and what it took to
     work out that the mask edit had landed and the cache had not noticed. -->
