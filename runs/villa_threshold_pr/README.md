# Evidence for the villa `ink_detection.inference.threshold` PR (2026-10-09)

Branch `feat/ink-borrow-threshold` on top of villa `main` `a329895ea`, commit `096760d7c`
(`villa_threshold.patch`). It is `tools/borrow_threshold.py` (docs/27) moved into the villa package,
reduced to the `value` rule (the quantile rule is left out to keep the PR small).

| file | what it shows |
|---|---|
| `loso_step010000.txt` / `.json`, `loso_step020000.txt` / `.json` | `threshold calibrate` run on docs/27 study 1's primary cells: 23 aligned segments of PHerc. Paris 4, 1667 and 0139, each predicted by the leave-one-scroll-out model that never saw its scroll (docs/15), seeds 42 and 43, one step per run. Per scroll, the threshold from the other two scrolls loses 0.009–0.019 F1 (step 10k) and 0.004–0.014 (step 20k); 128 loses 0.052–0.176 and 0.060–0.113. |
| `loso_run.py` | the driver: builds the `--cell` list from `runs/ink9um_scorecard/labelfree_cells.csv`, runs the CLI, and checks every cell's best threshold and F1 and every per-scroll borrowed threshold and loss against docs/27's committed `labelfree_cells.csv` (R1, R0). All 92 cells and 6 scroll rows match. |
| `compare_pherc0139-w028_loso0139_42_010000.png`, `make_figure.py` | one crop (the densest labelled 1000×1600 area) of pherc0139-w028, binarized at 128 (F1 0.522 on the whole segment) and at 90, the threshold taken from Paris 4 and 1667 (F1 0.607; the segment's own best is 96, F1 0.615). Colours: white ink found, orange marked but not ink, blue ink missed. |
| `released_s42_20k.txt` / `.json` | the same command on a released `ink_9um` checkpoint (seed 42, step 20,000) over the five open-data segments of PHerc. 0841, 0009B and 0500P2 (docs/27 study 2). Here 128 is fine: it loses 0.000–0.023, the borrowed threshold 0.001–0.013. |
| `match_tools_borrow_threshold_14ckpt.txt`, `compare.py` | the villa module against `tools/borrow_threshold.py` on all 14 released checkpoints × 5 open-label segments: thresholds, F1, borrowed thresholds and losses identical. |
| `pytest.txt` | the six new tests (`vesuvius/tests/ink_detection/test_inference_threshold.py`). |

Run with the ink-detection uv environment and `PYTHONPATH=D:/vw15/vesuvius/src`. Predictions for the
LOSO cells are archived on `Z:\아카이브\vesuvius-runs\ink9um_scorecard\preds` (not committed).
