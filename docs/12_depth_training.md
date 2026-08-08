# Training on depth-resolved ink labels

[The measured 3D label](11_measured_3d_labels.md) had nowhere to go. This is the
step that gives it a consumer: the flat pipeline can now train on a label that
varies along z, and the resulting model can still be scored on the same held-out
split as everything before it.

## The gap

The flat mode resamples the volume along the surface normal, so its z axis
*is* depth. But the training loop threw that away:

```python
targets = (torch.amax(batch['inklabels'], dim=2) > 0).to(dtype=batch['inklabels'].dtype)
supervision_mask = torch.amax(batch['supervision_mask'], dim=2)
```

Every label voxel was max-pooled into one plane before the loss saw it. A
depth-resolved label and the published single-plane label produce byte-identical
targets after that line, so no experiment on label depth was possible in flat
mode at all — which is a large part of why villa
[#192](https://github.com/ScrollPrize/villa/issues/192) sat untouched for
fifteen months.

The other 3D path, `full_3d`, does keep depth, but it needs the native scroll
volume rather than the segment's surface volume, and it builds its own band by
projecting the flat annotation out to a constant
`_DEFAULT_FULL_3D_PROJECTION_HALF_THICKNESS`. Neither is available to someone
who followed tutorial 5.

## The change

`flat_depth_targets: true` in the training config, and the flat path keeps the
volume:

* z projection is switched off for the model and every target, the same way the
  native 3D modes already do it, so the network predicts `[B, 1, Z, Y, X]`
  instead of `[B, 1, Y, X]`;
* the loss compares that volume against `inklabels` directly, with
  `supervision_mask` as the ignore mask — again matching what `full_3d` does;
* previews take the annotated plane out of the volume, reusing the reduction the
  `full_3d` previews already used;
* inference reduces a volume prediction back to a surface map with `--z-reduce`
  (`max` by default, `mean` available) over the slices `--z-window` selects.

That last one is what keeps the comparison honest. A model trained with
`z_projection_mode: max` and a model trained on a depth-resolved target both end
up writing the same kind of surface map, so the existing
[validation harness](09_validation_harness.md) scores them with one yardstick
and the fold-to-fold noise floor measured in July (~0.03 F1) still applies —
**provided the reduction covers the supervised column and nothing else**, which
is a trap sprung below.

Patch against `merge-ink-pipelines`:
[`submission/villa-flat-depth-targets.patch`](../submission/villa-flat-depth-targets.patch).

## The labels

`tools/make_label_version.py` packages a band as a **label version** —
`_inklabels_v4.zarr` and friends, which `Segment.discover_labels` already
understands and which a config selects with `"label_version": "v4"`. The
published `v1` assets are never touched, and a run that does not ask for a
version still sees exactly the published data.

Three bands, each the control for the next:

| version | band | what it claims |
|---|---|---|
| `v2` | `plane` | ink is one voxel thick, at the annotated plane — today's assets, read literally |
| `v3` | `constant` | ink is a fixed band around the surface — `full_3d`'s model, at this segment's measured thickness |
| `v4` | `measured` | the per-pixel band from `_inkdepth.zarr`, which moves with the sheet |

If `v3` captures whatever `v4` gains, then measuring depth bought nothing and
only thickness mattered. That arm exists so the claim can fail.

**`v3` vs `v4` is the controlled comparison**, and `v2` is not. The two banded
arms label the same number of voxels (8.00 per ink pixel), so they differ only in
where the band sits. `v2` labels one voxel per pixel, which is 0.7% of the
supervised column against `v3`/`v4`'s 5.5% — a different positive rate feeding a
Dice+BCE loss, so a `v2`-vs-`v4` gap mixes placement with class balance. `v2`
still belongs in the table as what today's assets literally say, but it is a
reference point, not the control.

### Supervision has to become a column

All three versions carry the same supervision: a column of ±16 voxels around the
annotated plane, at annotated pixels only. Without it the off-plane voxels are
unsupervised, no band is distinguishable from any other, and the loss is back to
where it started. With it, every voxel inside the column that is not labelled ink
is a negative the model has to get right — which is the whole experiment.

The column stops at ±16 rather than spanning the volume because the far end of
the flat volume drifts toward the neighbouring wrap. The
[model-free contrast measurement](10_depth_localization.md) found its largest
negative drift at z > 40, and calling that "background" would be a claim this
tool cannot support. ±16 covers every measured band on this segment (region
centers 29–40, half width 4) with room to spare.

The validation mask is extruded through the same column, and that is not
cosmetic: the trainer removes held-out voxels from the training supervision voxel
by voxel, so a plane-only validation mask would have left every off-plane voxel
of the held-out letters in the training set. The leak would have been invisible
and would have flattered exactly the arm under test.

## Measured, on `w00_20231016151002`

| | v2 `plane` | v3 `constant` | v4 `measured` |
|---|---|---|---|
| ink pixels | 21,902,496 | 21,902,496 | 21,902,496 |
| label voxels | 21,902,496 | 175,219,968 | 175,330,371 |
| voxels per ink pixel | 1.00 | 8.00 | 8.01 |
| band along z | 32 | 29–36 | moves with the sheet |
| supervised voxels | 3,165,887,472 | 3,165,887,472 | 3,169,480,390 |
| held-out voxels | 629,750,352 | 629,750,352 | 629,750,352 |

`v3` and `v4` came out within 0.15% of each other on label voxels without being
tuned to — `constant` takes its half width from the same measurement `measured`
varies per pixel. The comparison therefore holds the positive count fixed and
moves only the placement, which is exactly the question.

`v4`'s supervised column is 3.6M voxels larger because the supervision is the
column *unioned with the band*: where a measured band reaches past ±16, it brings
its own supervision rather than being labelled ink outside the supervised set.
Only 2,814 ink pixels (0.01%) fell back to the segment median for want of a depth
estimate — the median filter and bilinear upsampling in `make_3d_labels.py` cover
almost everything the per-cell measurement left blank.

Each version takes about 10 minutes to write and lands at a few tens of MB, since
the pyramid geometry, chunking and compressor are copied from the published
labels level for level.

A 200-iteration smoke run on `v2` confirms the path end to end:

* patches split 2,234 train / 1,337 validation — the same held-out set as the
  July runs, so the arms stay comparable to the 3-fold baseline;
* the patch cache key now includes the label version, so switching arms cannot
  silently reuse another arm's split;
* training runs at 3.6 it/s, unchanged from the 2D baseline, so a 20k arm is
  still ~1.5 h;
* the model returns `(1, 1, 64, 256, 256)`;
* inference over the supervised region writes the usual 2D TIFF in 34 s.

## The reduction has to match the supervision

Training on a depth-resolved label changes what inference has to do with the
prediction, and getting that second half wrong is expensive in a way that is
easy to misread as a bad label.

The supervision is a column: `make_label_version.py` supervises `z ±16` around
the annotated plane, because the negative drift past z40 is not something we can
honestly call background ([`10_depth_localization.md`](10_depth_localization.md)).
The loss therefore says nothing at all about the other 32 slices. Inference,
meanwhile, reduced over all 64. Asking a `v4` checkpoint for its raw volume on
12 supervised blocks (150,632 ink px, 582,216 background px) shows what lives
out there:

| z band | mean p(ink px) | mean p(background px) | difference |
|---|---|---|---|
| 0–14 (unsupervised) | 0.11 → 0.69 | 0.32 → 0.93 | **−0.30** |
| 16–48 (supervised) | peak 0.506 @ z32 | 0.083 | **+0.42** |
| 50–62 (unsupervised) | 0.64 → 0.16 | 0.59 → 0.55 | **−0.32** |

Inside the column the model is clean and sharply peaked. Outside it both classes
saturate above 0.6 — the network was never penalised there, so it does whatever
it likes, and a max down the full axis reports *that*. Same checkpoint, same
pixels, only the collapse differs:

| volume → surface | best F1 | precision | recall |
|---|---|---|---|
| `max` over z0–64 | **0.535** | 0.422 | 0.732 |
| `max` over z16–48 | **0.802** | 0.819 | 0.786 |
| `mean` over z16–48 | 0.803 | 0.842 | 0.767 |
| `mean` over z0–64 | 0.368 | 0.618 | 0.262 |

Across the full 3-fold `v4` arm the effect is the same size, and the tell is the
threshold: scored over the whole volume every fold's best threshold pinned to
254, the top of the uint8 range, which is what saturation looks like.

| fold | z0–64 (wrong) | z16–48 | best step | best threshold, z16–48 |
|---|---|---|---|---|
| 0 | 0.4708 | **0.7997** | 20000 | 168 |
| 1 | 0.5122 | **0.8192** | 19000 | 136 |
| 2 | 0.5308 | **0.8104** | 20000 | 139 |
| mean | 0.5046 | **0.8098** | — | — |

Spread across folds is 0.0195, inside the ~0.03 noise floor. Note where the best
step lands: 19000–20000, still climbing, where the July 2D runs peaked at 17000
and fell back. The volume task converges more slowly. The schedule stays at 20k
for every arm anyway — changing it mid-matrix would cost the comparison.

So `--z-window START:STOP` on `infer`, plumbed through `sweep_checkpoints.py`
and `run_cv_folds.py`. It defaults to the whole volume, which leaves models
without depth targets untouched. This is not only a scoring detail: a
full-segment prediction TIFF written without it is degraded in exactly the same
way, so anyone adopting depth-resolved labels needs the pair, not just the
label.

## The result: the measured band loses

Two arms are trained and scored: `v4`, the per-pixel band measured in
[`11_measured_3d_labels.md`](11_measured_3d_labels.md), and `v3`, a constant
band at the segment median (centre 32.47, half-width 4). They differ in the
label and nothing else — same folds, same held-out voxels, same seed, same
config, same 20k schedule, both scored over the supervised column.

| fold | `v3` constant | `v4` measured | difference |
|---|---|---|---|
| 0 | 0.8455 | 0.7997 | **+0.0458** |
| 1 | 0.8452 | 0.8192 | **+0.0260** |
| 2 | 0.8528 | 0.8104 | **+0.0424** |
| **mean** | **0.8478** | **0.8098** | **+0.0381** |
| spread | 0.0076 | 0.0195 | |

**The constant band wins on every fold**, by more than the ~0.03 fold-to-fold
noise floor measured in July. Three things make that hard to argue away:

* **`v3` is remarkably stable** — 0.8452 to 0.8528, a spread of 0.0076, tighter
  than the July baseline's own 0.0154 across the same three splits.
* **`v3` reproduces the 2D baseline almost exactly**: 0.8478 against July's
  0.8472 on the same folds. Depth-resolved targets are not the problem — a flat
  band placed at the median costs nothing and gains nothing. What costs
  something is moving that band around per pixel.
* **The circularity worry cuts the other way.** `v4`'s band was measured from a
  model trained on the depthless annotation, so any self-distillation effect
  should have flattered `v4`. It lost anyway.

Nor is this a stopping artifact. Over the last 3,000 steps both arms gain about
the same small amount — `v3` +0.0075 on average, `v4` +0.0068 — while the gap
between them is 0.0381, five times larger.

So on this segment, the premise behind villa
[#192](https://github.com/ScrollPrize/villa/issues/192) — that a more accurate
3D ink label should train a better model — is **not supported** by a band
measured this way. That is a negative result, and it is worth exactly as much as
a positive one would have been: the claim had gone fifteen months without a
number attached, and now it has three.

What it does *not* say is that #192 is wrong. It says this particular route to a
3D label — per-pixel depth read out of a 2D-trained model, with FWHM widths and
a median filter — does not beat putting the band in one place and leaving it
there. A band measured some other way, or on a segment whose sheet wanders more
than this one, could still win. The harness is now set up to check that in a day.

## Reproduce

```bash
uv run --project external/villa/ink-detection python tools/make_label_version.py \
    data/ink-dataset/phercparis4/w00_20231016151002 --version 4 --band measured
```

The arm configs are [`configs/ink_depth_v2.json`](../configs/ink_depth_v2.json),
`v3` and `v4` — the July validation config plus `label_version` and
`flat_depth_targets`, everything else untouched so the arms differ in the label
and nothing else. Copy one into the pipeline's `configs/` and train:

```bash
uv run --directory external/villa/ink-detection python -m koine_machines.training.train configs/ink_depth_v4.json
```

Across folds, the driver re-extrudes each fold's held-out split into the
version's own validation mask:

```bash
python tools/run_cv_folds.py SEGMENT_DIR --folds 3 --config configs/ink_depth_v4.json --label-version v4 --prefix ink_depth_v4_fold
```

`--dry-run` reports the geometry and writes nothing. Full flag list:
[`tools/README.md`](../tools/README.md).

## What this does not settle

* **`v2` has not been run.** The plane arm is a reference point rather than a
  control — at 1.00 label voxel per pixel against 8.00, its positive rate is
  0.7% where the other two sit at 5.5%, so a Dice+BCE loss sees a different
  class balance and not just a different geometry. It would say something about
  how much depth supervision is worth at all; it cannot sharpen `v4 − v3`.
* **One segment, three folds, one seed per fold.** The three splits share the
  same 15 annotated regions, so they are not independent samples of "papyrus" —
  they are three ways of cutting one letter set. Seed variance within a fold was
  never measured; the ~0.03 noise floor comes from split variance alone.
* **±16 is a judgement call**, and it bounds both arms. A wider column would
  give `v4`'s deeper bands more room and might change the ranking.
* **Circularity was never resolved, only rendered harmless.** The `v4` band
  still comes from a model trained on the depthless annotation. `v3` was the
  control that could have caught a self-distillation effect; it did not need to,
  because `v4` lost. Had `v4` won, this caveat would have been the headline.

---

MIT-licensed.
