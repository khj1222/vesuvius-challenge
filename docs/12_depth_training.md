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
  (`max` by default, `mean` available).

That last one is what keeps the comparison honest. A model trained with
`z_projection_mode: max` and a model trained on a depth-resolved target both end
up writing the same kind of surface map, so the existing
[validation harness](09_validation_harness.md) scores them with one yardstick
and the fold-to-fold noise floor measured in July (~0.03 F1) still applies.

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

* **The comparison has not been run.** This is the plumbing and the assets; the
  3 arms × 3 folds still have to be trained and scored, and until they are, no
  claim about label quality is supported.
* **Circularity is unchanged.** The `v4` band comes from a model trained on the
  depthless annotation. `v3` is the control that can catch it, not a proof that
  there is nothing to catch.
* **±16 is a judgement call**, informed by the contrast measurement but not
  derived from it.
* **One segment, one checkpoint**, as everywhere else in this repo.

---

MIT-licensed.
