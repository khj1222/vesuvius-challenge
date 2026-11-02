<!--
Draft correction (2026-11-02) for our #robots post "Run ink_9um on a VC3D segment and see it in VC3D's Ink Detection
panel (2 segments checked)", thread 1564220086158495754. A reply inside the thread, not a new post.
NOT posted — the user posts it.

What was wrong: the post says "two segments it never trained on" (PHerc0814 20250925212701 and PHerc0139 w045).
w045 IS an ink_9um training segment: the ink_9um label set uses its own 0139 case numbers, and case
pherc0139-w029 is public w045 (20260126000000-w045). Checked 2026-11-02 from the `source` attribute of our copy
data/ink_9um/surface-volumes/aligned9/pherc0139-w029.zarr/.zattrs. 0814 20250925212701 is outside the set
(its 0814 case is 20260226000000). Found by jo-tud, villa #2349 issuecomment-6542288910 (2026-10-31).
Public docs corrected the same day: docs/32 Check 2, tools/README segment_ink section, docs/15 Appendix 1 (#1547 row).

If the still-unposted object-store reply (discord_robots_segment_ink_objstore_reply.md) or a replacement for it
goes out first, this can be one line in it instead of a separate reply.

Re-check the thread right before posting.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** run and written by Claude (Opus 5.5) via Claude Code, posted by Hyojun Kwon (khj1222).

**Correction:** PHerc0139 w045 is *in* ink_9um's training set (the label set's case `pherc0139-w029` is public w045), so only the PHerc0814 segment above was unseen. The placement check still passes; it just isn't held out on w045. Thanks to jo-tud for spotting it (villa #2349). Corrected in https://github.com/khj1222/vesuvius-challenge/blob/main/docs/32_segment_ink_vc3d.md
