# November 2026 Progress Prize — submission S1 (tool) package

**Form:** https://docs.google.com/forms/d/e/1FAIpQLSeB6MC_--4UCCEGc3zalX57-uE4puRcE_vJoYJCrEt4uYaaaw/viewform
("November 2026 Progress Prizes", taken from https://scrollprize.org/prizes; the form URL is round-specific.)
**Deadline:** 2026-11-30 23:59 Pacific = 2026-12-01 16:59 KST.
**Status:** ready (2026-11-17). Not submitted yet: the user will submit S1 and S2 together shortly before the deadline;
re-check links and the form right before.

This is the first of two November submissions, split as villa #2102 asks (new methods, models and
measurements separately). S2, the measurements (docs/33–36), is submitted separately.

Final pre-submit check, 2026-11-17: the VC3D panel change is published on the fork
(`khj1222/villa` `feat/vc3d-ink-surface-channel` = `bb9ec5e2c` on villa main `8e21d010f`; no answer from the
VC3D maintainers by 2026-11-16, so no villa pull request); docs/37 updated to say so; field 5 read through;
all 12 field-4/5 links other than Discord returned HTTP 200.

Update 2026-11-18: every store round trip and the panel test rerun on villa main `1386f072e` (store schema 22,
after villa #2546): all exported channels pixel-identical, 9 of 9 (docs/37 checks 4 and 5). Field 5's Store and
Panel lines say so; field 5 read through again; all 12 links 200 again. Field 4 unchanged.

Update 2026-11-21: the VC3D app check repeated on the published change (its patch on villa main
`c8f3ba453`) and on that main without it, driven by the AI assistant at the user's request (agent bridge +
xdotool on a virtual display; the user's 11-02 check was by hand). Same result as 11-02: with the change the
panel offers and draws `ink_ink9um_s43` and `ink_reader_v3`; without it, `None`, disabled. docs/37 check 5,
limits and disclosure updated; field 5's Panel line now says so instead of "the hand check was not
repeated". Field 5 read through again. Field 4 unchanged.

## Form answers

**Your full name**
```
Hyojun Kwon
```

**Team description**
```
Individual submission — no team.
```

**Discord display name**
```
jamiolrangmalrang4936
```

**4. URL of your open source / publicly available contribution**
```
https://github.com/khj1222/vesuvius-challenge/blob/main/docs/37_ink_maps_as_vc3d_channels.md
  Any ink checkpoint on a tifxyz segment, written as an ink_* surface channel in VC3D's object store (segment_ink v2): https://github.com/khj1222/vesuvius-challenge/blob/main/tools/segment_ink.py
  ink-sdk runs (one model or a whole battery) placed on the segment's point grid as ink_* channels: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/ink_sdk_channel.py
  Offered to the ink-sdk authors: https://github.com/LimeGS/ink-sdk/issues/18
  VC3D Ink Detection panel lists a surface's ink / ink_* channels (branch on my fork; asked the VC3D maintainers first, no answer): https://github.com/khj1222/villa/tree/feat/vc3d-ink-surface-channel
  Checks and raw results: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/ink_sdk_channel , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/vc3d_ink_channel , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/segment_ink
  First version, with Reader V3 vs ink_9um on three held-out PHerc0841 segments: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/32_segment_ink_vc3d.md
Discord #robots thread: https://discord.com/channels/1079907749569237093/1564220086158495754
Data used: PHerc0841 w00, ag144, ag174 (9.366 µm scan 20250821151531, tifxyz meshes, open ink labels); placement also on PHerc0814 20250925212701 and PHerc0139 w045
Models used: KLAVIS Reader V3 (https://huggingface.co/domenicor046/reader-v3), ink_9um (https://huggingface.co/scrollprize/ink_9um), through segment_ink and through ink-sdk (https://github.com/LimeGS/ink-sdk)
```

**5. What is your contribution?**
```
A way to look at any ink model's prediction on a segment inside VC3D, kept working through VC3D's move
to an object store, and extended to ink-sdk, the tool that runs a battery of community ink models on a
segment.

(1) Which scroll data

PHerc0841 segments w00, ag144 and ag174 (meshes on the 9.366 µm 113 keV scan 20250821151531), scored
against the open human ink labels; neither model compared was trained on PHerc0841. Placement was also
checked on PHerc0814 20250925212701 and PHerc0139 w045. The object-store path, the ink-sdk runs and the
VC3D panel were checked on PHerc0841 w00; the crop rule also on ag144.

(2) How it raises the chance of reading these scrolls or others

Whoever traces a new segment, or wants to try another checkpoint on an old one, has to see the
prediction on the geometry to judge it. Since villa #2358 (10-29) VC3D keeps segments in an object store
and its Ink Detection panel lists only the maps the catalog publishes, so a locally made map had no
supported way onto a surface. The store already documents the place for one: a surface channel, an
image at a whole multiple of the point grid.

segment_ink is one command: render the mesh with VC3D's own vc_render_tifxyz, run villa's unmodified
ink inference with any checkpoint it loads, and write the map as an ink_<name> channel (an importable
tifxyz folder, or into an existing store). Swapping the checkpoint is one flag. On the three PHerc0841
segments, Reader V3 against ink_9um gives AUC 0.916 / 0.834 / 0.853 against 0.772 / 0.681 / 0.756; on
w00 this repeats a gap KLAVIS published (0.881 against 0.722). The layer direction matters more than the
checkpoint (reversed, both fall to 0.54–0.62), so the tool writes both directions.

ink-sdk (LimeGS, pscamillo) already runs many community models on a segment but stops at numpy files.
ink_sdk_channel.py turns its runs, one model or a whole battery, into ink_<profile> channels on the same
surface, so the models can be switched in VC3D's panel. An ink-sdk map is not on the point grid as
written: its render is auto-cropped to the valid points, and the renderer prints that offset only to
stdout. The tool recomputes it with the renderer's own rule and undoes ink-sdk's transpose/flips,
pooling and ROI; it refuses what it cannot place exactly. I offered it to the ink-sdk authors
(LimeGS/ink-sdk#18).

(3) What it enables that was not possible before

After #2358, a map from a new checkpoint, or from an ink-sdk battery, could not be shown on a VC3D
surface. Now any of them lands on the surface as a channel, with identical pixels after import and
export. The last piece is the panel listing those channels: a change of +147/−18 lines in three files
makes it list a surface's ink and ink_* channels. I asked the VC3D maintainers on Discord before opening
a pull request and had no answer by 11-16, so it is on my fork, not in villa. Built with that change,
the panel lists the ink_9um and Reader V3 maps on the imported w00 surface and draws them; built from
main, the same surface offers nothing to choose.

(4) Evidence (all in docs/37, raw files linked there)

- Crop rule: the renderer printed "auto-crop: [4721×4181 from (19,19)]" for w00 and "(19,39)" for ag144;
  the tool computes the same. One layer of the auto-cropped render matches our full render at that
  offset to a mean of 0.002 grey levels, against 5.5–8.2 at every ±1 px neighbour. Trap found on the way:
  the mesh scale is a float32, so 1/0.05 comes out as 19.9999997 and the crop starts at pixel 19, not 20.
- Placement: synthetic ink-sdk runs built from a real map on real geometry (native, all 8
  transpose/flip combinations, an ROI, 4× pooling) are placed back with 0 px different; 4 bad receipts
  are refused.
- Real ink-sdk runs (its pinned Reader V3 lane): on our render, correlation 0.99994 with segment_ink's map
  (max 3 grey levels); from the mesh and a local copy of the CT around the surface, ink-sdk's own
  auto-cropped render placed at (19,19), confirmed on the CT texture (9.38 at (0,0), ≥ 12.04 at ±1).
- Store: every set of channels (segment_ink's three maps, the synthetic and the real ink-sdk channels)
  ingested and exported with the store tools from villa main returns identical pixels; all rerun on 11-18
  on villa main 1386f072e, after the store moved to schema 22 (#2546), with the same pixel hashes.
- Panel: VC3D's own test_ink_detection_overlay with two channel cases added, 9 of 9 in villa's CI image
  on villa main 97fb9336c (11-14), and again on the published branch (villa main 8e21d010f) in main's new
  CI image (11-17) and on villa main 1386f072e (11-18). Before and after checked in the VC3D app: by
  hand on 11-02 on the first version of the change, and again on 11-21 with the published change on
  villa main c8f3ba453 (that run driven by the AI assistant through VC3D's agent bridge and xdotool, at
  my request); screenshots in runs/vc3d_ink_channel.
- Side finding: Reader V3's map on w00 depends on where the canvas starts. The same input on the full
  and on the 19-px auto-cropped canvas correlates 0.925 on the reading side (median difference 2 grey
  levels, 99th percentile 57). That is most of why ink-sdk's mesh run and segment_ink agree at 0.92, not
  ~1: I first blamed a half-layer depth offset, but a depth-matched input agrees at 0.993 only on the same
  canvas.

Limits: one scroll; only ink-sdk's 9 µm lane run for real (pooled, transposed and ROI runs checked on
synthetic cases); the panel change is on my fork, not in villa; the rules for each check were in my own
notes, not committed before the run, so this is a checked tool, not a pre-registered test.

Integration: reads the open data directly (OME-Zarr scans, tifxyz meshes) and writes what VC3D's object
store reads (tifxyz folders, surface channels). Rendering and inference are villa's own vc_render_tifxyz
and ink inference, or ink-sdk unchanged. MIT-licensed.
```

**Terms and Conditions:** read and accepted by the user on the form.

## Checklist

- [x] Re-check the live form on https://scrollprize.org/prizes (2026-11-14: same five questions as October).
- [x] Read field 5 straight through; check every link (2026-11-17, again 2026-11-18 and 2026-11-21).
- [x] Re-check the form and links right before submitting (2026-11-21, after pushing `e6faf55`: prizes page
  links the same form, "November 2026 Progress Prizes", same five questions + Terms; field 4 and 5 hashes as
  below; all 12 links 200, plus the 7 new evidence files under runs/vc3d_ink_channel).
- [ ] Paste the fenced answers, accept the Terms, and submit (user).
- [ ] Compare the submitted text with this file and mark it submitted (receipt e-mail).

## Field hashes

Calculated over each fenced block body with LF line endings and exactly one trailing newline:

- field 4 — 1,637 chars, `3e9d0677becc2c6613d04bd483872b2912192babbd79a19fbfe199629e927886`
- field 5 — 5,905 chars, `452a2dc319a4657039bab8966df8b71a8d69d822831018b0b53595663d09d0b8` (2026-11-21;
  the 11-18 text was 5,839 chars, `d8c3bd78…`; the 11-17 text 5,685 chars, `5fef8569…`)

If either field is edited before submitting, recompute these against the actual pasted text.
