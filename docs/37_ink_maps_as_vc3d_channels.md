# 37 — Ink maps on VC3D surfaces after the object-store move: segment_ink v2, ink-sdk runs, and the panel

**Status: tools and checks, 2026-11-02 to 2026-11-18** (store round trips and the panel test rerun on villa main
`1386f072e` on 2026-11-18). Code: [`tools/segment_ink.py`](../tools/segment_ink.py) (v2),
[`tools/ink_sdk_channel.py`](../tools/ink_sdk_channel.py). Evidence: [`runs/ink_sdk_channel/`](../runs/ink_sdk_channel),
[`runs/vc3d_ink_channel/`](../runs/vc3d_ink_channel), and the v2 files in [`runs/segment_ink/`](../runs/segment_ink).
The rules for each check were written before it ran, but only in our own notes. Read this as a checked tool,
not a pre-registered test. It follows [docs/32](32_segment_ink_vc3d.md), whose records stopped showing in VC3D
after villa #2358.

## The problem

Anyone who traces a segment, or wants to try another ink checkpoint on an existing one, has to see the
prediction on the segment's geometry to judge it. Since villa #2358 (2026-10-29), VC3D keeps segments in an
object store. Its Ink Detection panel lists only the ink images the catalog publishes for a surface, so a map
made locally had no supported way onto a surface.

