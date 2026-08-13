# PR to ScrollPrize/villa — flat_depth_targets

**Status: branch pushed, NOT opened (2026-08-13).** The branch is ready — opening is one
click. Open it when either trigger fires:
- a maintainer answers the offer in the [#192 comment](https://github.com/ScrollPrize/villa/issues/192), or
- there is still no reply by **~2026-08-24** (CI + a review round need lead time before the 08-31 deadline).

**Branch:** `khj1222:feat/flat-depth-targets`, commit `8515746`, pushed 2026-08-13.
**Open at:** https://github.com/ScrollPrize/villa/compare/merge-ink-pipelines...khj1222:feat/flat-depth-targets
(base **`merge-ink-pipelines`** — not `main`: `ink-detection/koine_machines/` is 404 on `main`,
and a wrong base produces a spurious 231-file diff, as #1234 briefly did).
Title/body below; **the user opens it on the web** (Claude has no `gh`/GitHub auth).

**Rebased 2026-08-13** onto upstream tip `33c463e`. Upstream had reworked `infer.py`
(default overlap 0.25→0.5, Hann blending, `--stride`/`--blend-mode`, per-patch occupancy
skip, input depth padding, preprocessing selection) and extended `test_train.py`. Three
conflicts, all clean unions (both sides kept): `TargetHeadWrapper.__init__` gains
`input_pad_depth_to` (theirs) *and* `z_reduce`/`z_window` (ours); its construction site
passes all three kwargs; the test-file import block merges their new imports with our
rename. **Verified: `py_compile` on all 3 files + unit tests 7 passed** (upstream added 3
tests to the base's 4) — run against the ported tree via
`cd D:/vw2/ink-detection && uv run --project D:/vesuvius-challenge/external/villa/ink-detection --no-sync python -m pytest koine_machines/training/tests/test_train.py`
(⚠️ `--project`, not `--directory` — `--directory` moves cwd and imports the wrong tree).

**Patch:** [`villa-flat-depth-targets.patch`](villa-flat-depth-targets.patch) — 3 files, +129 −13.
Regenerated 2026-08-13 from the rebased commit (`git diff origin/merge-ink-pipelines..HEAD` in
`D:/vw2`). Still plain `git diff` format — `git apply`, **not** `git am`. The copy applied to
the `external/villa` working tree (uncommitted, on the #1234 branch) is the **pre-rebase**
version; the committed branch in `D:/vw2` is the source of truth now.

**Follows up:** the "happy to open it as a PR" offer at the end of `submission/issue192_comment.md`.

---

## Remaining before opening

1. **Optional: one GPU smoke on the rebased branch** — deferred 2026-08-13 (user compute job
   held ~27/32 GB VRAM). Largely superseded the same day by a CPU functional check on the
   ported tree (scratchpad `cpu_wrapper_check.py`, `CPU_WRAPPER_CHECK_OK`): windowed max
   picks the in-window ink over louder out-of-window noise, default full-volume max
   reproduces the documented failure mode, mean reduction correct, 2D models pass through
   untouched, and `input_pad_depth_to` (upstream) coexists with `z_reduce`/`z_window` (ours)
   — that constructor was the main merge point. `infer --help` registers both flag sets.
   What only a GPU run still covers: real zarr reading + checkpoint loading + CUDA, none of
   which the rebase conflicts touched. **OK to open without it.** If wanted anyway, from
   `D:/vw2/ink-detection`:
   `uv run --project D:/vesuvius-challenge/external/villa/ink-detection --no-sync python -m koine_machines.inference.infer <abs>/w00_20231016151002/w00_20231016151002.zarr D:/vesuvius-challenge/external/villa/ink-detection/runs/ink_depth_v4_fold0/ckpt_020000.pth <scratch>/smoke.tif --mask-path <abs>/w00_20231016151002/w00_20231016151002_validation_mask.tif --batch-size 4 --no-compile --z-window 16:48`
   (~30 s masked run; exercises the 5D path + z-window on top of upstream's new
   overlap/Hann/occupancy code). Unit tests already pass; this is belt-and-braces.
2. User opens the PR at the compare URL above with the title/body below.
3. After the PR is open: `git -C D:/vesuvius-challenge/external/villa worktree remove D:/vw2`
   (keep `D:/vw2` until then — it is the committed branch and the place to run the smoke).

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

- Unit tests pass (`uv run pytest koine_machines/training/tests/test_train.py`, 7 passed on
  the current branch tip); the projection-gating tests are extended to cover the new flag.
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
