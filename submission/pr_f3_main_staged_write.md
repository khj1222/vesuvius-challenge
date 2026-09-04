<!--
PR body draft — F3 against `main`, written to villa's pull_request_template.md.

  head:  khj1222:fix/retry-staged-publish-on-windows  (8ce9725, pushed)
  base:  main   ← NOT merge-ink-pipelines
  diff:  2 files, +205 −3

⚠️ Structure matters here. CONTRIBUTING.md points at .github/pull_request_template.md and
   #1434 was closed for CONTRIBUTING non-compliance. The seven template fields below are the
   template's own, in its order, including its checkbox — which is NOT the issue template's
   "I personally encountered or reproduced this".

⚠️ TWO THINGS THE USER SUPPLIES, and I do not write either:
   1. **Why / where this is useful** — CONTRIBUTING: "Any LLM generated PR must be accompanied
      by human-written commentary explaining why this PR is relevant or useful."
   2. **The screenshots** in Proof — CONTRIBUTING: "Any bugfix PR must be accompanied by a
      screenshot of the error ... and the script/tool running without error afterward."
      Drag the two PNGs into the GitHub editor and replace the two IMAGE placeholders.

⚠️ Do not tick the checkbox until the screenshots are attached and you have looked at them.

Supersedes our own #1663. Evidence: runs/f3_main/.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** Preprocessing outputs no longer throw away a finished conversion when
Windows refuses to rename the directory they were staged in.

**One real example:** Starting with the public 2.399 µm surface volumes for PHerc. 0139 in
`ink_9um`, I ran `prepare_9um_isotropic_input` to build the 9.6 µm inputs the released recipe
expects. Every tile was written and the array was complete; the run then died renaming
`<output>.zarr.partial` onto `<output>.zarr`, with `PermissionError: [WinError 5]`.

**Before:** a `pathlib` traceback after all the work was done. The output path did not exist,
a `.partial` directory sat next to it, and nothing said which of those two facts mattered — so
the reasonable reading was that the conversion had to be run again.

**After this PR:** the rename is retried with backoff, which clears it whenever the handle was
transient. If it never clears, the error carries the fact that decides what to do next: the
staged output is complete, nothing needs recomputing, and renaming it by hand finishes the job.
The staged directory is always left in place; the output path is never partially created.

**Proof:** measured on Windows 11 against the patched function, so the codes are what the OS
actually raises rather than what a test asserts:

| condition | result |
|---|---|
| nothing holding the staged directory | publishes, 0.0 s |
| one file inside it open for read | `PermissionError` **WinError 5** → retried |
| the process working directory inside it | `PermissionError` **WinError 32** → retried |
| a handle released 0.4 s in | retries, then publishes |
| a handle never released | gives up, **staged tree intact, no output created** |

![staged publish, before and after](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/f3_main/f3_console.png)

*Console output of the script linked below: the rename Windows refuses, the same case publishing once the handle clears, and the message when it never does.*

Script and raw output: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/f3_main (`f3_shot.py`, `f3_console.txt`, `real_windows_conditions.json`)

**Why / where this is useful:**

I hit this on most of the twenty-four 9.6 µm inputs I prepared for this corpus. Every
time the data was already complete — only the rename had failed.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

The change is in `ink_detection/preprocessing/staged_write.py::publish_staged_output`, which
**four** preprocessing tools call — `clean_labels`, `composite_from_zarr`, `merge_predictions`
and `prepare_9um_isotropic_input` — so one function covers all of them. `attempts` and
`retry_delay` are keyword-only with defaults, so no call site changes.

The retry is gated on `winerror` being 5 or 32. That attribute only exists on Windows, so on
POSIX every `PermissionError` is raised on the first attempt exactly as it is today; nothing
about the current behaviour there changes. On give-up the original exception is re-raised with
`add_note`, rather than a new one, so callers that catch `PermissionError` are unaffected —
three of the four catch it and discard the stage, which stays correct because for them the
staged file is a disposable temporary.

Eight tests in `vesuvius/tests/ink_detection/test_staged_write.py`: publishing a file and a
directory, retry-until-clear for both error codes, an immediate raise with no sleep for any
other `PermissionError` (the POSIX guarantee), the give-up path asserting the note names both
paths while the staged bytes survive and no output appears, and — skipped off Windows — a real
open handle released by another thread.

An earlier version of this fix also released the script's own zarr handles before renaming. I
could not show those handles were the cause in the failure I hit, so that part is not here.

This supersedes [#1663](https://github.com/ScrollPrize/villa/pull/1663), which patches the same
rename inline in one script against `merge-ink-pipelines`, where this helper does not exist. I
will close that one. I asked on [#1608](https://github.com/ScrollPrize/villa/pull/1608) which
branch ink-detection work should target; this is the `main` answer.

**Disclosure:** most of the work in this project, including this reproduction, the change and
the tests, is done with an AI coding assistant. The problem, the data and the decisions are
mine; the failure above is one my project hit while preparing the 9.6 µm inputs for the ink_9um corpus.

Tested at `5479453` (`main`), Python 3.12 and 3.14, Windows 11.
