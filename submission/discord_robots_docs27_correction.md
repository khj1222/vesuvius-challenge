<!--
Reply to post in the user's own #robots thread (2026-10-02). NOT posted — the user posts it.
Same disclosure convention as the original post. Under 2,000 characters.
The human line at the end is the user's to write or delete.
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon, posted with his approval. Model output.

**Correction to the post above: the number does not carry over, and for the released checkpoints 128 is fine.**

I pre-registered a replication (commit 72c7679) on the three scrolls the released ink_9um checkpoints never saw and that now have reviewed labels in the open data: PHerc0841 (3 segments), 0009B (1), 0500P2 (1). All 14 released checkpoints, steps 10k/20k primary.

F1 lost vs the oracle (0841 / 0009B / 0500P2):
- the 87 recommended above: **0.096 / 0.118 / 0.095**, fails everywhere
- fixed 128: 0.008 / 0.006 / 0.027
- borrowing the optimum from the other new scrolls, same checkpoint: 0.003 / 0.003 / 0.009
- other scrolls' operating quantile: 0.003 / 0.006 / 0.003

The released models' optima on these scrolls are 98–141. The 84–92 band came from leave-one-scroll-out retrains, which are less confident on the scroll they never saw, and it does not describe the released checkpoints.

What survives: take the threshold from other scrolls scored *with the same model*. What does not: carrying a number from one model to another, including the one in my title. I predicted the opposite; the write-up says so.

https://github.com/khj1222/vesuvius-challenge/blob/main/docs/27_label_free_threshold.md

**Human (Hyojun):** <!-- write this yourself, or delete the line -->
