"""Compare villa threshold.calibrate with tools/borrow_threshold.py on the 70 open-label predictions."""
import io, json, sys, contextlib, tempfile
from pathlib import Path
sys.path.insert(0, "E:/vesuvius-challenge/tools")
import borrow_threshold as ours
from vesuvius.ink_detection.inference import threshold as villa

PREDS = Path("E:/vesuvius-challenge/runs/ink9um_openlabels/preds")
LABELS = Path("E:/vesuvius-challenge/data/ink_9um/labels/openlabels9")
SEGS = ["pherc0841-w00", "pherc0841-ag144", "pherc0841-ag174", "pherc0009b-ag055", "pherc0500p2-s1"]
SCROLL = {"pherc0841": "PHerc0841", "pherc0009b": "PHerc0009B", "pherc0500p2": "PHerc0500P2"}
tmp = Path(tempfile.mkdtemp())
bad = 0
for seed in (42, 43):
    for step in (10000, 20000, 30000, 40000, 50000, 60000, 75000):
        if step == 80000: continue
        cells = [[SCROLL[s.split("-")[0]], str(PREDS / f"{s}_s{seed}_{step:06d}.tif"),
                  str(LABELS / s / f"{s}_inklabels.zarr"), str(LABELS / s / f"{s}_supervision_mask.zarr")] for s in SEGS]
        if not Path(cells[0][1]).exists():
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            v = villa.calibrate(cells, tmp / "v.json")
            ours.main(["calibrate", "--out", str(tmp / "o.json")] + sum([["--cell", *c] for c in cells], []))
        o = json.loads((tmp / "o.json").read_text())
        ok = v["threshold"] == o["value_threshold"]
        for vc, oc in zip(v["cells"], o["cells"]):
            ok &= vc["best_threshold"] == oc["oracle_threshold"] and abs(vc["f1_best"] - oc["oracle_f1"]) < 1e-12 and abs(vc["f1_at_128"] - oc["f1_at_128"]) < 1e-12
        for scroll, row in v["check_against_other_scrolls"].items():
            orow = o["leave_one_scroll_out_check"][scroll]
            ok &= row["threshold_from_other_scrolls"] == orow["borrowed_value_threshold"]
            ok &= abs(row["mean_f1_loss_borrowed"] - orow["mean_regret_value"]) < 1e-12
            ok &= abs(row["mean_f1_loss_128"] - orow["mean_regret_128"]) < 1e-12
        bad += not ok
        print(f"seed {seed} step {step:06d}: threshold {v['threshold']}  {'MATCH' if ok else 'DIFF'}", flush=True)
print("all match" if bad == 0 else f"{bad} differ")
