<!--
Reply to stantheman0128 on villa #192 (draft 2026-10-14). NOT posted — the user posts it.
  target: https://github.com/ScrollPrize/villa/issues/192
  replying to: stantheman0128 2026-10-13 16:40Z (issuecomment-6150453855), announcing villa #1945
  (foundation/volume-registration/interface_distance.py, head 21c920a) which reads our
  submission/depth_anchors/w00_20231016151002_depth_anchors.csv directly and mentions @khj1222.
  No question was asked; this is optional.

Facts behind each sentence (checked 2026-10-14):
  - #1945 read_points(): point = base + offset_from_plane * unit(normal), rows with
    sampled_from != "center" dropped unless --include-block-median. That is what the exporter means
    (sidecar "composition": P(layer) = base + (layer - 32) * 1.0 * normal; offset_from_plane =
    center_layer - 32).
  - Exporter bug: np.where(keep, "center", "") is <U6, so 1,609 recovered rows were written as
    "block_" not "block_median". Fixed in khj1222/vesuvius-challenge 8f49482; regenerated w00 CSV
    differs only in that column, 5,396 center rows and JSON sidecar identical. #1945 filters on
    == "center", so its numbers are unaffected.
  - Sign: sidecar says the normal is cross(d/dx, d/dy) of the maps and its sign vs layer index is
    UNVERIFIED. Quick check (scratch script, rule fixed before running: >=80% agreement AND median
    winning corr >= 0.5): local w00 surface-volume column vs public 20260411134726 2.4 um volume
    sampled along base + s*(L-32)*normal, 30 center anchors: 25/30 prefer s=+1, median winning corr
    0.335 -> fails the corr gate -> undetermined. Local surface volume attrs say
    source_zarr=/volumes/esrf/20260311/2.4um_PHerc-Paris4_masked.zarr/, canvas 51380x32249; the
    public surface volume for this segment is 109x31960x51960 -> a different render.
  - Region 15 (the only region in the 1.129 um footprint): 481 center rows, median offset_from_plane
    -2.72 layers -> a flipped sign would move a typical point ~5.4 voxels, more than the 3-voxel
    threshold. So it matters for D too, not only for d_minus/d_plus.
  - No AI-disclosure line (same as earlier #192 replies, user decision) — user may add one.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@stantheman0128 Thanks for turning it into a tool and for writing the claim boundary into the README. I checked how #1945 reads the export, and it matches what the exporter means: the point is `base + offset_from_plane * normal`, and only `sampled_from == center` rows are kept by default.

Two things from our side:

1. The exporter wrote the 1,609 recovered rows as `block_` instead of `block_median` (a numpy string-width bug). It is fixed in khj1222/vesuvius-challenge@8f49482. Only that column changed, and the 5,396 `center` rows are byte-identical, so your numbers don't move.

2. The normal's sign is still the one convention the sidecar marks as unverified. With `d_minus`/`d_plus` it now decides which side is "minus", and it also decides where the band centre lands: in region 15 the median offset is −2.7 layers, so a flipped sign would move a typical point about 5 voxels. I tried to settle it today by correlating the w00 surface-volume column with the 2.4 µm volume sampled along ±normal. 25 of 30 anchors prefer `+`, but the correlations are weak (median 0.34), and my local surface volume was rendered from a different source than the public one. So I don't count it as settled. If you want the other reading next to yours, it is the same CSV with the three `normal_*` columns negated.
