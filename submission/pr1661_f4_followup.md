<!--
Draft comment on our own villa PR #1661 "patch cache: notice when a label asset changed
under it" (F4).
target: https://github.com/ScrollPrize/villa/pull/1661

Timing: this one's clock runs from 2026-08-31, so the 14-day auto-close lands ~09-14.
POST AROUND 09-10..09-12, not the same day as the #1608 comment — four near-identical
comments in one afternoon reads as pressure. This one carries a real design question, which
is the only reason it is worth posting at all.

Verified 2026-09-04: branch merges cleanly, base (`merge-ink-pipelines`) has not moved since
the branch was cut, diff is 3 files / +64, CI green apart from the Vercel deploy
authorisation that every external contributor's PR shows.

The base-branch question is asked once, on #1608 — do not repeat it here beyond the pointer.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

One open design question on this, in case it is what is holding it up.

The fingerprint is deliberately weak: relative filename plus size, hashed into
`Segment.cache_key`, so the existing rejection path does the work and no new invalidation
logic is added. That is cheap — 8 ms for a 6,429-file label array, because `os.scandir`
hands back sizes as it walks, where `Path.stat()` per entry costs 320 ms — and it preserves
the fast path exactly: an unchanged tree still resolves on the second pass in 0.03 s against
3.01 s cold, and a byte-identical copy of the tree hits the same fingerprint in 0.02 s.

What it cannot see is a label that was rewritten in place to the same byte count. That is
the honest limit, and it is in the PR body. Reading chunk contents would close it, at a cost
that scales with the array rather than with the file count.

**Which of those do you want?** I picked the cheap one because the failure I actually hit
was a mask regenerated in place with a different extent — 1,266 patches found before, 1,266
after, and the truth in a fresh `out_dir` was 1,162, so 104 patches kept training on
supervision that no longer existed while everything looked healthy. Name-and-size catches
that. If you would rather have the stronger check, or would rather this be opt-in behind a
flag, say which and I will change it.

Separately, I asked on #1608 whether `merge-ink-pipelines` is still the branch these should
target, since its tip has not moved since 2026-08-14. It matters here: `data/segment.py`
exists on `main` too, diverged enough (204 lines against 253) that retargeting would be a
rewrite rather than a rebase. Happy to do it, once, if that is the answer.
