<!--
Draft comment for villa issue #1611 (ours: "vc_render_tifxyz: remote chunk streaming stalls
indefinitely with no error").
target: https://github.com/ScrollPrize/villa/issues/1611

Purpose: report that the stall does NOT reproduce on the current build, and offer to close.
Evidence: runs/f6_render_retest/summary.json in our repo.

⚠️ This retracts the practical part of our own report. Say so plainly; do not bury it.
⚠️ Do not add the issue-template checkbox: this is a comment, not a new issue.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

I re-ran this on the current build and **it does not reproduce.** Details below so you can judge whether to close it, but my own recommendation is: close it.

## What I ran

The same segment, the same volume, the same flags as the original report — except that I deliberately dropped the `--timeout` / `--resume` chain, since that was the workaround and it would have hidden the stall.

| | original report | now |
|---|---|---|
| binary | `ghcr.io/scrollprize/villa/volume-cartographer:edge`, revision `1e3f4c0`, built 2026-05-13 | `VC3D-5479453-2026-08-30-win64.zip` from the `latest` release, built from `5479453` |
| flags | `--cache-gb 8 --resume --timeout 8`, chained | `--cache-gb 8`, nothing else |
| attempts | 4 | 3 |
| stalled | **4 of 4**, at 10%, 17%, 20%, 27% | **0 of 3** |
| wall clock | ~25 minutes across the chain | **5m55s, 3m56s, 3m50s**, exit 0 each |

The three runs produced byte-identical output to each other, and the same six pyramid levels with the same shapes as the render I got out of the chained run in May.

## What I think happened, and what I can't tell you

`core/src/render/ChunkCache.cpp` was 755 lines at the revision my container was built from and is 5,672 lines at `main` — the cache was rewritten in between, and "Rewire local remote cache" (#1554, 2026-08-21) is presumably where. So the most likely reading is simply that this was fixed by that work.

What I cannot claim: three clean runs are not proof of a fix. The original stalls were caused by dropped remote fetches, and network conditions today are not the conditions in May. **All I can honestly say is that it stopped reproducing on a binary built after the rewrite, in three attempts where the old binary failed in four of four.** If you want a stronger statement than that, it would have to come from someone who can reproduce a dropped fetch deliberately.

One observation I'll leave rather than push: the pattern that made the original failure unrecoverable is still in the file. There are four `cv_.wait` calls at `main` (1788, 1873, 2404, 2529), none with a timeout, where the old revision had two. The last one is `persistChunkBlocking`, whose only path to setting `operation->completed` is submitted as `[weakState, ...] { if (auto state = weakState.lock()) ... }` — if that `weak_ptr` has expired, nothing runs, nothing notifies, and the wait has no bound to escape through. I am not filing that as a bug, because I have not made it happen and I cannot build this project to try. It is just the thing I would look at first if a stall like mine is ever reported again.

## Two smaller things from the same session

**The container is three and a half months behind the releases.** Both application tags on GHCR, `:main` and `:edge`, still carry revision `1e3f4c0` from 2026-05-13, while `builder-ubuntu-26.04` was rebuilt on 2026-07-24 and the GitHub release `latest` ships 2026-08-30 binaries for Linux, macOS and Windows. The build pipeline is clearly alive; the application image just is not being republished by it. That matters here only because it is why my original report was against May's code in August — anyone reaching for the container gets the version this issue describes, and the fix for it is not in there.

**A note for anyone comparing renders across this change.** My new render differs from the May one by 2.6% of voxels, and 85% of those differ by more than 10 grey levels, so it is not rounding. I cannot attribute it: the old one was produced by a resumed chain, so "the rewrite changed sampling" and "the resumed render was inconsistent" are both live and I have no way to separate them. For what it is worth it made no difference downstream — ink inference on the new render gives 23.69% of sheet pixels above 128 against 23.38% before, max 215 against 214, median 102 against 101.

Happy for this to be closed. Thanks for the rewrite — the render that needed a babysitting script in May now runs in four minutes unattended.
