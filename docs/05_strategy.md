# 05 — How this track is won

**Written 2026-07-19, extended 2026-07-26.** A working note on what the Progress
Prizes actually reward, and how the targets in this repository were chosen. Kept
because the reasoning behind a negative result is worth as much as the result.

## The shape of the competition

The Vesuvius Progress Prizes are **not a metric leaderboard**. The stated
criteria (see `docs/03_submission.md`) are: released or open-sourced early,
actually gets used, improves results on real data, resolves outstanding bugs in
tools people rely on, reveals actionable information, and is well documented.

Which means the way to contribute usefully is different from a Kaggle-style
contest:

- Raising an ink-detection F1 by 0.01 is not, on its own, a contribution.
- **An open-source tool, fix or document that other people pick up and use** is.

So the effort here goes into clean engineering, reproducibility and
documentation, and into publishing early rather than at the end of a round.

## The working loop

1. **Reproduce the tutorial** end to end, so there is a working pipeline and a
   first visual output to reason about.
2. **Pick one improvement other people would use** from the wishlist or the open
   problems — a data loader, a visualisation, an augmentation, a good-first-issue.
   Aim at usefulness rather than at a frontier result.
3. **Publish early, document it, and share it**, so adoption has time to happen
   within the round.
4. **Repeat monthly.** The rolling schedule means the setup is reusable.

## Survey (2026-07-25)

### What has actually been awarded

From scrollprize.org/winners. The round's stated goal is "improve the tools and
training methods needed to read the scrolls".

| round | recipient | amount | contribution |
|---|---|---|---|
| 2026-06 | Paulo Sergio Camillo | $2,000 | CT-artifact-based augmentation for 3D segmentation, plus a ScrollFiesta improvement |
| 2026-06 | Joseph Balmaceda | $1,000 | fibre format converter (NML to CSV/JSON/SWC, with length, branching and orientation analysis) |
| 2026-05 | Ben Kyles | $10,000 | ScrollFiesta — automatic meshing of surface predictions with topology error correction |
| 2026-05 | Paulo Sergio Camillo | $2,000 | Scroll Decohesion / Realistic Warp / Squeeze transforms |

Reading it: **practical tools that attach to the existing pipeline are what the
round rewards**, and the larger awards go to systems that change what the
pipeline can do at all.

### help-wanted issues on ScrollPrize/villa (all three, at the time)

- **#192 Accurate 3d ink labels** — `good first issue` plus `help wanted`, opened
  2025-04-18, with **no comments, no assignee and no branch or PR for 15
  months**. It asks for genuine 3D ink labels to replace the current practice of
  manufacturing depth from a 2D annotation: zarr or tif, ready to run with no
  preprocessing.
- **#191 Surface/Fiber Predictions in Compressed or Highly Curved areas** — 7
  comments, active. nnUNetv2-based, on the surface and fibre track, outside this
  pipeline.
- **#193 Methods for generating surface/fiber/ink labels** — the generalised
  version of #192.

### Open problems within reach

- **#7 Cross-Scroll Ink Generalization** — heavy download burden, tens of GB per
  scroll.
- **#8 Direct 3D Ink Segmentation** — the same direction as #192; mentions
  self-distillation.
