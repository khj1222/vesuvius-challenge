<!--
PR body draft — #1893 fix, written to villa's pull_request_template.md.

  head:  khj1222:fix/render-voxel-unit-from-metadata  (ca4a5bd68, NOT pushed yet)
  base:  main (542c6deac)
  diff:  5 files, +267 −32

⚠️ SUPERSEDED 10-02: #1831 (merged 09-30) fixed #1893 first — do NOT open. Was: open only after 10-03 16:00 KST, when #1703/#1705 close and a non-draft slot frees.
⚠️ The user supplies the "Why / where this is useful" line (CONTRIBUTING: human-written commentary).
⚠️ Tick the checkbox only if the user runs the proof themselves.
⚠️ Keep it short: jrudolph closed #1898 on 09-28 for being unclear and not self-written.
   Evidence: planning/2026-09-29_issue1893_build/ (local; publish the key files under runs/ before opening).

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** `vc_render_tifxyz --zarr-output` now records the voxel size in the unit it is actually in, including for remote volumes, instead of calling micrometres nanometres.

**One real example:** Starting with the public PHerc0139 volume (`20250728140407-9.362um-1.2m-113keV-masked.zarr`, over `--remote-url`) and segment w040, I rendered one slice at `-g 5` with no voxel flags, and the output `.zattrs` now says `micrometer`, scale `299.584` (9.362 µm × 32).

**Before:** the same render wrote `nanometer`, scale `32.0`. The renderer did not read the `metadata.json` scan record the published volumes carry, so every remote render fell back to "1.0", and it labelled any size it did find with `--voxel-unit`'s default, `nanometer`, although volume metadata is in micrometres (`VoxelSizeMetadata.cpp`). Reported in #1893.

**After this PR:**
- size from metadata is written as `micrometer`; `--voxel-unit` converts it instead of relabelling it
- after a local `meta.json`, the size comes from the core resolver (`resolveLocalStoreVoxelSize`) and then from the remote volume's `voxelSize()`, which `Volume::NewFromUrl` already reads
- with no size known, scale stays `1.0` and the axes carry no unit
- `--voxel-size` alone still means nanometres, and TIFF resolution is unchanged in every case

**Proof:** `.zattrs` axes unit and level-0 scale, same binary before and after, built in the CI image (`vc3d-deps/linux:sha-0c371b1d…`):

| input | flags | before | after |
|---|---|---|---|
| PHerc0139 remote, `-g 5` | none | nanometer, 32.0 | micrometer, 299.584 |
| PHerc0139 remote, `-g 5` | `--voxel-unit nanometer` | nanometer, 32.0 | nanometer, 299584 |
| local, `meta.json` voxelsize 9.362 | none | nanometer, 9.362 | micrometer, 9.362 |
| local, `metadata.json` scan record | none | nanometer, 1.0 | micrometer, 9.362 |
| local, no metadata | none | nanometer, 1.0 | *(no unit)*, 1.0 |
| local, no metadata | `--voxel-size 9.362` | nanometer, 9.362 | nanometer, 9.362 |

TIFF `XResolution` for meta default / meta + `nanometer` / CLI size alone / CLI size + `micrometer`: identical before and after (2713.10, 2713.10, 2713095.5, 2713.10).

New `core/test/test_render_tifxyz_voxel_unit.py` (stdlib only, six cases, one over a local HTTP server): 6/6 pass on this branch, 5/6 fail on main (the passing one is the `--voxel-size` default, which should not change). `test_render_tifxyz_logging.py` and `test_render_fetch_failure.py` still pass.

**Why / where this is useful:** <!-- USER WRITES THIS LINE -->

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

**Disclosure:** most of the work in this project, including this fix and its tests, is done with an AI coding assistant. The problem, the data and the decisions are mine.

Closes #1893.

## Details

- Tested commit: this branch on `main` 542c6deac, built with the CI `cli-compile` flags (clang, QuickBuild, `-DVC_QUICKBUILD_OPT_LEVEL=0`) in `ghcr.io/scrollprize/vc3d-deps/linux:sha-0c371b1d472c5281b703d65517e980d945da693f`.
- Five public volumes (PHerc0139, 0800, 1203, 1447, 1667) were checked: none has `meta.json`, all have `metadata.json` with the detector pixel size, and their OME `.zattrs` declares no unit and scale 1.0. That is why this reads the scan record and not the input `.zattrs`.
- An unknown `--voxel-unit` together with a metadata size now fails with `unsupported --voxel-unit`, the same error `--voxel-size` already gave.
- The test is added to ctest and to the `cli-compile` job next to the two existing renderer tests. Configured with `-DVC_TESTING=ON` it registers as a ctest and all three renderer tests pass under `ctest`.
- Also checked on real data: a full-resolution (`-g 0`) 256×256 crop over `--remote-url` writes micrometer 9.362; with `#vc-base-scale=2` and `-g 3` it writes 37.448 µm per logical voxel and a level-0 scale of 299.584, the same as `-g 5` without the selector; a local store holding the published `metadata.json` verbatim writes micrometer 9.362.
- A `meta.json` with an invalid `voxelsize` is warned about and treated as no size. A `metadata.json` next to it is not consulted, because the core resolver and `Volume` both let `meta.json` take precedence; this keeps the renderer consistent with them.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
