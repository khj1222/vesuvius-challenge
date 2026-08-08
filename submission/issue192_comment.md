<!--
Comment for villa #192 "Accurate 3d ink labels"
  target: https://github.com/ScrollPrize/villa/issues/192
  status: not posted as of 2026-08-09

This header is an HTML comment, so the whole file can be pasted as-is —
GitHub renders nothing for it.
-->

I ran the experiment this issue implies — train the same model on differently
shaped 3D ink labels and score them against each other — and the result came out
against the premise, so I want to put the numbers somewhere they can be argued
with.

**Short version:** on `w00_20231016151002`, a per-pixel *measured* ink band loses
to a *constant* band by 0.038 F1, on every one of three folds. A one-voxel plane
and an eight-voxel constant band tie, so depth-resolved targets themselves cost
nothing — moving the band around per pixel is what costs.

## What was in the way first

In `flat` mode the label never reaches the loss with its depth intact:

```python
targets = (torch.amax(batch['inklabels'], dim=2) > 0).to(dtype=batch['inklabels'].dtype)
supervision_mask = torch.amax(batch['supervision_mask'], dim=2)
```

Every label voxel is max-pooled into one plane, so a depth-resolved label and the
published single-plane label produce byte-identical targets. No label-depth
experiment is possible in flat mode at all. (`full_3d` does keep depth, but it
wants the native scroll volume, and it builds its own band by projecting the flat
annotation out to a constant `_DEFAULT_FULL_3D_PROJECTION_HALF_THICKNESS` — so it
answers a different question.)

I gated a change behind `flat_depth_targets: true`: z projection off for model and
targets, volume-vs-volume loss with `supervision_mask` as the ignore mask, previews
reusing the `full_3d` central-slice reduction, and `--z-window` on inference so a
volume prediction reduces back to the usual 2D TIFF. That last part matters more
than it sounds — see the trap at the bottom.

## Setup

Three label versions over the same segment, packaged as `_inklabels_vN.zarr` so
`discover_labels` picks them up and the patch cache key keeps the arms separate:

| arm | band | label voxels / ink px |
|---|---|---|
| `v2` | the published plane, 1 voxel | 1.00 |
| `v3` | **constant**: centre z 32.47, half-width 4 — the segment median | 8.00 |
| `v4` | **measured**: per-pixel centre and FWHM half-width | 8.01 |

`v4`'s band comes from two independent measurements that agree: occlusion/window
profiling of a trained model puts its ink evidence at z≈16–36, and a model-free
CT contrast (ink vs background AUC per slice, max 0.546 @ z24) peaks in the same
place. Per region the measured centre ranges 29.3–40.3, so the band genuinely
moves. Label voxel budget is 8.01 per pixel for `v4` against 8.00 for `v3` — the
same number of positives, in different places.

All three arms supervise a ±16 voxel column around the annotated plane, and the
held-out mask is extruded into the same column (otherwise held-out voxels outside
the plane stay in training supervision and leak in favour of whichever arm is
being tested).

