<!--
GitHub issue draft for LimeGS/ink-sdk (2026-11-14). POSTED by the user as LimeGS/ink-sdk#18
(2026-11-14T02:07:50Z, khj1222); checked via the API the same minute: title equal, body identical (2,549 chars).
  where: https://github.com/LimeGS/ink-sdk/issues/new  (no issue template; no CONTRIBUTING)
  title (paste into the title field):
    Write maps back into VC3D as object-store ink channels?
  paste: only the text below the --- line.

Why an issue, not a PR: ink-sdk says "Inference only"; issue #17 (dlescanogithub, 11-14) set the
pattern of asking first. Short on purpose.

Facts behind each sentence (checked 2026-11-14):
  - ink-sdk 2df3ab5 writes probability*.npy + INK_SDK_RECEIPT.json; no VC3D/object-store output (README, src).
  - renderer passes --auto-crop (src/ink_sdk/renderers/vc_render_tifxyz.py); the renderer prints
    "auto-crop: [W×H from (x,y)]" with logPrintf(stdout) (villa main 97fb9336c apps/src/vc_render_tifxyz.cpp ~1401);
    ink-sdk keeps only stderr_tail in RENDER_RECEIPT.json.
  - 0841 w00: renderer printed "auto-crop: [4721×4181 from (19,19)]"; ag144 "(19,39)"; bridge computes both.
  - float32: QuadSurface::_scale is cv::Vec2f (QuadSurface.hpp:453); 1/float32(0.05) = 19.99999970 → floor(1·sx) = 19
    (first version of our tool was 1 px off). An earlier version of this draft said 19.99999997 — wrong, fixed 11-14.
  - store: vc_object_store/README.md:82 `--surface-channel SURFACE_UUID ink /data/ink_prediction.tif`;
    docs/ingestion.md:79 "whole multiple of the grid (for example ink at 20 pixels per grid step)";
    ArrayLayout.hpp:48 rejects other shapes. "20 px" for a --scale 1 render of a 0.05 mesh = our measurement (4220 = 211·20).
  - renderer .zattrs (writeZarrAttrs, main ~651-688) keeps canvas_size (the cropped size) but not the crop origin;
    RENDER_RECEIPT.json keys checked on the real run: no origin (`render_crop` = null is the ROI field).
  - real run: WSL `ink-sdk render` (local partial CT) + Windows `ink-sdk infer --surface-volume` (Reader V3),
    bridge crop (19,19,4181,4721); CT texture check mean|diff| 9.38 at (0,0) vs ≥12.04 at ±1; store round trip
    pixel-identical. planning/2026-11-14_ink_sdk_bridge/README.md (private) + tools/ink_sdk_channel.py (public).
  - VC3D main: vc_object_store README documents --surface-channel; InkDetectionOverlayController lists only
    catalog files (our I1 patch is local; question to sean posted 11-04 on #robots, no answer yet).
  - half layer: ink-sdk layer i = our 28-layer render's layer 21.5 − i (mean of our two neighbours matches at
    mean|diff| ≈ 2.4 vs ≈ 9.3 for either alone and ≈ 25 one further, i = 0/4/8/12/16); villa infer takes our
    layers 6–22. Forward/reverse swap: the order is reversed (we render --flip-normals).
  - WHY the maps correlate 0.92 (checked 11-14, results/halfshift_check.json + canvas test): NOT the half layer.
    Depth-matched input on the full canvas: still 0.92/0.86. Same depth-matched input on the CROPPED canvas
    (same as ink-sdk's): 0.993 with the mesh run. Same input, full vs cropped canvas: 0.925 (reverse) / 0.862
    (forward); differences spread everywhere (median 2 grey, p99 57), somewhat larger near 192-px tile phase.
    So the 19-px auto-crop shift of the tile grid dominates. An earlier version of this draft blamed the half layer.
  - Reader V3 on 0841 w00 is held out: DomRusso2/reader-v3 train_config.json (only version 95d12b4b1a, 10-19)
    names pherc0139/0814/1667/Paris4 and no 0841; the HF card (aee1d64) calls 0841 w00 "never-seen".
  - transpose/flips, pooling, ROI: checked on synthetic run folders only (real geometry, our maps); the real
    ink-sdk runs had none of them.
-->

---

Hi LimeGS and pscamillo, congratulations on the October prize.

Before opening anything, I wanted to ask whether this fits the SDK or should stay outside it.

VC3D's object store keeps ink as a surface channel (`vc_object_ingest --surface-channel SURFACE_UUID ink /data/ink_prediction.tif`): an image whose sides are whole multiples of the tifxyz grid. A `--scale 1` render of a scale-0.05 mesh gives 20 px per grid step. A map from a mesh run of `ink-sdk infer` is not on that grid as written. Because the render uses `--auto-crop`, pixel (0, 0) sits at the valid-point bounding box. `vc_render_tifxyz` prints that offset only to stdout (`auto-crop: [4721×4181 from (19,19)]` on PHerc0841 w00); neither its `.zattrs` nor `RENDER_RECEIPT.json` keeps it.

I wrote a small converter outside the SDK: [`tools/ink_sdk_channel.py`](https://github.com/khj1222/vesuvius-challenge/blob/main/tools/ink_sdk_channel.py). It recomputes the crop from the mesh using the renderer's rule, undoes the umbilicus transpose/flips, pooling and ROI (those three checked on synthetic cases only), and writes one `ink_<profile>` channel per map. On PHerc0841 w00, a real `ink-sdk render` + `infer` run (Reader V3, held out for that model) lands at (19, 19), and the object-store round trip is pixel-identical. One trap if you do this yourselves: the tifxyz scale is a float32, so 1/float32(0.05) = 19.9999997 and the crop origin floors to 19, not 20.

Two possible shapes, either of which I'm happy to PR:
1. Receipt only: keep the renderer's auto-crop rectangle in `RENDER_RECEIPT.json`, so any downstream tool can place a map without recomputing it.
2. An `ink-sdk export-vc3d RUN_DIR...` command that writes the channels (an importable store folder, or through `vc_object_ingest`).

Or neither, if you'd rather keep the SDK inference-only. Caveat: VC3D main stores and exports these channels, but its Ink Detection panel doesn't list them yet. I have a local patch for that and have asked the VC3D maintainers.

Side observation, not a request: on w00, Reader V3's map depends noticeably on where the canvas starts. The same input run on the full canvas and on the auto-cropped one (shifted 19 px) correlates only 0.93 on the reading side. The differences are spread over the whole segment (median 2 grey levels, 99th percentile 57). So two runs of the same model on the same segment can differ just because one was auto-cropped.

AI disclosure: the converter, the checks and this text were made with Claude (Anthropic, Opus 5.5) via Claude Code; I decided to offer it.
