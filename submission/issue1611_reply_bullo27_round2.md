# Reply to Bullo27 on villa issue #1611 (round 2)

**Post as:** a comment on https://github.com/ScrollPrize/villa/issues/1611
**Status:** drafted 2026-08-30, awaiting the user posting it.
**Verified before drafting:** the local image labels below were read from the image
that produced the stalls (`docker image inspect`), on 2026-08-30.

---

Pinned, and your registry read matches my disk exactly. The image the four stalls came out
of:

```
org.opencontainers.image.revision = 1e3f4c021f4e53bea3867772ed05f51a7e586a9c
org.opencontainers.image.version  = main
org.opencontainers.image.created  = 2026-05-13T18:26:28.356Z
digest                            = sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4
```

So there is no ambiguity left about which tree to read: it is `1e3f4c021`, and everything
you measured there applies to my binary and not by analogy.

**Striking the no-retry line.** You are right and I was wrong about it. I inferred "no
retries" from `TieredChunkCache.cpp:320` on `merge-ink-pipelines` — a branch whose cache
subsystem my binary does not contain. At `1e3f4c021` the fetch layer already retries three
times with a 30 s transfer cap that `ZarrChunkFetcher` raises to 60 s, which is exactly the
configuration you quote. I will edit that claim out of the issue body rather than leave it
for the next reader, and mark the image staleness where the reproduction steps are, since
you are right that it is load-bearing: anyone pulling `:edge` today gets the same May binary
I did.

**What that leaves.** Your corrected mechanism — untimed `cv_.wait` with no attempt cap, at
`1e3f4c021:render/ChunkCache.cpp:218` and `:749` — is the one candidate that still fits every
observation I actually have: four stalls at four different points (10 / 17 / 20 / 27%), zero
chunks and zero cache activity for a full minute at 4–6% CPU and ~1 GB resident, and no error
on any of them. It also keeps the one piece I could not otherwise explain, which is that a
*larger* cache made it worse (`--cache-gb 24` → 100–130 chunks per attempt; `--cache-gb 8` →
361 and 540, and it finished twice): more live entries mean more entries that can be parked
`InFlight`, which is a property of the wait and not of the network.

**On the next measurement.** I agree a current-main build is where the useful answer is, and
I cannot get one the cheap way: `:edge` is the only runtime tag published and it is the May
image, so "test against current main" means building volume-cartographer from source here.
That is a bigger commitment than I can make this week, and I would rather say so than let the
suggestion sit as though it were queued. If a runtime image for current main does get
published — your #1619 point — I will re-run the identical render (PHerc1447
`20250703034159-auto_grown_20250703034159599`, ~25 min when it does not stall) at both
`--cache-gb` settings and report whether it still parks, in the same format as the original
report. That is the same cost to me as the first run, so the constraint is the image, not the
work.

Thank you for reading the tree I was actually running rather than the one I quoted. The
staleness finding is worth more to the next person than my original report was.

- [x] The image labels and digest above were read from the local image that produced the
      stalls, today.