Scoring is the [held-out harness](https://github.com/khj1222/vesuvius-challenge)
from last month: whole annotated regions held out rather than a rectangle,
3-fold, threshold sweep per checkpoint. Same folds, same seed, same 20k schedule
for every arm — the label is the only thing that differs.

## Result

| fold | `v2` plane | `v3` constant | `v4` measured |
|---|---|---|---|
| 0 | 0.8567 | 0.8455 | 0.7997 |
| 1 | 0.8259 | 0.8452 | 0.8192 |
| 2 | 0.8496 | 0.8528 | 0.8104 |
| **mean** | **0.8441** | **0.8478** | **0.8098** |
| spread | 0.0308 | 0.0076 | 0.0195 |

The measured band is last on every fold. It trails the constant band by 0.0381 on
average — above the ~0.03 fold-to-fold noise floor I measured in July by running
one unchanged config four times — and trails the plane by 0.0343, though on fold 1
that margin narrows to 0.0067.

**`v2` and `v3` tie** (0.0037 apart), which I did not expect and which I think is
the more useful half: **thickness is not the variable.** One voxel and eight score
the same. What costs 0.04 is letting the eight-voxel band move per pixel.

Three things make the negative result hard to explain away:

- **The constant arm reproduces the 2D baseline almost exactly** — 0.8478 against
  0.8472 for 2D targets on `v1` labels over the same three folds. So depth-resolved
  training is not itself harmful.
- **`v3` is very stable**: spread 0.0076, tighter than the 2D baseline's own 0.0154.
  (`v2` is the jumpy arm at 0.0308 — a 0.7% positive rate against 5.5% changes what
  Dice+BCE sees, so I would not read a single `v2` fold on its own.)
- **Circularity runs the wrong way for the hypothesis.** `v4`'s band was read out of
  a model trained on the depthless annotation, so any self-distillation effect
  should have flattered `v4`. It lost anyway.

Not a stopping artifact either: over the last 3,000 steps the arms gain about the
same (`v3` +0.0075, `v4` +0.0068) while the gap between them is five times that.

## What I think this does and doesn't say

It does not say this issue is wrong. It says that **this route** to a 3D label —
per-pixel depth read out of a 2D-trained model, FWHM widths, median-filtered on a
64 px cell grid — does not beat putting the band in one place and leaving it there,
on a segment whose sheet is fairly flat. A band measured some other way, or a
segment with more wander, could still win. The harness now runs that comparison in
a day, so it is cheap to check.

As far as I can tell this is the first time anyone has reported *training* on 3D
ink labels and scoring the result: #923 was explicitly a sketch, and #1295 was
closed for want of validated depths — both proposed a way to make the labels,
neither measured a model trained on them. So the useful part of a negative result
here may be the yardstick rather than the verdict.

One measurement may help whoever picks this up next. #1295 places the band using
CT brightness, which is the natural thing to reach for. Before building the `v4`
band I checked how well a single voxel's brightness separates ink from background
on this segment with no model in the loop
([docs/10](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/10_depth_localization.md)):
per-slice AUC peaks at **0.546** at z24 and never exceeds 0.55 anywhere in the
volume. Brightness does carry real signal — its peak sits in the same z range as
the model's own evidence, which is why I trust both measurements — but it is far
too weak to threshold a label out of on its own. Below z40 there is also a strong
*negative* drift, ink darker than background, which reads as surface geometry
rather than ink and is exactly what a brightness rule would happily label.

Limits worth stating: one segment, three folds that share the same 15 annotated
regions, one seed per fold, and ±16 as a judgement call that bounds all three arms.
`v2` is not a clean control either — its tie with `v3` shows thickness does not
decide the outcome, but the class-balance difference means it cannot say why.

## A trap for anyone else trying this

A model trained on depth targets predicts a volume, and inference collapses it to
a surface map with a max down z. Only the supervised column means anything —
outside it the loss constrained nothing, and measurement shows ink and background
both saturating above 0.6 there. Reducing over the full volume reports that noise:

| volume → surface | best F1 |
|---|---|
| `max` over z0–64 | 0.535 |
| `max` over supervised z16–48 | 0.802 |

Same checkpoint, same pixels. The tell is the threshold pinning to 254. My first
pass at the `v4` arm scored 0.47–0.53 for exactly this reason and looked like a
catastrophic label failure; the checkpoints were fine. Whatever shape 3D labels
eventually take, the inference reduction has to move with them, or full-segment
prediction TIFFs are degraded the same way.

## Availability

Tooling, configs, docs and the raw per-checkpoint CSVs are at
[khj1222/vesuvius-challenge](https://github.com/khj1222/vesuvius-challenge)
(MIT) — `docs/10` for the depth measurement, `docs/11` for the label build,
`docs/12` for the training path and this comparison. The villa-side change is a
single patch against `merge-ink-pipelines` (`train.py`, `infer.py`, plus a test).
Happy to open it as a PR if the `flat_depth_targets` route looks worth having,
whether or not the measured band ever wins — without it, flat mode cannot express
a depth experiment at all.
