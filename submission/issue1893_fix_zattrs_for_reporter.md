<!--
⚠️ SUPERSEDED 10-02: no PR of ours (#1831 fixed #1893). Use issue1893_superseded_by_1831.md instead.
Draft reply on ScrollPrize/villa#1893 to Sartoshirelli, who handed the fix over (09-26) and offered
to check the three .zattrs against #1891. Post only after the PR is open, and put its number in the
first line. Source files: planning/2026-09-29_issue1893_build/results/{after,after_all}/.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

Fix is up as #NNNN. Here are the three cases you asked for, from that branch (axes and level-0 scale only; the rest of `.zattrs` is unchanged):

**1. local volume with `meta.json` (`voxelsize: 9.362`), no flags**
```json
{"axes": [{"name": "z", "type": "space", "unit": "micrometer"}, {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}],
 "scale": [9.362, 9.362, 9.362]}
```

**2. no local metadata, `--remote-url` to the public PHerc0139 volume, `-g 5`, no flags**
```json
{"axes": [{"name": "z", "type": "space", "unit": "micrometer"}, {"name": "y", "type": "space", "unit": "micrometer"}, {"name": "x", "type": "space", "unit": "micrometer"}],
 "scale": [299.584, 299.584, 299.584]}
```
(9.362 µm × 32 at level 5; before the fix this was `nanometer`, `32.0`.)

**3. no metadata anywhere, no flags**
```json
{"axes": [{"name": "z", "type": "space"}, {"name": "y", "type": "space"}, {"name": "x", "type": "space"}],
 "scale": [1.0, 1.0, 1.0]}
```

One change from your suggestion (2): I didn't read the input's OME `.zattrs`, because on the published volumes it has no unit. I checked five (PHerc0139, 0800, 1203, 1447, 1667): none has `meta.json`, all have a `metadata.json` scan record with the detector pixel size, and all have `.zattrs` with no `unit` and scale `1.0`. So the fix reads the scan record through the same resolver VC3D already uses (`VoxelSizeMetadata.cpp`), locally and over `--remote-url`. If there's a volume whose `.zattrs` does carry a unit and no scan record, I can add that as a last fallback.
