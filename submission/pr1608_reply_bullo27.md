# Reply to Bullo27 on villa PR #1608

**Post as:** a comment on https://github.com/ScrollPrize/villa/pull/1608
**Status:** drafted 2026-08-28, awaiting the user posting it.
**Fix pushed:** `dc9edb6` on `khj1222:feat/holdout-config-generator` (1 file, +13 −3).

---

Thank you — the crash is real and it is fixed in `dc9edb6`.

I reproduced it exactly where you said. `--batch-size 3` with four surviving scrolls, on
`c61cc9f`:

```
  File "scripts/make_holdout_config.py", line 91, in renormalise
    victim = max((s for s in order if out[s] > 1), key=lambda s: out[s])
ValueError: max() arg is an empty sequence
```

and after the fix:

```
error: batch_size 3 cannot cover 4 scrolls; FixedScrollPriorStratifiedBatchSampler needs at least one slot per scroll
```

I used your wording with the class spelled out in full, because the reason the floor of 1
cannot simply be dropped is `samplers.py:84` — `fixed scroll quotas must all be positive`.
A zero quota is rejected there, so when `batch_size < len(live)` there is no valid config to
write and refusing is the whole answer. My own docstring had the class name wrong; that is
corrected too. The guard sits immediately after `live` is built, as you suggested.

Boundaries, on the real `ink_9um` tree: `--batch-size 4` with four scrolls gives
`{0139: 1, 1667: 1, Paris4: 1, 0814: 1}`, and `--batch-size 3 --exclude-scroll 0814` gives
`{0139: 1, 1667: 1, Paris4: 1}`. The three leave-one-scroll-out configs still regenerate
byte-identical to the ones I trained, so the guard does not touch the normal path.

On the branches you listed as untested — I have the released corpus on disk, so I ran them:

* `--exclude-segment`, four exclusions (`pherc0139-w035 w035 pherc0139-w039 w039`): 25
  representations kept, quotas `{0139: 29, 1667: 22, Paris4: 11, 0814: 2}`, and the output
  differs from the config I actually trained only in `dataloader_workers`, which I had
  lowered from 12 to 6 by hand for an unrelated Windows reason.
* zarr discovery: both branches run on every invocation here, because the released layout
  uses both forms — `surface-volumes/aligned9/<segment>.zarr` is the direct case and
  `surface-volumes/native9/<segment>/<one>.zarr` is the holder case.
* `--allow-missing`: this turned up a second wart, so thank you for pointing at it. With a
  labels root where nothing at all could be located, the script exited
  `error: every scroll was excluded` — which is untrue and sends you looking at your
  exclusion flags. It now names the two roots instead. The partial case behaves: with
  `--volumes-root` pointed at `aligned9` only, it keeps the 24 aligned representations and
  prints `WARNING: 5 input(s) not located`, and without the flag it refuses and lists them
  by name.

On the template — what you saw was GitHub's pre-fill. I pasted the prepared body over it a
few minutes after opening the PR, which was after your read; the filled template and the
checked verification box are in the body as it stands now. Sorry for the wasted look.
