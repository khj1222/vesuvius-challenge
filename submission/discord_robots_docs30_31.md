<!--
Draft for the project Discord, #robots forum (2026-10-14). NOT posted — the user posts it.
Same conventions as discord_robots_docs27.md / docs28.md: name the model, separate model output from
human commentary, testable claims, under Discord's 2,000-character limit, lists instead of tables.
New forum post (not a reply in the docs/27 thread): different question.

Numbers, all from docs/30 and docs/31 Results (commits bc87201, 4a7e797):
  - docs/30: wander arm on wandering renders −0.005/−0.006 vs control (rule +0.015); every model loses
    0.009–0.019 to a 2-slice wander; one-sided ~0.02 at 1–2 slices.
  - docs/31: jitter5 − control on large set +0.001/+0.007 (rule +0.015); clean +0.002/+0.001.
    Released reader, mean of 3 scrolls: clean 0.642/0.646; −5 0.485/0.475 (loss 0.157/0.171);
    +5 0.609/0.606 (loss 0.033/0.040); −3 0.582/0.567 (loss 0.060/0.079). jitter5 at −5 loses ~0.15
    vs control ~0.16. 1 slice = 4 × 2.4 µm pooled ≈ 9.6 µm; ±5 ≈ ±48 µm.
  - Shift sign (docs/31): k = the model reads slices k positions further along the render's slice axis
    than the traced surface puts them.
  - Test: PHerc0841 w00/ag144/ag174, PHerc0009B ag055, PHerc0500P2 s1 (open labels); none in training.
  - Cause of one-sidedness: open (post-hoc depth profile does not match per scroll).

Checked 2026-10-14 (#robots list, read only): nothing on ink loss vs surface offset. Related, not
overlapping: Matteo Bulloni "PHerc0841 as an unseen-scroll exam for 9 µm ink reads, plus GrowPatch drift
off a known sheet" (09-25, thread 1552768204382674964: 0 of 3 GrowPatch patches stay within 5 voxels of
the team's sheet, median 20–28 voxels) -> credited in Limits without converting his voxels to our slices
(his voxel size not checked). Bullo27 "v8-in on a 12 GB GPU: depth order from geometry" (10-02) is
about stack direction, not offset. Re-read once more right before posting.

Suggested tags: ink-detection (or analysis).
Title (forum post title field) — no stronger than the body:
  How far off can the surface be before ink_9um loses ink? (two pre-registered negatives)

The last line is the human part. Write it yourself (one or two lines is enough), or delete it.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** planned, run and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

**Question:** a traced surface a little off the sheet feeds the ink model the wrong depths. How much does the released `ink_9um` reader lose, and does training against offsets fix it?

**Setup:** released checkpoints (seeds 42/43) fine-tuned 10k steps, two seeds, scored on five open-label segments from PHerc0841, 0009B and 0500P2 (no scroll in training), on renders shifted or wandering in depth. 1 slice ≈ 9.6 µm. Both studies pre-registered before training.

**What it costs (released reader, mean of 3 scrolls, best F1 ≈ 0.64 clean):**
- surface 5 slices (≈ 48 µm) off one way: −0.16 / −0.17
- 5 slices the other way: −0.03 / −0.04
- 3 slices on the bad side: already −0.06 / −0.08
- a smooth wander of ±2 slices: only −0.01 to −0.02 (the recipe already jitters the window ±2)

**What did not help (both negatives):**
- in-patch depth wander up to 2 slices (docs/30): −0.005 / −0.006 vs control on wandering renders, rule was +0.015
- whole-window jitter widened ±2 → ±5 on 27-slice inputs (docs/31): +0.001 / +0.007 on 3–5 slice offsets, rule +0.015. No cost on clean renders either way.

**Open:** why the loss is one-sided. A post-hoc depth profile of annotated ink did not explain it scroll by scroll.

**Limits:** one recipe, three test scrolls, best-F1 with an oracle threshold. Synthetic offsets on real renders, not real segmentation errors (for those, see Matteo Bulloni's GrowPatch-drift post on PHerc0841 here).

Write-ups with per-render CSVs:
https://github.com/khj1222/vesuvius-challenge/blob/main/docs/31_wide_depth_jitter.md
https://github.com/khj1222/vesuvius-challenge/blob/main/docs/30_surface_offset_robust_ink.md

**Human (Hyojun):** <!-- write this yourself, or delete the line -->
