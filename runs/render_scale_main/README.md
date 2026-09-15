# `render_ink.py --scale-segmentation`, against `main`

`spiral-fitting/render_ink.py` builds the `vc_render_tifxyz` command for each
strip and assumes the fitted mesh is already in the ink volume's level-0 frame.
When the mesh lives in a coarser working lattice (the spiral inputs are 9.6 µm,
the published Paris 4 ink volume is 2.4 µm at level 0), the renderer samples the
wrong coordinates, writes an all-black strip and exits 0 — villa
[#1660](https://github.com/ScrollPrize/villa/issues/1660). The renderer already
has `--scale-segmentation` for this; `render_ink.py` had no way to pass it.

Branch: `khj1222:fix/render-ink-scale-segmentation-passthrough`, one commit on
top of `main` (`4b3c728`, 2026-09-15). 2 files: the option, its validation, the
one-line pass-through, and three tests. Patch: `patch_render_ink_scale_segmentation.patch`.

## Files

| file | what |
|---|---|
| `real_before_after.png` | The same public mesh rendered against the same public ink volume by the official renderer image, once with segmentation scale 1 (what `render_ink.py` does today) and once with 4 (from metadata). Left is entirely zero; right is not. |
| `render_baseline_scale1.log`, `render_corrected_scale4.log` | The renderer's own logs for those two runs: identical inputs, `render_scale` 0.125 vs 0.5, exit 0 both times. |
| `render_commands.sh` | The exact two commands, plus how the four mesh files were fetched. |
| `real_cell_samples.csv` | Three surface cells fixed in advance (first, centre, last): the level-1 coordinate each arm actually sampled and the value it read. |
| `metrics.json` | Per-slice statistics for both arms, the coordinate chain that fixed the scale at 4 before rendering, the synthetic coordinate-coded control, and the source URLs. |
| `renderer_image.txt` | Digest of the renderer image used. |
| `tests.txt` | The upstream test file with the three new tests, run on Windows; the one failure is a pre-existing POSIX-path assertion unrelated to this change (fails identically on unpatched `main`). |

## What was measured

Mesh: the public verified patch
`spiral/PHercParis4/verified_patches/0000_w010_spliced_flatboi_sel_20260611_234312_1`
(46×15 tifxyz). Volume: the public ink prediction
`PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr`,
streamed from S3. Renderer: `ghcr.io/scrollprize/villa/volume-cartographer`
at digest `bad516f6…` (the published image). Settings identical except the scale.

| | scale 1 (today) | scale 4 |
|---|---:|---:|
| exit code | 0 | 0 |
| TIFFs written | 5 | 5 |
| per-slice nonzero pixels | 0 / 4,255 | 57,034–57,071 / 69,000 |
| per-slice max | 0 | 251–252 |
| max-composite p95 | 0 | 2 |

The 4 was not chosen by looking at brightness. It comes from metadata that agree
with each other: the reporter's own scroll JSON says `voxel_size_um: 9.6`; the
public lasagna input store says `working_voxel_um: 9.6` with source CT group 2;
the official banner script declares `MESH_ZARR_LEVEL = 2` for the same scan;
and the base CT and the ink volume both declare level-0 shape
`[75784, 32693, 32693]` with 2× pyramid steps. Level-2 mesh coordinates therefore
map to level 0 by ×4. Because both renders read pyramid group 1, the effective
sample-coordinate factor is 0.5 for the baseline and 2 for the corrected arm.

A synthetic coordinate-coded 64³ volume with the same surface written in both
frames confirms the contract independently of the real volume: `coarse + 4` and
`identity + 1` are byte-identical (72/72 pixels) and match a direct trilinear
evaluation at 42/42 supported cells, while `coarse + 1` changes 42/42 and
`identity + 4` changes 41/42. All four arms are nonzero on their support, which is
why the PR does **not** try to infer the scale from brightness or nonzero
fraction: those cannot tell a correct frame from a wrong one.

## Scope, stated plainly

- This is a **public-substitute reproduction**. The reporter's exact fitted
  `w010–019` mesh is not published anywhere we could find (their repository at
  `c4f7f6c` has the scroll JSON but no mesh body); the mechanism is reproduced on
  a public patch from the same surface family.
- The tests stub the renderer and check the command `render_ink.py` builds; the
  full concat/flatten path was not re-run through the patched script.
- [#1728](https://github.com/ScrollPrize/villa/pull/1728) (warn when a strip is
  entirely black) touches the strip-writing block; this change touches the option
  block and the command list. They do not overlap and are complementary: one
  makes the failure visible, the other gives the user a way to fix it.
