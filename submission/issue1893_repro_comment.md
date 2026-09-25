<!-- Draft comment for ScrollPrize/villa#1893 (Sartoshirelli, 2026-09-25). Not posted.
     Evidence: planning/2026-09-26_issue1893/ (local). Paste only what is below the line. -->

---

I have a build, so I ran it. This reproduces as you describe from the source.

**Build:** the released Linux AppImage `VC3D-f07d33b-2026-09-19-linux-x86_64`, run in WSL2 (Ubuntu 24.04). The voxel-size block in `vc_render_tifxyz.cpp` is identical at `f07d33b`, at your `d285029a` and at current `main` (`557df7c`).

**Input:** a synthetic 64³ uint8 OME-Zarr volume whose `meta.json` says `"voxelsize": 9.362` (its own `.zattrs` declares `micrometer`, 9.362), and a flat 32×32 tifxyz. `-g 0 --scale 1 --num-slices 3 --zarr-output`, no other flags unless listed:

| run | log line | output `.zattrs` unit | L0 scale |
|---|---|---|---|
| no voxel flags | `Voxel size (from volume metadata): 9.362 nanometer` | `nanometer` | `[9.362, 9.362, 9.362]` |
| `--voxel-unit micrometer` | `... 9.362 micrometer` | `micrometer` | `[9.362, 9.362, 9.362]` |
| `--voxel-size 9.362 --voxel-unit micrometer` | `Voxel size (from CLI): 9.362 micrometer` | `micrometer` | `[9.362, 9.362, 9.362]` |
| same volume without `meta.json`, no flags | `Voxel size: 1.0 (no metadata found; override with --voxel-size)` | `nanometer` | `[1.0, 1.0, 1.0]` |

So the default path labels a micrometre value as nanometres, and `--voxel-unit micrometer` alone is enough to get it right.

The last row is the one most renders actually hit. With `--remote-url`, `-v` is usually a local cache directory with no `meta.json`, so the output says 1 nm per voxel. Every render I have on disk made this way carries `nanometer` / `[1.0, 1.0, 1.0]`: public PHerc0800, PHerc1203, PHerc1447 and PHerc0139 segments, made with three different builds in August and September. The input volume's own OME `.zattrs` (which does say micrometer, 9.362) is never consulted.

I haven't checked the TIFF path at runtime. From the source, when the size comes from metadata the DPI branch treats the value as micrometres, so the TIFF resolution would be right while the Zarr attrs are wrong.

Are you planning to send the fix yourself? If not, I'm happy to. The smallest change I can see is to write `micrometer` when the size came from `meta.json` and `--voxel-unit` was not given. That does not cover the no-metadata case, which would still need either the input's OME scale or no unit at all.
