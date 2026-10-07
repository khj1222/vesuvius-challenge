<!--
Second reply to kartoun on villa #192 (draft 2026-10-07, v2 after the Frag1 check). NOT posted — the user posts it.
  target: https://github.com/ScrollPrize/villa/issues/192
  replying to: kartoun 10-06 14:08Z (issuecomment-6018077755)

User decision 10-07: offer our w00 occluder, but only after checking it on Frag1.
Check (planning/2026-10-07_w00_occluder_frag1/PREREG.md, rule fixed before inference):
  - Checkpoint = ink_holdout_20k/ckpt_020000.pth (the docs/11 occluder), one segment w00, scale 0.
  - kartoun's score_3d.py (a) functions, whole Frag1: A native 0.521, B resampled to 7.91 um 0.565;
    post-hoc layer-order flips 0.578 / 0.553. All below his LOFO occluder's 0.654 -> not stronger.
  - Prediction maps show no letters (compare.png).
  - v1 of this draft (handing over the checkpoint) is superseded; no release was created.
  - No AI-disclosure line (same as the 10-06 reply, user decision).

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@kartoun Thanks, that answers it: if the rows that track better also have less relief, and a model that never saw Frag1 doesn't track there at all, 0.40 is a local effect and I won't read more into it.

Your third point is the stronger result. docs/11 only hedged the band's width ("what this model's evidence spans", not the ink's physical thickness). A 15-layer shift between two occluders on the same fragment and annotation shows the same is true of where the band sits, and shows it directly.

On the third occluder: before offering mine I ran it over Frag1 and scored it with your `score_3d.py` ink-map score (your functions, whole fragment). It is the checkpoint that produced the `w00` band, trained on a single PHerc Paris 4 segment at 7.91 µm. AUC was 0.52 at Frag1's native 3.24 µm and 0.57 resampled to 7.91 µm (0.55–0.58 with the layer order reversed), against 0.654 for your leave-one-fragment-out model, and the map shows no letters. So it isn't the stronger occluder you asked for, and I don't have one. A model trained on scroll segments doesn't transfer to this fragment without adaptation, and that is all this check says.
