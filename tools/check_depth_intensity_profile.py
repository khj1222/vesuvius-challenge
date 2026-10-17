#!/usr/bin/env python3
"""check_depth_intensity_profile.py -- docs/31 follow-up (post-hoc, not pre-registered): which way along the
slice axis of the 27-slice wide volumes is the target sheet, and which way the gap to the next sheet?

For each segment, mean raw intensity per slice inside the supervision mask. The traced surface (annotation
centre) is slice 13. Reports the brightest slice, the darkest slice within 8 slices on the + side of it (the
gap), and the half-maximum crossing between the two (a rough position of the sheet face). In docs/31's perturbed renders a
shift of k makes the model read the slices k positions further along this axis (out[z] = vol[z + k]), so
-k reads toward lower slice index. Writes runs/segrobust/widejitter_depth_intensity_profile.json.

    external/villa/ink-detection/.venv/Scripts/python.exe tools/check_depth_intensity_profile.py

License: MIT.
"""
import json

import numpy as np
import zarr

R = "E:/vesuvius-challenge/data/ink_9um"
CENTRE = 13


def summarise(m):
    m = np.asarray(m)
    peak = int(np.argmax(m))
    gap = peak + int(np.argmin(m[peak:peak + 9]))   # first dip within 8 slices: the gap, not the far end
    half = (m[peak] + m[gap]) / 2
    face = None
    for z in range(peak, gap):           # linear interpolation of the first crossing below half-max
        if m[z] >= half > m[z + 1]:
            face = z + (m[z] - half) / (m[z] - m[z + 1])
            break
    return {"profile": [round(float(x), 2) for x in m], "peak_slice": peak, "gap_slice": gap,
            "face_slice": None if face is None else round(float(face), 2),
            "peak_minus_gap": round(float(m[peak] - m[gap]), 2)}


out = {}
for seg in ["pherc0841-w00", "pherc0841-ag144", "pherc0841-ag174", "pherc0009b-ag055", "pherc0500p2-s1"]:
    vol = zarr.open(f"{R}/surface-volumes/openlabels9_wide/{seg}.zarr", mode="r")["0"]
    sup = np.asarray(zarr.open(f"{R}/labels/openlabels9/{seg}/{seg}_supervision_mask.zarr", mode="r")["0"][0]) > 0
    v = np.asarray(vol[:, ::4, ::4]).astype(np.float32)
    out[seg] = summarise([v[z][sup[::4, ::4]].mean() for z in range(v.shape[0])])
for seg in ["pherc0139-w028", "pherc1667-w018", "phercparis4-w02"]:
    vol = zarr.open(f"{R}/surface-volumes/aligned9_wide/{seg}.zarr", mode="r")["0"]
    lab = f"{R}/labels/aligned-scrollprizeorg-27slices/{seg}/{seg}_"
    sup = np.asarray(zarr.open(lab + "supervision_mask.zarr", mode="r")["0"][CENTRE, ::4, ::4]) > 0
    v = np.asarray(vol[:, ::4, ::4]).astype(np.float32)
    out[seg] = summarise([v[z][sup].mean() for z in range(v.shape[0])])
for k, s in out.items():
    print(f"{k:18s} peak {s['peak_slice']:2d}  gap {s['gap_slice']:2d}  face {s['face_slice']}  "
          f"contrast {s['peak_minus_gap']:5.1f}  " + " ".join(f"{x:4.0f}" for x in s["profile"]))
json.dump({"centre_slice": CENTRE, "segments": out},
          open("E:/vesuvius-challenge/runs/segrobust/widejitter_depth_intensity_profile.json", "w"), indent=1)
