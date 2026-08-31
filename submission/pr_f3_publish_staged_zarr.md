<!--
Body for a villa PR against `merge-ink-pipelines`.
Branch: khj1222:fix/publish-staged-zarr-on-windows   Worktree: D:/vw8
Base tip when written: 3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e

⚠️ BEFORE OPENING
  1. CONTRIBUTING.md wants human-written commentary on an LLM-assisted PR. The section
     marked "Why this matters to me" is left for the user.
  2. GitHub prefills the body from the commit message; replace it after opening.
  3. Tick the verification checkbox after pasting.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** A finished 9 µm conversion is no longer thrown away by the last line of the script on Windows.

**One real example:** Preparing the aligned inputs for the `ink_9um` corpus, `prepare_9um_isotropic_input.py` wrote all 416 tiles of `phercparis4-w00` and then died renaming the staging directory onto the output path:

```
tiles=416/416
Traceback (most recent call last):
  File "...\scripts\prepare_9um_isotropic_input.py", line 107, in main
    partial.replace(args.output_zarr)
  File "...\Lib\pathlib.py", line 1376, in replace
    os.replace(self, target)
PermissionError: [WinError 5] Access is denied:
  'D:\...\aligned9\phercparis4-w00.zarr.partial' -> 'D:\...\aligned9\phercparis4-w00.zarr'
```

**Before:** the data was complete and on disk, but the script exited non-zero with a traceback that points at `pathlib`. The obvious reading is that the conversion has to be repeated; the actual remedy is a manual rename. Across 24 inputs this happened often enough that I wrote a driver to finish the renames.

**After this PR:** the store's handles are released before the rename, the rename is retried with backoff, and if it still cannot publish the script says so in the terms that matter:

```
The conversion finished -- every tile was written -- but the result could not be published:
  ...\phercparis4-w00.zarr.partial
  -> ...\phercparis4-w00.zarr
  [WinError 5] Access is denied
On Windows a directory cannot be renamed while any file inside it is open.
Nothing needs recomputing: rename the staging directory by hand.
```

**Proof:** the cause first — a directory rename on Windows, one condition changed at a time:

| what is held during the rename | result |
|---|---|
| nothing | renamed |
| one file inside, open for read | **PermissionError WinError 5** |
| one file inside, open for write | **PermissionError WinError 5** |
| an unfinished `os.scandir` on the directory | renamed |
| the process cwd inside the directory | PermissionError WinError 32 |

So WinError 5 here means a file inside is still open — which is what an indexer or scanner does for a moment after a large write, and why a short retry is the right shape of fix rather than a louder failure.

Then the function, on Windows:

| case | result |
|---|---|
| nothing held | published in 0.001 s |
| a handle released after 0.8 s | retried, published at 1.5 s |
| a handle never released | `SystemExit` with the message above; staging directory left intact |

And end to end, on a synthetic 84×300×260 uint8 volume (84 = 21 × `POOL_Z`): exit 0, output shape `(21, 300, 260)`, and the bytes are identical to the expected rounded mean pooling. No staging directory left behind.

**Why / where this is useful:** anyone preparing aligned inputs on Windows, which is the first step of the ink recipe. The cost of the bug is not the rename — it is that a completed multi-gigabyte conversion looks lost.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

Three changes in one file:

1. `output_shape` is captured and `target`/`group` deleted before the rename, so the store is not holding the directory it is about to move. (The final `print` used `target.shape` *after* the rename; it now uses the captured value.)
2. `publish_partial()` retries `Path.replace` six times with exponential backoff from 0.5 s.
3. On exhaustion it raises `SystemExit` with both paths, the OS error, the reason, and the fact that nothing needs recomputing.

POSIX renames a directory whose files are open, so this is invisible on Linux and macOS; nothing changes there beyond one `del` and a loop that succeeds on its first attempt.

Scope: `main` factors this into `ink_detection/preprocessing/staged_write.py:publish_staged_output`, shared by `clean_labels`, `composite_from_zarr` and `merge_predictions`. The same exposure applies wherever a *directory* is published rather than a file. I have kept this PR to the script whose failure I actually hit; happy to follow up there if you want the helper hardened too.

**Why this matters to me:** <!-- TO BE WRITTEN BY THE USER before opening: a couple of
sentences on preparing the 24 aligned inputs on Windows and what the failure looked like
from the outside. -->
