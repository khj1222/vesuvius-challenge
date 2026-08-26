**In one sentence:** Turn the published aligned-21 recipe into a config you can actually run,
and optionally hold a scroll or a segment out of it so the same recipe measures how well the
model transfers to data it never saw.

**One real example:** Starting with the released `ink_9um` labels and surface volumes, I ran

```bash
python scripts/make_holdout_config.py \
  --labels-root  /data/ink_9um/labels \
  --volumes-root /data/ink_9um/surface-volumes \
  --exclude-scroll 0139 \
  --seed 42 \
  --out configs/loso_no0139_s42.json \
  --run-dir runs/loso_no0139_s42
```

and it produced a 15-representation training config with quotas
`{'1667': 40, 'Paris4': 20, '0814': 4}` — byte-identical to the config I had previously
written by hand and trained on.

**Before:** `configs/aligned21_hybrid_3d2d.json` ships a single `datasets` entry whose paths
are `/path/to/aligned-21slice-data`, and the 29 representations it is meant to train on live
in a different file, `configs/aligned21_fixed_scroll_prior.json`. To run the recipe you join
the two by hand: 29 entries, each carrying its own `segments_path`, `surface_volume_paths`,
`sampling_physical_segment_keys` and `sampling_representation_keys`. To hold anything out you
also have to fix `fixed_scroll_prior.target_batch_counts` yourself. Drop a scroll without
renormalising and training stops at startup with
`fixed scroll quotas sum to 51, expected batch_size=64`, or, if the sums happen to work out,
with `fixed scroll quota keys must exactly match patch scrolls`. The sampler is right to
refuse; what is left to the user is finding a valid integer split that sums to `batch_size`,
once per arm.

**After this PR:** one command. Exclusions are `--exclude-scroll` / `--exclude-segment`, both
repeatable, and the quotas are renormalised over the survivors by largest remainder so they
still sum to `batch_size`.

**Proof:** the script regenerates the configs behind measurements I have already published,
from the contract rather than from my copies. Four arms, same seed, compared key by key
against the configs the checkpoints were actually trained with:

| arm | flags | representations | renormalised quotas | vs. the config I trained |
|---|---|---|---|---|
| leave-0139-out | `--exclude-scroll 0139` | 15 | `{1667: 40, Paris4: 20, 0814: 4}` | **identical** |
| leave-1667-out | `--exclude-scroll 1667` | 23 | `{0139: 44, Paris4: 17, 0814: 3}` | **identical** |
| leave-Paris4-out | `--exclude-scroll Paris4` | 21 | `{0139: 35, 1667: 27, 0814: 2}` | **identical** |
| two segments, both families | `--exclude-segment pherc0139-w035 --exclude-segment w035 --exclude-segment pherc0139-w039 --exclude-segment w039` | 25 | `{0139: 29, 1667: 22, Paris4: 11, 0814: 2}` | differs only in `dataloader_workers`, which I had lowered from 12 to 6 by hand |

With no exclusions it emits all 29 representations and reproduces the released quotas
`{0139: 29, 1667: 22, Paris4: 11, 0814: 2}` unchanged, which is the renormaliser's no-op case.

Failure modes are loud rather than silent: an unknown scroll prints the valid ones
(`error: unknown scroll(s) ['0247']; known: ['0139', '0814', '1667', 'Paris4']`), and a
representation whose labels or surface volume cannot be located is listed by name instead of
being written into a config that dies later in patch finding.

**Why / where this is useful:** anyone who wants to run the published recipe at all, and
anyone measuring cross-scroll generalisation — open problem #7. Holding a scroll out makes its
entire supervision mask honest held-out ground truth, so it can be scored directly. The three
leave-one-scroll-out arms above are what I used to get the first numbers on that problem, and
the point of upstreaming the generator is that the next person can re-run or disagree with
them without reconstructing the config by hand.

- [ ] I personally verified that the example and proof above were produced by this PR on the
      stated data.

## Details

- Tested at `c61cc9f`, branched from `3ea17f5` (`merge-ink-pipelines` tip).
- Representations are located by exact directory name under the two roots, so a layout with
  `aligned/<segment>.zarr` and `native/<segment>/<one>.zarr` both work without flags. The walk
  does not descend into `.zarr` stores, so it stays fast on a full corpus (0.14 s over 29
  representations here).
- `--recipe` and `--contract` default to the two files in `configs/` next to the script and can
  be pointed elsewhere.
- Not covered: the script does not verify that a located surface volume is at the scale the
  recipe trains at. #1580 is adding exactly that check on the inference side, and it belongs
  there rather than here.
- No changes to any existing file.

**Why this matters to me:** I wanted to see whether the publicly released ink_9um model could
generalize to scrolls it had never seen before. The recipe was available, but it did not run
as-is, so before I could even get to that question, I had to manually define 29 dataset
entries. I then repeated the joins and quota calculations for each arm across three
leave-one-scroll-out splits and one two-segment holdout. At that point, it made more sense to
keep the setup in the repository than in my notes.
