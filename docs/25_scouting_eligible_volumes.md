# Scouting the First Letters volumes: which public segment, if any, does a released ink model already react to?

**Pre-registration. Written and committed on 2026-09-19 before any render or inference on
the target segments.** The commit hash of this file is the timestamp. Sections 1–7 are the
plan; results go in section 8 and are not edited back into the plan.

## 1. The question

Vesuvius Challenge lists 23 scroll volumes eligible for the First Letters prize, none of
which has produced legible text yet ([prizes page](https://scrollprize.org/prizes), read
2026-09-19). The suggested workflow is segment → render → run an ink model → fine-tune on
whatever ink is visible. This project has done the back half of that once, on PHerc1447's
largest public segment (docs/16): the render works, the released models produce output, and
the output has none of the signatures of real ink. Label-free adaptation on the same segment
met none of three pre-committed criteria (docs/18, arm D on 1447).

Two results from this project's own measurements decide the shape of what follows:

- Label-free methods recover at most 14% of the cross-scroll gap; one annotated segment is
  worth about seven times the best of them (docs/18). So the lever is not a better model, it
  is **a target the model already responds to**, because that is the only place a
  foothold annotation can start.
- The docs/16 verdict was for one segment of one scroll. Between them, PHerc0800, PHerc1203
  and PHerc1447 have 43 public segments or patches, and 42 have never been looked at this way.

**Question:** among the public segments of the eligible volumes, is there one on which the
released ink models produce output that looks like ink by criteria fixed in advance — the
same criteria that PHerc1447's largest segment failed?

## 2. What exists (inventory, 2026-09-19, S3 bucket `vesuvius-challenge-open-data`)

Raw listing: `runs/scouting/eligible_inventory_s3.json`.

| | count |
|---|---|
| eligible volumes | 23 |
| with a `segments/` prefix at all | **3** — PHerc0800, PHerc1203, PHerc1447 |
| with only `representations/` (surface predictions, no mesh) | 20 |

Every eligible scroll has exactly one ~9 µm masked volume (8.640 or 9.362 µm); PHerc0846A
and PHerc1203 also have a 2.403 µm volume. **Only one of those two has any segment
(PHerc1203)**, and its patches sit on the 9.362 µm volume with no registered mesh on the
2.4 µm one, so the docs/15 guidance "render from the aligned family" cannot be followed on
any eligible scroll today. Everything below is native ~9 µm, the representation docs/15
measured as the weaker one.

The 20 scrolls without meshes are out of scope: growing a segment is the front half of the
workflow (VC3D GrowPatch, a GUI step) and this project has not done it. They are listed so
that "0 of 23" is not misread as "0 of 23 examined".

### Targets (all public segments of the three scrolls)

Area is estimated from the tifxyz grid: valid cells × (voxel size / grid scale)², where the
grid scale is 0.05 in every meta.json, so one cell is 20 voxels square. On the one segment
with a published figure this gives 8.03 cm² against docs/16's 7.40, so treat it as ±10%.
Per-segment numbers: `runs/scouting/eligible_segment_areas.json`,
`runs/scouting/pherc1203_raw_areas.json`.

| scroll | volume | segments | form | area range (cm²) | note |
|---|---|---|---|---|---|
| PHerc0800 | 20250521135224, 8.640 µm | 6 | flattened tifxyz (`mesh/<id>-on-…-8.64um.tifxyz`) | 0.40 – 2.43 | small; the 0.40 one is below the 4 cm² prize window and is scouted anyway |
| PHerc1447 | 20250521151220, 8.640 µm | 15 | flattened tifxyz | 2.52 – 8.38 | `20250703034159` already rendered and judged (docs/16); the other 14 are new, including `20251105093211-z_dbg_gen_00320` (682×411 grid, 10% valid) |
| PHerc1203 | 20250820131727, 9.362 µm | 22 | **raw GrowPatch tifxyz** (`segments/raw/auto_grown_*`, not flattened) | 2.92 – 14.83 | 22 distinct bounding boxes but heavily overlapping (11 grown within 15 s of each other from nearby seeds); rendered individually, judged with overlap noted |

**43 targets, 42 new.** (Corrected from 44/43 in the same hour as the first commit, before any render: the bucket's `raw/` prefix had been counted as a sixteenth PHerc1447 segment.) Everything is rendered from the tifxyz that the bucket publishes;
no mesh is edited, grown or re-flattened by this project.

## 3. Pipeline (fixed)

1. **Render**: `vc_render_tifxyz` from the scroll's ~9 µm masked volume, remote streaming,
   `--scale 1 --num-slices 28 --slice-step 1`, exactly as docs/16. Preferred binary is the
   official `VC3D-5479453-2026-08-30-win64` release (0/3 stalls, ~4–6 min per 8 cm²
   segment, byte-identical across repeats — `runs/f6_render_retest/summary.json`); fallback
   is the `:edge` container with the `--timeout 8` + `--resume` chain.
2. **Inference**: the released ink_9um checkpoints `hybrid_3d2d-seed42` and `-seed43` at
   steps 10,000 and 20,000 (four predictions per target), `--overlap 0.5 --blend-mode hann
   --no-compile`, unchanged from docs/16. No adaptation, no fine-tuning, no pseudo-labels.
3. **Score**: the three criteria in section 4, computed by one script over all targets and
   both references, on the **sheet only** (the render's valid area, 21% of the canvas on
   the docs/16 segment; off-sheet padding is excluded because docs/18 found the model's
   output there is indistinguishable from its output on the sheet).

## 4. Criteria and thresholds

The three criteria are the ones committed for arm D on 1447 (docs/18, "What would change my
mind"), now with a numeric proxy each so the judgement is not only by eye. **A target passes
if two of the three pass in the same place.** Eye judgement on crops is reported alongside
and can only *demote* a proxy pass, never promote a proxy fail.

Thresholds are set relative to two references measured with the same script:

- **Positive control (unseen scroll, real ink)**: PHerc0139 segment `w040`
  (`20250831000000-w040_2025083102`, mesh `-on-20250728140407-9.362um.tifxyz`), rendered
  from the 9.362 µm volume through the identical pipeline, predicted with the
  **leave-0139-out** checkpoints `ink9um_loso_no0139_s42/s43` step 20,000 — a model that
  never saw the scroll, on a segment whose withheld annotation it scores F1 0.68–0.70
  (`runs/ink9um_scorecard/no0139_matrix.csv`). This is what "an unseen scroll with ink"
  looks like to these criteria. The released checkpoints trained on this segment; their
  numbers on it are reported too, labelled *seen*, and are not used to set thresholds.
- **Negative reference**: PHerc1447 `20250703034159` with the released checkpoints, the
  render and predictions already on disk (docs/16, docs/18).

For each proxy, with `c` the control value and `n` the 1447 value, **pass = at or beyond
the midpoint (c + n) / 2 in the control's direction**, plus an absolute floor so a weak
control cannot make the bar trivial:

| criterion | proxy (computed on-sheet, per target, on the seed-42 step-20,000 prediction unless stated) | absolute floor |
|---|---|---|
| **C1 connected strokes** | in the 512 px window with the most pixels above the prediction's own Otsu threshold, components ≥ 50 px, the 30 largest: **median skeleton length / equivalent diameter**. Strokes are long and thin, blobs are ~1. | ≥ 1.5 |
| **C2 seeds agree on where** | **top-decile IoU** between seed 42 and seed 43 at step 20,000, on-sheet — the statistic that stayed at 0.17 on 1447 while correlation rose to 0.86. Also computed inside the C1 window ("same place"). | ≥ 0.30 whole-sheet **and** in the window |
| **C3 bimodal, not hedging** | three-way split of on-sheet values into thirds of [0, 255]: **min(low share, high share)**. Mid-grey hedging and one-sided collapse both score near 0. | ≥ 0.10 |

Guards carried over from docs/16 that do **not** count as evidence: the non-zero share
(it is the render's valid area), the maximum value alone, and the > 128 share alone (it
disagreed threefold across checkpoints on 1447). The checkpoint disagreement itself is
reported as a fourth, non-scoring column: the ratio of the largest to the smallest > 128
share across the four predictions.

**If the positive control fails two or more criteria under the unseen checkpoints, the
criteria are not fit for purpose and the scouting stops there**, reported as a null on the
method, not on the scrolls.

## 5. Predictions, written before running

- The control passes 3/3 with the unseen checkpoints. (If it does not, see above.)
- 1447 `20250703034159` scores 0/3 again on the new script — this is a re-derivation check,
  not a result.
- **Most targets score 0/3.** They are the same acquisition family and the same
  segmentation family as the segment that failed. My expectation for the count of passing
  targets is **0**, with a stated hope of 1–2, most plausibly among the larger PHerc1203
  patches (the only scroll of the three whose volume was also scanned at 2.4 µm, which says
  nothing about the papyrus but does say the team thought it worth a second scan).
- A pass on an *overlapping* set of 1203 patches counts once, not per patch.

## 6. Decision rule and what happens next

- **≥ 1 target passes 2/3**: a separate pre-registration for the First Letters attempt on
  that target follows. Its shape is docs/15 part 4 (annotate → 2,500-step fine-tune →
  re-infer), and it will have to solve the prize's own constraints — no overlap between
  training and prediction regions, held-out evidence against hallucination — before any
  training starts. **No image of a candidate letter is published**; the First Letters
  rules require the discovery to stay private until announced, and that overrides this
  project's early-publication habit.
- **0 targets pass**: the scorecard itself (43 targets × 4 checkpoints × 3 criteria, with
  the control and the reference) is published as a Progress Prize submission, and the bet
  stops. Its value is the map — which public segments the released models react to at all —
  not a finding.

## 7. Budget and what is not being done

- Renders: 42 × ~5 min (native binary) ≈ 4 h unattended; inference 42 × 4 × ~1 min ≈ 3 h;
  scoring seconds. **GPU under one day**, disk ≈ 42 × 400 MB ≈ 17 GB on E:.
- Not done here: growing segments on the 20 mesh-less scrolls; rendering from 2.4 µm
  volumes (no registered mesh); any adaptation or training; any threshold chosen after
  seeing target output.
- Runs in parallel with the October plan of driving open PRs to merge; it does not compete
  with it for time.

## 8. Results

### 8.1 The control caught a pipeline bug before any target was rendered (2026-09-19)

The 0139 w040 control was rendered with the native `VC3D-88d4aa8-2026-09-18` build (the
5479453 asset named in section 3 is no longer on the release tag; 88d4aa8 is the same
post-rewrite lineage, 11m55s for 50 tile rows, and it hangs at exit after writing a complete
pyramid — `tools/render_native.sh` kills it once level 0 is done and the log has been quiet
for 60 s). The `:edge` container segfaulted twice on the same segment and was dropped.

The render has the same canvas and chunking as the team's published surface volume for
this segment, `(28, 6400, 7980)` in `(28, 128, 128)` chunks, **but the slice order is
reversed**: the per-slice mean profile is the team's read backwards, and reversing z makes
the two volumes agree on **99.7% of bytes with a mean absolute difference of 0.0**.
`vc_render_tifxyz --flip-normals` reproduces the team's volume directly (99.74% of bytes,
mean |diff| 0.003). Scored against the segment's withheld annotation
(`runs/scouting/control_w040_honest_f1.json`, 1,629,613 supervised pixels):

| render orientation | leave-0139-out s42 / s43 (unseen) | released s42 / s43 (seen) |
|---|---|---|
| as rendered (default normals) | **0.611 / 0.611 — the trivial classifier**, best threshold 58 / 0 | 0.611 / 0.611 |
| slice order reversed (= team volume) | **0.650 / 0.651** (corpus: 0.684 / 0.703 on a slightly different scored region) | **0.805 / 0.777** |

So the default orientation does not merely weaken the models, it turns every one of them
into "all ink". Consequence for this project's earlier work: the docs/16 render of PHerc1447
was made the same way, so its "no letters" verdict had to be re-tested in the other
orientation (8.3).

### 8.2 The criteria, audited on the control (before any target)

Scores from `tools/score_scouting.py`, seed 42 vs 43 at step 20,000:

| case | C2 sheet | C2 window | C1 | C3 | > 128 share | ckpt ratio | median |
|---|---|---|---|---|---|---|---|
| 1447, docs/16 orientation (negative reference) | 0.173 | 0.379 | 4.89 | 0.059 | 0.230 | 3.04 | 100 |
| 1447, reversed | 0.100 | 0.169 | 5.52 | 0.065 | 0.236 | 3.16 | 101 |
| control, wrong orientation, unseen | 0.209 | 0.339 | 2.44 | 0.003 | 0.020 | 7.57 | 70 |
| control, wrong orientation, seen | 0.230 | 0.101 | 3.83 | 0.015 | 0.083 | 3.15 | 83 |
| **control, right orientation, unseen** | **0.285** | **0.431** | 3.22 | 0.009 | 0.036 | 6.42 | 70 |
| control, right orientation, seen | 0.407 | 0.398 | 3.54 | 0.056 | 0.163 | 2.06 | 86 |

- **C2 (seeds agree on where) works.** Unseen control 0.285 against the reference's 0.173,
  and the same control in the wrong orientation drops to 0.209 — below the midpoint 0.229 —
  which is the right answer for a render on which the model is the trivial classifier.
- **C1 (skeleton ratio) fails: the control scores *lower* than the reference** (3.22 vs
  4.89). Hann-blended predictions make large soft components everywhere, and the ratio
  measures blending, not letters. Its absolute floor of 1.5 was already exceeded by the
  negative reference.
- **C3 (outer-thirds share) fails: it measures calibration, not commitment.** The unseen
  model's best F1 sits at threshold 70–74, so almost none of its ink exceeds 170 and the
  proxy reads 0.009 on a render where it scores F1 0.65. The wrong-orientation control also
  shows what collapse looks like — median 70, 83% of the sheet in the low third — and the
  proxy cannot tell the two apart.

Under section 4's own rule, two of three proxies failed on the control, so **the plan as
written stops here as a null on the method.** Because no target has been rendered or
predicted, the criteria can be revised and re-registered before the targets run; that is
section 9. It is an amendment made with the control and reference in hand and nothing else.

### 8.3 PHerc1447 `20250703034159` in the other orientation

Reversing the docs/16 render and running the four released checkpoints gives C2 0.100
(step 20,000) and 0.199 (step 10,000) — no higher than the original 0.173 / 0.314 — with the
same > 128 share (0.236 vs 0.230) and median (101 vs 100). The docs/16 verdict survives the
orientation check: neither orientation of that segment makes the two seeds agree on where
the ink is, whereas the control does in exactly one orientation. The 1447 reference values
used below are therefore the *better* of its two orientations per statistic.

## 9. Amendment (v2), registered before any target is rendered — 2026-09-19 10:50 KST

1. **Pipeline.** Every target is rendered with `--flip-normals` (the orientation that
   reproduces the team's volumes), and its z-reversed copy is scored too. The orientation
   whose primary prediction gives the higher C2 is reported as the target's "responsive"
   orientation; both rows are kept. A target whose two orientations are within 0.03 of each
   other on C2 is read as "the model does not care", i.e. no signal.
2. **The numeric gate is C2 alone.** Pass = whole-sheet top-decile IoU (seed 42 vs 43,
   step 20,000) **≥ 0.229** (midpoint of unseen control 0.285 and reference 0.173) **and**
   window IoU **≥ 0.405** (midpoint of 0.431 and 0.379). The wrong-orientation control
   (0.209 / 0.339) fails this gate, the right-orientation control passes it, the reference
   fails it in both orientations.
3. **C1 and C3 return to what they were in docs/18: eye judgement on full-resolution crops
   of the C2 window, both seeds side by side**, reported for every target that passes the
   gate and able only to demote. Their numeric proxies are still computed and stored but
   decide nothing.
4. **Trivial-classifier guard.** A prediction with on-sheet median ≤ 75 *and* low-third
   share ≥ 0.80 under the released checkpoints is flagged "collapsed" (the wrong-orientation
   signature). A flag on the responsive orientation demotes the target regardless of C2.
5. **Decision rule.** A target that passes the C2 gate in its responsive orientation and is
   not demoted is a *candidate*. Section 6 applies to candidates, with one addition: before
   any First Letters step, the candidate is re-rendered and re-predicted from scratch and
   must pass the gate again.
6. **Predictions, restated.** 0 candidates expected. The only place I would not be
   surprised by one is among the larger PHerc1203 patches, for the reason given in section 5.
7. **What this amendment cannot fix.** A single numeric criterion is a weaker screen than
   three, and the thresholds come from one control segment. A candidate is a reason to look
   harder, not a finding.
