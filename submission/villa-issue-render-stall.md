# villa issue draft — `vc_render_tifxyz` remote streaming stalls forever

**Posted:** https://github.com/ScrollPrize/villa/issues/1611 (2026-08-26, checkbox ticked)
**Status at posting:** open, no labels, no assignee, 0 comments.
The body below is what the issue carries.

---

## Title

```
vc_render_tifxyz: remote chunk streaming stalls indefinitely with no retry or error
```

## Body

**In one sentence:** When `--remote-url` streaming stalls mid-render, `vc_render_tifxyz` waits
forever instead of retrying or failing, so a render that is 20% done simply stops with no error.

**I was trying to:** Render a PHerc1447 auto-grown segment into a ~9 µm surface volume so I
could run the released `ink_9um` ink-detection checkpoints on it. PHerc1447 has 15 segments but
none of them ship a rendered surface volume, so the render is the first step to getting any ink
prediction on that scroll at all.

**Using:** `ghcr.io/scrollprize/villa/volume-cartographer:edge`, digest
`sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4`, pulled 2026-08-26.
Real data: segment `20250703034159-auto_grown_20250703034159599` (7.40 cm², the largest on that
scroll) against `PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr` streamed from
the public bucket.

```bash
docker run --rm -v /data/first_letters:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_render_tifxyz \
    -v /work/cache/1447.zarr \
    --remote-url https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr \
    -g 0 --scale 1 \
    -s /work/pherc1447/20250703034159-auto_grown_20250703034159599/tifxyz_original \
    --num-slices 28 --slice-step 1 \
    --zarr-output /work/render/out.zarr \
    --cache-gb 24
```

**What happened:** Throughput decays and then reaches zero, and the process never returns.

```
tile-row 1/29 (3%)   3.1 chunks/s  0m14s  eta 6m34s
tile-row 2/29 (6%)   2.9 chunks/s  0m29s  eta 6m43s
tile-row 3/29 (10%)  2.7 chunks/s  0m47s  eta 6m47s
tile-row 4/29 (13%)  2.4 chunks/s  1m11s  eta 7m26s
tile-row 5/29 (17%)  1.8 chunks/s  1m59s  eta 9m34s
   (nothing further; no error, no exit)
```

The container is still alive and looks busy-ish, but does no work. Measured over a 60 second
window while it was in this state:

| | |
|---|---|
| chunks written to the output zarr | 219 → 219 (**zero**) |
| staging cache directory | 0 MiB → 0 MiB (**zero**) |
| memory | 902 MiB → 1.128 GiB of 30 GiB |
| CPU | 4–6% |

So it is neither out of memory nor computing; it is waiting on something that is not coming.

**What I expected or needed:** Either retry the chunk fetch (the public bucket returns transient
5xx and drops connections under sustained reads — I hit the same thing this month running
`prepare_9um_isotropic_input` over the whole `ink_9um` corpus, where only *per-tile* retries with
backoff got through), or give up on that chunk with an error so the caller knows the render
stopped.

**Evidence / reproduction:** The command above, run against that public volume, on a connection
that sustains roughly 4 MiB/s. It stalled at a different tile-row on each of four attempts
(10%, 17%, 20%, 27%), so it is not a specific chunk that is broken.

The workaround that got the render finished, in case it helps anyone else: bound each attempt
with `--timeout` and chain `--resume`.

```bash
# repeat until the level-0 chunk count stops rising
vc_render_tifxyz ... --cache-gb 8 --resume --timeout 8
```

Two chained attempts completed it (`347 → 708 → 1248` of 1248 level-0 chunks, ~25 min total).
The output is correct: `[28, 3700, 5460]`, chunks `[28,128,128]`, pyramid L0–L5 complete, 389 MB,
and it fed straight into ink inference without modification.

- [ ] I personally encountered or reproduced this using the version and data stated above.

## Details

Three smaller things noticed while working around it, in case any of them points at the cause:

1. **A bigger `--cache-gb` made it worse, consistently.** At `--cache-gb 24` each attempt
   managed 100–130 chunks before stalling. At `--cache-gb 8`, attempts managed 361 and 540 and
   the render finished. Measured RSS never exceeded ~1.2 GiB either way, so the cache was not
   being filled — but the larger setting still hurt.
2. **The staging cache path passed to `-v` is never created or written.** After four runs,
   `/work/cache/1447.zarr` had zero files. Streaming appears to bypass it entirely, which also
   means `--resume` against a `-v` path that does not exist hangs before printing anything —
   that cost me a couple of confused attempts before I realised the render itself was fine.
3. **One run died with heap corruption rather than hanging**, at 10%, on the very first attempt:
   `malloc(): largebin double linked list corrupted (nextsize)`. I saw this once in five runs and
   cannot reproduce it on demand, so I am not filing it separately — but it was the same command
   and the same data as above, and it may share a cause with the stall.

Happy to re-run any of this with extra logging if that would help narrow it down.
