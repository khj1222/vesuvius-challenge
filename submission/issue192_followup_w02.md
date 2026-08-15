<!--
Follow-up comment for villa #192 "Accurate 3d ink labels"
  target: https://github.com/ScrollPrize/villa/issues/192
  context: follows our 2026-08-09 result comment and 2026-08-14 reply to
           stantheman0128. Reports the two robustness checks run 08-15/16.
  status: DRAFT, not posted as of 2026-08-16 — user posts it themselves.

This header is an HTML comment, so the whole file can be pasted as-is —
GitHub renders nothing for it.
-->

Two follow-ups on the comparison above, each aimed at a loose end the original
comment flagged.

**1. The schedule was not the problem.** `v4`'s best checkpoints sat at
19000–20000, still rising, so I resumed all six depth runs (both arms, all
folds) to 30000 steps — full-state resume, identical warm-restart tail for
both arms. The gap moves from **0.038 to 0.036**; no fold improves by more
than +0.008 after 20k. Fifty percent more training does not change the
verdict.

**2. The result replicates on a second segment, wider.** The biggest stated
limit was "one segment", so I reran the whole pipeline unchanged on
`w02_20231031143852`: 2D baseline with a held-out split, depth measurement,
measured band, `v3`/`v4` versions, same 3-fold protocol. Two consistency
checks lined up almost exactly — the 2D baseline lands at F1 **0.8235**
against `w00`'s 0.8232, and the measured geometry looks like `w00`'s (median
centre 31.8 vs 32.5, same ±4 half-width, per-region centres 26.4–40.3).

| fold | `v3` constant | `v4` measured |
|---|---|---|
| 0 | 0.8291 | 0.6436 |
| 1 | 0.8133 | 0.7520 |
| 2 | 0.8364 | 0.7905 |
| **mean** | **0.8263** | **0.7287** |

**Gap +0.098 — two and a half times `w00`'s — and the ordering is total**:
the best measured fold sits below the worst constant fold. The constant band
again reproduces the segment's own 2D baseline, so depth-resolved training
stays harmless; but on this segment the per-pixel band also destabilises
training (fold spread 0.147, best checkpoints at steps 19000/13000/9000 —
peaking early and decaying). Caveats in the writeup: measured coverage is
64.6% here vs 85.9% on `w00`, and `v4`'s label budget comes out 12% thinner
than `v3`'s from half-width clamps — though `w00`'s plane-vs-constant tie
already showed an 8× budget difference costs nothing, so that does not
explain 0.098.

Details and raw numbers are in
[docs/12](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/12_depth_training.md)
(sections "The stopped-too-early check" and "Second segment").

@stantheman0128 in the meantime I exported the `w00` band in a form your
pipeline can consume directly: one record per measured cell — segment-grid
position, band centre/half-width in layers, scroll-space base point from the
released `x/y/z.tif` maps, and a surface normal, with every convention I
cannot verify (normal sign, layer step) declared in a sidecar —
[`submission/depth_anchors/`](https://github.com/khj1222/vesuvius-challenge/tree/main/submission/depth_anchors)
([exporter](https://github.com/khj1222/vesuvius-challenge/blob/main/tools/export_depth_anchors.py)).
If you would rather have a different format, say the word. Given the `w02`
result above, the geometry question your scoring answers has become sharper,
not less interesting: if the band is geometrically sound and *still* loses
this badly, that is the strong version of the claim.
