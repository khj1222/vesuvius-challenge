#!/usr/bin/env python3
"""check_ink_depth_profile.py -- docs/31 post-hoc check (not pre-registered): at which slice of the 27-slice
wide volumes does annotated ink differ most from annotated background?

For each segment, mean raw intensity inside ink minus inside non-ink (within the supervision mask), per
slice. The annotation sits at slice 13. A rough indicator only: the difference also reflects papyrus vs
gap, not ink alone. Writes runs/segrobust/widejitter_ink_depth_profile.json.

    external/villa/ink-detection/.venv/Scripts/python.exe tools/check_ink_depth_profile.py

License: MIT.
"""
import zarr, numpy as np, json
R="E:/vesuvius-challenge/data/ink_9um"
out={}
def prof(vol, ink, sup):
    v=np.asarray(vol).astype(np.float32)
    bg=sup&~ink
    return [float(v[z][ink].mean()-v[z][bg].mean()) for z in range(v.shape[0])]
for seg in ["pherc0841-w00","pherc0841-ag144","pherc0841-ag174","pherc0009b-ag055","pherc0500p2-s1"]:
    vol=zarr.open(f"{R}/surface-volumes/openlabels9_wide/{seg}.zarr",mode="r")["0"]
    sup=np.asarray(zarr.open(f"{R}/labels/openlabels9/{seg}/{seg}_supervision_mask.zarr",mode="r")["0"][0])>0
    ink=(np.asarray(zarr.open(f"{R}/labels/openlabels9/{seg}/{seg}_inklabels.zarr",mode="r")["0"][0])>0)&sup
    s=(slice(None),slice(None,None,2),slice(None,None,2))
    out[seg]=prof(vol[s], ink[::2,::2], sup[::2,::2])
for seg in ["pherc0139-w028","pherc1667-w018","phercparis4-w02"]:
    vol=zarr.open(f"{R}/surface-volumes/aligned9_wide/{seg}.zarr",mode="r")["0"]
    lab=f"{R}/labels/aligned-scrollprizeorg-27slices/{seg}/{seg}_"
    sup=np.asarray(zarr.open(lab+"supervision_mask.zarr",mode="r")["0"][13,::4,::4])>0
    ink=(np.asarray(zarr.open(lab+"inklabels.zarr",mode="r")["0"][13,::4,::4])>0)&sup
    out[seg]=prof(vol[:,::4,::4], ink, sup)
for k,p in out.items():
    p=np.array(p); print(f"{k:18s} peak slice {int(np.argmax(p)):2d}  "+" ".join(f"{x:5.1f}" for x in p))
json.dump(out,open("E:/vesuvius-challenge/runs/segrobust/widejitter_ink_depth_profile.json","w"),indent=1)
