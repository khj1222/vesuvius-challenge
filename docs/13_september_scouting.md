# Scouting the September round (2026-08-18)

Target hunting after the August submission (only the form was left at the time,
around 08-24). The question that started it: "is a $50k or $1M prize really out
of reach?" The answer: **the $1M is out of our weight class, First Letters at
$50k has a nearest path that exists but whose input is unfinished, and the real
opportunity is `ink_9um`, an official dataset released on 08-14** (section 3).

## 1. The prize board (scrollprize.org/prizes, checked 2026-08-18; all deadlines 2027-06-25)

| prize | amount | condition |
|---|---|---|
| 2027 Grand Prize | $1M ($800k for first place) | one of 13 target scrolls, fully automatically unrolled to 100% with 70% readability |
| First Letters | $50k per scroll (up to $500k) | 10 readable letters within 4 cm2 of a target scroll |
| PHerc. Paris 4 Title | $50k | find Scroll 1's title (any scan, including the 2.4 um volume) |
| Progress Prizes | monthly, $20k guaranteed for the best | contributions to open problems (our current track) |

Going rate, read off July's distribution of awards: the measurement, validation
and tooling niche pays $1k-$2.5k; core pipeline work (meshing, unwrapping) pays
$20k.

## 2. Data inventory for the 13 First Letters scrolls (S3 `vesuvius-challenge-open-data`, measured 2026-08-18)

| scroll | full volume | segments | note |
|---|---|---|---|
| PHerc0125, 0191, 0211, 0257, 0358, 0813, 0826, 1545 | 9.362 um masked | **0** | unwrapping not started |
| PHerc0268, 1218 | 8.640 um masked | **0** | same |
| PHerc1203 | 9.362 um **plus 2.403 um** | raw only | a high-resolution scan exists, but no segments |
| **PHerc0800** | 8.640 um | **6** auto-grown (2025-10-28) | **mesh only, no rendered surface volume** |
| **PHerc1447** | 8.640 um | **15** auto-grown (2025-05 to 07) | same |

- All 13 have their full CT volumes published, but **11 have zero segments**, so
  they need unwrapping before ink detection is even a question — not our lane.
- 0800's and 1447's auto-grown segments have only `mesh/`, so a
  **mesh-to-surface-volume render** (villa/VC's `tifxyz` family) has to happen
  before our pipeline has an input it can eat. We had not tried that step.
- The S3 catalogue (`metadata.json`) lags the actual bucket — it lists all 13
  scrolls as having only photos. Do not trust it; list the bucket directly.

## 3. The key find: the `ink_9um` dataset (released 2026-08-14, four days old at the time)

`hf://buckets/scrollprize/datasets/ink_9um/`. From its README:

- **9 um-scale ink labels for 29 segments across 4 scrolls** (labels only; the CT
  lives in the open-data S3 bucket):
  - `aligned-scrollprizeorg-21slices/`, 24 segments = PHerc0139 x9, PHerc1667 x6,
    **PHercParis4 x8 (w00 to w09 — the segments we had been working on)**, and
    PHerc0814 x1. Built by taking the public 2.399 um surface volumes at level-2
    XY with a 4x mean pool in z, giving ~9.6 um. 21 slices, annotated on z=10
    only.
  - `native9-scrollprizeorg-21slices/`, 5 segments = PHerc0139 at its native
    9.362 um. 28 slices, annotated on z=14 only.
- **Only 3 of the 29 carry a `_validation_mask.zarr`** (pherc0139-w016,
  pherc0814-46527, pherc1667-w029) — the exact gap July's harness was built to
  fill, reproduced in a brand-new dataset. At the same time, an official dataset
  adopting the `_validation_mask` convention at all is de facto acknowledgement
  of the premise behind issue #1231.
- The consuming code is **villa `merge-ink-pipelines`** — the same branch and
  pipeline our two merged PRs landed in.
- Trained models are published too: HF `scrollprize/ink_9um`. So the harness can
  start by **scoring the released checkpoints**, with no training at all.
- **Measured size: one native 9 um surface volume is 1.7 GB** (PHerc0139 w040,
  3,763 files). All 29 segments should come to tens of GB (the 2.4 um aligned
  side can be partially synced at level 2 only) — **a lane that needs no new
  disk**.

## 4. Candidate plans for September

- **Plan A (the main bet, recommended): extend the harness to ink_9um and measure
  cross-scroll generalisation.**
  - Generate held-out splits for the 26 segments without a mask, giving a
    per-scroll baseline and noise floor.
  - Leave-one-scroll-out CV produces **the first systematic numbers for open
    problem #7, "cross-scroll ink generalization"** (and touches #10,
    diagnostics). Starting from scoring the released checkpoints keeps the GPU
    budget light.
  - The story is continuous: July built the harness, August used it to test
    #192, September extends it to a new official dataset and the top unsolved
    problem. The dataset being four days old means the niche is unclaimed.
