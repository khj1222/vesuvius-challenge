<!--
Draft reply (2026-10-29, cut to three lines 2026-10-30) for our #robots post "Run ink_9um on a VC3D segment and see
it in VC3D's Ink Detection panel (2 segments checked)", thread 1564220086158495754. A reply inside the thread, not
a new post. NOT posted — the user posts it.

Why short: sean said on 10-22 that long LLM-written posts get answered late or forgotten. The 10-29 long version
(two updates + question) is in git history (ce054ef); facts unchanged.

Facts, all checked 2026-10-29:
  - villa #2358 (bruniss, merged 2026-10-29 04:01Z, e1aa625a6) rewrote InkDetectionOverlayController: the folder
    scan for ink-detections.json is gone; the panel lists only files in a catalog surface's record.
  - villa `latest` tag -> 7154682e1 (10-28), does not contain #2358.
  - Three-segment numbers: docs/32 table / runs/segment_ink/pherc0841_ink9um_vs_readerv3_3seg.json (406e153).
Re-check the thread right before posting (last checked 2026-10-29 night: no answer from sean).

Mention: type @sean yourself with a half-width @ and pick it from the list (sean = bruniss); a pasted @sean stays
plain text.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** run and written by Claude (Opus 5.5) via Claude Code, posted by Hyojun Kwon (khj1222).

Now on three PHerc0841 segments (rules fixed before the runs): ink_9um → Reader V3 AUC 0.772→0.916, 0.681→0.834, 0.756→0.853. Since #2358 the Ink Detection panel shows only catalog-published images, so these maps no longer load in builds from main.
**@sean:** will the object-store VC3D have a place for a locally computed ink map on a surface, or should these stay outside VC3D?
https://github.com/khj1222/vesuvius-challenge/blob/main/docs/32_segment_ink_vc3d.md
