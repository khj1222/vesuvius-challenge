# Running the render path on an unseen scroll: PHerc1447 (2026-08-26)

docs/13 section 6 argued that this path existed and that the only thing blocking
it was one missing environment (WSL2 and Docker). With that resolved, this is
the record of running it to the end. **Conclusion: every stage of the path
works, and direct inference does not read letters** — exactly what docs/15
predicted.

## The path, measured end to end

```
S3 mesh 0.6MB  ->  vc_render_tifxyz, remote streaming, 25 min  ->  surface volume 389MB (L0-L5)
   ->  public ink_9um checkpoint, 47 s each  ->  prediction TIFF
```

| stage | measured |
|---|---|
| image | `ghcr.io/scrollprize/villa/volume-cartographer:edge`, **12 GB** |
| input mesh | `mesh/intermediate/tifxyz_original/{meta.json,x,y,z.tif}` = **0.6 MB** |
| volume | `PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr`, 24297x8343x8343 u1, 128^3 chunks, uncompressed — **streamed with `--remote-url`, no download** |
| render output | `[28, 3700, 5460]`, chunks `[28,128,128]`, **389 MB**, pyramid L0-L5 complete |
| render time | **~25 min** including the resume chain (30 chunks/min) |
| inference | 3,112 blocks in **47 s** (66 blocks/s) |

docs/13's prediction that **the renderer's output drops into our inference
pipeline unmodified** held. The pyramid depth and chunk shape match the native9
contract (`[28,6400,7980]`, chunks `[28,128,128]`, L0-L5).

## Choosing the target

All 15 of 1447's auto-grown segments had their `meta.json` fetched and their
areas ranked. (The numbers agree with docs/13, which had not recorded the IDs.)

| rank | segment | area |
|---|---|---|
| **1** | `20250703034159-auto_grown_20250703034159599` | **7.40 cm2** |
| 2 | `20250703025628-auto_grown_20250703025628283` | 6.57 |
| 3 | `20250502184845-auto_grown_20250502164121265` | 4.92 |
| 4 | `20250502182456-auto_grown_20250502161202782` | 4.74 |
| 5 | `20250502183421-auto_grown_20250502161744358` | 4.51 |
| 6 | `20250502184658-auto_grown_20250502163923577` | 4.46 |

The first was chosen: over the 4 cm2 First Letters window, `max_gen` 200, and
tagged `partial_review`, so a human has looked at it once. Bounding box
2551x2709x3523 voxels, grid scale 0.05.

## Result: nothing readable

Direct inference with four public checkpoints (seeds 42 and 43 x steps 10k and
20k — docs/15 puts the LOSO peak at 10-20k in all three arms).

| checkpoint | mean | **>128** | p50 | p99 | max |
|---|---|---|---|---|---|
| s42 / 10k | 77.3 | **21.3%** | 91 | 193 | 246 |
| s42 / 20k | 68.8 | 13.9% | 79 | 185 | 221 |
| s43 / 10k | 71.9 | 14.3% | 85 | 171 | 219 |
| s43 / 20k | 62.7 | **6.5%** | 76 | 170 | 211 |

**The numbers speak first**, and all of these are signatures of no signal:

1. **The >128 share swings threefold between checkpoints, 6.5% to 21.3%.** The
   models disagree wildly about the same pixels.
2. **None of them reaches 255** (211-246). Not one pixel is predicted with
   confidence.
3. **p50 sits at 76-91** — half the surface is mid-grey. This is not the bimodal
   distribution real signal produces (most mass near 0, ink near 255).
4. The non-zero share is **67.034% in all four**, identical, because it is not a
   model output at all: it is the render's valid area (33% of the canvas is off
   the sheet). Do not misread that number as a detection rate.

**The images say the same.** In both the 4x downsampled preview and 700x700
crops at native resolution:

- rounded amorphous blobs (100-200 px) dominate, and **there is no connected
  linear stroke structure**;
- viewing the same coordinates under two checkpoints, **the coarse layout agrees
  and only the detail differs** — the two models are responding to the same
  thing, and it is surface geometry and fibre structure rather than ink;
- the bright rim at the surface boundary is an edge artifact of the valid-area
  to blank transition, and the straight bright lines and stepped corners are
  128-chunk boundaries. Neither is ink.

**Scale check**: at 8.64 um/px this segment is 3.2 cm x 4.7 cm. Letters of 2-5
mm would be 230-580 px with strokes 35-60 px thick, so a single 700 px crop
should hold one or two letters. Connected structure at that thickness is nowhere
in the image.

