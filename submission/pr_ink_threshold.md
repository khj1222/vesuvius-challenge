<!--
villa PR draft: vesuvius.ink_detection.inference.threshold (2026-10-09). NOT opened — the user opens it.
  branch: khj1222/villa feat/ink-borrow-threshold (local D:/vw15, commit 096760d7c on main a329895ea; NOT pushed yet)
  base: main. Title:
    ink_detection: threshold, pick the binarization threshold for an unlabelled scroll from labelled predictions
  Evidence: runs/villa_threshold_pr/ (README there). Image to upload: compare_pherc0139-w028_loso0139_42_010000.png
  Checked before drafting:
    - no open/merged PR on threshold/calibration/binarization for ink_detection (gh search 10-09);
      #1872 (Danishk2445, open) adds inference/sweep.py with AUC; it touches docs/ink_detection.md's
      "Flat inference" end and README's flat-inference lines; ours adds a section before "Labeling loop"
      and a block after native inference -> different hunks.
    - merge_predictions.py's FOREGROUND_THRESHOLD_U8 = 128 is a vote between predictions, not the final
      binarization; this PR does not touch it.
  ⚠️ The "Why / where this is useful" paragraph must be written by the user (CONTRIBUTING: human-written
     commentary). Facts the user can draw on:
       - every reading of an unlabelled scroll ends with a threshold; the package had none, so people use 0.5/128
       - for the released ink_9um checkpoints 128 is fine on three new scrolls (this tool confirms it)
       - for models trained without a scroll (like anyone training their own ink model and pointing it at a new
         scroll), 128 cost 0.05-0.18 F1; the threshold borrowed from other scrolls cost 0.004-0.019
       - users: anyone training a new ink model (Discord: v8-in, Reader v2, Bullo27's native 3D ink) before First Letters-style reading
  ⚠️ Checkbox stays UNTICKED unless the user runs the commands (or tests) themselves.
  Push first: git -C D:/vw15 push fork feat/ink-borrow-threshold (remote name to confirm), then open the PR.
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** Before you binarize an ink prediction of a scroll nobody has labelled, `threshold calibrate` measures, on segments you do have labels for, which threshold your checkpoint needs and what 128 would cost, and `threshold apply` cuts the new prediction there.

**One real example:** Starting with predictions of 23 labelled segments of PHerc. Paris 4, PHerc. 1667 and PHerc. 0139 (the aligned ink_9um representations), each made by an ink_9um-recipe model trained without that scroll (seeds 42 and 43, step 10,000), I ran `threshold calibrate`. Scored at the median best threshold of the other two scrolls (86–92), each scroll lost 0.009–0.019 F1 against its own best; at 128 it lost 0.052–0.176.

**Before:** Flat inference writes a uint8 probability TIFF, and the package had nothing to choose where to cut it, so 128 (0.5) is the usual choice. For these models the best threshold on a scroll they had not seen was well below 128 (median 89), and at 128 much of the ink was left out (figure below).

**After this PR:**
```bash
uv run --extra models python -m vesuvius.ink_detection.inference.threshold calibrate \
  --cell PHerc0841 preds/pherc0841-w00.tif labels/pherc0841-w00/pherc0841-w00_inklabels.zarr labels/pherc0841-w00/pherc0841-w00_supervision_mask.zarr \
  --cell PHerc0009B preds/pherc0009b-ag055.tif labels/pherc0009b-ag055/pherc0009b-ag055_inklabels.zarr labels/pherc0009b-ag055/pherc0009b-ag055_supervision_mask.zarr \
  --out calibration.json
uv run --extra models python -m vesuvius.ink_detection.inference.threshold apply \
  preds/unlabelled.tif --calibration calibration.json --out unlabelled_ink.tif
```
`calibrate` prints each prediction's best threshold and F1, stores their median, and with two or more scrolls scores each scroll at the other scrolls' median next to 128.

**Proof:**

pherc0139-w028, predicted by the model trained without PHerc. 0139 (seed 42, step 10,000). White = ink found, orange = marked but not ink, blue = ink missed. At 128 the segment's F1 is 0.522; at 90, the threshold taken from Paris 4 and 1667, it is 0.607 (its own best is 96, 0.615).

<!-- upload runs/villa_threshold_pr/compare_pherc0139-w028_loso0139_42_010000.png here -->

`calibrate` output on all 46 cells, mean F1 lost per scroll:

| step | scroll | cells | threshold from the other scrolls | lost at that threshold | lost at 128 |
|---|---|---|---|---|---|
| 10,000 | PHerc. 0139 | 18 | 90 | 0.018 | 0.176 |
| 10,000 | PHerc. 1667 | 12 | 86 | 0.009 | 0.052 |
| 10,000 | PHerc. Paris 4 | 16 | 92 | 0.019 | 0.145 |
| 20,000 | PHerc. 0139 | 18 | 85 | 0.014 | 0.113 |
| 20,000 | PHerc. 1667 | 12 | 84 | 0.004 | 0.060 |
| 20,000 | PHerc. Paris 4 | 16 | 86 | 0.009 | 0.082 |

For the released `ink_9um` checkpoints the same command says 128 is fine. Seed 42, step 20,000, on the five open-data segments of PHerc. 0841, 0009B and 0500P2 published on 2026-09-22 (not in the ink_9um training set): 128 loses 0.000–0.023 and the threshold from the other scrolls 0.001–0.013. The tool is for finding out which case your checkpoint is in.

**Why / where this is useful:** <!-- USER WRITES THIS -->

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

**Motivation.** I was scoring ink_9um-recipe models on scrolls they had not been trained on, and every F1 I reported picked its threshold with the scored scroll's own labels. A scroll nobody has labelled does not have those, so I measured what a label-free choice costs. I pre-registered and tested the rule this tool implements twice (both write-ups, with the predictions that failed: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/27_label_free_threshold.md). The table above reproduces that study's numbers exactly: every cell's best threshold and F1 and every per-scroll threshold and loss.

**Method.** For each labelled prediction, F1 of `prediction >= t` against the ink labels inside the mask (the supervision mask here), for every t in 0–255; its argmax is that prediction's best threshold. The stored threshold is the median of those, rounded half up. The check scores each scroll's predictions at the median of the other scrolls' predictions only. Label Zarrs are read at level 0, middle Z plane, as `create_label_zarrs` writes them; label TIFF/PNG images work too.

**Tested commit.** `main` at `a329895ea`. New files: `vesuvius/src/vesuvius/ink_detection/inference/threshold.py`, `vesuvius/tests/ink_detection/test_inference_threshold.py` (6 passed); a section in `vesuvius/docs/ink_detection.md` and a block in the package README. Nothing existing changes behaviour.

**Data.** Predictions: the leave-one-scroll-out models in the write-up above (aligned 9.6 µm representations, ink_9um recipe), and the released `ink_9um` checkpoints. Labels: the ink_9um `_inklabels` / `_supervision_mask` Zarrs, and the reviewed ink labels in the open-data bucket for PHerc. 0841, 0009B and 0500P2. Raw outputs, the figure script and the comparison against the original script: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/villa_threshold_pr

**Limitations.** Tested on six scrolls with one recipe's checkpoints. A threshold measured on unadapted checkpoints does not carry over to a checkpoint fine-tuned on the new scroll (fine-tuning moved the best threshold in the write-up), so re-calibrate after any further training. Calibrating on the validation mask of segments a checkpoint trained on was not tested, and the docs say to calibrate on scrolls the checkpoint never saw.

**Disclosure:** most of the work in this project, including the study, this code and the tests, is done with an AI coding assistant. The problem, the data and the decisions are mine.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
