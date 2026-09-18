"""Score a scouted segment on the three pre-registered criteria of docs/25.

Inputs per target: the render (OME-Zarr from vc_render_tifxyz, level 0 = [slices, H, W])
and four prediction TIFFs (seed42/seed43 x step-010000/step-020000). Everything is computed
on the sheet only: a pixel is on-sheet when any rendered slice is non-zero there.

Proxies (docs/25 section 4):
  C1  median skeleton length / equivalent diameter over the 30 largest components (>= 50 px)
      above the prediction's own Otsu threshold, inside the 512 px window with the most
      above-threshold pixels. Computed on seed42 step-020000.
  C2  top-decile IoU between seed42 and seed43 at step-020000, whole sheet and inside the
      C1 window.
  C3  min(low third share, high third share) of on-sheet values in [0, 255], seed42 step-020000.
Guards (reported, never scored): > 128 share per checkpoint and its max/min ratio, max value,
sheet share of canvas.

Usage:
  python tools/score_scouting.py --render R.zarr --pred seed42:010000=a.tif seed42:020000=b.tif \
      seed43:010000=c.tif seed43:020000=d.tif --name pherc0800-xxx --out score.json
The thresholds are applied by summarise_scouting.py against the control and the reference,
not here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
import zarr
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
from skimage.morphology import skeletonize


WINDOW = 512
MIN_COMPONENT = 50
TOP_COMPONENTS = 30


def sheet_mask(render_path: Path) -> np.ndarray:
    group = zarr.open(str(render_path), mode="r")
    arr = group["0"] if "0" in group else group
    mask = np.zeros(arr.shape[1:], dtype=bool)
    for z in range(arr.shape[0]):
        mask |= np.asarray(arr[z]) != 0
    return mask


def read_pred(path: Path, shape: tuple[int, int]) -> np.ndarray:
    pred = tifffile.imread(str(path))
    if pred.ndim == 3:
        pred = pred.max(axis=0)
    if pred.shape != shape:
        raise SystemExit(f"{path}: prediction {pred.shape} does not match render {shape}")
    return pred.astype(np.uint8)


def best_window(binary: np.ndarray, sheet: np.ndarray) -> tuple[int, int]:
    """Top-left of the WINDOW x WINDOW box with the most above-threshold on-sheet pixels."""
    hits = (binary & sheet).astype(np.float32)
    integral = np.pad(hits.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    h, w = hits.shape
    wy, wx = min(WINDOW, h), min(WINDOW, w)
    sums = (
        integral[wy:, wx:] - integral[:-wy, wx:] - integral[wy:, :-wx] + integral[:-wy, :-wx]
    )
    y, x = np.unravel_index(int(np.argmax(sums)), sums.shape)
    return int(y), int(x)


def stroke_ratio(binary: np.ndarray) -> tuple[float, int]:
    labels, n = ndi.label(binary)
    if n == 0:
        return 0.0, 0
    sizes = ndi.sum(binary, labels, index=np.arange(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s >= MIN_COMPONENT]
    keep = sorted(keep, key=lambda i: -sizes[i - 1])[:TOP_COMPONENTS]
    if not keep:
        return 0.0, 0
    skel = skeletonize(binary)
    ratios = []
    for i in keep:
        comp = labels == i
        area = float(sizes[i - 1])
        length = float((skel & comp).sum())
        eq_diam = 2.0 * np.sqrt(area / np.pi)
        ratios.append(length / eq_diam)
    return float(np.median(ratios)), len(keep)


def top_decile_iou(a: np.ndarray, b: np.ndarray, region: np.ndarray) -> float:
    va, vb = a[region], b[region]
    if va.size == 0:
        return 0.0
    ta, tb = np.percentile(va, 90), np.percentile(vb, 90)
    sa, sb = va >= ta, vb >= tb
    union = (sa | sb).sum()
    return float((sa & sb).sum() / union) if union else 0.0


def thirds(values: np.ndarray) -> dict[str, float]:
    n = values.size
    low = float((values < 85).sum() / n)
    high = float((values >= 170).sum() / n)
    return {"low": low, "mid": 1.0 - low - high, "high": high, "min_outer": min(low, high)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True, type=Path)
    ap.add_argument("--pred", nargs="+", required=True, help="seedNN:STEP=path.tif")
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--primary", default="seed42:020000")
    ap.add_argument("--partner", default="seed43:020000")
    args = ap.parse_args()

    sheet = sheet_mask(args.render)
    preds = {}
    for spec in args.pred:
        key, path = spec.split("=", 1)
        preds[key] = read_pred(Path(path), sheet.shape)
    if args.primary not in preds or args.partner not in preds:
        raise SystemExit(f"need both {args.primary} and {args.partner} among --pred")

    primary = preds[args.primary]
    thr = float(threshold_otsu(primary[sheet])) if sheet.any() else 255.0
    binary = (primary >= thr) & sheet
    y, x = best_window(binary, sheet)
    win = (slice(y, y + WINDOW), slice(x, x + WINDOW))
    c1, n_components = stroke_ratio(binary[win])
    partner = preds[args.partner]
    c2_sheet = top_decile_iou(primary, partner, sheet)
    win_region = np.zeros_like(sheet)
    win_region[win] = sheet[win]
    c2_window = top_decile_iou(primary, partner, win_region)
    c3 = thirds(primary[sheet])

    guards = {}
    for key, pred in preds.items():
        on = pred[sheet]
        guards[key] = {
            "gt128_share": float((on > 128).mean()),
            "max": int(on.max()),
            "median": int(np.median(on)),
        }
    shares = [g["gt128_share"] for g in guards.values()]
    out = {
        "name": args.name,
        "render": str(args.render),
        "canvas": list(sheet.shape),
        "sheet_share_of_canvas": float(sheet.mean()),
        "primary": args.primary,
        "partner": args.partner,
        "otsu_threshold": thr,
        "window_top_left": [y, x],
        "window_above_threshold_px": int(binary[win].sum()),
        "C1_stroke_ratio": c1,
        "C1_components_used": n_components,
        "C2_top_decile_iou_sheet": c2_sheet,
        "C2_top_decile_iou_window": c2_window,
        "C3_thirds": c3,
        "C3_min_outer": c3["min_outer"],
        "guards": guards,
        "guard_gt128_ratio_max_over_min": (max(shares) / min(shares)) if min(shares) > 0 else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("name", "C1_stroke_ratio", "C2_top_decile_iou_sheet",
                                          "C2_top_decile_iou_window", "C3_min_outer",
                                          "guard_gt128_ratio_max_over_min")}))


if __name__ == "__main__":
    main()
