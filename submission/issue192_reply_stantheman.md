<!--
Reply to stantheman0128's offer on villa #192 "Accurate 3d ink labels"
  target: https://github.com/ScrollPrize/villa/issues/192
  replying to: stantheman0128's comment of 2026-08-13 (offer to run D/FWHM
               scoring of our v4 measured band against the independent 1.129um
               scan), in the context of pmh47's pushback on that method.
  status: POSTED 2026-08-14 by the user. Keep this file identical to the
          posted comment (same convention as issue192_comment.md).

This header is an HTML comment, so the whole file can be pasted as-is —
GitHub renders nothing for it.
-->

@stantheman0128 Yes, please — that scoring is exactly the measurement my
result cannot produce for itself.

The matrix above settles the downstream half: training on the `v4` band loses
to a constant band. What it cannot distinguish is *why*, and the two readings
lead in opposite directions:

1. **The band's geometry is wrong** — the per-pixel wander is estimator noise,
   not the sheet. Then the negative result indicts my estimator rather than
   per-pixel bands in general, and this issue's premise survives untouched.
2. **The geometry is right and it still loses.** Then the result is stronger:
   even a band that follows the true sheet does not beat leaving the band in
   one place, under this training setup.

I cannot pick between these from inside my own pipeline — the band was read
out of a model, and out of the same CT that is being labelled, so every check
I have is circular somewhere. Scoring it against an independently scanned and
reconstructed volume is the non-circular test it has been missing.

On @pmh47's caveat: agreed, and for this use it cuts the other way. I do not
need D to certify ink — the ink question was already asked downstream, and it
came out against my band. What I need to know is whether the band's per-pixel
*movement* tracks a real structure or is noise. Distance to an independently
observed surface seems a reasonable proxy for that even if ink does not sit
exactly on the recto: a band that is offset but follows the sheet should show
spatially coherent D, while an estimator artifact should not. If you report
per-anchor records as in your confirmatory run, the coherence will be visible
either way.

What the band is, practically:

- Segment `w00_20231016151002` (PHercParis4), in **surface-volume
  coordinates**: 65 layers, the published annotation plane at z=32.
- Per-pixel centre + half-width, stored as a 2D float32 pair
  (`_inkdepth.zarr`, NaN outside the annotation). The honest resolution is
  coarser than per-pixel: estimated per 64 px cell (centroid centre, FWHM
  width), median-filtered on the cell grid, bilinearly upsampled. Measured
  centres run 29.3–40.3 by region; median half-width ≈ 4 voxels.
- It exists only inside the 15 annotated regions, so anchors would come from
  those. A y–z cross-section QC figure of the band against the sheet is in
  [docs/11](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/11_measured_3d_labels.md)
  if you want to eyeball it before spending a run.

The piece I would need your input on is coordinates. My z is a layer index in
the flattened surface volume; mapping an (x, y, layer) to scroll space goes
through the segment's per-pixel coordinate maps (`x/y/z.tif` in the released
segment folder). Tell me what anchor format your pipeline wants — scroll-space
points plus an expected surface direction? — and I will produce it; a
cell-level CSV (x, y, centre, half-width, region id) is trivial to emit if
that is easier than the zarr.

Either verdict is useful, and I will report the outcome back on this issue
either way.
