# Reply to Bullo27 on villa issue #1611

**Post as:** a comment on https://github.com/ScrollPrize/villa/issues/1611
**Status:** drafted 2026-08-28, awaiting the user posting it.

---

Thank you — a lifecycle bug in the cache fits my four observations better than the network
story I told, in particular the part I could not explain: a *larger* cache made it worse.
`--cache-gb 24` got 100–130 chunks per attempt, `--cache-gb 8` got 361 and 540 and finished
the render twice, and resident memory never exceeded 1.2 GiB, so neither setting was near a
real memory limit. A bigger budget meaning more live entries and more churn is a much better
explanation than anything about the connection.

One thing I cannot check, though: I think we are reading different trees, so it is worth
pinning the ref before anyone starts editing.

On `merge-ink-pipelines` (which my other PR is based on, so it is the checkout I have) there
is no `ChunkCache.cpp`. The cache lives in `volume-cartographer/core/src/cache/` as
`ChunkSource.cpp`, `TieredChunkCache.cpp`, `DiskStore.cpp`, `IOPool.cpp`,
`HttpMetadataFetcher.cpp`, `SimpleCacheFactory.cpp`, `VcDecompressor.cpp`. In that tree:

* `ChunkSource.cpp:218` sets `CURLOPT_TIMEOUT` to 30, not 60, and I find no retry loop —
  `TieredChunkCache.cpp:320` carries the comment "Fetch failed — remember so we don't retry".
* there is no condition variable anywhere under `core/src/cache/`. The only `wait(lock` in
  the whole `volume-cartographer/` tree is in `utils/include/utils/priority_queue.hpp`, and
  that one file has one untimed wait and one timed one.

On `main`, `volume-cartographer/core/src/` has no `cache/` subdirectory at all.

So: which ref are the four `cv.wait` calls and the 3-retry / 60 s fetch in? That matters for
what I should correct in the report, because I did not build from source — I ran the
prebuilt `ghcr.io/scrollprize/villa/volume-cartographer:edge` image, and I do not know which
ref that is built from either. If `:edge` is the tree you read, then my "no retry" line is
simply wrong and I will strike it. If `:edge` is closer to the tree I can see, then the
missing retry is real *and* the untimed wait is real, and they are two separate fixes.

Either way I agree with where you land. My workaround is an external version of the timed
wait you propose: `--timeout` plus `--resume` in a chain converts the indefinite wait into a
process-level failure that a script can react to, and because the pyramid levels persist,
nothing is recomputed. It got the render finished — but it is a user reinventing a timeout
outside the process, which is the argument for putting one inside it.