- **Plan B (the lottery ticket): the nearest path to First Letters** —
  PHerc0800/1447 mesh, render to a surface volume, infer with the 9 um models.
  - Plan A's by-products (a validated 9 um model and per-scroll generalisation
    numbers) are exactly the equipment for it.
  - Ink probably will not show, but diagnosing *why* is itself a submission for
    open problems #7 and #10 — so the work is dual-use.
  - Prerequisite: learning the mesh-to-render step (villa's
    `tifxyz_label_transfer` and render scripts need investigating).
- **Plan C (the safety net): a large PR upstreaming the harness**, once #1434
  gives a review signal. A $1k-class contribution.
- Suggested order: **A first**, to secure a definite submission by 9/30, then B
  with whatever time and GPU remain; C waits for a signal.

## 5. Where the work stood (updated the night of 2026-08-18)

1. **`ink_9um` labels synced** (confirmed 2026-08-19) — 380,991 files plus the
   README, 453 MB. The bytes are small but the file count is the bottleneck, so
   a single process ran at a ~23h pace; restarting as **a per-segment parallel
   sync with 9 workers** finished it overnight. Sync is idempotent, so
   interrupting and resuming is free.
   WARNING — **a matching file count does not mean the data is intact.** A sync
   killed midway leaves truncated chunks that pass `hf`'s size and mtime
   comparison and only fail at read time with a blosc error — `native9/w040`'s
   inklabels had 8,496 files, matching, and was corrupt. **After any large sync,
   actually decompress the zarrs to check** (the `scratchpad/check_zarrs.py`
   pattern: read every array of every `*.zarr` with `a[:]`; 61 stores took about
   4 minutes). Deleting and re-syncing the affected zarr folder fixed it, and
   re-verification gave **61 of 61 clean**.
2. Five native 9 um surface volumes downloaded (7.77 GB, straight from S3, into
   `data/ink_9um/surface-volumes/native9/`).
   WARNING — when listing S3, **find the volume folders with a delimiter first**
   and enumerate only inside them. Enumerating all of `surface-volumes/` pages
   through the 1.129 um ultra-high-resolution volumes (hundreds of thousands of
   keys) and stalls for minutes.
3. All 14 public checkpoints downloaded
   (`data/ink_9um/models/hybrid_3d2d-seed{42,43}/`, 138 MB each).
4. **Smoke inference succeeded** (w040 with seed42 / step-075000): 2,770 blocks
   in 45 s (~61 blocks/s), output 6400x7980, 11% strong ink, and **Greek letters
   clearly legible in the preview** (`runs/ink9um_smoke/`). The command is the
   vw2 tree with the external environment:
   `cd D:/vw2/ink-detection && uv run --project <repo>/external/villa/ink-detection --no-sync python -m koine_machines.inference.infer <volume.zarr> <ckpt> <out.tif> --batch-size 4 --no-compile`.
5. **All three official validation masks analysed** (night of 2026-08-18) — one
   design principle, consistent across the three:

   | segment | val regions | val share of annotated area | ink density, val vs sup |
   |---|---|---|---|
   | pherc0139-w016 | 2 (88k + 87k px) | 29.5% | 0.235 vs 0.214 |
   | pherc0814-46527 | 1 (161k px) | 27.3% | 0.373 vs 0.296 |
   | pherc1667-w029 | 2 (236k + 147k px) | 24.0% | 0.230 vs 0.294 |

   In common: **separate annotated regions with zero overlap with supervision**
   (drawn apart at annotation time), roughly a quarter to a third of the
   annotated area assigned to validation, in one or two large contiguous
   patches, with ink density roughly but not exactly matched. That reads as the
   same semantics as July's harness — hold out whole regions — reached from the
   other direction (ours derives them after the fact, the official ones separate
   them at annotation time). The trainer-side consumption is structurally what
   July's was (validation pixels subtracted from training patches), so the
   harness ports over. Labels sit on one slice of 21, z=10, the same pattern as
   w00.

   *(Later correction, 2026-08-29: "hold out whole regions" turned out to be
   wrong as a description of the official masks. All three split their
   annotation **within** connected regions, and on two of them a leak-free
   held-out subset cannot be constructed at all — see
   [docs/17](17_holdout_audit.md). The zero overlap with supervision is real;
   what does not follow from it is separation in space.)*
