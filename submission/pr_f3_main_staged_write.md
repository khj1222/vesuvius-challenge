<!--
PR body draft — F3 rewritten against `main`.

  head:  khj1222:fix/retry-staged-publish-on-windows  (8ce9725, pushed)
  base:  main   ← NOT merge-ink-pipelines
  diff:  2 files, +205 −3

⚠️ Two things before opening this:

1. **"Why this matters to me" is left blank on purpose.** villa/CONTRIBUTING.md asks for
   human commentary on an LLM-assisted PR, and #1434 was closed partly over it. I do not
   write that paragraph — the user does, in their own words.

2. **This supersedes our own #1663**, which fixes the same failure inline in one script on
   `merge-ink-pipelines`. Do not leave both open silently; the body says so and offers to
   close #1663. If the maintainers prefer the other branch, close this one instead.

⚠️ GitHub prefills a new PR body from the commit message plus the template. Overwrite it
   after opening, and keep the template's checkbox line — #1638 lost the template that way.

Evidence: runs/f3_main/ (committed). Every number below comes from
runs/f3_main/real_windows_conditions.json and pytest.txt.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

- [x] I personally encountered or reproduced this, and the change is verified rather than assumed.

`publish_staged_output` renames a finished stage onto its output path. POSIX renames
regardless of who holds the path; Windows refuses while anything does, and one open file
inside a staged directory is enough. Measured against the patched module on Windows, so the
codes are what the OS actually raises rather than what a mock asserts:

| condition | result |
|---|---|
| nothing holding the staged directory | publishes, 0.0 s |
| one file inside it open for read | `PermissionError` **WinError 5** |
| the process working directory inside it | `PermissionError` **WinError 32** |
| a handle released 0.4 s in | retries, then publishes |

The refusal is transient. The cost of treating it as fatal is not, because all four callers
stage a completed output and rename it last, so the failure lands after the work is done —
for `prepare_9um_isotropic_input`, after every tile of a multi-gigabyte conversion is already
on disk. What surfaced was a bare `pathlib` traceback, which reads like the conversion has to
be run again. It does not: the output is complete, under the staged name.

**The change.** Retry a sharing violation with backoff. Raise every other `PermissionError`
on the first attempt, so POSIX takes exactly the path it takes today — the retry is gated on
`winerror`, which does not exist off Windows. If it never clears, attach a note saying the
staged output is complete and naming both paths, so what is finished gets renamed instead of
recomputed. The staged tree is left in place; `output_path` is never partially created.

It sits in `staged_write.py` rather than in a caller because `clean_labels`,
`composite_from_zarr`, `merge_predictions` and `prepare_9um_isotropic_input` all publish
through it — one function, four tools. `attempts` and `retry_delay` are keyword-only with
defaults, so every existing call site is unchanged.

**Tests**: eight, in `vesuvius/tests/ink_detection/test_staged_write.py`. They cover
publishing a file and a directory, retry-until-clear for both winerror codes, an immediate
raise for any other `PermissionError` with no sleep at all (the POSIX guarantee), the give-up
path asserting the note names both paths while the staged bytes survive and the output does
not appear, and — `skipif` off Windows — a real open handle released by another thread.

**What I left out on purpose.** An earlier version of this fix also dropped the script's own
zarr handles before renaming. I could not show that those handles were the cause in the
failure I hit, and an unmeasured change does not belong in a fix for a measured one, so it is
not here.

**This supersedes [#1663](https://github.com/ScrollPrize/villa/pull/1663)**, which I opened
against `merge-ink-pipelines`, where this code has no shared module and the rename is inline
in `prepare_9um_isotropic_input`. That version fixes one script; this one fixes four callers
in three fewer lines of change. I will close #1663 if you take this — say the word, or close
this one if the other branch is where you want it. I have also asked on
[#1608](https://github.com/ScrollPrize/villa/pull/1608) which branch ink-detection work
should target now; this PR is my answer for the case where it is `main`.

## Why this matters to me

<!-- USER WRITES THIS PARAGRAPH. Do not draft it. Suggested substance, in your own words:
     the 24 input preparations this ate, what the traceback looked like at the time, and
     why "the data is fine, just rename it" is the sentence you wanted to see. -->
