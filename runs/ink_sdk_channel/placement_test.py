"""Placement test for tools/ink_sdk_channel.py on real geometry (PHerc0841 w00) and a real map.

Ground truth: our full-canvas Reader V3 prediction P (4220x4760 = 20 px per grid step, rendered without
--auto-crop on 10-26). vc_render_tifxyz --auto-crop on the same mesh printed "auto-crop: [4721x4181 from
(19,19)]" (render log 11-14), and that render equals the full render shifted by (19,19) up to +-1 grey
level (mean |diff| 0.002 at (19,19) vs >= 5.7 at any neighbouring shift). The crop below is that
printed one, typed in -- NOT recomputed with the tool's own code.

Each case writes an ink-sdk-shaped run folder (INK_SDK_RECEIPT.json + probability*.npy) whose map is
built from P with the transform ink-sdk would apply, runs the bridge's place(), and compares with P.
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path("E:/vesuvius-challenge")
sys.path.insert(0, str(ROOT / "tools"))
from ink_sdk_channel import PlacementError, place  # noqa: E402

SEG = ROOT / "data/a_lite/PHerc0841_w00/20260220213127-w00"
P = tifffile.imread(ROOT / "data/a_lite/PHerc0841_w00/_segment_ink/20260220213127-w00_klavis_reader-v3.tif")
Y0, X0, H, W = 19, 19, 4181, 4721  # printed by the renderer
CROP = P[Y0:Y0 + H, X0:X0 + W]
results = {"P_shape": list(P.shape), "P_nonzero_outside_crop": int(P.sum() - CROP.astype(np.int64).sum() > 0)}
outside = P.copy(); outside[Y0:Y0 + H, X0:X0 + W] = 0
results["P_nonzero_px_outside_crop"] = int((outside != 0).sum())


def receipt(shape_yx, render_hw, orient=None, mode="native", factors=(1, 1, 1), origin=(0, 0), in_shape=None):
    o = {"traspuesta": False, "filas_invertidas": False, "columnas_invertidas": False}
    o.update(orient or {})
    return {
        "schema": "ink-sdk.receipt.v1", "profile_id": "ink_9um@reader-v3", "primary": "forward",
        "segment": {"surface_mesh": str(SEG), "render": {
            "renderer": "vc_render_tifxyz", "mesh": {"path": str(SEG)}, "scale": 1.0, "auto_crop": True,
            "orientation": o, "shape_zyx": [28, *render_hw], "slice_step": 1,
            "command": ["AppRun", "vc_render_tifxyz", "-v", "ct.zarr", "-g", "0", "--scale", "1.0"]}},
        "input": {"scale_plan": {"mode": mode, "factors_zyx": list(factors), "source_um": 9.366, "target_um": 9.366},
                  "shape_zyx": [17, *(in_shape or shape_yx)], "origin_px": list(origin)},
        "maps": {"forward": {"shape_yx": list(shape_yx), "origin_px": list(origin)}},
    }


def run(name, prob, rec, expect_box):
    canvas, info = place(rec, prob, SEG, "forward")
    y0, y1, x0, x1 = expect_box
    inside = canvas[y0:y1, x0:x1]
    ref = P[y0:y1, x0:x1]
    rest = canvas.copy(); rest[y0:y1, x0:x1] = 0
    ok = bool(canvas.shape == P.shape and np.array_equal(inside, ref) and not rest.any())
    results[name] = {"ok": ok, "canvas": list(canvas.shape), "crop": info["crop_y0x0hw"],
                     "diff_px_in_box": int((inside != ref).sum()), "nonzero_outside_box": int((rest != 0).sum())}
    return canvas


f = CROP.astype(np.float32) / 255.0
# 1 native, auto-crop
run("native_autocrop", f, receipt(f.shape, (H, W)), (Y0, Y0 + H, X0, X0 + W))
# 2 all eight orientation combinations: ink-sdk applies transpose, then rows, then cols
for t in (0, 1):
    for r in (0, 1):
        for c in (0, 1):
            a = f.T if t else f
            a = a[::-1] if r else a
            a = a[:, ::-1] if c else a
            a = np.ascontiguousarray(a)
            run(f"orient_t{t}r{r}c{c}", a,
                receipt(a.shape, a.shape, {"traspuesta": bool(t), "filas_invertidas": bool(r),
                                           "columnas_invertidas": bool(c)}),
                (Y0, Y0 + H, X0, X0 + W))
# 3 ROI (y0,y1,x0,x1 in model-input pixels), origin (x0, y0)
ry0, ry1, rx0, rx1 = 1000, 2200, 1500, 3100
roi = f[ry0:ry1, rx0:rx1]
run("roi", np.ascontiguousarray(roi), receipt(roi.shape, (H, W), origin=(rx0, ry0), in_shape=roi.shape),
    (Y0 + ry0, Y0 + ry1, X0 + rx0, X0 + rx1))
# 4 pool 4x (trim, mean) -- expected = each pooled value repeated over its 4x4 block, at the crop origin
hq, wq = H // 4, W // 4
pooled = CROP[:hq * 4, :wq * 4].reshape(hq, 4, wq, 4).mean(axis=(1, 3)) / 255.0
canvas, info = place(receipt(pooled.shape, (H, W), mode="pool", factors=(4, 4, 4)), pooled.astype(np.float32), SEG, "forward")
exp = np.zeros_like(P)
q = np.rint(np.clip(pooled, 0, 1) * 255).astype(np.uint8)
exp[Y0:Y0 + hq * 4, X0:X0 + wq * 4] = np.kron(q, np.ones((4, 4), np.uint8))
results["pool4"] = {"ok": bool(np.array_equal(canvas, exp)), "diff_px": int((canvas != exp).sum()),
                    "corr_with_P_in_crop": float(np.corrcoef(canvas[Y0:Y0 + hq * 4, X0:X0 + wq * 4].ravel(),
                                                             P[Y0:Y0 + hq * 4, X0:X0 + wq * 4].ravel())[0, 1])}
# 5 must refuse
refusals = {}
for name, rec, prob in [
    ("resample_mode", receipt(f.shape, (H, W), mode="resample"), f),
    ("render_shape_mismatch", receipt(f.shape, (H + 1, W)), f),
    ("map_vs_receipt_shape", receipt((H, W - 1), (H, W)), f),
    ("level_not_0", {**receipt(f.shape, (H, W))}, f),
]:
    if name == "level_not_0":
        rec["segment"]["render"]["command"] = ["AppRun", "vc_render_tifxyz", "-g", "1"]
    try:
        place(rec, prob, SEG, "forward")
        refusals[name] = "NOT refused"
    except PlacementError as e:
        refusals[name] = f"refused: {e}"
results["refusals"] = refusals
results["all_ok"] = all(v["ok"] for k, v in results.items() if isinstance(v, dict) and "ok" in v) and \
    all(v.startswith("refused") for v in refusals.values())
out = Path(__file__).with_name("test_placement_result.json")
out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print(json.dumps(results, indent=2))
