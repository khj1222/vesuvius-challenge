<!--
Draft reply (2026-10-29) for our #robots post "Run ink_9um on a VC3D segment and see it in VC3D's Ink Detection
panel (2 segments checked)", thread 1564220086158495754. A reply inside the thread, not a new post.
NOT posted — the user posts it. Conventions as in discord_robots_segment_ink.md.

Why now: villa #2358 (bruniss, merged 2026-10-29 04:01Z, e1aa625a6) rewrote InkDetectionOverlayController.
The folder scan for ink-detections.json is gone; the panel lists only the files in a catalog surface's
record (catalog.files, fetched into its artifacts directory). So the question in the original post
("is ink-detections.json with local_file the format to build on?") has been answered by the code: no.
The new question is narrower: is there, or will there be, a place for a locally computed map.

Facts, all checked 2026-10-29:
  - villa `latest` tag -> 7154682e1 (10-28 18:06Z), does not contain #2358; overlay code identical to
    322cb0899 (the commit we tested 10-25). main 8ff06f762 has no "ink-detections" string.
  - AttachedDocument (new in #2358) is for point collections, not images.
  - Three-segment numbers: docs/32 table / runs/segment_ink/pherc0841_ink9um_vs_readerv3_3seg.json
    (commit 406e153): AUC w00 0.772->0.916, ag144 0.681->0.834, ag174 0.756->0.853, mean +0.131.
    Reversed layers: ink_9um 0.553-0.617, Reader V3 0.540-0.575.
  - docs/32 Update paragraph pushed in 29864ac.
Checked 2026-10-29 ~afternoon KST: thread's last message is our 10-26 Reader V3 reply; no answer from sean.
Re-check the thread right before posting.

Mention: type @sean yourself with a half-width @ and pick it from the list (sean = bruniss); a pasted
@sean stays plain text.

The last line is the human part. Write it yourself, or delete it.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** run and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

**Update 1: three PHerc0841 segments.** Same rules as w00, fixed before the runs, applied unchanged to ag144 and ag174. AUC vs the open human ink labels, ink_9um seed43 step-075000 → Reader V3, forward layers:
- w00: 0.772 → 0.916
- ag144: 0.681 → 0.834
- ag174: 0.756 → 0.853

Mean gain +0.131. With the layers reversed, both models drop to AUC 0.54–0.62. Neither model trained on PHerc0841. This repeats KLAVIS's result on more segments; it is not a new claim about Reader V3.

**Update 2: VC3D after #2358.** Since villa #2358 (merged 2026-10-29), the Ink Detection panel lists only the images published with a catalog surface. The `ink-detections.json` folder scan is gone. So these records show in the 2026-10-28 "VC3D Latest" and earlier, not in builds from main after #2358. The maps and numbers are unchanged. That answers my earlier format question.

**Question (@sean):** in the object-store VC3D, is there, or will there be, a place for a locally computed ink map on a surface, e.g. in a user store? Or should ink maps from new checkpoints stay outside VC3D? I would rather not build against code you are still changing.

Write-up (with the 3×3 figure) and numbers:
https://github.com/khj1222/vesuvius-challenge/blob/main/docs/32_segment_ink_vc3d.md
https://github.com/khj1222/vesuvius-challenge/blob/main/runs/segment_ink/pherc0841_ink9um_vs_readerv3_3seg.json
