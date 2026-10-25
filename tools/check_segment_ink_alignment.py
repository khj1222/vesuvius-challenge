"""Check that a segment_ink prediction lands on the same pixels as the team's catalog ink map.

Both images span the segment's full point grid, so after resizing ours to the catalog map's size
the same papyrus should sit at the same pixel. The two maps come from different models and scans
(ours: ink_9um on the 9.362 um render; the team's: their 2.4 um model), so the test is not how
similar they are but WHERE they agree best: of the four orientations that keep the canvas shape
(as is, left-right, up-down, 180 deg) the unflipped one must correlate highest, and clearly above
the same map shifted by a tenth of the canvas (a null that keeps both images' statistics).

Usage: python tools/check_segment_ink_alignment.py OURS.tif TEAM.jpg [--out report.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter


def load_gray(path: Path) -> np.ndarray:
    if path.suffix.lower() in (".tif", ".tiff"):
        a = tifffile.imread(path)
    else:
        a = np.asarray(Image.open(path).convert("L"))
    return a.astype(np.float32)


def corr(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    x, y = a[mask], b[mask]
    x = x - x.mean()
    y = y - y.mean()
    return float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum() + 1e-12))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ours", type=Path)
    ap.add_argument("team", type=Path)
    ap.add_argument("--blur", type=float, default=2.0, help="gaussian sigma in team-map pixels")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    team = load_gray(args.team)
    ours_full = load_gray(args.ours)
    h, w = team.shape
    ours = np.asarray(Image.fromarray(ours_full).resize((w, h), Image.BILINEAR), dtype=np.float32)
    team_b = gaussian_filter(team, args.blur)
    variants = {
        "as_is": ours,
        "flip_lr": ours[:, ::-1],
        "flip_ud": ours[::-1, :],
        "rot180": ours[::-1, ::-1],
    }
    scores = {}
    for name, v in variants.items():
        vb = gaussian_filter(v, args.blur)
        mask = (team > 0) & (v > 0)
        scores[name] = corr(vb, team_b, mask)
    shifts = {}
    for name, (dy, dx) in {"shift_x+10%": (0, w // 10), "shift_y+10%": (h // 10, 0),
                           "shift_x-10%": (0, -(w // 10)), "shift_y-10%": (-(h // 10), 0)}.items():
        v = np.roll(ours, (dy, dx), axis=(0, 1))
        mask = (team > 0) & (v > 0)
        shifts[name] = corr(gaussian_filter(v, args.blur), team_b, mask)
    best = max(scores, key=scores.get)
    null_max = max(shifts.values())
    report = {
        "ours": str(args.ours), "team": str(args.team),
        "ours_shape": list(ours_full.shape), "team_shape": [h, w],
        "aspect_ours": ours_full.shape[1] / ours_full.shape[0], "aspect_team": w / h,
        "orientation_corr": scores, "shifted_null_corr": shifts,
        "best_orientation": best, "pass": best == "as_is" and scores["as_is"] > 2 * max(null_max, 0.0) and scores["as_is"] > 0.1,
    }
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
