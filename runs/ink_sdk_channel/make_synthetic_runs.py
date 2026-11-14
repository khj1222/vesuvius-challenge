"""Two ink-sdk-shaped run folders from real 0841 w00 predictions, cropped like an --auto-crop render
(crop (19,19) 4181x4721, as the renderer printed). Run A: Reader V3 forward + reverse, native.
Run B: ink_9um seed43 forward, pooled 4x (trim + mean, as ink-sdk's pool_volume). Placement inputs only;
these are NOT ink-sdk inference outputs."""
import json, sys
from pathlib import Path
import numpy as np, tifffile
R = Path("E:/vesuvius-challenge/data/a_lite/PHerc0841_w00"); SEG = R / "20260220213127-w00"
OUT = R / "_ink_sdk_synthetic"
Y0, X0, H, W = 19, 19, 4181, 4721
def rec(profile, maps, shape, mode="native", f=(1, 1, 1)):
    return {"schema": "ink-sdk.receipt.v1", "profile_id": profile, "primary": "forward", "synthetic": True,
            "segment": {"surface_mesh": str(SEG), "render": {"renderer": "vc_render_tifxyz", "mesh": {"path": str(SEG)},
                "scale": 1.0, "auto_crop": True, "orientation": {"traspuesta": False, "filas_invertidas": False,
                "columnas_invertidas": False}, "shape_zyx": [28, H, W], "slice_step": 1,
                "command": ["AppRun", "vc_render_tifxyz", "-g", "0", "--scale", "1.0", "--auto-crop"]}},
            "input": {"scale_plan": {"mode": mode, "factors_zyx": list(f)}, "shape_zyx": [17, *shape], "origin_px": [0, 0]},
            "maps": {k: {"shape_yx": list(shape), "origin_px": [0, 0]} for k in maps}}
w = R / "_segment_ink"
a = OUT / "runA_reader_v3"; a.mkdir(parents=True, exist_ok=True)
for key, fn in (("forward", "20260220213127-w00_klavis_reader-v3.tif"), ("reverse", "20260220213127-w00_klavis_reader-v3_reverse.tif")):
    m = tifffile.imread(w / fn)[Y0:Y0 + H, X0:X0 + W].astype(np.float32) / 255
    np.save(a / ("probability.npy" if key == "forward" else "probability_reverse.npy"), m)
(a / "INK_SDK_RECEIPT.json").write_text(json.dumps(rec("ink_9um@reader-v3", ["forward", "reverse"], (H, W)), indent=2))
b = OUT / "runB_seed43_pool4"; b.mkdir(parents=True, exist_ok=True)
c = tifffile.imread(w / "20260220213127-w00_hybrid_3d2d-seed43_step-075000.tif")[Y0:Y0 + H, X0:X0 + W]
hq, wq = H // 4, W // 4
p = (c[:hq * 4, :wq * 4].reshape(hq, 4, wq, 4).mean(axis=(1, 3)) / 255).astype(np.float32)
np.save(b / "probability.npy", p)
(b / "INK_SDK_RECEIPT.json").write_text(json.dumps(rec("ink_9um@scrollprize-seed43-step75000", ["forward"], p.shape, "pool", (4, 4, 4)), indent=2))
print("ok", OUT)
