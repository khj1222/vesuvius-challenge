"""Prediction | errors at 128 | errors at the threshold borrowed from the other scrolls, on the densest labelled crop."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from vesuvius.ink_detection.inference import threshold as T

OUT = Path(sys.argv[1]); seg, arm, step, scroll = sys.argv[2:6]
PRED = Path(r"Z:\아카이브\vesuvius-runs\ink9um_scorecard\preds") / f"{seg}_{arm}_{step}.tif"
LAB = Path("E:/vesuvius-challenge/data/ink_9um/labels/aligned-scrollprizeorg-21slices") / seg
cal = json.loads((OUT / f"loso_step{step}.json").read_text())
borrowed = cal["check_against_other_scrolls"][scroll]["threshold_from_other_scrolls"]
pred = T.read_prediction(PRED)
ink = T.read_mask(LAB / f"{seg}_inklabels.zarr"); sup = T.read_mask(LAB / f"{seg}_supervision_mask.zarr")
curve = T.f1_curve(pred, ink, sup)
H, W = 1000, 1600
ii = np.pad((ink & sup).astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
_, by, bx = max((ii[y+H, x+W] - ii[y, x+W] - ii[y+H, x] + ii[y, x], y, x)
                for y in range(0, max(1, pred.shape[0] - H), 100) for x in range(0, max(1, pred.shape[1] - W), 100))
sl = (slice(by, by + H), slice(bx, bx + W))
p, k, s = pred[sl], ink[sl], sup[sl]

def errors(t):
    m = p >= t
    rgb = np.full((*p.shape, 3), 70, np.uint8)          # outside the supervision mask
    rgb[s] = (0, 0, 0)                                   # true negative
    rgb[s & m & k] = (255, 255, 255)                     # ink found
    rgb[s & m & ~k] = (230, 159, 0)                      # marked, not ink (orange)
    rgb[s & ~m & k] = (86, 180, 233)                     # ink missed (sky blue)
    return rgb

font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
panels = [("prediction (uint8), crop of the densest labelled area", np.repeat(p[..., None], 3, -1)),
          (f"binarized at 128: F1 {curve[128]:.3f} on the whole segment", errors(128)),
          (f"binarized at {borrowed}, the median best threshold of the other two scrolls: F1 {curve[borrowed]:.3f}", errors(borrowed))]
head = [f"{seg}, predicted by the {arm} step-{step} model (trained without {scroll}).",
        f"Best threshold for this segment {int(np.argmax(curve))} (F1 {curve.max():.3f}). Crop y {by}:{by+H}, x {bx}:{bx+W}, at 60%.",
        "white = ink found, orange = marked but not ink, blue = ink missed,",
        "black = correctly left empty, grey = outside the supervision mask (not scored)"]
scale = 0.6; w, h = int(W * scale), int(H * scale)
out = Image.new("RGB", (w, 30 * len(head) + 10 + len(panels) * (h + 40)), (255, 255, 255))
d = ImageDraw.Draw(out)
for i, line in enumerate(head): d.text((6, 6 + 30 * i), line, fill=(0, 0, 0), font=font)
y = 30 * len(head) + 10
for title, img in panels:
    d.text((6, y + 8), title, fill=(0, 0, 0), font=font)
    out.paste(Image.fromarray(img).resize((w, h), Image.NEAREST), (0, y + 36)); y += h + 40
name = OUT / f"compare_{seg}_{arm}_{step}.png"; out.save(name, optimize=True)
print(name, round(float(curve[128]), 4), borrowed, round(float(curve[borrowed]), 4), round(float(curve.max()), 4))
