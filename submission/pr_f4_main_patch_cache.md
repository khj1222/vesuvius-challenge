<!--
PR body draft — F4 against `main`, written to villa's pull_request_template.md.

  head:  khj1222:fix/patch-cache-fingerprints-labels  (596e865, pushed)
  base:  main   ← NOT merge-ink-pipelines
  diff:  2 files, +131 −1

⚠️ Seven template fields below, in the template's order, with ITS checkbox (not the issue
   template's). #1434 was closed for CONTRIBUTING non-compliance.

⚠️ TWO THINGS THE USER SUPPLIES:
   1. **Why / where this is useful** — CONTRIBUTING requires human-written commentary.
   2. **The screenshot** in Proof — the stale count next to the true one.

⚠️ This is the one whose example is already on real scroll data end to end (phercparis4-w00),
   which CONTRIBUTING asks for explicitly. Keep it that way.

⚠️ Do not tick the checkbox until the screenshot is attached and you have looked at it.

Supersedes our own #1661. Evidence: runs/f4_main/ and runs/f4_patch_cache/.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** The patch cache now notices when the labels underneath it changed, instead
of handing back a split that describes labels that no longer exist.

**One real example:** Starting with `phercparis4-w00` from `ink_9um`, I ran patch discovery and
it found **1,266** patches. I then halved that segment's supervision mask **in place**, at the
same path, and re-ran against the same `out_dir`: **1,266 again, with identical bounding
boxes.** The truth, from a fresh directory, is **1,162**.

**Before:** 104 patches kept training on supervision that had been deleted, and nothing in the
run looked wrong — the count matched, so the natural reading was that my mask edit had not
taken effect. That is what a held-out split looks like while you are building it, and it cost
me a day of believing a validation number that was measuring the wrong pixels.

**After this PR:** the second run rejects the cache and rediscovers, returning 1,162 — the same
answer as the fresh directory.

**Proof:** the reproduction above, on that segment, before and after the change. The cache is
keyed on the label *paths*, so pointing a run at a different tree was always caught; a mask
regenerated at the same path was not.

![patch cache, before and after](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/f4_main/f4_console.png)

*Console output of the script linked below, run against a copy of this segment's real ink labels: the cache returning the stale split before, and rejecting it after.*

Cost of the check, on this repository's real w00 label assets — 12,619 files across the ink
labels and the supervision mask:

| | |
|---|---|
| the fingerprint, five runs | **22.5 – 32.4 ms** |
| the same thing written on `Path.stat()` | **187.4 – 270.5 ms** |

No chunk data is read; `os.scandir` hands back the size as it walks, and that is the entire
difference.

Script and raw output: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/f4_main (`f4_shot.py`, `f4_console.txt`, `real_fingerprint_cost.json`)

**Why / where this is useful:**

I lost a day to this in July. I had halved the supervision mask while building a held-out
split, the patch count came back the same, and I read that as my edit not having taken — so I
went looking at the mask writer, which was fine all along. Anyone building or revising a
validation split hits this the same way, because the number you would check to catch the
mistake is the number that is wrong.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

Each label asset is fingerprinted by the relative names and sizes of the files under it, and
that fingerprint goes into the cached record and into the lookup key — so the rejection path
that already exists does the work, and there is no new invalidation logic. Names and sizes
rather than contents, because that is what moves for the changes that matter: rewriting a zarr
changes chunk sizes, and dropping annotation deletes chunks outright when the store does not
write empty ones.

The whole change fits in `ink_detection/data/patch_cache.py`; the `Segment` type is untouched.

Three tests are added beside the existing round-trip test, which passes unmodified: a mask
regenerated in place is rejected both when a chunk disappears and when one is rewritten to a
different size under the same name; an untouched tree keeps hitting the cache; and the
fingerprint is stable, order-independent, sensitive to each asset, and defined for a missing
path.

Limits, stated rather than found later: two different labels that compress to identical sizes
under identical names are indistinguishable; a byte-identical copy of a tree fingerprints the
same as its source, which is the behaviour I want; and a cache written before this change
carries no fingerprint, so it misses once and is rebuilt — no migration.

This supersedes [#1661](https://github.com/ScrollPrize/villa/pull/1661), which does the same
thing across three files against `merge-ink-pipelines`, where this identity is not yet in one
place. I will close that one. Same branch question as on
[#1608](https://github.com/ScrollPrize/villa/pull/1608).

Tested at `5479453` (`main`), Python 3.12, Windows 11.
