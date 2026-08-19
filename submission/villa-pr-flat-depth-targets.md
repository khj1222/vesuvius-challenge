# PR to ScrollPrize/villa — flat_depth_targets

**Status: ✅ [#1535](https://github.com/ScrollPrize/villa/pull/1535) OPEN and complete —
opened 2026-08-19 11:18 UTC from the same branch, base `merge-ink-pipelines`, 2 commits,
3 files +112 −13, mergeable (`unstable` = the Vercel team-authorization bot, the same
code-unrelated check as #1234/#1434). Body below matches what was posted, including the
"Why this matters to me" paragraph (added 11:23 UTC). Verified against the API after
posting.**

⚠️ **One correction outstanding in the live body: "15 training runs, ~22 GPU-hours"
understates the time.** The five 3-fold summaries total 1,771 min = **29.5 h** wall clock
(`ink_depth_v2` 334 + `ink_depth_v3` 462 + `ink_depth_v4` 320 + `ink_w02_v3` 328 +
`ink_w02_v4` 328). The 22 came from adding the w00 matrix (16 h, `docs/12`) to the 30k
extension (5.8 h) — a different scope that leaves out `w02` entirely. `~30 GPU-hours` is
the honest figure; dropping the hours and keeping "15 training runs across two segments"
is the safe alternative. (`docs/12`'s "nine runs, 16 GPU-hours" is training-only; the
summaries' 18.6 h for those nine is wall clock and includes a fold slowed ~2x by GPU
contention.)

⚠️ **Also outstanding: the pointer comment on #1434** (bottom of this file, `#NNNN` →
`#1535`). Confirmed 2026-08-19 that #1434 still carries only the vercel bot, `erdpx`'s
close, and our reply — nothing points at the new PR yet.

Predecessor: [#1434](https://github.com/ScrollPrize/villa/pull/1434), opened 2026-08-13,
**closed by `erdpx` 2026-08-18 22:08 UTC** unmerged, **and not reopenable** — the button
never appeared, even after the branch was rolled back to the exact commit the closed PR
points at (`8515746`), which rules out head divergence as the cause. Its body was already
replaced with the rewrite below and the reply comment was posted before that was
discovered; both stay there.

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

## New-PR procedure — ✅ steps 1-4 done 2026-08-19, step 5 pending

1. **Write the "Why this matters to me" paragraph first**, before opening anything. It is
   the one part that must not be model-written, and it is the requirement
   `CONTRIBUTING.md` is most explicit about. ⚠️ On #1434 this section went up as a bare
   heading with nothing under it, because the guidance was an HTML comment and GitHub
   renders those invisibly. **Either fill it or delete the heading — never ship the
   heading empty**, least of all in a PR that was just closed for not following
   `CONTRIBUTING.md`.
2. Open https://github.com/ScrollPrize/villa/compare/merge-ink-pipelines...khj1222:feat/flat-depth-targets
   ⚠️ base must read **`merge-ink-pipelines`**, not `main` (wrong base = spurious
   231-file diff, as #1234 briefly showed). It should say *2 commits*, +112 −13.
3. Title and body below. Keep the `Reopening #1434` first line — it is what carries
   `erdpx`'s review context across, since the thread itself does not follow.
4. **Drag `docs/images/w00_z_window_before_after.png` into the GitHub editor** where the
   IMAGE marker sits. Fallback link (verified 200):
   `https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/docs/images/w00_z_window_before_after.png`
5. Add the one-line pointer comment (bottom of this file) to #1434 so the closed thread
   points at the new number and `erdpx`, who is assigned there, gets notified.

---

# ▼ PR TITLE

train: keep label depth in the flat-mode loss behind an opt-in flat_depth_targets flag

# ▼ PR BODY (copy from here to the END marker)

Reopening #1434, which was closed by review — both asks are addressed here, and the
reply is on that thread. `--z-reduce mean` is gone; the description now follows
`CONTRIBUTING.md`.

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

I did not set out to add a flag. I wanted an answer to #192 — whether more accurate
3D ink labels actually train better models — and found that in `flat` mode the question
cannot be asked at all: the label is max-pooled into a plane before the loss, so a
depth-resolved label and the published one produce identical targets. Nothing errors and
nothing warns; the experiment just quietly measures nothing, which is a bad way for a
codebase to say "not supported".

My own answer came out negative — the measured band lost to a constant one, on two
segments — and I am still submitting the gate, because the wall is not about my band.
Anyone who tries a label-depth idea here hits it, and they hit it silently. The
`--z-window` half is the same lesson: the first time I scored a depth-target run I got
F1 0.53 and assumed the labels had failed, when the actual fault was reducing the
prediction over slices the loss never constrained. That cost me a scoring round, and it
belongs in the tool rather than in my notes.

Whether it belongs in villa is your call. It is config-gated and default-off, so my
argument is only that the flat path should be able to express the experiment the issue
asks for. If you would rather keep flat mode simple, I would find that a reasonable
answer — I would just ask that it be said on #192, so the next person does not spend a
month rediscovering it.

On process, per CONTRIBUTING: the code was written with an LLM assistant. I read the
diff, ran the tests, and every number above comes from runs on my own hardware —
15 training runs on PHercParis4 `w00` and `w02`, scored with a held-out split I built
for the July round.

# ▲ END OF PR BODY

---

# ▼ REPLY COMMENT — ✅ already posted on #1434 (2026-08-19), kept for the record

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

# ▼ POINTER COMMENT (post on #1434 once the new PR has a number)

Reopening was not available on this PR, so the revision is up as #NNNN — same branch,
`mean` removed, description rewritten against CONTRIBUTING.md.

# ▲ END OF POINTER COMMENT

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
