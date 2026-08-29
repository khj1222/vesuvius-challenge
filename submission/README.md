# submission/ — what was sent, and what was said upstream

Every Progress Prize entry and every message posted to `ScrollPrize/villa` is kept
here as a file, so a claim in a submission can be traced to the text that was
actually posted and to the artifact behind it. Files here are records, not drafts,
unless they say otherwise at the top.

The submission form is issued fresh for each round and the previous one closes —
get the current link from https://scrollprize.org/prizes rather than from an older
file.

## Round submissions

| file | round | outcome |
|---|---|---|
| [`2026-07_progress_prize.md`](2026-07_progress_prize.md) | July, submitted 2026-07-26 | **Progress Prize, $1,000** (Papyrus tier) for the held-out validation harness |
| [`2026-08_progress_prize.md`](2026-08_progress_prize.md) | August, submitted 2026-08-29 | pending; the villa #192 measured-3D-label experiment and its negative result |
| [`2026-09_progress_prize.md`](2026-09_progress_prize.md) | September, draft | cross-scroll generalisation (open problem #7) |

Each holds the exact text of every form field. The July and August files are frozen
byte-for-byte against what was submitted.

## Upstream pull requests

| file | pull request | state |
|---|---|---|
| [`villa-pr-untiled-labels.md`](villa-pr-untiled-labels.md) + [`.patch`](villa-pr-stream-untiled-labels.patch) | [#1234](https://github.com/ScrollPrize/villa/pull/1234) — stream striped TIFFs in `create_label_zarrs` | merged 2026-08-14 |
| [`pr1234_reply.md`](pr1234_reply.md) | the review round on #1234 | posted |
| [`villa-pr-flat-depth-targets.md`](villa-pr-flat-depth-targets.md) + [`.patch`](villa-flat-depth-targets.patch) | [#1535](https://github.com/ScrollPrize/villa/pull/1535) — `flat_depth_targets` | open |
| [`villa-pr-holdout-config.md`](villa-pr-holdout-config.md), [`pr1608_body.md`](pr1608_body.md) | [#1608](https://github.com/ScrollPrize/villa/pull/1608) — make the released recipe runnable, and hold a scroll out of it | open, one review round |
| [`pr1608_reply_bullo27.md`](pr1608_reply_bullo27.md) | reply fixing the crash that review found | posted |

A community-projects listing PR, [#1249](https://github.com/ScrollPrize/villa/pull/1249),
was merged 2026-07-31 and has no file here — it was a three-line change.

## Upstream issues and threads

| file | thread | note |
|---|---|---|
| [`maintainer_issue.md`](maintainer_issue.md) | [#1231](https://github.com/ScrollPrize/villa/issues/1231) | why deployed segments ship no validation mask |
| [`issue192_comment.md`](issue192_comment.md), [`issue192_followup_w02.md`](issue192_followup_w02.md), [`issue192_reply_stantheman.md`](issue192_reply_stantheman.md) | [#192](https://github.com/ScrollPrize/villa/issues/192) | the 3D-ink-label experiment, its replication, and the independent scoring offer that followed |
| [`pr1580_comment.md`](pr1580_comment.md), [`issue1582_comment.md`](issue1582_comment.md) | [#1580](https://github.com/ScrollPrize/villa/pull/1580), [#1582](https://github.com/ScrollPrize/villa/issues/1582) | the representation-family question, including the retraction of our own reading |
| [`issue1582_reply_nerln.md`](issue1582_reply_nerln.md) | #1582 | the pyramid-pooling measurement that settles the mechanism |
| [`villa-issue-render-stall.md`](villa-issue-render-stall.md), [`issue1611_reply_bullo27.md`](issue1611_reply_bullo27.md), [`issue1611_reply_bullo27_round2.md`](issue1611_reply_bullo27_round2.md) | [#1611](https://github.com/ScrollPrize/villa/issues/1611) | the renderer stall, and the correction after a reviewer identified the binary |
| [`villa-issue-holdout-audit.md`](villa-issue-holdout-audit.md), [`issue1638_reply_pmh47.md`](issue1638_reply_pmh47.md) | [#1638](https://github.com/ScrollPrize/villa/issues/1638) | the held-out mask audit — **closed and locked** by the research lead; the reply was never posted and is kept as a record of what we would have said |
| [`pr1471_comment.md`](pr1471_comment.md) | [#1471](https://github.com/ScrollPrize/villa/pull/1471) | a second contributor's fix to the same preprocessing path |

## Data shipped with a submission

- [`depth_anchors/`](depth_anchors) — 7,005 depth-band anchors from the measured 3D
  labels, in scroll coordinates with normals and an explicit list of the
  assumptions they carry. Exported so `stantheman0128` could score the band's
  geometry against an independent 1.129 µm scan, which they did (villa #192,
  2026-08-25).

`*.png` in this folder is git-ignored; a submission image has to be added with
`git add -f`.
