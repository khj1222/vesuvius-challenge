<!--
Follow-up comment for villa #2012, to post AFTER pushing 720a487d4 to fork feat/ink-borrow-threshold
(draft 2026-10-09). NOT posted, NOT pushed — both wait for the user's go-ahead.
  Re-read the #2012 thread before posting (a maintainer may have answered the 09:45Z comment).
  Evidence: runs/villa_threshold_pr/quantile_evidence.{txt,json,py}, pytest_quantile.txt (8 passed),
  tools/check_quantile_sheet.py + runs/ink9um_scorecard/quantile_sheet_check.json (prediction>0 sheet
  vs the surface-volume sheet the studies used: per-scroll differences within 0.002 either way — released
  0841 -0.0013, 0009B -0.0013, 0500P2 +0.0008; docs/29 all five models -0.0019/-0.0014/-0.0011; LOSO vs
  docs/27's R3 table 0139 +0.002, 1667 -0.001, Paris4 0.000).
  Numbers below copied from quantile_evidence.txt.
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

Pushed the quantile rule as offered (`apply --rule quantile`; `value` stays the default). `calibrate` now also stores the median fraction of the sheet (non-zero prediction pixels) that each labelled prediction's best threshold marks, and its per-scroll check prints both rules next to 128.

The same command on all three datasets, each rule taken from the other scrolls only (mean F1 lost against each segment's own best threshold):

| checkpoints | scroll | value | quantile | 128 |
|---|---|---|---|---|
| leave-one-scroll-out, steps 10k/20k | PHerc0139 / 1667 / Paris 4 | 0.016 / 0.007 / 0.014 | 0.022 / 0.001 / 0.025 | 0.145 / 0.056 / 0.113 |
| 14 released `ink_9um` | PHerc0841 / 0009B / 0500P2 | 0.005 / 0.001 / 0.008 | 0.005 / 0.004 / 0.003 | 0.009 / 0.008 / 0.026 |
| 4 dense-label | PHerc0841 / 0009B / 0500P2 | 0.011 / 0.002 / **0.062** | 0.009 / 0.003 / 0.003 | 0.002 / 0.001 / **0.062** |

The quantile rule never lost more than 0.025; the value rule lost 0.062 once. Using `prediction > 0` as the sheet (so no surface volume is needed) changed the per-scroll losses by at most 0.002, in either direction, against the surface-volume sheet the studies used. Tests: 8 passed (two new ones for the quantile path).