- (#2 to #6 are surface, topology and spiral work, outside this pipeline.)

### The gap we found: the tutorial pipeline has no held-out validation

Confirmed on our own 20k-iteration run (2026-07-21 outputs):

- the patch cache `runs/ink_tutorial/flat_ink_patches_...json` has
  **`is_validation: true` on 0 patches**, and false on 2,710;
- `runs/ink_tutorial/val_previews/` is an **empty directory**;
- the cause is that the dataset segment `w00_20231016151002` ships no
  `_validation_mask` asset — only `_inklabels` and `_supervision_mask`;
- `preprocessing/create_label_zarrs.py` **does support**
  `_validation_mask.{tif,tiff,png}`, but the tutorial
  (`scrollprize.org/docs/07_tutorial5.md`) never mentions validation, and no
  tool exists to make the mask;
- so Confusion, BalancedAccuracy, **DRD** and **pFM**, all implemented under
  `evaluation/metrics/`, are **dead code for anyone following the tutorial**, and
  `val_every: 500` iterates an empty loop.

Anyone who follows this pipeline has **no way to say in numbers whether a change
helped**.

### Three candidates

| | candidate | deliverable | cost | rationale and risk |
|---|---|---|---|---|
| **A** | **a held-out validation harness for the ink pipeline** | (1) a CLI that carves a reproducible, seeded validation region out of a segment as `_validation_mask`; (2) a tutorial config and document that use it; (3) an eval script sweeping checkpoints for DRD, pFM and balanced accuracy; (4) our own 20k run's measured numbers | 2-4 days (1.5h per run on a 5090) | matches the round's stated goal exactly, and it is a thin PR that revives metric code already in the repository. **Risk: the maintainers may hold validation masks internally — ask before building.** |
| **B** | **port the scroll-specific augmentations to ink, with an ablation** | apply `sheet_compression`, `thick_slice` and `layer_mix_dropout` — present in `create_training_transforms` but unused for ink — to 2.5D ink training, measure the effect, and PR a recommended augmentation set | 3-5 days (however many ablation runs) | this exact category has been awarded before, so the precedent is clear. **But it cannot be measured without A**, so A has to come first. |
| **C** | **villa #192, accurate 3D ink labels** | localise ink depth from a trained checkpoint's per-z response, generate 3D label candidates, plus an inspection tool and a released dataset | 2-4 weeks | the maintainers explicitly want it and a dataset has real adoption value. **But there is no ground truth, so "accurate" is hard to demonstrate — probably why nobody has touched it in 15 months.** |

**Order: A, then B, then C.** A builds the measurement that makes B's ablation
possible, and neither B nor C can state a claim in numbers without it.

## Risks

- **Reproducing and stopping there earns nothing.** There has to be a layer on
  top that someone else can adopt.
- The community is mature, so easy improvements may already be taken — check the
  wishlist for what is genuinely still open.
- The data volumes are large. Manage disk, and never commit data.
- Accepting an award requires permissive open-sourcing. This repository is MIT,
  so there is nothing to change.

---

# The August round (deadline 2026-08-31) — choosing a target

**Written 2026-07-26**, right after the July submission went in.

## Where to aim

Measurement, validation and reproducibility tooling had become a well-populated
area by late July, with several contributors working on audits and label-quality
metrics. The harness we submitted in July is differentiated by being the only
one covering **held-out validation for ink specifically** — so the way to avoid
duplicating anyone's work is not to build another measurement tool, but to
**use this one to adjudicate an open question**.

## Decision: villa #192, plus upstreaming the harness

- **#192** (bruniss, 2025-04-18, `good first issue` + `help wanted`): ink labels
  today are drawn in 2D and given depth downstream, which risks teaching the
  model **surface texture rather than ink**. The requested deliverable is
  genuine 3D ink label and image pairs, in zarr or tif slices, trainable with no
  preprocessing.
- **One comment and no assignee in 15 months.** The reason nobody has taken it
  looks like the absence of any way to *demonstrate* accuracy — and that is
  exactly what July built (held-out scoring plus a measured fold-variance
  baseline).

### Why this is a good fit

Training on a z-copied label and on a 3D label, over the **same folds with the
same seed**, and comparing held-out F1, states the label-quality claim in
numbers for the first time. The decision threshold is already measured: four
runs of one unchanged config gave 0.823 to 0.854, so **anything under ~0.03 F1
is noise**.

### Approach (draft)

1. **Depth localisation**: extract per-z contribution from a trained 2.5D
   checkpoint, two ways — sliding a z sub-window (8 slices, stride 4), and
   occluding one z slice at a time and measuring the drop in ink logit. Running
   inference over the supervised area only (166 blocks) takes ~30 s a pass, so
   64 passes fit in half an hour.
2. **3D label generation**: the 2D ink label intersected with a per-(x,y) depth
   profile band. Deterministic, with the parameters documented.
3. **An honest three-arm comparison** (3 folds each):
   - `baseline`, the z-copied label (already held: 3-fold 0.8472);
   - `3d`, the depth-localised label;
   - `control`, self-distillation with no depth information — **the circularity
     control**, which is what shows any gain is not simply a self-distillation
     effect.
4. **Physical consistency**: show, per region, whether the ink-depth histogram
   concentrates in a coherent layer relative to the surface, against a flat
   prior.
5. **Packaging**: zarr and tif pairs, the generator CLI, documentation, and the
   result posted as a comment on #192.

### Risks, declared up front

- **Circularity**: the depth profile comes from a model trained on the z-copied
  label. Only the control arm defends against that. If the defence fails, the
  result gets published as "a 3D label generation pipeline plus an adjudication
  protocol" instead.
- **A single segment**: `w00_20231016151002` first. Extending to other scrolls
  in the ink bucket is bounded by a ~86 GB download per segment.
- **"Accurate" cannot be proven** — so the claim has to stay at "supervision
  that is measurably better".

### Side track (2-3 days, in parallel)

**Upstreaming the harness**: a PR folding `tools/make_validation_mask.py` into
villa's preprocessing commands, plus a validation section for the tutorial
document. It pushes issue #1231 forward in code rather than in a question. Base
it on `merge-ink-pipelines`, since `koine_machines` is not on `main`.

### Milestones

| week | plan |
|---|---|
| 7/27 - 8/2 | depth-localisation prototype (two methods, compared and visually inspected), plus the upstream harness PR |
| 8/3 - 8/9 | 3D label generator, labels for every region, QC visualisation |
| 8/10 - 8/16 | 3 arms x 3 folds, trained and scored (~14 GPU hours) |
| 8/17 - 8/23 | results, dataset packaging, the #192 comment, documentation |
| 8/24 - 8/31 | submission text plus buffer |

**Actual progress as of 2026-07-31 — about 10 days ahead.** Depth localisation
(7/27, `docs/10`), 3D label generation and QC (7/27, `docs/11`), and the
**training consumption path plus the three arms' assets (7/31, `docs/12`)** are
done. Only the training matrix, budgeted for 8/10-8/16, remains — and the step
in front of it was not in the plan at all: the pipeline could not consume 3D
labels, because the `flat` loss folds z and makes the arm comparison impossible.

The remaining matrix is **~16.2 hours** (longer than the 14 planned, going by
July's measured 104-111 minutes per fold) and ~198 GB of disk. It runs one arm
at a time as GPU time allows: v4, then v3 — which alone completes the
position-only controlled comparison — then v2. Commands are in CLAUDE.md.

The side track had not started; with #1231 unanswered, pushing in code may be
the way to get a reply.

---

MIT-licensed.
