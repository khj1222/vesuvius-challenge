<!--
Reply to kartoun on villa #192 "Accurate 3d ink labels" (draft 2026-10-06). NOT posted — the user posts it.
  target: https://github.com/ScrollPrize/villa/issues/192
  replying to: kartoun 10-05 (issuecomment-5994122648) and 10-06 (issuecomment-6016079974)

Checked before drafting:
  - kartoun/vesuvius-fragment-ink-depth (MIT, created 10-05): khj_recipes.py constants match
    tools/make_3d_labels.py defaults (occlude 4, cell 64, clamp [2,16], min-response 0.2,
    min-prominence 1.5, regularize 3, min-cell-ink 64). Declared differences: own 3D U-Net
    occluder (input layers 12-43), blank = global mean, no regions -> fragment-wide fallback.
  - outputs/khj_recipes/depth_vs_surface.txt: whole fragment corr 0.158, v3/v4 MAD 2.00/2.00,
    |off|<=3 45.9%/42.4%; held-out rows 3298-4432 corr 0.398, MAD 2.00/1.71, |off|<=3 47.8%/46.1%,
    |off|<=5 74.3%/75.3%. The comment only quoted the whole-fragment row.
  - Our 08-31 comment (issuecomment-5485400566) said stantheman's D~2 put us on the
    "geometry sound, still loses" branch "without the escape hatch that the geometry was simply bad".
    stantheman's own 08-25 / 10-02 comments were narrower (interface, not tracking). docs/12's
    closing paragraph says "not obviously misplaced" — milder, but needs the same correction.
  - Our w00 occluder was trained on w00's own 2D annotation (docs/11 "Circularity").
  - No AI-disclosure line (user decision 10-06, matching our earlier #192 comments).
  - docs/12 correction + README clause committed before posting, so the link resolves.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@kartoun Thanks for porting it. I checked `khj_recipes.py` against `tools/make_3d_labels.py` and it is the same construction (4-layer occlusion, 64 px cells, centroid centre, FWHM half-width clamped to [2, 16], fallback at 0.2 logit / 1.5 sd, 3×3 median on the cell grid), and the differences you list are the ones a fragment forces. Using your own model as the occluder is how the recipe is meant to run anyway: on `w00` the occluder was a model trained on that segment's own 2D annotation, so a checkpoint of mine would be a less faithful port on Frag1, not a more faithful one.

Your table corrects something I wrote here on 08-31. I said @stantheman0128's D ≈ 2 put the result on the "geometry is right and still loses" branch and removed the escape hatch that the band was simply misplaced. That was more than the measurement says. D ≈ 2 shows the band sits near an interface on average; it does not show that the per-cell movement follows that interface, and stantheman said as much at the time (adjacent-cell |ΔD| had the same median as random pairs). Your corr(v4 centre, surface) = 0.16, with v4 no closer to the surface than the constant band, is the first test that looks at the movement itself, and on Frag1 the movement mostly does not follow the surface. So the better reading of `v4` losing is that the band moves per cell in ways the sheet does not, which is closer to the first of the two readings I listed on 08-14 than I claimed. [docs/12](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/12_depth_training.md#independent-check-is-the-band-where-it-says-it-is) now says that, with your numbers credited.

One thing in your outputs I'd like to understand: `depth_vs_surface.txt` gives corr 0.40 on the held-out rows 3298–4432 against 0.16 for the whole fragment, and there v4's MAD is 1.71 against v3's 2.00 (though |off| ≤ 3 is still 46.1% vs 47.8%). Do those rows have more surface relief, so there is more for the band to follow? If the movement tracks the surface where there is something to track, that is a different statement from "it does not track".

Same limits as yours: one fragment, and an exposed fragment surface is not a buried scroll sheet.
