# PHerc.1667-iteration-N model cards: the input scaling that actually works

The six released `scrollprize/PHerc.1667-iteration-{0..5}` checkpoints document
their input convention in three places that disagree (module docstring: z-score;
quick-start comment: clip to [0, 200] then an "identity" `Normalize`; full-segment
snippet: raw uint8), and none of the three produces usable output — villa
[#1659](https://github.com/ScrollPrize/villa/issues/1659), found by jonmarrs.

The paper's Supplementary Table 2 names the training transform: clip to [0, 200]
then Albumentations `Normalize(mean=0, std=1)`. With that library's default
`max_pixel_value=255.0` this is `clip(x, 0, 200) / 255`, verified on
`albumentations==2.0.8` (`albumentations_normalize_contract.json`, max abs
difference 6e-8). The fix is documentation only: the same two-hunk patch applied
to each repo's `README.md` and `modeling_inkdetection.py`.

This one lives on the Hugging Face Hub, not in villa, so it goes out as one PR per
model repo (`open_hf_prs.py`, run under the user's own login).

## Files

| file | what |
|---|---|
| `hf_input_example.patch` | The two-hunk patch (LF line endings; the CRLF copy from 09-05 does not apply). Applies cleanly to all six repos at their current revisions (`f2012ce`, …, `6288ba6`). |
| `patched/iteration-N/` | Each repo's `README.md` and `modeling_inkdetection.py` with the patch applied; `patched/sha256.json` hashes them. The READMEs differ per iteration (header, family table); the modeling file is identical across the six. |
| `w029_conventions.png`, `w029_conventions.json` | Five input conventions on three annotated PHerc. 1667 w029 regions, same weights (`iteration-5`), same tiles, z window `[24:86]`, scored against the annotation after 4×4 pooling. Rows copied from the local 2026-09-05 run. |
| `quickstart_check.py`, `quickstart_check.txt` | The patched quick start executed against the real weights, offline, from the repo's own modeling file: strict load, `torch.Size([1, 1, 64, 64])`, input range `[0, 0.784]`. |
| `albumentations_normalize_contract.json` | `Normalize(mean=0, std=1)` on `[0, 100, 200, 255]` under 2.0.8 → `[0, .392, .784, 1.0]`. |
| `hf_pr_description.md` | The PR description, identical for the six PRs. |
| `open_hf_prs.py` | Opens the six PRs with `HfApi.create_commit(create_pr=True)`. Dry run by default; `--send` requires `hf auth login` first. |

## The measurement, in one table

| convention | documented where | AP (mean of 3 regions) | annotated px > 0.5 |
|---|---|---:|---:|
| raw uint8 | card snippet | 0.470 | 98.8% |
| clip [0, 200] only | card prose | 0.470 | 99.1% |
| per-tile z-score | docstring | 0.593 | 100% |
| clip [0, 200] / 255 | this patch | 0.836 | 39.8% |
| clip [0, 200] / 200 | villa `optimized_inference`, other model | 0.878 | 52.9% |

`/255` vs `/200` is inside what three regions can resolve: on the three *other* w029
regions measured on 09-05 (`planning`, not in this repo) the order is 0.834 vs
0.814. The patch says `/255` because that is what the card's own named transform
computes; the PR text says so and does not pick a divisor from these scores.

## Not in scope

The z window (the paper's "layers 1–62" against today's 109-layer stacks) is not
resolved; the 2.4 µm level-0 expectation is not added; weights and compute are
untouched. Whole-segment runs on PHerc. 0814 exist locally and were not used here.
