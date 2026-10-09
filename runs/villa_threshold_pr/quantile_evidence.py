"""villa `threshold calibrate` (with the quantile rule) on the three threshold studies' data.

Per study and scroll: mean F1 lost by the value rule, the quantile rule (sheet = prediction > 0)
and 128, each rule taken from the other scrolls only, as the tool's own check prints it.
  study 1 (docs/27): LOSO models, steps 10k and 20k, one calibration per step
  study 2 (docs/27 replication): the 14 released ink_9um checkpoints, one calibration each
  study 3 (docs/29): four dense-label checkpoints and the manual-label control, one calibration each
Run from D:/vw15/vesuvius with PYTHONPATH=D:/vw15/vesuvius/src in the ink-detection env.
"""
import contextlib
import csv
import io
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, "E:/vesuvius-challenge/tools")
from vesuvius.ink_detection.inference import threshold as T  # noqa: E402

ROOT = Path("E:/vesuvius-challenge")
OUT = ROOT / "runs/villa_threshold_pr"
tmp = Path(tempfile.mkdtemp())


def run(cells):
    with contextlib.redirect_stdout(io.StringIO()):
        return T.calibrate(cells, tmp / "c.json")["check_against_other_scrolls"]


def pool(checks):
    out = {}
    for scroll in checks[0]:
        out[scroll] = {k: float(np.mean([c[scroll][k] for c in checks]))
                       for k in ("mean_f1_loss_value", "mean_f1_loss_quantile", "mean_f1_loss_128")}
    return out


results = {}
# study 1: LOSO
lab = ROOT / "data/ink_9um/labels/aligned-scrollprizeorg-21slices"
pred = Path(r"Z:\아카이브\vesuvius-runs\ink9um_scorecard\preds")
name = {"phercparis4": "PHercParis4", "pherc1667": "PHerc1667", "pherc0139": "PHerc0139"}
rows = list(csv.DictReader(open(ROOT / "runs/ink9um_scorecard/labelfree_cells.csv")))
checks = []
for step in ("010000", "020000"):
    cells = []
    for r in (r for r in rows if r["step"] == step):
        arm = f"loso0139_{r['seed']}" if r["scroll"] == "pherc0139" else f"loso{r['seed']}"
        seg = r["segment"]
        cells.append([name[r["scroll"]], str(pred / f"{seg}_{arm}_{step}.tif"),
                      str(lab / seg / f"{seg}_inklabels.zarr"), str(lab / seg / f"{seg}_supervision_mask.zarr")])
    checks.append(run(cells))
results["study1_loso_steps10k20k"] = pool(checks)

# study 2 and 3: open-label scrolls
olab = ROOT / "data/ink_9um/labels/openlabels9"
segs = {"pherc0841-w00": "PHerc0841", "pherc0841-ag144": "PHerc0841", "pherc0841-ag174": "PHerc0841",
        "pherc0009b-ag055": "PHerc0009B", "pherc0500p2-s1": "PHerc0500P2"}


def open_cells(path_of):
    return [[s, str(path_of(seg)), str(olab / seg / f"{seg}_inklabels.zarr"),
             str(olab / seg / f"{seg}_supervision_mask.zarr")] for seg, s in segs.items()]


checks = [run(open_cells(lambda seg, sd=sd, st=st: ROOT / f"runs/ink9um_openlabels/preds/{seg}_s{sd}_{st}.tif"))
          for sd in ("42", "43") for st in ("010000", "020000", "030000", "040000", "050000", "060000", "075000")]
results["study2_released_14"] = pool(checks)

pdir = ROOT / "runs/ink9um_openlabels/preds_otherrecipes"
dense = ("K_ex016_75k", "K_ex016_60k", "K_all7_75k", "N_native_16k")
results["study3_dense_4"] = pool([run(open_cells(lambda seg, m=m: pdir / f"{seg}_{m}.tif")) for m in dense])
results["study3_control"] = pool([run(open_cells(lambda seg: pdir / f"{seg}_K_control_75k.tif"))])

(OUT / "quantile_evidence.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
lines = ["mean F1 lost per scroll, each rule taken from the other scrolls (villa threshold calibrate)", ""]
for study, per in results.items():
    lines.append(study)
    for scroll, v in per.items():
        lines.append(f"  {scroll:12} value {v['mean_f1_loss_value']:.3f}  quantile {v['mean_f1_loss_quantile']:.3f}  "
                     f"128 {v['mean_f1_loss_128']:.3f}")
(OUT / "quantile_evidence.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
