<!--
Draft comment for https://github.com/ScrollPrize/villa/issues/1659 (jonmarrs's issue), PR links filled in 2026-09-15 after the six HF PRs
were opened (each repo's discussions/1). NOT POSTED. Paste only what is below ---.
-->
---
Reproduced on three annotated regions of the model's own scroll (PHerc. 1667 w029, `iteration-5`, strict load, the card's own tiling, z window `[24:86]`), scored against the annotation rather than by firing rate alone:

| convention | AP, mean of 3 | annotated px > 0.5 |
|---|---:|---:|
| raw uint8 (card snippet) | 0.47 | 99% |
| clip [0, 200] only (card prose) | 0.47 | 99% |
| per-tile z-score (docstring) | 0.59 | 100% |
| clip [0, 200] / 255 | 0.84 | 40% |
| clip [0, 200] / 200 (what `optimized_inference` does for `ink_canonical_2um`) | 0.88 | 53% |

Your ranking holds with ground truth attached. One correction to the mechanism in your write-up, which I only note because it decides what the card should say: Albumentations' `Normalize(mean=0, std=1)` is not the identity — its default `max_pixel_value=255.0` divides first, so `[0, 100, 200, 255]` → `[0, .39, .78, 1.0]` on 2.0.8. The card's prose therefore names the right transform and describes it wrongly; the undocumented `clip/255` you found *is* the documented one, computed correctly.

I have opened the card fix as one PR per repo, all six iterations, same two hunks (quick start, tiled snippet, docstring), weights and compute untouched:
[iteration-0](https://huggingface.co/scrollprize/PHerc.1667-iteration-0/discussions/1) · [iteration-1](https://huggingface.co/scrollprize/PHerc.1667-iteration-1/discussions/1) · [iteration-2](https://huggingface.co/scrollprize/PHerc.1667-iteration-2/discussions/1) · [iteration-3](https://huggingface.co/scrollprize/PHerc.1667-iteration-3/discussions/1) · [iteration-4](https://huggingface.co/scrollprize/PHerc.1667-iteration-4/discussions/1) · [iteration-5](https://huggingface.co/scrollprize/PHerc.1667-iteration-5/discussions/1)

Figure, per-region rows and the Albumentations check: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/hf1667_input_example. `/255` vs `/200` is within what three regions resolve (three other regions reverse it), so the PRs state the named transform and do not pick a divisor from scores. The z-window question ("layers 1–62" against a 109-layer stack) and the 2.4 µm note you raise are left open.

*Disclosure: most of this project's work, including this reproduction and the wording here, is done with an AI coding assistant; the decisions are mine.*
