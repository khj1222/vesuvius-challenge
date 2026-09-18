<!-- Reply to hendrikschilling on villa PR #1701 (2026-09-18 comment suggesting mtime).
     Paste only what is below the --- line. Numbers: runs/f4_main/mtime/real_fingerprint_cost_mtime.json,
     tests: runs/f4_main/mtime/pytest.txt, commit 0c2ce57 on khj1222:fix/patch-cache-fingerprints-labels. -->
---
Done in 0c2ce57: the fingerprint now hashes `st_mtime_ns` next to `st_size`, from the same `stat()` call the walk already makes. Agreed that the same-size case is ordinary rather than a compression corner — a mask painted over in place lands there whenever the chunk stays the same length, which for uncompressed chunks is always.

Cost on the same 12,619 real label files (five runs each): 24.2 – 27.3 ms with mtime against 22.9 – 25.7 ms without, so inside the run-to-run spread.

The one property it trades away is the size-only version's "a byte-identical copy of the tree hits the cache": that now holds only when the copy preserved modification times (`cp -p`, `robocopy`, `shutil.copytree` do; a plain `cp` does not), and a label rewritten to the same bytes at a new time misses once. Both err towards rebuilding the split, which is the cheap side, so I think that is the right trade — but if you would rather keep copies cache-stable I can drop the mtime and leave the same-size hole documented instead.

Tests: the in-place test now covers the same-size edit (content changed, mtime bumped), and the fingerprint test covers an mtime-preserving copy hitting and a touched copy missing; the repository's round-trip test still passes unmodified. The PR body's fingerprint description and limits paragraph are updated to match.
