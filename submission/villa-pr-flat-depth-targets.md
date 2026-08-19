# PR to ScrollPrize/villa — flat_depth_targets

**Status: ⛔ CLOSED by `erdpx` 2026-08-18 22:08 UTC, unmerged. Revision prepared
2026-08-19 — needs a push + reopen by the user.**
[#1434](https://github.com/ScrollPrize/villa/pull/1434) · branch
`khj1222:feat/flat-depth-targets` · base `merge-ink-pipelines`.

## The review

> hi, thanks for the pr. please follow villa/CONTRIBUTING.md. also, the experiments only
> validate max over the supervised z window; mean over the logits was not evaluated, so
> we'd need evidence that it produces valid predictions before including it

Two asks, both addressed below.

### 1. `mean` removed — commit `8922c5e`

Correct on the substance. `--z-reduce mean` was carried on a **single** ad-hoc checkpoint
comparison (`docs/12`, 0.803 vs `max` 0.802 over z16–48); it never entered the 3-fold
matrix and no full-segment prediction was ever written with it. That is not evidence, so
the flag is gone rather than argued for:

* `_Z_REDUCTIONS` table and `--z-reduce` deleted; a volume prediction is always collapsed
  with `max`.
* `--z-window START:STOP` stays — that is the configuration the measurements cover.
* New `LOGGER.warning` when a volume prediction is reduced over its full depth, i.e. the
  exact footgun the window exists to avoid.

Diff shrinks **+129 −13 → +112 −13**, still 3 files. Unit tests **7 passed**;
`infer --help` no longer lists `--z-reduce` and still lists `--z-window`.

### 2. `CONTRIBUTING.md` — what we had missed

The file lives at the repo root on `main`; our checkouts are all `merge-ink-pipelines`
descendants, so **we never had it locally.** Against its requirements the old body failed
on three counts, all fixed in the rewrite below:

| requirement | old body | now |
|---|---|---|
| before/after comparison on real scroll data (images/video) | numbers only, **0 figures** | `docs/images/w00_z_window_before_after.png` — held-out π, same checkpoint, both reductions |
| bug fixes show the error and the resolution | described in prose | same figure |
| LLM-assisted PRs carry **human-written** commentary on why it matters | absent | slot below — **the user writes this one, in their own words** |
| concise and accessible | ~60 lines, wall of text | ~35 lines |

Everything else it asks for we already satisfied: the change came out of running the
pipeline on real scroll data (15 training runs, ~22 GPU-hours, two PHercParis4 segments),
there is a motivation section, and no claim rests on synthetic data (the unit tests are
synthetic; every number is from `w00`/`w02`).

## Reopen procedure

1. `git -C D:/vw2 push fork feat/flat-depth-targets` — the branch already carries
   `8922c5e`. (Claude can push; PR actions need the web UI.)
2. Reopen #1434 (the head branch still exists, so the button is there) — keeps
   `erdpx`'s comment in the thread. Opening a fresh PR loses it.
3. Replace the body with the one below, then **drag
   `docs/images/w00_z_window_before_after.png` into the GitHub editor** at the marked
   spot so it uploads to `user-images.githubusercontent.com`. Fallback if you would
   rather link it: `https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/docs/images/w00_z_window_before_after.png`
   (needs `main` pushed first).
4. Post the reply comment at the bottom of this file.
5. Write the "why this matters to me" paragraph yourself — that is the one part of this
   PR that must not be model-written, and it is the requirement `CONTRIBUTING.md` is
   most explicit about.

---

# ▼ PR TITLE

train: keep label depth in the flat-mode loss behind an opt-in flat_depth_targets flag

# ▼ PR BODY (copy from here to the END marker)

## Motivation

Testing the premise of #192 — that more accurate 3D ink labels train better models — on
PHercParis4 `w00_20231016151002` and `w02_20231031143852`, I hit a wall in the pipeline
itself. In `flat` mode the label never reaches the loss with its depth intact:

    targets = (torch.amax(batch['inklabels'], dim=2) > 0).to(dtype=batch['inklabels'].dtype)
    supervision_mask = torch.amax(batch['supervision_mask'], dim=2)

Every label voxel is max-pooled into one plane first, so a depth-resolved label and the
published single-plane label produce **byte-identical targets**. The experiment #192 asks
for is not expressible in flat mode at all. `full_3d` does keep depth, but it wants the
native scroll volume and builds its own band by projecting the flat annotation to a
constant half-thickness, so it answers a different question.

## The half that is easy to get wrong

Training on a depth-resolved label changes what inference must do with the prediction.
The loss only constrains the supervised z column; outside it the network is free, and it
saturates. A max down the full axis reports that noise instead of the ink:

<!-- IMAGE: drag docs/images/w00_z_window_before_after.png in here -->

Same checkpoint, same held-out region, only the volume→surface collapse differs:
**F1 0.499 → 0.814**. The tell is the threshold — scored over the whole volume, every
fold's best threshold pinned to 254, the top of the uint8 range. A full-segment
prediction TIFF written without the window is degraded the same way, so this is not just
a scoring detail.

## Change — opt-in, default path untouched

Everything is behind `flat_depth_targets: true`; without the key nothing changes.

* z projection is disabled for model and targets the way the native 3D modes already do
  it, and the model emits `[B, 1, Z, Y, X]`.
* The loss runs volume-to-volume, with `supervision_mask` as the ignore mask.
* Train previews reuse the `full_3d` central-slice reduction.
* `infer` gains `--z-window START:STOP` to collapse a volume prediction back to the
  ordinary 2D TIFF over the supervised slices, and warns when it is reduced over the full
  depth. Default (no window) reproduces existing behaviour.

## Verification on real scroll data

| check | result |
|---|---|
| a constant 8-voxel band trained through this path vs the 2D baseline, same 3 folds | 0.8478 vs 0.8472 mean F1 — within the 0.03 noise floor, so the depth path is calibrated, not just plumbed |
| the same on a second segment (`w02`) | 0.8263 vs its own 2D baseline 0.8235 |
| `--z-window` across the full 3-fold arm | 0.5046 → 0.8098 mean F1 |
| default-off path | a config without the key takes the existing `amax` branch, unchanged |
| unit tests | 7 passed; projection-gating tests extended to cover the flag |
| shapes / throughput | output `(1, 1, 64, 256, 256)`, ~3.6 it/s, unchanged from 2D targets |

15 training runs, ~22 GPU-hours, two segments. The full write-up and raw numbers are in
#192.

## Changed since the first round

`--z-reduce mean` is gone. It rested on one ad-hoc checkpoint comparison and never
entered the matrix, so there was no evidence to offer for it — `max` over the supervised
window is what the runs actually validate.

## Why this matters to me

<!-- USER: replace this block with your own words, ~3-5 sentences. Worth covering:
     - what you were actually trying to do when you hit this (the #192 experiment)
     - that the answer came out negative and you are still submitting the gate, because
       the next person testing a label-depth idea hits the same wall
     - your own read on whether this belongs in villa
     - a line disclosing that the code was written with an LLM assistant and that you
       ran, read and verified it — CONTRIBUTING asks for exactly this. -->

# ▲ END OF PR BODY

---

# ▼ REPLY COMMENT (post after reopening)

Thanks — both points taken.

`mean` is removed (`8922c5e`). You are right that it was never evaluated: it rested on a
single ad-hoc checkpoint comparison and never entered the 3-fold matrix, so I would
rather drop it than argue from that. `max` over the supervised window is what the runs
actually cover, and that is all the PR now ships. I also added a warning when a volume
prediction gets reduced over its full depth, since that is the failure mode the window
exists for.

On CONTRIBUTING.md — I had genuinely not seen it: it is on `main`, and this work has been
on `merge-ink-pipelines` throughout. Reading it now, the body was missing the before/after
figure on real data and the human commentary, both of which are in the rewritten
description. Sorry for the noise.

# ▲ END OF REPLY COMMENT

---

## Archive

* Patch: [`villa-flat-depth-targets.patch`](villa-flat-depth-targets.patch) — 3 files,
  +112 −13, regenerated 2026-08-19 from `8922c5e`. Plain `git diff`: use `git apply`,
  **not** `git am`.
* Figure source: scratchpad `make_zwindow_figure.py`. Built from artifacts already on
  disk — `runs/ink_depth_v4_fold1/validation/val_017000.tif` (full-depth max) and
  `validation_z16_48/val_017000.tif` (windowed), same checkpoint, plus the published
  `_inklabels.tif`. No GPU rerun. Crop = the held-out annotation region at
  y 12384–15360, x 24256–26880; rendered ink-dark so the saturated panel reads as
  buried rather than bright.
* Worktree `D:/vw2` stays until the PR resolves — it holds the committed branch, and
  review fixes get committed and pushed from there (`git -C D:/vw2 ...`, remote `fork`).
  ⚠️ Run tests as `cd D:/vw2/ink-detection && uv run --project <repo>/external/villa/ink-detection --no-sync ...`
  (`--project`, not `--directory` — the latter moves cwd and imports the wrong tree).
* The `external/villa` working tree still holds the **pre-rebase** copy of this change,
  uncommitted, on the #1234 branch. `D:/vw2` is the source of truth.
