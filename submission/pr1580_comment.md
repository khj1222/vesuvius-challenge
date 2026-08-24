<!--
Comment for villa PR #1580 "ink_detection: report a prepared input whose scale does not
match its recipe"
  target: https://github.com/ScrollPrize/villa/pull/1580
  author of that PR: nerln, opened 2026-08-24 (independent repro by Bullo27 same day)
  why we are commenting: it instruments prepare_9um_isotropic_input, the exact script our
    September LOSO track used. We have a measured, complementary data point: two input
    families that BOTH pass this check still transfer differently, 4/4 on the same
    physical segments.
  numbers below recomputed from runs/ink9um_scorecard/no0139_matrix.csv on 2026-08-24.
  status: DRAFT, not posted as of 2026-08-24 — user posts it themselves.

This header is an HTML comment, so the whole file can be pasted as-is —
GitHub renders nothing for it.
-->

Nice measurement — varying `--level` and the depth order independently is what makes it
convincing, since the two faults arrived together in the incident.

A supporting data point from the other end of the same failure, offered as evidence for the
PR rather than as a request: I have been running `prepare_9um_isotropic_input` across the
whole `ink_9um` corpus this month.

Where your check would have caught me: it would not have, and I think that is the
interesting part rather than an objection. Both input families I trained and scored on are
scales this recipe trains at:

- **aligned** — built with `prepare_9um_isotropic_input --level 2` from the public 2.399 µm
  volumes with 4× z mean pooling, i.e. 9.596 µm. Your table's first row, correct usage.
- **native** — the published 9.362 µm surface volumes, not produced by the preparer.
  Your third row: silent, no recipe tag.

Both pass your check, and both should. They are still not interchangeable at transfer time.

PHerc0139 is the only scroll in the corpus where the same physical segments exist in both
families, so it is a controlled comparison. Holding out all of PHerc0139 and retraining the
recipe on the remaining 15 representations (2 seeds, 7 checkpoints each, best of that grid,
threshold swept per cell), scored against each segment's own trivial-classifier lower bound
2p/(1+p) — the bound differs slightly between the two renders, which is why I compare
margins rather than raw F1:

| segment | aligned F1 (margin) | native F1 (margin) | Δ margin |
|---|---|---|---|
| w035 | 0.740 (+0.260) | 0.679 (+0.203) | +0.057 |
| w039 | 0.654 (+0.169) | 0.585 (+0.103) | +0.066 |
| w040 | 0.703 (+0.088) | 0.652 (+0.040) | +0.048 |
| w041 | 0.734 (+0.145) | 0.703 (+0.117) | +0.028 |

Aligned wins 4/4, +0.028 to +0.066. That arm's training corpus is entirely aligned-family,
so the reading I take is domain match: transfer into the family you trained on is
consistently better, and some of what looks like cross-scroll difficulty is scan and
preprocessing domain difference rather than the scroll.

**Caveats, because this is not a replication of your measurement.** Different metric (F1
margin, not AUC), cross-scroll rather than same-scroll, best-of-grid selection applied
identically to both families, and the two families ship their own label sets — so
representation is not perfectly isolated from label transfer. Against your 0.95 → 0.64 the
effect I see is small. The point I would make for the PR is the direction, not the size:
the catastrophic case you catch is silent today, and the residual within-spec case is
measurable too, which makes the provenance you are already recording worth surfacing rather
than only comparing.

Raw numbers, if useful — the grid this table comes from, one row per arm × segment × step:
https://github.com/khj1222/vesuvius-challenge/blob/main/runs/ink9um_scorecard/no0139_matrix.csv
(`pherc0139-wNNN` rows are aligned, bare `wNNN` are native; `loso42`/`loso43` are the
held-out arm, `ref42`/`ref43` the reference models that trained on these segments). The
arm generator is `tools/make_ink9um_config.py` in the same repo. The write-up is in Korean
at the moment; happy to put the method in English here if anyone wants it.
