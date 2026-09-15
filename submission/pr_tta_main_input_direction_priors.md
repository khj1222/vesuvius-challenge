<!--
PR body draft — Copy direction priors through TTA, against `main`.

  head:  khj1222:fix/tta-transform-input-direction-priors  (079bc58, pushed to fork)
  base:  main (4b3c728)
  diff:  3 files, +188 −2  (displacement_tta.py, displacement_helpers.py, one new test file)
  evidence: runs/tta_main/  (must be on origin/main before the PR is opened — the images are raw URLs)

⚠️ Open as DRAFT until #1608 is closed by the bot (2026-09-19): non-draft PRs sit at the cap of 3.
⚠️ Two things the USER supplies before this goes out:
   1. **Why / where this is useful** — human-written, in the user's own words (CONTRIBUTING).
   2. The checkbox stays UNTICKED unless the user runs tta_shot.py (or the tests) themselves.
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** Copy inference with test-time augmentation (the default) now shows every flipped or rotated variant a direction prior that points the same physical way as the volume it is looking at, instead of a prior that still points along the un-flipped axes.

**One real example:** Starting with six 256³ CT cubes of PHerc. Paris 4 that carry manual sheet-instance labels ([`volumetric-instance-labels`](https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumetric-instance-labels/README.txt)), the released `scrollprize/copy_displacement_latest` checkpoint (revision `4da5323`) and the default mirror TTA (8 variants, `vector_geomedian`), I copied 11 manually labelled start surfaces onto their neighbouring sheet twice, changing only whether the input direction priors are transported with the flip. The share of source-surface area that landed on the correct neighbouring sheet went from 13.7% to 17.7% over all six cubes (4 cubes up, 2 down) and from 13.3% to 13.7% on the three held-out cubes.

**Before:** `run_model_tta` flips or axis-permutes all eight input channels spatially, and on the way back negates or reorders the *output* displacement components so the variants agree in the original frame. The two ZYX direction priors in the input (channels 2:5 and 5:8) are vectors too, but their components were not touched: after a z flip the prior still said "+z" inside a volume that now runs the other way. Each of the eight variants was therefore answering a differently posed question, and the merge averaged the answers. With a model that simply returns its own input priors, mirror TTA on `main` returns (0, 0, 0) for a constant prior — the variants cancel. `infer_streamline.py::_flip_tta_inputs` already swaps its `±` direction input channels when it flips an axis; the triplet-wraps path did not do the equivalent for its vector priors.

**After this PR:** `run_model_tta` takes `input_vector_channel_starts` (empty by default) and negates the flipped component, or reorders the components with the axis permutation, for each listed 3-channel group after the spatial transform. `predict_displacement` passes `(2, 5)` only when the checkpoint config has `use_triplet_direction_priors` and the input is the 8-channel layout. Every other caller, and the same call without the argument, is bit-identical to `main`. The returning-priors model now gets its priors back to 3.6e-7 (mirror) and 2.4e-7 (rotate3).

**Proof:**

![main vs this PR on a model that returns its own input priors](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/tta_main/tta_console.png)

*Console output of `tta_shot.py`, CPU, no weights: the same TTA code from `main` and from this branch, driven by a model whose "displacement" is its own input priors. Look at the first block: a constant prior merges to (0, 0, 0) on `main` and comes back unchanged here. The last column shows the legacy call on this branch is identical to `main`.*

![Copy on six manually labelled Paris 4 cubes, before and after](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/tta_main/real_data_paris4_cubes.png)

*Real data, same model, same crops, same merge; only the input-prior transport differs. Left: per cube. Right: pooled by area. The effect is not uniform — one cube drops from 17.4% to 5.8% — so I am not claiming an accuracy gain, only that the variants now see consistent geometry.*

Scripts, transcript, numbers and the 43-test run: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/tta_main

**Why / where this is useful:**

<!-- USER WRITES THIS. -->

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

**Tested commit.** `main` at `4b3c728` (2026-09-15). The two changed source files are byte-identical to their state at `23adee0`, where the defect was first reproduced.

**What changes.** `_transform_input_vector_channels(inputs, vector_channel_starts, flip_dims, axis_perm)` clones the input and, per group, applies `FLIP_DIM_TO_CHANNEL` sign flips (mirror) or `[start + axis for axis in perm]` reordering (rotate3) — the same conventions the existing output-side code uses in `_negate_flipped_displacement_channels` and `_reorder_rotated_displacement_channels`. It raises on a group that does not fit inside the channel axis. The gate in `predict_displacement` reads `model_state["model_config"]`, which `load_model` already stores; a direction-conditioned checkpoint with any other input width transports nothing rather than guessing a layout.

**Tests** (`vesuvius/tests/neural_tracing/test_displacement_tta_input_vectors.py`, 13 tests): priors survive TTA in both modes with transport and do not without; scalar channels and the input tensor are untouched; a flip negates only the flipped component; out-of-range groups are rejected; `predict_displacement` transports for the 8-channel direction-conditioned case and is unchanged for an empty config and for a 6-channel input. `test_displacement_scale.py` still passes (43 passed in total).

**Real-data method.** Cubes `02000_02256_04816`, `01744_02512_04048`, `09168_02512_02768`, `07376_03024_04304`, `10192_04304_03024`, `10192_03024_02768` from the instance-label set, three used as development and three held out by z region. Start surfaces were chosen from well-supported manual IDs near each cube centre before any prediction was looked at; the neighbouring sheet is the first different manual ID along the start surface's normal. A copied point counts as correct when the nearest manual ID within 2 native voxels of its destination is that neighbour. Scores are area-weighted over the source surface. Input crops 128³, TTA micro-batch 1.

**Limitations, stated up front.** (1) The real-data effect is mixed per cube; a second run at 128×256×256 on the start points common to both crop sizes moves the same score 12.8% → 18.8% (all) and 8.1% → 14.0% (held-out), but a round-trip-consistency measure in the same study moves the other way. (2) The NRRD cubes carry no physical unit; 7.91 µm was assumed from the legacy Paris 4 volume and resampled to the checkpoint's 4.8 µm. (3) Crops are smaller than the training crop (128×384×384) and field sampling was single trilinear, not the CLI's radius-1 average and overlap merge. (4) `rotate3` is covered by the fixture and tests only; the real-data arms used the default `mirror`. (5) The model was trained on Paris 4 among other scans; the held-out split is a split of cubes, not an independent generalisation test.

**Deliberately not done.** No change to training-time augmentation, to `infer_streamline.py`, or to how the priors are built. If the priors were meant to be TTA-invariant features rather than vectors in volume coordinates, this PR is wrong and should be closed; the training code treats them as ZYX normals (`_build_triplet_direction_priors_for_crop` writes `+n` and `−n` per axis), which is why I read them as vectors.

**Disclosure:** most of the work in this project, including this reproduction, the change and the tests, is done with an AI coding assistant. The problem, the data and the decisions are mine; the defect above is one my project hit while measuring the released Copy model on manually labelled Paris 4 cubes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