6. **The key gap, confirmed: the public checkpoints have never been validated on
   PHercParis4** — all three online-validation cases are 0139, 0814 and 1667.
   The model card carries no performance numbers at all, so the first scorecard
   would be ours.
7. Remaining at the time: analyse the other two official masks (0814 and
   1667-w029) after the sync,
   design held-out generation for the 26 segments (segment-level holdout looks
   natural, since supervision comes in 2-3 large patches per segment), then
   score 14 checkpoints per scroll.

## 6. Scouting the Plan B render path (2026-08-22, while the LOSO training ran)

**Conclusion at the time: the path exists, and the only thing blocking it is one
environment (no WSL2, no Docker).**

- **The renderer is `vc_render_tifxyz`**
  (villa `volume-cartographer/apps/src/vc_render_tifxyz.cpp`). It takes an
  OME-Zarr volume plus a tifxyz segment folder, samples `--num-slices` along the
  normal, and `--zarr-output` writes **an L0-L5 XY pyramid zarr**. It has
  `--remote-url` streaming, `--prefetch-remote`, `--cache-gb` and `--resume`, so
  **the full volume never has to be downloaded**.
- **The output contract checks out**: our local native9 w040 surface volume — the
  one we ran smoke inference on — has exactly this renderer's signature: 28
  slices, chunks (28,128,128), a z-fixed XY-only pyramid. So if the render works
  at all, it drops into our inference and scoring pipeline unmodified.
- **Inputs, measured**:
  - full volumes (masked, RAW uncompressed 128^3 chunks): 0800 is
    24298x9867x9867 u1, 1447 is 24297x8343x8343. Dense that is ~2.4 TB, so no
    wholesale download — but masked and limited to a segment's bounding box,
    **5-15 GB of streaming per segment** is enough.
  - segment meshes are **tiny**: `mesh/intermediate/tifxyz_original/` holds
    x/y/z.tif (~0.1 MB, grid scale 0.05 = a 20x grid) plus meta.json (bbox,
    area_cm2) and one obj.
- **Area inventory (all 22 segments)**: **1447 is the main bet** — 13 of its
  segments are over 2 cm2, the largest is **7.4 cm2, above the First Letters
  4 cm2 window**, and all are max_gen=200 (mature growth). 0800's six are small,
  0.38-2.28 cm2 at gen 20-101. Total 67.5 cm2. The top six: 7.40 / 6.57 / 4.92 /
  4.74 / 4.51 / 4.46, all on 1447.

**Executed 2026-08-26 — every stage works, and the result is unreadable. Details
in [docs/16](16_first_letters_render.md).** The blocker below was cleared by
installing WSL2 and Docker Desktop.

- **Environment trap (the only blocker at the time, now cleared)**: VC cannot be
  built on native Windows (it needs \*nix atomic rename, as the README states).
  The official path is the Docker image
  `ghcr.io/scrollprize/villa/volume-cartographer:edge`, or WSL. **This machine
  had neither** — no `docker`, no WSL distribution — so it needed **a one-time
  install by the user, as administrator**: WSL2 (`wsl --install`, one reboot)
  and then either building inside it or using Docker Desktop. Inference and
  scoring can stay on the Windows side, so only the render step needs the
  container.
  - Fallback: tifxyz is a simple format (three coordinate grids plus a scale), so
    writing a small Python renderer was feasible in 2-3 days. But losing
    contract-identity with the official renderer weakens the adoption axis, so
    it was second choice.
- **Model fit**: 8.640 um native sits inside the range the model card blesses
  ("native ~9 um renders work directly"), 8% off 9.362. If the response is weak,
  suspect the z offset first (sweep `--layer-start`/`--layer-end` — the card's
  own tip, and the same family of problem as our z-window lesson).
- **Command sketch** (verified inside the container on the day it ran):
  `vc_render_tifxyz -v <volume.zarr (or remote cache)> -g 0 --scale 1 -s <tifxyz_dir>
  --num-slices 28 --slice-step 1 --zarr-output <seg_surface.zarr> --remote-url <S3 URL>
  --prefetch-remote --cache-gb 24` (28 slices reproduces the native9 contract).
  *(What actually worked used a smaller `--cache-gb` and a `--timeout` chain; see
  docs/16.)*
- **How this connects to LOSO**: the cross-scroll numbers being measured at the
  time were the go/no-go for this path. Paris4 held-out F1 around 0.7 would mean
  letters could be expected on an unseen scroll (0800/1447); around 0.5 would mean domain
  adaptation has to come first. Either way, diagnosing why is a submission for
  #7 and #10. *(It came out around 0.49 — see [docs/15](15_loso_cross_scroll.md)
  — and the render duly read nothing.)*

---

MIT-licensed.
