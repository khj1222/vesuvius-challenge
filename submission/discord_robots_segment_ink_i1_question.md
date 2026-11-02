<!--
Draft reply (2026-11-02) for our #robots post "Run ink_9um on a VC3D segment and see it in VC3D's Ink Detection panel
(2 segments checked)", thread 1564220086158495754. A reply inside the thread, not a new post. NOT posted — the user
posts it. Replaces the unposted discord_robots_segment_ink_objstore_reply.md, and carries the w045 correction as its
last line, so discord_robots_segment_ink_w045_correction.md is then not needed.

Why short: sean said on 10-22 that long LLM-written posts get answered late or forgotten.

Facts, checked 2026-11-02 on villa main fd97a4b60:
  - vc_object_store/README.md:82 documents `vc_object_ingest --surface-channel SURFACE_UUID ink /data/ink_prediction.tif`;
    docs/README.md "Arrays, surface channels" gives "ink rendered at 20 pixels per grid step" as the example.
  - InkDetectionOverlayController::refreshOptionsForActiveSurface lists only catalogReference(row->record)->files;
    nothing in VC3D displays an `ink` channel.
  - No open or closed villa PR found for this (searches: InkDetectionOverlay, ink channel, surface channel, ink overlay).
  - w045: see discord_robots_segment_ink_w045_correction.md (fixed in docs, bb35177).
Re-check the thread right before posting.

Mention: type @sean yourself with a half-width @ and pick it from the list (sean = bruniss); a pasted @sean stays
plain text.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** run and written by Claude (Opus 5.5) via Claude Code, posted by Hyojun Kwon (khj1222).

**@sean:** the object store already takes a locally made ink map as a surface channel (`vc_object_ingest --surface-channel UUID ink pred.tif`), but the Ink Detection panel lists only catalog files. Would a small PR that also lists a surface's `ink*` channels there be welcome, or is that already planned on your side?
Correction to the post above: PHerc0139 w045 is in ink_9um's training set (thanks jo-tud), so only the 0814 segment was unseen.
