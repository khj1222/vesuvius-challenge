"""Run villa `threshold calibrate` on docs/27's LOSO cells (one step at a time) and compare with labelfree_cells.csv."""
import csv, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path("E:/vesuvius-challenge")
PRED = Path(r"Z:\아카이브\vesuvius-runs\ink9um_scorecard\preds")
LAB = ROOT / "data/ink_9um/labels/aligned-scrollprizeorg-21slices"
OUT = Path(sys.argv[1])
NAME = {"phercparis4": "PHercParis4", "pherc1667": "PHerc1667", "pherc0139": "PHerc0139"}
rows = list(csv.DictReader(open(ROOT / "runs/ink9um_scorecard/labelfree_cells.csv")))
py = str(ROOT / "external/villa/ink-detection/.venv/Scripts/python.exe")
for step in ("010000", "020000"):
    sel = [r for r in rows if r["step"] == step]
    args = [py, "-m", "vesuvius.ink_detection.inference.threshold", "calibrate"]
    for r in sel:
        arm = f"loso0139_{r['seed']}" if r["scroll"] == "pherc0139" else f"loso{r['seed']}"
        seg = r["segment"]
        args += ["--cell", NAME[r["scroll"]], str(PRED / f"{seg}_{arm}_{step}.tif"),
                 str(LAB / seg / f"{seg}_inklabels.zarr"), str(LAB / seg / f"{seg}_supervision_mask.zarr")]
    js = OUT / f"loso_step{step}.json"
    args += ["--checkpoint", f"docs/15 leave-one-scroll-out models, seeds 42+43, step {step}; each scroll predicted by the model that left it out", "--out", str(js)]
    res = subprocess.run(args, capture_output=True, text=True, env={**__import__('os').environ, "PYTHONPATH": "D:/vw15/vesuvius/src", "PYTHONIOENCODING": "utf-8"})
    (OUT / f"loso_step{step}.txt").write_text(res.stdout + res.stderr, encoding="utf-8")
    print(res.stdout[-900:], res.stderr[-2000:])
    v = json.loads(js.read_text())
    bad = 0
    for vc, r in zip(v["cells"], sel):
        if vc["best_threshold"] != int(r["oracle_threshold"]) or abs(vc["f1_best"] - float(r["oracle_f1"])) > 1e-6:
            bad += 1
    for scroll, row in v["check_against_other_scrolls"].items():
        key = [k for k, n in NAME.items() if n == scroll][0]
        own = [r for r in sel if r["scroll"] == key]
        r1 = np.mean([float(r["regret_R1"]) for r in own]); r0 = np.mean([float(r["regret_R0"]) for r in own])
        t1 = {r["t_R1"] for r in own}
        ok = abs(row["mean_f1_loss_borrowed"] - r1) < 1e-5 and abs(row["mean_f1_loss_128"] - r0) < 1e-5 and t1 == {str(row["threshold_from_other_scrolls"])}
        bad += not ok
        print(f"  {scroll}: tool {row['threshold_from_other_scrolls']} {row['mean_f1_loss_borrowed']:.6f}/{row['mean_f1_loss_128']:.6f}  docs/27 R1 {t1} {r1:.6f} R0 {r0:.6f}  {'OK' if ok else 'DIFF'}")
    print(f"step {step}: {len(sel)} cells, {'ALL MATCH docs/27' if bad == 0 else f'{bad} DIFF'}\n", flush=True)
