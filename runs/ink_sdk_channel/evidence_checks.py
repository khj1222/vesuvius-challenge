"""Recompute, and save, the two checks that were only printed on 2026-11-14:
 1. crop truth: vc_render_tifxyz --auto-crop renders vs our full-canvas renders (PHerc0841 w00, ag144);
    the offset the renderer printed, the offset tools/ink_sdk_channel.py computes, and mean |diff| of one
    layer at that offset and its +-1 neighbours.
 2. canvas origin: Reader V3 (via ink-sdk) on the same depth-matched input, full canvas vs the 19-px
    auto-cropped canvas, and both against the real ink-sdk mesh run.
Also writes a path-free summary of the real ink-sdk run receipts.
Paths are this machine's; data are the public PHerc0841 files named in docs/37."""
import json, re, sys
from pathlib import Path
import numpy as np, zarr

ROOT = Path("E:/vesuvius-challenge")
sys.path.insert(0, str(ROOT / "tools"))
from ink_sdk_channel import read_tif, render_canvas  # noqa: E402
OUT = ROOT / "planning/2026-11-14_ink_sdk_bridge/results"
A = ROOT / "data/a_lite"

crop = {}
for name, seg, full, auto in [
        ("w00", "PHerc0841_w00/20260220213127-w00", "PHerc0841_w00/_segment_ink/20260220213127-w00_render.zarr",
         "PHerc0841_w00/_segment_ink/w00_autocrop_render.zarr"),
        ("ag144", "PHerc0841_ag144/20260220214732-ag144", "PHerc0841_ag144/_segment_ink/20260220214732-ag144_render.zarr",
         "PHerc0841_ag144/_segment_ink/ag144_autocrop_render.zarr")]:
    log = (A / (auto + ".render.log")).read_text(encoding="utf-8", errors="replace").replace("\r", "\n")
    m = re.search(r"auto-crop: \[(\d+)\D+(\d+) from \((\d+),(\d+)\)\]", log)
    w, h, x0, y0 = map(int, m.groups())
    meta = json.loads((A / seg / "meta.json").read_text())
    x = read_tif(A / seg / "x.tif").astype(np.float64)
    _, (cy, cx, ch, cw) = render_canvas(x.shape[:2], meta, 1.0, x, True)
    a = zarr.open(str(A / auto / "0"), mode="r")[14].astype(np.int32)
    f = zarr.open(str(A / full / "0"), mode="r")[14].astype(np.int32)
    H, W = a.shape
    grid = {f"{dy - y0},{dx - x0}": round(float(np.abs(a[:H - 2, :W - 2] - f[dy:dy + H - 2, dx:dx + W - 2]).mean()), 3)
            for dy in (y0 - 1, y0, y0 + 1) for dx in (x0 - 1, x0, x0 + 1)}
    crop[name] = {"renderer_printed": {"w": w, "h": h, "x0": x0, "y0": y0},
                  "tool_computed": {"w": cw, "h": ch, "x0": cx, "y0": cy},
                  "equal": (w, h, x0, y0) == (cw, ch, cx, cy),
                  "layer14_mean_abs_diff_by_shift_from_printed_origin": grid}
(OUT / "crop_truth.json").write_text(json.dumps(crop, indent=2) + "\n")

R = A / "PHerc0841_w00/_ink_sdk_real"
cc = lambda p, q: round(float(np.corrcoef(p[20:-20, 20:-20].ravel(), q[20:-20, 20:-20].ravel())[0, 1]), 5)
origin = {}
for key, fn in (("forward", "probability.npy"), ("reverse", "probability_reverse.npy")):
    mesh = np.load(R / "mesh_v3" / fn)
    cropped = np.load(R / "halfshift_crop_v3" / fn)
    full = np.load(R / "halfshift_v3" / fn)[19:19 + 4181, 19:19 + 4721]
    d = np.abs(cropped - full) * 255
    origin[key] = {"same_input_full_vs_cropped_canvas_corr": cc(cropped, full),
                   "diff_grey_median_p90_p99": [round(float(v), 1) for v in np.percentile(d, [50, 90, 99])],
                   "mesh_run_vs_same_canvas_depth_matched_corr": cc(mesh, cropped),
                   "mesh_run_vs_full_canvas_depth_matched_corr": cc(mesh, full)}
origin["note"] = ("ink-sdk 'reverse' is the reading side on w00 here (ink-sdk renders without --flip-normals). "
                  "Depth-matched input: layer i = mean of layers 21-i and 22-i of our 28-layer render.")
(OUT / "canvas_origin_check.json").write_text(json.dumps(origin, indent=2) + "\n")

def strip(v):
    if isinstance(v, str):
        v = re.sub(r"[A-Za-z]:[\\/][^\s\"']*|/(?:mnt|root|home|tmp)/[^\s\"']*", lambda m: "<path>/" + re.split(r"[\\/]", m.group(0))[-1], v)
    elif isinstance(v, list):
        v = [strip(i) for i in v]
    elif isinstance(v, dict):
        v = {k: strip(i) for k, i in v.items() if k not in ("environment", "stderr_tail")}
    return v
summary = {}
for run in ("full_v3", "mesh_v3"):
    r = json.loads((R / run / "INK_SDK_RECEIPT.json").read_text())
    summary[run] = strip({k: r[k] for k in ("schema", "sdk_version", "profile_id", "checkpoint", "input", "primary",
                                            "runtime_seconds")} |
                         {"villa_revision": r["execution"].get("villa_revision"),
                          "maps": {k: {kk: v[kk] for kk in ("shape_yx", "origin_px", "direction")} | {"liveness": v["liveness"]["verdict"]}
                                   for k, v in r["maps"].items()}})
rr = json.loads((R / "render_mesh/render/RENDER_RECEIPT.json").read_text())
summary["mesh_render"] = strip({k: rr[k] for k in ("schema", "command", "scale", "num_slices", "slice_step", "auto_crop",
                                                   "orientation", "shape_zyx", "pixel_um", "mesh", "render_crop")})
text = json.dumps(summary, indent=2) + "\n"
assert not re.search(r"[A-Za-z]:[\\/]|/(?:mnt|root|home|Users)/", text), "absolute path left in summary"
(OUT / "real_runs_summary.json").write_text(text)
print(json.dumps(crop, indent=1)); print(json.dumps(origin, indent=1))
