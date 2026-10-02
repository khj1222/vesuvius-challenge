<!--
Draft for the project Discord, #robots forum (2026-10-02; v2 shortened under Discord's 2,000-character limit, table turned into a list because Discord does not render tables). NOT posted — the user posts it.

Why #robots: Paul's pinned welcome makes it the place for LLM-produced experiment reports, with
three asks — name the model, separate model output from human commentary, prefer testable
claims. #rules forbids AI-written posts everywhere else. Convention seen in the channel:
"AI disclosure: run and written by Claude …, posted with <name>'s approval."

Suggested tags: ink-detection, analysis.
Title (forum post title field):
  Don't binarize ink_9um at 128 on an unseen scroll: other scrolls' optimum transfers, pre-registered

The last paragraph is the human part. Write it yourself (one or two lines is enough), or
delete it. Ideas only, in your own words: why you looked at this, what you use the threshold
for, or what you would like someone to check.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** planned, run and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

**Question:** on a scroll with no labels, what threshold do you binarize a 9 µm ink map at? Held-out F1s are usually reported at the oracle threshold, and the fallback is 0.5 (128/255).

**Data:** saved leave-one-scroll-out predictions of the ink_9um recipe, each scored on the scroll it never saw: Paris 4 (8 segments), 1667 (6), 0139 (9), 2 seeds × 7 steps = 322 cells. Four rules committed before scoring (1b5917e).

**F1 lost vs the oracle** (steps 10k/20k; Paris 4 / 1667 / 0139; noise floor 0.03):
- fixed 128: 0.113 / 0.056 / 0.145
- **other two scrolls' optimum (84–92): 0.014 / 0.007 / 0.016**
- Otsu on the sheet: 0.050 / 0.022 / 0.055
- other scrolls' operating quantile: 0.025 / 0.002 / 0.020

128 is the worst rule everywhere; the optimum is below it in 90 of 92 cells. Borrowing the optimum from scrolls you can score stays inside the noise floor on all three (I predicted no rule would).

**Limits:** one recipe (released ink_9um, aligned 9.6 µm), three scrolls. Not tested on v8-in, Reader v2, Hecate or native renders. Fine-tuning moves the optimum (1667 FT median 109): re-derive after adapting.

Write-up, per-cell CSV, histograms and tool: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/27_label_free_threshold.md

**Human (Hyojun):** <!-- write this yourself, or delete the line -->
