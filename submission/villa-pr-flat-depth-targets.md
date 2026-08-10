# PR to ScrollPrize/villa — flat_depth_targets

**Status: NOT opened.** Open it when either trigger fires:
- a maintainer answers the offer in the [#192 comment](https://github.com/ScrollPrize/villa/issues/192), or
- there is still no reply by **~2026-08-24** (CI + a review round need lead time before the 08-31 deadline).

**Patch:** [`villa-flat-depth-targets.patch`](villa-flat-depth-targets.patch) — 3 files, +133 −15
(`infer.py` +98, `train.py` +44, `test_train.py` +6). Regenerated 2026-08-08, includes `--z-window`.
⚠️ Plain `git diff` format — `git apply`, **not** `git am` (unlike the #1234 patch).
**Base branch: `merge-ink-pipelines`** — not `main`. `ink-detection/koine_machines/` does not
exist on `main` (404); opening against `main` produces a spurious 231-file diff (#1234 made
this mistake once).
**Suggested branch:** `feat/flat-depth-targets`
**Follows up:** the "happy to open it as a PR" offer at the end of `submission/issue192_comment.md`.

---

## How to submit

⚠️ Do **not** commit from `D:/vesuvius-challenge/external/villa` — that worktree sits on
`fix/stream-untiled-label-images` (PR #1234) with these same changes applied **uncommitted**
on top. Committing there would entangle the two PRs. Cut a fresh sparse worktree instead
(short path — long paths fail with `Filename too long`):

```bash
cd D:/vesuvius-challenge/external/villa
git worktree add --no-checkout -b feat/flat-depth-targets D:/vw2 merge-ink-pipelines
cd D:/vw2
git sparse-checkout set --cone ink-detection
git checkout
git apply --check D:/vesuvius-challenge/submission/villa-flat-depth-targets.patch
git apply D:/vesuvius-challenge/submission/villa-flat-depth-targets.patch
git add ink-detection/koine_machines
git commit -m "train: keep label depth in the flat-mode loss behind flat_depth_targets"
git push fork feat/flat-depth-targets
```

Claude can run everything above (push works via GCM); **opening the PR itself is done by the
user on the web**: base = `merge-ink-pipelines`, compare = `khj1222:feat/flat-depth-targets`.
Afterwards: `git -C D:/vesuvius-challenge/external/villa worktree remove D:/vw2`.

---

## PR title

```
train: keep label depth in the flat-mode loss behind an opt-in flat_depth_targets flag
```

## PR body

```markdown
In `flat` mode the label never reaches the loss with its depth intact:

```python
targets = (torch.amax(batch['inklabels'], dim=2) > 0).to(dtype=batch['inklabels'].dtype)
supervision_mask = torch.amax(batch['supervision_mask'], dim=2)
```

Every label voxel is max-pooled into one plane before the loss, so a depth-resolved label
(e.g. an `_inklabels_vN.zarr` with a real z band) and the published single-plane label
produce byte-identical targets — the experiments #192 asks about are not expressible in
flat mode at all. `full_3d` does keep depth, but it wants the native scroll volume and
builds its own band by projecting the flat annotation to a constant half-thickness, so it
answers a different question.

### Change

Everything is behind `flat_depth_targets: true` in the training config; without the key,
nothing changes.

- When set, z projection is disabled for model and targets the same way the native 3D
  modes already do it, and the model emits `[B, 1, Z, Y, X]`.
- The loss runs volume-to-volume, with `supervision_mask` as the ignore mask.
- Train previews reuse the `full_3d` central-slice reduction.
- `infer` gains `--z-reduce {max,mean}` and `--z-window start:stop` to collapse a volume
  prediction back to the ordinary 2D TIFF. The defaults (`max`, full depth) reproduce the
  existing behaviour, so current checkpoints and scripts are unaffected.

`--z-window` is not cosmetic. A depth-target model is only constrained inside the
supervised z column; outside it, measurement shows ink and background both saturating
above 0.6, and a full-volume max reports that noise. Same checkpoint, same pixels:
best F1 0.535 reducing over z0–64 vs 0.802 over the supervised z16–48 (the tell is the
best threshold pinning to 254). Whatever shape 3D labels eventually take, the inference
reduction has to move with the supervision, or full-segment prediction TIFFs degrade the
same way.

### Verification

- Unit tests pass (`uv run pytest koine_machines/training/tests/test_train.py`, 4 passed);
  the projection-gating tests are extended to cover the new flag.
- Default-off path unchanged: a config without the key takes the existing `amax` branch.
- End-to-end: this path trained a 3-arm × 3-fold label-geometry matrix on
  `w00_20231016151002` (reported in #192). A constant 8-voxel band trained through it
  reproduces the 2D baseline within noise (0.8478 vs 0.8472 mean F1 over the same three
  folds), so the depth path is calibrated, not just plumbed. Output shape checked at
  `(1, 1, 64, 256, 256)`; training throughput matches 2D targets (~3.6 it/s on the same
  hardware).
- Inference: masked 166-block run produces the usual 2D TIFF (~30 s); with the new flags
  omitted, behaviour on existing 2D checkpoints is unchanged.

Context and the full experiment write-up are in #192; this PR is the villa-side gate that
made the experiment expressible. Whether or not a measured band ever wins, without it flat
mode cannot express a label-depth experiment at all.
```
