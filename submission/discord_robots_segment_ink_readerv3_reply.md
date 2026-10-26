<!--
Draft reply (2026-10-26) for our #robots post "Run ink_9um on a VC3D segment and see it in VC3D's Ink Detection
panel (2 segments checked)", thread 1564220086158495754. A reply inside the thread, not a new post.
NOT posted — the user posts it. Conventions as in discord_robots_segment_ink.md.

Numbers, all from runs/segment_ink/pherc0841_w00_ink9um_vs_readerv3.json (commit dcf1b93):
  - forward: M1 placement 0.3548 (ink_9um) / 0.6662 (V3); M2 letter-scale 0.0222 / 0.1009, shifted nulls
    0.0033 / 0.0038; M3 AUC 0.7719 / 0.9158 (recomputed on the label grid: 0.7724 / 0.916).
  - inference per direction: ink_9um 19:40:10 -> 19:42:47 (2m37s), V3 19:44:10 -> 19:44:35 (25 s).
  - KLAVIS published 0841_w00 AUC: reader-v3 0.8805, base 0.7217 (results/suite_*.json @aee1d64).
  - Held out: ink_9um never trained on PHerc0841; V3 train_config has no PHerc0841. 0814 20250925212701 and
    0139 w045 are in V3's train_config (datasets 8 and 9).
  - Rules fixed before inference: planning/2026-10-26_reader_v3_segment_ink/PREREG.md (sha256 eba6683b9767…).
Checked 2026-10-26 ~20:30 KST: thread has 0 replies. Re-check right before posting.

The last line is the human part. Write it yourself, or delete it.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** run and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

**Update: the same tool with KLAVIS's Reader V3** (only `--checkpoint` changes). The two segments above are in Reader V3's training set, so this uses PHerc0841 w00, which neither model trained on. Same render, both directions, comparison fixed before inference; forward reads for both:
- placement vs the team's 2.4 µm map: ink_9um 0.355 → Reader V3 0.666
- letter-scale correlation (both maps minus a ~48 µm blur): 0.022 → 0.101 (shifted maps ≤ 0.004)
- AUC vs the open human ink labels: 0.772 → 0.916
- inference per direction on an RTX 5090: ~2.6 min → ~25 s

KLAVIS's own numbers for this segment are 0.881 vs 0.722, so the gap holds through a different render path (ours are ~0.04–0.05 higher for both).

**Limits:** one segment, one ink_9um checkpoint. Reader V3's map has a staircase band along the left and bottom canvas edge. This repeats KLAVIS's result; it is not a new claim. If this turns into a VC3D action, Reader V3 looks like the sensible default checkpoint.

Side by side (team map, ink_9um, Reader V3) and numbers:
https://github.com/khj1222/vesuvius-challenge/blob/main/runs/segment_ink/pherc0841_w00_ink9um_vs_readerv3.png
https://github.com/khj1222/vesuvius-challenge/blob/main/runs/segment_ink/pherc0841_w00_ink9um_vs_readerv3.json
