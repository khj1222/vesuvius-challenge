"""Put ink-sdk probability maps on a tifxyz segment's point grid, as VC3D object-store `ink_*` channels.

ink-sdk (github.com/LimeGS/ink-sdk) renders a tifxyz segment and runs a battery of ink models on it,
writing `probability*.npy` plus `INK_SDK_RECEIPT.json` per run. VC3D's object store keeps ink as a
surface channel: an image whose sides are whole multiples of the point grid ("20 pixels per grid
step"). An ink-sdk map is generally NOT on that grid as written:
  * the render uses `--auto-crop`, so map pixel (0, 0) sits at the valid-point bounding box, not at
    grid (0, 0) -- the renderer prints the offset to stdout, which the receipt does not keep;
  * with an umbilicus, ink-sdk may transpose / flip rows / flip columns after rendering;
  * a 2.4 um source is pooled 4x (the remainder is trimmed), and `--roi` crops after pooling.
This tool undoes each step using only the receipt and the mesh, and refuses whatever it cannot place
exactly. The offset is recomputed with vc_render_tifxyz's own rule (bounding box of points whose x
is finite and not -1, times render_scale / meta scale, floor at the low edge), and checked against
the render shape the receipt records.

Then the channels go where segment_ink v2 puts them (tools/segment_ink.py): an importable store
folder (default) or `vc_object_ingest --surface-channel`. Showing `ink*` channels in VC3D's Ink
Detection panel needs the VC3D change on branch feat/vc3d-ink-surface-channel (not in villa main yet).

Usage:
  python tools/ink_sdk_channel.py RUN_DIR [RUN_DIR ...] [--maps primary|forward|reverse|mean|all]
  python tools/ink_sdk_channel.py BATTERY_DIR            # every INK_SDK_RECEIPT.json below it
  python tools/ink_sdk_channel.py RUN_DIR --segment SEG  # surface-volume runs: full canvas, no crop
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segment_ink import add_store_channel, channel_name, store_uuid, write_store_folder  # noqa: E402

RECEIPT = "INK_SDK_RECEIPT.json"
MAP_FILES = {"forward": "probability.npy", "reverse": "probability_reverse.npy",
             "mean": "probability_mean.npy"}


class PlacementError(Exception):
    pass


def read_tif(path: Path) -> np.ndarray:
    import tifffile
    return tifffile.imread(path)


def grid_scale(meta: dict) -> tuple[float, float]:
    """meta.json "scale" is [sx, sy]: grid steps per voxel along columns and rows."""
    s = meta.get("scale")
    if not (isinstance(s, list) and len(s) == 2 and s[0] > 0 and s[1] > 0):
        raise PlacementError(f"meta.json has no usable scale: {s!r}")
    return float(s[0]), float(s[1])


def valid_bbox(x: np.ndarray) -> tuple[int, int, int, int]:
    """vc_render_tifxyz: points with x == -1 become NaN; bbox of points whose x is finite."""
    ok = np.isfinite(x) & (x != -1)
    if not ok.any():
        raise PlacementError("mesh has no valid points")
    rows = np.flatnonzero(ok.any(axis=1))
    cols = np.flatnonzero(ok.any(axis=0))
    return int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])


def render_canvas(grid_hw: tuple[int, int], meta: dict, render_scale: float, x: np.ndarray | None,
                  auto_crop: bool) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
    """Full canvas (H, W) and crop (y0, x0, h, w) in render pixels, as vc_render_tifxyz computes them."""
    msx, msy = grid_scale(meta)
    # QuadSurface::_scale is cv::Vec2f: 0.05 is stored as float32 0.0500000007, so the factor is
    # 19.9999997, not 20, and floor(col_min * sx) lands one pixel low (0841 w00: crop from (19,19),
    # as the renderer itself prints). Reproduce the float32 -> double promotion exactly.
    sx = float(render_scale) / float(np.float32(msx))
    sy = float(render_scale) / float(np.float32(msy))
    full_w = max(1, int(round(grid_hw[1] * sx)))  # std::lround
    full_h = max(1, int(round(grid_hw[0] * sy)))
    if not auto_crop:
        return (full_h, full_w), (0, 0, full_h, full_w)
    rmin, rmax, cmin, cmax = valid_bbox(x)
    x0, y0 = math.floor(cmin * sx), math.floor(rmin * sy)
    x1, y1 = math.ceil((cmax + 1) * sx), math.ceil((rmax + 1) * sy)
    # cv::Rect & canvasROI
    x0c, y0c = max(x0, 0), max(y0, 0)
    x1c, y1c = min(x1, full_w), min(y1, full_h)
    return (full_h, full_w), (y0c, x0c, y1c - y0c, x1c - x0c)


def undo_orientation(a: np.ndarray, orientation: dict) -> np.ndarray:
    """ink-sdk applies transpose, then flip rows, then flip columns; undo in reverse order."""
    if orientation.get("columnas_invertidas"):
        a = a[:, ::-1]
    if orientation.get("filas_invertidas"):
        a = a[::-1, :]
    if orientation.get("traspuesta"):
        a = a.T
    return a


def to_uint8(p: np.ndarray) -> np.ndarray:
    """Same quantisation as ink-sdk's own preview.tif."""
    p = np.nan_to_num(np.asarray(p, dtype=np.float32), nan=0.0, posinf=1.0, neginf=0.0)
    return np.rint(np.clip(p, 0.0, 1.0) * 255.0).astype(np.uint8)