The store already has a documented place for one: a **surface channel**, an image whose sides are whole
multiples of the point grid (`vc_object_ingest --surface-channel SURFACE_UUID ink /data/ink_prediction.tif`
in [`vc_object_store/README.md`](https://github.com/ScrollPrize/villa/blob/main/vc_object_store/README.md);
"for example ink at 20 pixels per grid step" in its `docs/ingestion.md`). Two things were missing:

1. something that writes a prediction there, on the right pixels, and
2. a panel that lists such a channel.

## What exists now

| piece | what it does | status |
|---|---|---|
| `segment_ink.py` v2 ([`72bc3c7`](https://github.com/khj1222/vesuvius-challenge/commit/72bc3c74770050057820df306cfe121c1629fd59)) | renders a tifxyz segment with VC3D's own `vc_render_tifxyz`, runs villa's unmodified ink inference with any checkpoint it loads, writes the map as an `ink_<name>` channel | public |
| `ink_sdk_channel.py` | takes [ink-sdk](https://github.com/LimeGS/ink-sdk) run folders (one model or a whole battery) and writes each map as an `ink_<profile>` channel | public |
| VC3D panel change (3 files, +147/−18) | the Ink Detection panel also lists the active surface's `ink` and `ink_*` channels and draws the selected one | on our fork, [`khj1222/villa` branch `feat/vc3d-ink-surface-channel`](https://github.com/khj1222/villa/tree/feat/vc3d-ink-surface-channel) (one commit, [`bb9ec5e2c`](https://github.com/khj1222/villa/commit/bb9ec5e2cb9a896974c32cbb0f0c58b1ce3e8a6b), on villa main `8e21d010f`); not in villa: we asked the VC3D maintainers on 2026-11-04 (Discord #robots) before opening a pull request and had no answer by 2026-11-16 |

Both tools write either an importable tifxyz folder with the maps as sidecars, which ingestion turns into
channels (VC3D: File → Stores → Import from Folder, or `vc_object_ingest --surface`), or add the channels to a
surface already in a store (`--target store`). Published meshes carry `"uuid": "output_tifxyz"`, which the
store refuses. The folder gets a UUID derived from the segment (the same on every run) and keeps the old
value as `segment_ink_source_uuid`.

Without the panel change, VC3D main stores and exports these channels but does not show them in that panel.

## Why ink-sdk maps need placing

ink-sdk (LimeGS and pscamillo, October prize) runs many ink models on one segment. A map from a mesh run is
not on the point grid as written:

- **`--auto-crop`**: ink-sdk renders with it, so pixel (0, 0) sits at the bounding box of the valid points,
  not at grid (0, 0). `vc_render_tifxyz` prints the offset to stdout only. Neither the render's `.zattrs`
  (which keeps the cropped `canvas_size`) nor ink-sdk's `RENDER_RECEIPT.json` keeps it.
- **orientation**: with an umbilicus, ink-sdk transposes and flips the render afterwards.
- **scale**: a 2.4 µm source is pooled 4× (remainder trimmed), and `--roi` crops after pooling.

`ink_sdk_channel.py` undoes each step from the receipts and the mesh alone. It recomputes the crop with the
renderer's rule (`apps/src/vc_render_tifxyz.cpp`: bounding box of points whose x is finite and not −1,
times render scale ÷ mesh scale, floor at the low edge).

Trap: the mesh scale is stored as a float32 (`QuadSurface::_scale`, a `cv::Vec2f`), so 1 / 0.05 becomes
19.9999997 and a box starting at grid column 1 starts at pixel 19, not 20. Our first version was 1 px off
for this reason. It also refuses, rather than guesses, in these cases:

- the 8.64 → 9.362 µm resample path;
- renders not from CT level 0;
- a recomputed crop that differs from the render shape in the receipt;
- a map whose shape differs from the receipt.

The mesh is matched by the x/y/z hashes in the render receipt, so a render made in WSL and a run made on
Windows still pair up.

## Checks

All on public PHerc0841 data (9.366 µm 113 keV scan `20250821151531`, segments w00 and ag144). Reader V3 never
trained on PHerc0841: its [`train_config.json`](https://github.com/DomRusso2/reader-v3/blob/main/train_config.json)
names only PHerc0139, 0814, 1667 and Paris4.

**1. The crop the tool computes is the renderer's.** `vc_render_tifxyz --auto-crop` printed
`auto-crop: [4721×4181 from (19,19)]` for w00 and `[4681×4581 from (19,39)]` for ag144. The tool computes the
same for both. Against our full-canvas render of the same mesh, one layer of the auto-cropped render differs
by a mean of 0.002 grey levels at that offset, and by 5.5–8.2 at every ±1 px neighbour.
→ [`crop_truth.json`](../runs/ink_sdk_channel/crop_truth.json)

**2. Placement, on real geometry.** From our full-canvas Reader V3 map of w00, cropped as the renderer printed,
we built ink-sdk-shaped runs:

- native;
- all 8 transpose/flip combinations;
- an ROI;
- 4× pooling.

All placed back with 0 px different and nothing outside the box. Four bad receipts were refused.
→ [`test_placement_result.json`](../runs/ink_sdk_channel/test_placement_result.json),
[`placement_test.py`](../runs/ink_sdk_channel/placement_test.py)

These are synthetic runs. The real ink-sdk runs below had no transpose, flip, pooling or ROI.

**3. Real ink-sdk runs.** ink-sdk `2df3ab5` with its pinned 9 µm lane (villa `3ea17f54a`), Reader V3, checkpoint
sha256 = the profile's pin. → [`real_runs_summary.json`](../runs/ink_sdk_channel/real_runs_summary.json)

- *Surface-volume run* on our full-canvas render. Against the map segment_ink made from the same render
  through villa main: correlation 0.99994, max difference 3 grey levels, peak at zero shift.
- *Mesh + CT run.* ink-sdk rendered w00 itself, with `--auto-crop` and 17 layers. The CT was a local copy of
  only the 1,878 level-0 chunks within 24 voxels of the surface
  ([`fetch_ct_band.py`](../runs/ink_sdk_channel/fetch_ct_band.py)).
  - The tool placed the map at (19, 19). On the CT texture itself, ink-sdk's layer against our render placed
    there differs by 9.38 at (0, 0) and by ≥ 12.04 at every ±1 neighbour.
  - The maps correlate 0.916 with segment_ink's. For why, see the observation below.
    → [`real_mesh_run_compare.json`](../runs/ink_sdk_channel/real_mesh_run_compare.json)

**4. Store round trip.** Each set of channels was ingested and exported with the store tools from villa main,
built in villa's CI image. The exports are pixel-identical to what was written:

- segment_ink v2's three maps on w00 → [`v2_store_folder_roundtrip.json`](../runs/segment_ink/v2_store_folder_roundtrip.json),
  [`v2_store_target_roundtrip.json`](../runs/segment_ink/v2_store_target_roundtrip.json);
- the synthetic bridge channels → [`store_roundtrip_compare.json`](../runs/ink_sdk_channel/store_roundtrip_compare.json);
- the real mesh-run channels → [`real_mesh_store_roundtrip_compare.json`](../runs/ink_sdk_channel/real_mesh_store_roundtrip_compare.json).

Those runs (2026-11-06 and 2026-11-14) used the store before villa #2546 moved it to schema 22. On 2026-11-18
all of them were run again with the store tools of villa main `1386f072e`, in main's CI image: the three folder
round trips above, and the store mode (surface first, then `vc_object_ingest --surface-channel`). Every exported
channel is again pixel-identical to what was written, with the same pixel hashes as before.
→ [`store_recheck_main_1386f072e.json`](../runs/vc3d_ink_channel/store_recheck_main_1386f072e.json),
[`store_recheck.sh`](../runs/vc3d_ink_channel/store_recheck.sh)

**5. The panel.**

- *Automated test:* VC3D's own `test_ink_detection_overlay`, with two cases added for channels, passes 9 of
  9 in villa's CI image on villa main `97fb9336c` (2026-11-14), and again on the published branch (villa
  main `8e21d010f`) in the CI image main switched to on 2026-11-16 (2026-11-17), and once more with the same commit
  on villa main `1386f072e` (2026-11-18; no conflict).
  → [`test_ink_detection_overlay_main_97fb9336c.txt`](../runs/vc3d_ink_channel/test_ink_detection_overlay_main_97fb9336c.txt),
  [`test_ink_detection_overlay_main_8e21d010f.txt`](../runs/vc3d_ink_channel/test_ink_detection_overlay_main_8e21d010f.txt),
  [`test_ink_detection_overlay_main_1386f072e.txt`](../runs/vc3d_ink_channel/test_ink_detection_overlay_main_1386f072e.txt)
- *By hand:* a person checked it in VC3D on 2026-11-02, on the first version of the change (on villa
  main `fd97a4b60`), with the w00 folder imported:
  - built with the change, the panel offers `ink_ink9um_s43` and `ink_reader_v3` and draws them on the surface;
  - built from main, the same surface offers nothing (`None`, disabled).
  - Screenshots: [`runs/vc3d_ink_channel/`](../runs/vc3d_ink_channel) (`before_*`, `after_*`).
- The change has since been rebased four times over upstream edits to the same file. The by-hand check
  has not been repeated on the published version.

## Observation: Reader V3's map depends on where the canvas starts

This explains the 0.916 in check 3, and it is not the depth sampling. ink-sdk's layer i equals our 28-layer
render's layer 21.5 − i: the mean of our two neighbouring layers matches at ≈ 2.4 grey levels, either one
alone at ≈ 9.3. So the two inputs are half a layer apart in depth.

But a 17-layer input built from our render to match ink-sdk's depth gives:

| input | correlation with the mesh run |
|---|---|
| on the full canvas | 0.92 |
| cropped to the mesh run's canvas | 0.993 |

The same input on the full canvas and on the canvas shifted 19 px correlates 0.925 on the reading side (0.862
on the other). The differences are spread over the whole segment (median 2 grey levels, 99th percentile 57).
→ [`canvas_origin_check.json`](../runs/ink_sdk_channel/canvas_origin_check.json)

So two runs of the same model on the same segment can differ at this level just because one was auto-cropped.
One segment, one model; not investigated further.

## Limits

- One scroll (PHerc0841): two segments for the crop rule, one for everything else.
- Only ink-sdk's 9 µm lane was run for real. Pooled, transposed and ROI runs were checked on synthetic cases only.
- The panel change is on our fork, not in villa, and the by-hand check was on its first version.
- Nobody else has used these tools yet.

## Reproduce

```bash
# any checkpoint, rendered and inferred by segment_ink (see docs/32 for the render and model options)
python tools/segment_ink.py SEGMENT_DIR --scroll PHerc0841 \
    --volume 20250821151531-9.366um-1.2m-113keV-masked.zarr --checkpoint CKPT.pth --direction both
# ink-sdk runs (one folder or a battery folder) -> channels
python tools/ink_sdk_channel.py RUNS_DIR --maps all            # mesh runs: segment taken from the receipt
python tools/ink_sdk_channel.py RUN_DIR --segment SEGMENT_DIR  # surface-volume runs or WSL paths
# either: import <work>/<segment>-store in VC3D (File -> Stores -> Import from Folder),
# or add to an existing store with --target store --store objects.vcobj --ingest-cmd "vc_object_ingest"
```

The checks are scripted in [`runs/ink_sdk_channel/`](../runs/ink_sdk_channel). Paths in them are this machine's.

## Credits

- ink-sdk: LimeGS and pscamillo.
- Reader V3: KLAVIS (Domenico Russo).
- The object store and the Ink Detection panel: the VC3D maintainers (villa #2358, #2440, #2462, #2491).

AI disclosure: the tools, checks and this text were made with Claude (Anthropic, Opus 5.5) via Claude Code,
directed by the repository owner. The by-hand VC3D check was done by the owner.
