<!--
Comment for villa #2012 (draft 2026-10-09). NOT posted — the user posts it.
  target: https://github.com/ScrollPrize/villa/pull/2012 (thread had only the Vercel bot on 10-09)
  why: the PR implements the value rule (median of other scrolls' optima); docs/29 found it failing on
  one scroll for dense-label checkpoints. The PR body's Limitations say "tested on six scrolls with one
  recipe's checkpoints" — now incomplete.
  numbers (docs/29, runs/ink9um_scorecard/otherrecipes_*): dense pooled R1b 0.011 / 0.002 / 0.062,
  R0 0.003 / 0.001 / 0.062, R3 0.010 / 0.004 / 0.003; per checkpoint on 0500P2 R1b 0.047–0.071;
  villa calibrate reproduces every per-checkpoint loss (otherrecipes_villa_crosscheck.txt).
  No AI-disclosure line (the PR body already has the Disclosure paragraph).
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

A follow-up test narrows one claim in the Limitations above.

I ran the same check on public checkpoints trained with dense pseudo-labels instead of the manual labels (three of KLAVIS's `ink9um-dense` checkpoints and Nieuwlaar's `dense_native_016000`), on the same three open-label scrolls, which none of them trained on. Pre-registered before inference: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/29_threshold_other_recipes.md

Mean F1 lost against each segment's own best threshold, four checkpoints pooled:

| | PHerc0841 | PHerc0009B | PHerc0500P2 |
|---|---|---|---|
| threshold from the other two scrolls (this PR) | 0.011 | 0.002 | **0.062** |
| 128 | 0.003 | 0.001 | **0.062** |

For these checkpoints PHerc0500P2's best threshold sits about 25 grey levels below the other two scrolls', so taking it from them does not work there. `threshold calibrate` prints exactly this loss for each checkpoint (0.05–0.07), so the check in this PR shows the case before anyone applies the value, but the PR offers nothing else to use.

Cutting each prediction where it marks the same fraction of the sheet as the other scrolls' best thresholds did held on all three (0.010 / 0.004 / 0.003), as it has in every test so far. If that is useful here, I can add it as `apply --rule quantile` with the same real-data checks; otherwise I'll change the docs to say the value can fail for some checkpoints and to read the check before using it.