## Verdict and implications

**As predicted.** The cross-scroll margin from docs/15 (+0.06 to +0.17 over the
trivial floor) is what this looks like as an image. Part 4's playbook was also
right to call direct inference **scouting** rather than reading.

WARNING — **but the scouting does not achieve its purpose.** Step 3 of the
playbook is "annotate the single most promising segment, then fine-tune in
minutes", and **this prediction does not say where to annotate**. On Paris4
there were labels, so fine-tuning was possible; 1447 has no ground truth, and
this output alone cannot pick a starting point. **Unsupervised domain adaptation
has to come first, and that is a separate problem.** It was then run as a
pre-registered ladder of the three cheapest methods
([docs/18](18_uda_design.md), 2026-08-30): input-space spectrum matching buys
nothing, test-time entropy minimisation actively harms, and pseudo-label
self-training recovers about a tenth of what one annotated segment recovers. The
prerequisite named here is still a prerequisite, and it is now priced. This document is the
quantitative case for that — the same statement made at the end of docs/15 part
1, now demonstrated on an actually unseen scroll.

The remaining 14 segments would take about 30 minutes each, but the result is
likely to be the same, so they were not run.

## Traps worth recording

- WARNING — **run it from the tip tree, not `external/villa`**, and give the
  inference command paths in **Windows form (`D:/...`)**. Handed a Git Bash path
  (`/d/...`), the Windows Python cannot read it and **exits immediately with no
  error** and no output file. This cost one wasted run.
- WARNING — **the renderer can die of heap corruption**: on the first run, at
  the 10% mark, `malloc(): largebin double linked list corrupted (nextsize)`.
  The conditions to reproduce it are not established.
- WARNING — **remote streaming waits forever after a stall**: CPU at 4-6% and
  memory around 1 GB, alive, but zero chunk and cache growth for 60 s. There is
  no retry logic. The only workaround is **a chain of `--timeout N` (minutes)
  runs with `--resume`**.
- WARNING — **a bigger `--cache-gb` makes it worse.** At 24 GB it stalled after
  100-130 chunks per run; at 8 GB it managed 361 and 540 chunks and finished in
  two runs. Actual memory use was around 1 GB either way.
- **The pyramid is built incrementally** — L1 to L5 fill alongside L0, so a
  timeout leaves the pyramid intact. There is no need to wait for one run to
  exit cleanly.
- The staging cache path given with `-v` **collects nothing** (0 files); the
  renderer streams directly from the remote. So pointing `--resume` at a cache
  path that does not exist stalls with no output.

## Reproduce

```bash
# 1) area ranking and tifxyz (0.6 MB per segment)
curl -s "https://vesuvius-challenge-open-data.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=PHerc1447/segments/&max-keys=100"
# -> each segment's mesh/intermediate/tifxyz_original/{meta.json,x,y,z.tif}

# 2) render (container, remote streaming). The --timeout + --resume chain is
#    required, because a stall otherwise waits forever.
docker run --rm -e OMP_NUM_THREADS=4 -v D:/vesuvius-challenge/data/first_letters:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_render_tifxyz -v /work/cache/1447.zarr \
    --remote-url https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr \
    -g 0 --scale 1 -s /work/pherc1447/<SEG>/tifxyz_original \
    --num-slices 28 --slice-step 1 --zarr-output /work/render/<SEG>.zarr \
    --cache-gb 8 --resume --timeout 8

# 3) inference (paths in Windows form!)
cd D:/vw2/ink-detection
uv run --project D:/vesuvius-challenge/external/villa/ink-detection --no-sync python \
  -m koine_machines.inference.infer \
  D:/.../render/<SEG>.zarr D:/.../models/hybrid_3d2d-seed42/step-020000.pth D:/.../pred.tif \
  --overlap 0.5 --blend-mode hann --no-compile

# 4) judge it (do not go by the preview alone -- the contrast stretch turns
#    noise into pattern)
python tools/ink_viz.py stats pred.tif
python tools/ink_viz.py preview pred.tif --downsample 4
```

Outputs live in `data/first_letters/` (gitignored — a 389 MB zarr, four
prediction TIFFs, and the preview and crop PNGs).

The stall in step 2 was reported upstream as
[villa #1611](https://github.com/ScrollPrize/villa/issues/1611).

---

MIT-licensed.