def render_receipt(receipt: dict) -> dict | None:
    """The render receipt: inside the run receipt (mesh + CT runs), or next to a surface volume that
    `ink-sdk render` wrote (RENDER_RECEIPT.json in the folder, or `ink_sdk_render` in its .zattrs)."""
    seg = receipt.get("segment") or {}
    if seg.get("render"):
        return seg["render"]
    sv = seg.get("surface_volume")
    if not sv:
        return None
    sv = Path(sv)
    for folder in (sv, sv.parent):
        if (folder / "RENDER_RECEIPT.json").is_file():
            return json.loads((folder / "RENDER_RECEIPT.json").read_text(encoding="utf-8"))
        if (folder / ".zattrs").is_file():
            attrs = json.loads((folder / ".zattrs").read_text(encoding="utf-8"))
            if isinstance(attrs.get("ink_sdk_render"), dict):
                return attrs["ink_sdk_render"]
    return None


def place(receipt: dict, prob: np.ndarray, seg_dir: Path, map_key: str) -> tuple[np.ndarray, dict]:
    """Return the map on the full render canvas (uint8) and a placement record."""
    meta = json.loads((seg_dir / "meta.json").read_text(encoding="utf-8"))
    x = read_tif(seg_dir / "x.tif").astype(np.float64)
    grid_hw = x.shape[:2]

    inp = receipt.get("input") or {}
    plan = inp.get("scale_plan") or {}
    mode = plan.get("mode")
    if mode not in ("native", "pool"):
        raise PlacementError(f"scale plan mode {mode!r} is not supported (native and integer pooling only)")
    fz, fy, fx = (plan.get("factors_zyx") or [1, 1, 1]) if mode == "pool" else (1, 1, 1)
    info = receipt["maps"][map_key]
    if list(prob.shape) != list(info["shape_yx"]):
        raise PlacementError(f"{map_key}: array {prob.shape} != receipt shape {info['shape_yx']}")
    in_hw = (inp.get("shape_zyx") or [0, 0, 0])[1:]
    if list(prob.shape) != list(in_hw):
        raise PlacementError(f"{map_key}: map {prob.shape} is not the model input's {in_hw}")
    ox, oy = (info.get("origin_px") or [0, 0])  # ROI origin (x, y) in model-input pixels

    render = render_receipt(receipt)
    if render:
        if render.get("renderer") != "vc_render_tifxyz":
            raise PlacementError(f"renderer {render.get('renderer')!r} is not vc_render_tifxyz")
        # Same mesh? Compare the x/y/z hashes the render receipt keeps (paths differ across WSL/Windows).
        hashes = (render.get("mesh") or {}).get("sha256") or {}
        if hashes:
            import hashlib
            for axis in "xyz":
                got = hashlib.sha256((seg_dir / f"{axis}.tif").read_bytes()).hexdigest()
                if hashes.get(axis) != got:
                    raise PlacementError(f"{axis}.tif differs from the mesh the render used ({render['mesh'].get('path')})")
        elif Path(render["mesh"]["path"]).resolve() != seg_dir.resolve():
            raise PlacementError(f"receipt mesh {render['mesh']['path']} is not {seg_dir}")
        if "-g" in render.get("command", []) and render["command"][render["command"].index("-g") + 1] != "0":
            raise PlacementError("render was not from CT level 0")
        render_scale = float(render["scale"])
        auto_crop = bool(render.get("auto_crop"))
        orientation = render.get("orientation") or {}
        render_hw = tuple(render["shape_zyx"][1:])  # after ink-sdk's own orientation step
    else:
        # A surface volume given directly: accept only a full-canvas render at an integer grid factor.
        render_scale, auto_crop, orientation, render_hw = None, False, {}, None

    if render_scale is None:
        hw = (in_hw[0] * fy, in_hw[1] * fx)
        k = (hw[0] / grid_hw[0], hw[1] / grid_hw[1])
        if not (k[0] == int(k[0]) and k[1] == int(k[1]) and k[0] >= 1):
            raise PlacementError(
                f"surface-volume run: input {in_hw} x pool {fy} is not a whole multiple of the grid {grid_hw}; "
                "only full-canvas, uncropped renders can be placed without a render receipt")
        msx, msy = grid_scale(meta)
        render_scale = k[1] * msx
        orientation = {}

    (full_h, full_w), (cy0, cx0, ch, cw) = render_canvas(grid_hw, meta, render_scale, x, auto_crop)
    oriented_hw = (cw, ch) if orientation.get("traspuesta") else (ch, cw)
    if render_hw is not None and tuple(render_hw) != oriented_hw:
        raise PlacementError(f"recomputed render crop {oriented_hw} != receipt render shape {render_hw}")
    if full_h % grid_hw[0] or full_w % grid_hw[1]:
        raise PlacementError(f"canvas {full_h}x{full_w} is not a whole multiple of the grid {grid_hw}")

    # Model-input pixels -> render pixels (in ink-sdk's oriented frame), then undo orientation.
    a = to_uint8(prob)
    if fy > 1 or fx > 1:
        a = np.repeat(np.repeat(a, fy, axis=0), fx, axis=1)
    oriented = np.zeros(oriented_hw, dtype=np.uint8)
    y0, x0 = oy * fy, ox * fx
    h = min(a.shape[0], oriented_hw[0] - y0)
    w = min(a.shape[1], oriented_hw[1] - x0)
    if h <= 0 or w <= 0:
        raise PlacementError("ROI falls outside the render")
    oriented[y0:y0 + h, x0:x0 + w] = a[:h, :w]
    crop = undo_orientation(oriented, orientation)
    canvas = np.zeros((full_h, full_w), dtype=np.uint8)
    canvas[cy0:cy0 + ch, cx0:cx0 + cw] = crop
    record = {
        "map": map_key, "profile": receipt.get("profile_id"), "grid_hw": list(grid_hw),
        "canvas_hw": [full_h, full_w], "px_per_grid_step": [full_h // grid_hw[0], full_w // grid_hw[1]],
        "crop_y0x0hw": [cy0, cx0, ch, cw], "auto_crop": auto_crop, "pool_yx": [fy, fx],
        "roi_origin_xy": [ox, oy], "orientation": {k: orientation.get(k) for k in
                                                   ("traspuesta", "filas_invertidas", "columnas_invertidas")},
    }
    return canvas, record


def find_receipts(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        if (p / RECEIPT).is_file():
            out.append(p / RECEIPT)
        else:
            out.extend(sorted(p.rglob(RECEIPT)))
    if not out:
        sys.exit(f"no {RECEIPT} under {', '.join(map(str, paths))}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+", type=Path, help="ink-sdk run folders (or a battery folder)")
    ap.add_argument("--segment", type=Path, help="tifxyz folder (default: the mesh in the receipt)")
    ap.add_argument("--maps", choices=("primary", "forward", "reverse", "mean", "all"), default="primary")
    ap.add_argument("--work", type=Path, help="output folder (default: <segment>/../_ink_sdk_channels)")
    ap.add_argument("--target", action="append", choices=("store-folder", "store"))
    ap.add_argument("--store")
    ap.add_argument("--store-uuid")
    ap.add_argument("--ingest-cmd", default="vc_object_ingest")
    ap.add_argument("--author", default="ink_sdk_channel")
    args = ap.parse_args()
    targets = args.target or ["store-folder"]
    if "store" in targets and not args.store:
        sys.exit("--target store needs --store")

    import tifffile

    seg_dir = None
    channels: dict[str, Path] = {}
    records = []
    for rp in find_receipts([p.resolve() for p in args.runs]):
        run = rp.parent
        receipt = json.loads(rp.read_text(encoding="utf-8"))
        rr = render_receipt(receipt)
        mesh = (receipt.get("segment") or {}).get("surface_mesh") or (rr["mesh"]["path"] if rr else None)
        this_seg = (args.segment or (Path(mesh) if mesh else None))
        if this_seg is None:
            sys.exit(f"{run}: surface-volume run; give --segment")
        this_seg = this_seg.resolve()
        if seg_dir is None:
            seg_dir = this_seg
        elif this_seg != seg_dir:
            sys.exit(f"{run}: segment {this_seg} differs from {seg_dir}; one segment per call")
        keys = list(receipt["maps"]) if args.maps == "all" else (
            [receipt["primary"]] if args.maps == "primary" else [args.maps])
        work = (args.work or seg_dir.parent / "_ink_sdk_channels").resolve()
        work.mkdir(parents=True, exist_ok=True)
        for key in keys:
            if key not in receipt["maps"]:
                sys.exit(f"{run}: no {key!r} map (has {sorted(receipt['maps'])})")
            prob = np.load(run / MAP_FILES[key])
            try:
                canvas, rec = place(receipt, prob, seg_dir, key)
            except PlacementError as e:
                sys.exit(f"{run} [{key}]: cannot place: {e}")
            stem = re.sub(r"[@.]", "_", receipt.get("profile_id") or run.name)
            name = channel_name(stem if key == "forward" else f"{stem}_{key}")
            if name in channels:
                name = channel_name(f"{name}_{run.name}")
            out = work / f"{seg_dir.name}_{name}.tif"
            tifffile.imwrite(out, canvas)
            channels[name] = out
            rec.update(channel=name, run=str(run), tif=str(out))
            records.append(rec)
            print(f"channel {name}: {rec['canvas_hw'][0]}x{rec['canvas_hw'][1]} "
                  f"({rec['px_per_grid_step'][0]} px/grid step), crop {rec['crop_y0x0hw']}, pool {rec['pool_yx']}")

    meta = json.loads((seg_dir / "meta.json").read_text(encoding="utf-8"))
    work = (args.work or seg_dir.parent / "_ink_sdk_channels").resolve()
    (work / "placement.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    if "store-folder" in targets:
        folder = work / f"{seg_dir.name}-store"
        uid = write_store_folder(seg_dir, meta, folder, channels)
        print(f"store folder (surface uuid {uid}): {folder}")
    if "store" in targets:
        uid = args.store_uuid or store_uuid(seg_dir, meta)
        for name, out in channels.items():
            add_store_channel(args.ingest_cmd, args.store, args.author, uid, name, out)
            print(f"store {args.store}: surface {uid} channel {name}")


if __name__ == "__main__":
    main()
