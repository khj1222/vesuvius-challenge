# September 20 retrospective evidence audit

This directory contains numerical research artifacts, not model weights or candidate
letter images. The original reports elsewhere in `runs/` remain unchanged.

- `pseudo_threshold_bounds.json`: conservative bounds reconstructed from saved rounded
  sweeps, with the necessary source fields embedded. Not confidence intervals.
- `scouting_control_audit.json`: replay of the complete gate on known-positive controls,
  plus a non-clipping additive-offset diagnostic. Not a replacement detector.
- `fixed_threshold_manifest.json`: portable input specification for the 58 TIFFs used
  in the fixed-threshold follow-up. Adapt prediction/label roots to local storage.
- `fixed_threshold_calibration.json`: frozen thresholds from Paris4 w01 and 1667 w013.
- `fixed_threshold_evaluation.json`: 48 evaluation cells, full 256-bin positive/negative
  histograms, exact counts, and SHA-256 identities for predictions and decoded label planes.
- `fixed_threshold_scores.csv`, `fixed_threshold_summary.json`: per-cell and paired summaries.

Both arms use the same calibration labels. FT training segments w00/w018 and calibration
segments w01/w013 are excluded from evaluation. 1667's primary base is its 10k initialization;
20k is a declared sensitivity. Primary scores count each valid pixel once; legacy counts
and scores reproduce the old overlapping-region-box evaluator as a sensitivity check.

This is retrospective reuse of previously inspected segments. Seeds are correlated,
and calibration is an additional labeled segment; this is not a label-free method or
an independent test on unread scrolls. Old recovery percentages use other selection
rules and a train-pixel reference, so are not replaced by these fixed-threshold values.

To verify arithmetic without model data or third-party packages:

```bash
python tools/verify_september_evidence.py
```

To re-score the prediction and label artifacts named in the manifest, from repository root:

```bash
python tools/eval_fixed_threshold_ft.py runs/september_evidence_audit/fixed_threshold_manifest.json --phase calibration --out calibration.json
python tools/eval_fixed_threshold_ft.py runs/september_evidence_audit/fixed_threshold_manifest.json --phase evaluation --calibration calibration.json --out evaluation.json
```

Dependencies for re-scoring: numpy, tifffile, zarr2, scipy. The archived binary inputs
are not part of Git; numerical histograms suffice to independently verify all reported
fixed F1 values. Calibration was recorded before the overlap-counting issue was found;
the evaluation runner adds legacy reproduction, and records both runner hashes. That
change did not alter thresholds or calibration histograms.
