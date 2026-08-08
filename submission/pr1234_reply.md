<!--
Reply comment for villa PR #1234
  target: https://github.com/ScrollPrize/villa/pull/1234
  status: not posted as of 2026-08-09 (commit fc6d9a7 is pushed, this comment is not)

This header is an HTML comment, so the whole file can be pasted as-is.
-->

Done — thanks, that is faster. Pushed as a follow-up commit.

Each 2D level is now derived from the one before it in memory and written
straight to `DEFAULT_LABEL_SLICE`; nothing reads a zarr level back. On the
32249×51380 striped label that sent me down this path in the first place:

| | time | peak RSS |
|---|---|---|
| before (stream levels from zarr) | 114.5 s | 1.61 GiB |
| after (2D pyramid in memory) | **66.5 s** | 1.99 GiB |

against the 25 GiB the original in-memory route tried to allocate.

One wrinkle worth flagging: for `mean` mode I average in row bands rather than
in one pass, because `_downsample_mean`'s accumulator is `float64` — eight times
the output, which is a few GiB at level 1 of a full-size label and would have
undercut the point of the change. Bands start on even source rows, so every
output pixel still comes from the same four inputs through the same code.

Verified byte-identical against both the tiled streaming path and the original
`build_pyramid_with_mode` output, over 6 levels, for binary and grayscale inputs
at even and odd dimensions, plus all 6 levels of the real striped label above.
