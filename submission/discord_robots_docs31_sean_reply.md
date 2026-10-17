<!--
Draft reply in the #robots thread "How far off can the surface be before ink_9um loses ink?"
(thread 1559894798830272512), answering sean (admin, 2026-10-14 20:48 KST). Drafted 2026-10-17.
NOT posted — the user posts it. Re-read the thread right before posting.

Check behind it (post-hoc, not pre-registered): tools/check_depth_intensity_profile.py →
runs/segrobust/widejitter_depth_intensity_profile.json. Sign from tools/run_widejitter.py perturb():
out[z] = vol[z + k], so shift −5 = the model reads slices 5 lower than the trace puts them.
Numbers (mean raw intensity in the supervision mask, 27-slice renders, trace = slice 13):
  - PHerc0009B ag055: 114–122 over slices 0–13, gap 87 at slice 19, back to 112 by slice 26.
  - Gap (darkest within 8 slices on the + side of the brightest slice) at 17–19 on 0841-w00, 0841-ag174,
    0009B-ag055, 0500P2-s1 and training 0139-w028 / 1667-w018 / Paris4-w02. 0841-ag144: no clear gap.
  - Half-max face: test 14.5 / 15.3 / 16.0 / 16.1; training 16.2 / 13.6 / 13.3.
  - Losses: docs/31 table, released reader −5: −0.157/−0.171, +5: −0.033/−0.040.
-->

AI disclosure: checked and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

@sean thanks, that fits, and the renders say which side is which.

In our perturbed renders a shift of −5 makes the model read the slices 5 positions lower than the trace puts them. Mean intensity per slice in the labelled area (27-slice renders, trace at slice 13):
- lower slices stay bright: the target sheet's body (PHerc0009B ag055: 114–122 over slices 0–13)
- higher slices drop to a gap at slices 17–19 and climb again: the gap, then the next sheet (ag055: 87 at 19, 112 by 26). Same on 6 of the other 7 segments checked, test and training (PHerc0841 ag144 has no clear gap)

So the costly side (−5: −0.16 / −0.17) is the window sliding deeper into the target sheet; the cheap side (+5: −0.03 / −0.04) slides toward the gap and the next sheet.

A lead, not a test: on the test segments the bright-to-gap edge sits 1.5–3 slices above the trace (half-max at slices 14.5–16.1), so −5 leaves that face at the window's edge and +5 keeps it near the centre. It does not sort the per-scroll losses, so docs/31 keeps the "why" open.

Script and numbers: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/check_depth_intensity_profile.py

**Human (Hyojun):** <!-- write this yourself, or delete the line -->
