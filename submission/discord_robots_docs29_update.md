<!--
Discord #robots reply in the docs/27 thread (draft 2026-10-09). NOT posted — the user posts it.
  thread: https://discord.com/channels/1079907749569237093/1555465594969661440
  ("Label-free ink threshold: borrow the same model's optimum from other scrolls (pre-registered x2)")
  10-09 check: only our two posts + title change in the thread, no replies.
  format = the 10-02 correction reply (AI disclosure first line).
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

AI disclosure: Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon, posted with his approval. Model output.

Third test, and the method does not hold everywhere.

Pre-registered (commit a2a187c) on public checkpoints trained with dense pseudo-labels instead of manual labels: KLAVIS's ink9um-dense (3 checkpoints) and Nieuwlaar's dense-native, on the same three scrolls none of them trained on (PHerc0841, 0009B, 0500P2). Checked afterwards: the same files reproduce KLAVIS's published validation AUCs (within 0.0007), so it is not a loading error.

F1 lost vs the oracle (0841 / 0009B / 0500P2, 4 checkpoints pooled):

- borrow the other scrolls' optimum: 0.011 / 0.002 / **0.062**, fails
- fixed 128: 0.003 / 0.001 / **0.062**
- borrow the other scrolls' operating quantile: 0.010 / 0.004 / 0.003

For these models 0500P2's optimum sits ~25 levels below the other two. The quantile rule is the only one that has held in all three tests, so that is what I'd use on an unfamiliar model. Three of my four predictions were wrong; the write-up says which.

https://github.com/khj1222/vesuvius-challenge/blob/main/docs/29_threshold_other_recipes.md
