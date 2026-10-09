<!--
Third reply to kartoun on villa #192 (draft 2026-10-09). NOT posted — the user posts it, and only if
the user grants the permission he asked for.
  target: https://github.com/ScrollPrize/villa/issues/192
  replying to: kartoun 2026-10-07 12:37Z (issuecomment-6038055753), asking permission to add our Frag1
  result to his repo's results table as an external entry, credited and linked to our comment.

Facts for the table entry (planning/2026-10-07_w00_occluder_frag1/PREREG.md, result table):
  - model: docs/11 w00 occluder, ink_holdout_20k ckpt_020000, one PHerc Paris 4 segment (w00), 7.91 um
  - his score_3d.py (a), whole Frag1: A native 3.24 um 0.521 [0.494, 0.556]; B resampled to 7.91 um
    0.565 [0.523, 0.610] (both pre-registered); post-hoc layer-order flips 0.578 / 0.553
  - positive control: same predict loop, w00 held-out regions, AUC 0.952
  - checkpoint is not published (runs/release/ is local only) -> the entry can only link the comment.
  - No AI-disclosure line (same as the two earlier replies, user decision).

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@kartoun Yes, please add it. For the entry: the model is the `w00` occluder from docs/11 (trained on one PHerc Paris 4 segment at 7.91 µm), scored with your `score_3d.py` (a) on the whole fragment. The two variants I fixed before running were 0.521 [0.494, 0.556] at native 3.24 µm and 0.565 [0.523, 0.610] resampled to 7.91 µm; reversing the layer order afterwards gave 0.578 and 0.553. The checkpoint is not published, so the comment is the only thing to link.
