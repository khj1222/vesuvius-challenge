<!--
Draft comment on our own villa PR #1663 "prepare_9um_isotropic_input: publish the staged
zarr even when Windows holds a handle" (F3).
target: https://github.com/ScrollPrize/villa/pull/1663

Timing: clock runs from 2026-09-02 (the user ticked the template checkbox) → auto-close
~09-16. POST AROUND 09-10..09-12 with the other two. This is the strongest of the three
comments because it offers to make the PR smaller and cover more callers.

Status note for us: DRAFT only because of GitHub's three-open-PR cap. #1535 closing freed a
slot; #1662 is the other candidate to promote. If both stay drafts, drop the last line.

Verified 2026-09-04:
  - branch merges cleanly; base has not moved since the branch was cut
  - diff is 1 file, +38 −2
  - `main` has this factored out already:
    vesuvius/src/vesuvius/ink_detection/preprocessing/staged_write.py::publish_staged_output
    is a three-line helper doing `staged_path.replace(output_path)` — the exact fragile call
  - four callers on main import it: clean_labels.py, composite_from_zarr.py,
    merge_predictions.py, prepare_9um_isotropic_input.py
  - merge-ink-pipelines (this PR's base) has no such module; the call is inline

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

I think this PR is in the wrong place, and it can be made smaller.

On `main`, this publish step is already factored into
`ink_detection/preprocessing/staged_write.py`, whose `publish_staged_output` is
`staged_path.replace(output_path)` — the exact call that fails here — and **four
preprocessing tools import it**: `clean_labels.py`, `composite_from_zarr.py`,
`merge_predictions.py`, and `prepare_9um_isotropic_input.py`. This branch has no such
module, so I patched the call inline in one script. The same fix in that helper would be one
function and would cover all four. I would rather write that version. I have asked on #1608
whether ink-detection changes should be targeting `main` now, since
`merge-ink-pipelines` has not moved since 2026-08-14; this is the concrete case where the
answer changes the diff.

The failure itself is not exotic, and I measured which conditions actually produce it before
writing anything: with nothing holding the directory the rename succeeds; with **one file
inside it open** it raises `WinError 5`, which is what killed all 24 of my input
preparations; with an incomplete `scandir` it still succeeds; and with the process's own
working directory inside the tree it raises `WinError 32`. So the fix is a bounded retry
rather than a rewrite: it publishes in 0.001 s when nothing is holding on, republishes at
1.5 s when a handle is released 0.8 s in, and if the handle is never released it exits
saying the staged output is complete and needs no recomputation, leaving it in place. That
last part is the one that mattered to me — the original failure discarded ~40 minutes of S3
streaming per segment for a directory rename.

Two things I would take direction on: whether the retry window is the right length, and
whether the give-up path should be an error or a warning. I made it a non-zero exit that
preserves the staging, on the grounds that silently leaving a `.partial` next to a missing
output is worse than saying so.

End-to-end check is a synthetic 84×300×260 input, published as 21×300×260 after the z-pool
and byte-identical to what the unpatched path produces when the rename happens to succeed.

(Draft only because GitHub caps open pull requests per author at three and I was at the cap
— the diff is finished.)
