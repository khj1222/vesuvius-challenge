<!--
Draft comment on our own villa PR #1608 "scripts: expand the aligned-21 contract into a
runnable (optionally held-out) config".
target: https://github.com/ScrollPrize/villa/pull/1608

Why post this now, 2026-09-04:
  - Our PR #1535 was CLOSED on 2026-09-03 by a bot: "Closed automatically under the
    repository PR time limits because this PR has had no activity for 14 days."
    https://github.com/ScrollPrize/villa/pull/1535#issuecomment-5522067422
    Its last activity was 08-19, so the window is real and it applies to all four of our
    open PRs. #1608's last activity was 08-28 → it goes around 09-11.
  - `origin/merge-ink-pipelines` tip is 3ea17f54a (2026-08-14), which is our own #1234.
    Zero commits in three weeks, while `main` is committing daily. That is a genuine
    question worth asking, and asking it is also what keeps the PR open.

⚠️ This is a QUESTION, not a ping. If it reads as "please review me", cut it back further.
Do not complain about the wait or about reviewer assignment.

⚠️ #1434 could not be reopened after it was closed, which is why we ask before the bot
fires rather than after. Keep that to one clause; it is context, not a grievance.

Verified 2026-09-04:
  - branch merges cleanly, base has not moved since the branch was cut
  - diff is 1 file, +222 (c61cc9f + dc9edb6)
  - CI green; the only red check is Vercel "Authorization required to deploy", which is the
    bot's reaction to an external contributor and needs a team member, not a code change

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

A question about targeting rather than about this diff.

This PR is based on `merge-ink-pipelines`, because `ink-detection/scripts/` only exists
there. That branch's tip is still `3ea17f5` from 2026-08-14, while `main` has been
committing daily since. I have four open PRs pointed at it, so before any of them go
further: **is `merge-ink-pipelines` still the branch ink-detection changes should target,
or has that work moved?** If it should go to `main` instead, I am happy to rewrite these
against whatever the current layout there is — the `main` copy of this pipeline has
diverged enough that it would be a rewrite rather than a rebase, and I would rather do that
once, deliberately, than guess.

Concretely, why it matters rather than being bookkeeping: #1663 patches a `.replace()`
inline in one script on this branch, but on `main` that same publish step is already
factored into `ink_detection/preprocessing/staged_write.py` with four callers, so the same
fix there would be one function covering all of them and a much smaller diff to read. #1662
is the same shape — the compile fallback it repairs lives in
`inference/inference_runtime.py` on `main`, shared, where I patched it inline here. I would
rather find that out before asking anyone to review the versions I have.

Asking now because #1535 was closed automatically yesterday under the repository's 14-day
inactivity policy, and a previously closed PR of mine (#1434) turned out not to be
reopenable, so I would rather ask while these are open than re-open the same work a third
time.

Status of this one, unchanged since 08-28: @Bullo27's review found a real crash —
`renormalise` returning all-1 quotas when `batch_size` is smaller than the number of
surviving scrolls, which made the trim loop call `max()` on an empty sequence — and that is
fixed in `dc9edb6` by refusing the configuration outright, since `samplers.py:84` rejects a
zero quota anyway so there is no valid config in that corner. Everything they flagged as
unverified was then run against the real corpus: `--exclude-segment` reproduces our three
LOSO configs byte-identically, both zarr-discovery branches fire on the real trees
(`aligned9` as `<seg>.zarr`, `native9` as `<seg>/<one>.zarr`), and `--allow-missing` turned
up a second wart, which is fixed too. CI is green; the one red check is Vercel asking a team
member to authorise a deploy for an outside contributor.

Also happy to shrink it if 222 lines is the obstacle — the `--exclude-*` flags and the
contract-expansion are separable.
