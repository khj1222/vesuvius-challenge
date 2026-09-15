# Copy direction priors through TTA, against `main`

Neural Copy (`infer_rowcol_triplet_wraps`) feeds the model 8 channels: CT, the
conditioning mask, and two ZYX direction priors (`+n` in 2:5, `-n` in 5:8).
Test-time augmentation is on by default. `run_model_tta` flips or axis-permutes
all eight channels spatially and, on the way back, negates or reorders the
**output** displacement components so the variants agree in the original frame.
The **input** prior components were left alone, so after a z flip the prior
still said "+z" inside a volume that now runs the other way. Each variant was
answering a different question and the merge averaged the answers.

Branch: `khj1222:fix/tta-transform-input-direction-priors`, one commit on top of
`main` (`4b3c728`, 2026-09-15). 3 files, +188 −2: the transform helper, the
call-site gate, and 13 tests. Patch: `patch_tta_main_input_direction_priors.patch`.

## Files

| file | what |
|---|---|
| `tta_shot.py`, `tta_console.txt`, `tta_console.png` | main vs this branch on a model that returns its own input priors. Constant prior through mirror TTA on main merges to (0, 0, 0); after the change it comes back unchanged (max error 6e-8). Random priors: mirror 6.08 → 3.6e-7, rotate3 2.45 → 2.4e-7. The legacy call on the new tree is bit-identical to main. CPU, no weights. |
| `real_data_paris4_cubes.png`, `real_data_ab.json` | The real-data A/B: six 256³ CT cubes of PHerc. Paris 4 with manual sheet-instance labels ([volumetric-instance-labels](https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumetric-instance-labels/README.txt)), released `scrollprize/copy_displacement_latest` at revision `4da5323`, default mirror TTA (8 variants, `vector_geomedian`, micro-batch 1), 11 manually labelled start surfaces copied to their neighbouring sheet. The only difference between the two arms is the input-prior transport. Numbers in the JSON are copied from the local analysis; the per-point CSVs and predictions are not in this repository. |
| `pytest.txt` | 43 passed: the 13 new tests plus the existing `test_displacement_scale.py`, run with the real package on `PYTHONPATH` (Python 3.12, torch 2.10). |

## The real-data effect is mixed, and the PR says so

Score = fraction of the source surface's area whose copied points land on the
manually labelled neighbouring sheet (nearest manual ID within 2 native voxels).

| 128³ crops | main | this PR |
|---|---:|---:|
| all 6 cubes (9,475 points) | 13.72% | 17.74% |
| held-out 3 cubes (4,893 points) | 13.27% | 13.69% |
| cubes better / worse | | 4 / 2 |

The worst cube goes 17.4% → 5.8%. A second run at 128×256×256 on the start
points common to both crop sizes moves the same score 12.83% → 18.80% (all) and
8.10% → 14.01% (held-out) while a round-trip-consistency AUROC used in the same
study goes down. What is established is the coordinate defect, by construction
and by the synthetic fixture; the change in what Copy produces on real data is
real but not uniformly in one direction on six cubes, and is not claimed as an
accuracy gain.

## Caveats carried into the PR body

- The CT cubes have no physical unit in their NRRD header; 7.91 µm was assumed
  from the legacy Paris 4 volume and resampled to the checkpoint's 4.8 µm.
- The crops (128³, 128×256×256) are smaller than the checkpoint's training crop
  (128×384×384), and field sampling was single trilinear, not the CLI's
  radius-1 average and overlap merge.
- `rotate3` is covered by the synthetic fixture and the tests only; the
  real-data arms used the default `mirror` mode.
- The model has seen Paris 4 in training; the dev/held-out split is a split of
  cubes, not an independent generalisation test.

## Precedent inside the repository

`infer_streamline.py::_flip_tta_inputs` already swaps its `±` direction input
channels when it flips the corresponding axis. This change gives the
triplet-wraps path the same treatment for its vector-valued priors.
