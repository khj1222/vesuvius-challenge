<!--
PR body draft — render_ink.py --scale-segmentation pass-through, against `main`.

  head:  khj1222:fix/render-ink-scale-segmentation-passthrough  (pushed to fork)
  base:  main (4b3c728)
  diff:  2 files  (spiral-fitting/render_ink.py, spiral-fitting/tests/test_render_ink.py)
  evidence: runs/render_scale_main/  (must be on origin/main before the PR is opened — the image is a raw URL)

⚠️ Open as DRAFT while non-draft PRs sit at the cap of 3 (#1608 closes 2026-09-19).
⚠️ USER SUPPLIES: the **Why / where this is useful** paragraph, in their own words (CONTRIBUTING).
⚠️ The checkbox stays UNTICKED unless the user reproduces the render or runs the tests themselves.
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** `render_ink.py` can now be told that a fitted mesh lives in a coarser frame than the ink volume, so the renderer samples the right voxels instead of writing a black strip and exiting 0.

**One real example:** Starting with the public PHerc. Paris 4 verified patch `0000_w010_spliced_flatboi_sel_20260611_234312_1` and the public ink volume `20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr`, I rendered the same mesh twice with the published `vc_render_tifxyz` image, identical settings, changing only `--scale-segmentation`: at 1 (what `render_ink.py` does today) all five slices are entirely zero and the run exits 0; at 4 (the level-2 → level-0 factor from the metadata) every slice reads 57,034–57,071 nonzero pixels of 69,000 with a maximum of 252.

**Before:** `render_ink.py` exposes `--scale` and `--group-idx` but has no way to say the mesh is in a different frame, so the only route to the renderer's existing `--scale-segmentation` was a wrapper binary passed as `--vc-render-bin` (#1660). A mesh that samples nowhere in the volume produced a normal-looking run with `p95=0.0` in one line of output and `total_fg_pixels = 0` downstream.

**After this PR:** `--scale-segmentation FLOAT` (default `1.0`, shown in `--help`) is validated to be finite and positive before anything is rendered, and forwarded unchanged to every `vc_render_tifxyz` call. Nothing changes for anyone who does not pass it. The option's help says where the number must come from: a mesh-to-volume frame scale established from metadata, independent of `--scale`, which sets output density. `render_ink.py` does not try to infer it.

**Proof:**

![same public mesh and volume, segmentation scale 1 vs 4](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/render_scale_main/real_before_after.png)

*Both renders use `render_ink.py`'s own display transform (slice max, then divide by p95 when p95 > 0). Left: scale 1, every pixel zero. Right: scale 4. Look at the renderer logs for the two runs — same inputs, `render_scale` 0.125 vs 0.5, exit 0 both times.*

| | scale 1 (today) | scale 4 |
|---|---:|---:|
| exit code | 0 | 0 |
| per-slice nonzero pixels | 0 / 4,255 | 57,034–57,071 / 69,000 |
| per-slice max | 0 | 251–252 |
| max-composite p95 | 0 | 2 |

Three surface cells fixed in advance (first, centre, last) show what each arm actually sampled at pyramid level 1: the baseline reads around (2286, 2361, 7798) and gets 0; the corrected arm reads around (9145, 9443, 31191) and gets 1. Logs, commands, the cell table and the test run: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/render_scale_main

**Why / where this is useful:**

<!-- USER WRITES THIS. -->

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

**Tested commit.** `main` at `4b3c728` (2026-09-15); `render_ink.py` is unchanged since the `--remote-url` pass-through in #1627.

**Where the 4 comes from, fixed before rendering.** The reporter's own scroll JSON says `voxel_size_um: 9.6`; the public lasagna input store `las_008_surf_sdt.ome.zarr` says `working_voxel_um: 9.6` with source CT group 2; the official `render_banner_spiral_gif.py` declares `MESH_ZARR_LEVEL = 2` for the same `20260411134726` scan; and the base CT and the ink volume both declare level-0 shape `[75784, 32693, 32693]` with 2× steps per level. Level-2 mesh coordinates map to level 0 by ×4. Since both renders read group 1, the renderer's `sample = mesh × scale_segmentation × ds_scale` gives an effective factor of 0.5 (baseline) and 2 (corrected), which is also why the output rasters differ in size (37×115 vs 150×460).

**Why no auto-detection.** A synthetic 64³ volume coded as `1 + ((3x + 5y + 7z + xy) mod 251)`, with the same surface written in a coarse and an identity frame, confirms the contract: `coarse + 4` and `identity + 1` are byte-identical and match a direct trilinear evaluation at 42/42 supported cells; `coarse + 1` changes 42/42 and `identity + 4` changes 41/42. But all four arms are nonzero on their support, and on the real volume scale 2 also reads mostly nonzero (#1660's table). Bounds, nonzero fraction and brightness cannot tell a right frame from a wrong one, so the value has to be supplied from metadata. This PR only makes supplying it possible.

**Tests** (added to `spiral-fitting/tests/test_render_ink.py`, same stubbing style as the existing test): the strip path is driven with concat, save and the renderer stubbed; explicit `4` arrives in the renderer command as `4.0` next to an untouched `--scale 0.25`; the default arrives as `1.0`; `0`, `-1`, `nan`, `inf` fail with the parameter error and no renderer call.

**Scope and limitations.** (1) This is a public-substitute reproduction: the reporter's exact fitted `w010–019` concat is not published (their repository has the scroll JSON, not the mesh), so the mechanism is reproduced on a 46×15 public patch from the same surface family, not on their strip. (2) The tests check the command `render_ink.py` builds; the full concat/flatten pipeline was not re-run through the patched script. (3) Whether the intended workflow is instead to always supply an ink volume in the fit's frame is the maintainers' call, as #1660 asks; this option does not take a position on that, it only removes the need for a wrapper binary when the frames differ.

**Relation to #1728.** That PR warns when a strip is entirely black and touches the strip-writing block; this one touches the option block and the command list. They do not overlap: one makes the failure visible, the other gives the user a way to correct it.

**Disclosure:** most of the work in this project, including this reproduction, the change and the tests, is done with an AI coding assistant. The problem, the data and the decisions are mine; the black strip above is one my project reproduced while checking whether published spiral patches could be rendered against the published ink volume.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
