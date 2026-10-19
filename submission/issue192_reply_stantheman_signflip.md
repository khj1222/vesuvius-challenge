<!--
Reply to stantheman0128 on villa #192 (draft 2026-10-19). NOT posted — the user posts it.
  target: https://github.com/ScrollPrize/villa/issues/192
  replying to: stantheman0128 2026-10-18 05:12Z (issuecomment-6245982183): re-ran #1945 (21c920a)
  with the three normal_* columns negated. No question was asked; this is optional (user chose to
  reply, 2026-10-19).

Facts behind each sentence (checked 2026-10-19):
  - Their table, sigma 0: as exported 164 evaluable / 123 within 3 / median D 2.0; negated
    163 / 113 / 2.0. Per point: median move 5.5 voxels, within-3 verdict agrees 104/163.
  - Our 10-14 check: 25/30 prefer +, median winning corr 0.335, local surface volume from a
    different render (esrf/20260311, 65 layers) than the public one (109 layers).
  - Our side today: docs/12 "Update (2026-10-18): the normal's sign" paragraph and a tools/README
    note under export_depth_anchors.py, both saying the sign is unverified and the distance score
    does not separate the two readings. Sidecar already said UNVERIFIED (normal_orientation).
  - No AI-disclosure line (same as earlier #192 replies, user decision) — user may add one.
  - Check before posting: re-read #192 for anything newer than 10-18 05:12Z; COMMIT filled with 4306ab3.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@stantheman0128 Thanks for running the flipped reading. Agreed on both points: the aggregate score can't decide the sign, and anything built on the band fields should carry both readings until something that sees the surface directly settles it.

I've added that to our side so the export doesn't look more settled than it is. docs/12 now has a short update saying the sign is unverified and that the distance score doesn't separate two readings about 5 voxels apart, with a link to your comparison. The exporter notes in tools/README say to run both signs (khj1222/vesuvius-challenge@4306ab3). I don't have anything more decisive than the 25 of 30 check, so I'm leaving it marked open.
