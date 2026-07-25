# PR to ScrollPrize/villa — stream untiled label images

**Branch (local):** `fix/stream-untiled-label-images` in `external/villa` (commit `a5179a8`)
**Patch:** [`villa-pr-stream-untiled-labels.patch`](villa-pr-stream-untiled-labels.patch)
**Base branch: `merge-ink-pipelines`** — not `main`. `ink-detection/koine_machines/` does not
exist on `main` (404); the uv/koine_machines pipeline lives only on that branch.
**Follows up:** the second half of https://github.com/ScrollPrize/villa/issues/1231

Diff: 1 file, +54 −8.

---

## How to submit

1. Fork `ScrollPrize/villa` on GitHub (button, top right).
2. Push the branch from the existing local clone:

```bash
cd D:/vesuvius-challenge/external/villa
git remote add fork https://github.com/<your-gh-user>/villa.git
git push fork fix/stream-untiled-label-images
```

3. Open the PR with **base = `merge-ink-pipelines`**, compare = your branch.

(If the clone is ever re-made, `git am < submission/villa-pr-stream-untiled-labels.patch`
reapplies the commit.)

---

## PR title

```
create_label_zarrs: stream untiled label images instead of building the pyramid in memory
```

## PR body

```markdown
Converting a label image only streams when the input TIFF is **tiled**.
`_get_tiled_tiff_metadata` returns `None` for a striped TIFF (or a PNG), and
`convert_image` falls back to `build_pyramid_with_mode`, which materializes the whole
`DEFAULT_DEPTH`-deep volume once per pyramid level. For a full-resolution segment label
that is tens of GiB — even though 64 of the 65 slices are zeros:

```
ERROR ..._validation_mask.tif: Unable to allocate 25.1 GiB for an array
      with shape (65, 16125, 25690) and data type uint8
```

The shipped `_inklabels` / `_supervision_mask` TIFFs are tiled 256×256, so published assets
never hit this. Any label image written elsewhere does — in my case a validation mask
produced with a default `tifffile.imwrite`, which is striped.

### Change

Route untiled inputs through the same zarr-backed path the tiled branch already uses:
create the datasets, write the 2-D image into level 0 at `DEFAULT_LABEL_SLICE` in blocks,
then build the downsampled levels from zarr with the existing
`_build_downsample_levels_from_zarr`. Peak memory becomes one 2-D image instead of
`DEFAULT_DEPTH` times it. No new dependencies, no change to the tiled path, and
`build_pyramid` / `write_ome_zarr` are left in place for other callers.

### Verification

Same-output check on a synthetic 1500×2300 image written both ways:

- all six pyramid levels byte-identical between the tiled and untiled paths
- the only non-empty z slice is 32, and it equals the source image
- group attrs identical

Real-size check on a 32249×51380 uint8 mask: the striped input that previously raised
`Unable to allocate 25.1 GiB` now converts in 83 s, and levels 0/3/5 match the output of
the tiled path exactly.

Second half of #1231.
```
