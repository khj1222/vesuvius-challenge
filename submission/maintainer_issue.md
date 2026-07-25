# GitHub issue — final text

**Post at:** https://github.com/ScrollPrize/villa/issues/new
**Posted by:** khj1222 (Claude has no GitHub auth in this session and does not post)

---

## Title

```
Tutorial 5 trains with no validation set — published segments ship no `_validation_mask`
```

## Body

```markdown
Following [tutorial 5](https://scrollprize.org/tutorial5) end to end on `w00_20231016151002`
(native Windows, RTX 5090, `merge-ink-pipelines`), I ended up with a model I had no way to
evaluate, and I'd like to check whether that's intended.

### 1. Is the missing `_validation_mask` deliberate?

The pipeline clearly supports one:

- `data/patch_finding/default.py` marks every patch touching `_validation_mask` as a
  validation patch, and `_exclude_validation_voxels_from_training_supervision` in
  `data/ink_dataset.py` removes those voxels from the training supervision;
- `training/train.py` runs a validation pass every `val_every` steps and logs
  Confusion / BalancedAccuracy;
- `preprocessing/create_label_zarrs.py` already converts `_validation_mask.{tif,tiff,png}`;
- `evaluation/metrics/` implements DRD and a weighted pseudo-F-measure.

But the published segment carries only `_inklabels` and `_supervision_mask`, and the tutorial
never mentions validation. A stock tutorial run therefore gives:

```
flat_ink_patches_...json   "is_validation": true  ->     0
                           "is_validation": false -> 2,710
val_previews/              (empty)
```

`val_every` iterates an empty loader, and DRD / pseudo-F-measure never execute — so there is
no way to tell whether a change to the config, the model or the augmentations helped.

Are the validation masks kept internally and simply not published, or is generating one left
to the user? If the latter, is there a convention for choosing the held-out region that I
should match?

I ask because the choice turns out to matter more than I expected. On this segment the
supervision mask is **15 disconnected regions** around annotated letters (1.5%–20.7% of the
supervised area each, ink density 0.114–0.440), and 4 of them sit closer to another region
than one 256 px patch. A naive rectangular split cuts individual letters in half, so the
model trains on one stroke and is scored on the one beside it.

Holding out whole regions instead (20% of supervised area, ink density matched to 0.2283 vs
the segment's 0.2283) gives 1,337 validation / 2,240 training patches, and the numbers that
come out are:

| | best F1 | IoU |
|---|---|---|
| clean 20k run, scored on held-out regions | 0.8232 | 0.6995 |
| the pre-existing checkpoint that had trained on those regions | 0.8594 | 0.7535 |

Per-region F1 on the clean run spans 0.796–0.895, and a 3-fold rerun puts another fold at
0.8497 — i.e. the split matters by ~0.03 F1 on its own, which is larger than many changes
people would want to claim.

### 2. `create_label_zarrs` OOMs on striped TIFF input

Separate and much smaller, but it cost me a while: converting a full-resolution label image
only streams when the input TIFF is **tiled**. `_get_tiled_tiff_metadata` returns `None` for a
striped TIFF, `convert_image` falls back to `build_pyramid`, and that materializes the whole
65-deep volume:

```
ERROR ..._validation_mask.tif: Unable to allocate 25.1 GiB for an array
      with shape (65, 16125, 25690) and data type uint8
```

The shipped `_inklabels` / `_supervision_mask` TIFFs happen to be tiled 256×256, so this never
bites on published assets — but any label image written with a default `tifffile.imwrite` hits
it. Would you take a PR that either falls back to a streamed strip path, or fails early with a
clear "input must be tiled" message? Happy to open that as its own issue if you'd rather keep
this one to the validation question.

---

In the meantime I wrote the tooling I needed for the above — region-aware held-out mask
generation, evaluation against it (threshold sweep, your DRD / pseudo-F-measure classes, and a
per-region breakdown), a checkpoint sweep, and a k-fold driver. Happy to share or upstream it
in whatever shape you'd prefer, or to drop it if masks already exist on your side.
```
