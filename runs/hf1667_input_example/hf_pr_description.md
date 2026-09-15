The card documents the input convention in three places and the three disagree: the module docstring says "intensity already z-score normalised", the quick-start comment says the training pipeline clipped to [0, 200] and applied `Normalize(mean=0, std=1)` so inputs are "roughly [0, 1]", and the full-segment snippet passes raw uint8 straight to the model. None of the three is what the stated transform computes, and all three saturate the model (villa [#1659](https://github.com/ScrollPrize/villa/issues/1659), reported by @jonmarrs).

**What the stated transform actually is.** The paper's Supplementary Table 2 (W&B run `rd0qz8ps`, requirements `albumentations==2.0.8`) says the layers were clipped to [0, 200] and then passed through `Normalize(mean=0, std=1)`. In Albumentations that call is not the identity: its default `max_pixel_value=255.0` divides first. Measured on 2.0.8, the values `[0, 100, 200, 255]` come out as `[0, 0.392, 0.784, 1.0]`, i.e. `clip(x, 0, 200) / 255` to within 6e-8. So the recipe the card names is *clip to 200, divide by 255* — not z-score, and not "roughly [0, 1] after an identity".

**This PR** makes the three descriptions say that, and nothing else:

- quick start: builds the demo tensor as `raw.float().clamp(0, 200) / 255.0` and says so in the comment;
- full-segment snippet: adds the one line `tile = np.clip(tile.astype(np.float32), 0, 200) / 255.0` before the tensor is built;
- `modeling_inkdetection.py`: the docstring's "(intensity already z-score normalised)" becomes "(raw uint8 clipped to [0, 200] and divided by 255; not z-score normalised)".

Weights, `config.json`, and the model's computation are untouched; the modeling file changes by one docstring line.

**Checked on real data, home scroll.** Same weights (`iteration-5`, `model.safetensors`, strict load), same three annotated regions of PHerc. 1667 segment w029, same tiling as the card's own snippet (256 window, stride 128, sigmoid, bilinear ×4, overlap mean), z window `[24:86]` of the 109-layer stack; only the input convention differs. Scores are against the annotation, pooled 4×4 to its grid.

| input convention | where it is documented | AP (mean of 3) | annotated pixels > 0.5 |
|---|---|---:|---:|
| raw uint8 → float | card snippet | 0.47 | 99% |
| clip [0, 200], nothing else | card prose read literally | 0.47 | 99% |
| per-tile z-score | docstring | 0.59 | 100% |
| **clip [0, 200] / 255** | **this PR** | **0.84** | **40%** |
| clip [0, 200] / 200 | villa `optimized_inference` (for `ink_canonical_2um`) | 0.88 | 53% |

![five conventions on three annotated w029 regions](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/hf1667_input_example/w029_conventions.png)

Numbers, per-region rows and the Albumentations check: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/hf1667_input_example. The patched quick start was executed against the real weights and returns `torch.Size([1, 1, 64, 64])`.

**What this PR does not claim.** `/255` and `/200` are within what three regions can separate (on three other w029 regions the order reverses, 0.834 vs 0.814); the card should carry a working recipe, and `/255` is the one its own stated transform computes. The paper's "layers 1–62" is not resolved here (the current w029 stack is 109 layers and the training layer stack's alignment to it is not public), so the z window is left as the card has it. The 2.4 µm level-0 expectation that #1659 also raises is not added here.

*Disclosure: most of this project's work, including this measurement and the wording of this PR, is done with an AI coding assistant; the decision to propose it, and what it claims, are mine. The finding is jonmarrs's (#1659); this PR is the card change that follows from it.*
