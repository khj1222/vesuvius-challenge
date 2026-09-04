<!--
Draft comment on our own villa PR #1662 "infer: fall back to eager at the first forward, not
at compile time" (F2).
target: https://github.com/ScrollPrize/villa/pull/1662

Timing: clock runs from 2026-08-31 → auto-close ~09-14. POST AROUND 09-10..09-12, after
#1608's base-branch question has had a week to draw an answer. Not the same day as the
others.

Status note for us: this PR is a DRAFT only because GitHub caps open PRs per author at three
and we were at the cap. #1535 closing on 09-03 freed a slot, so it CAN be marked ready now —
that is a click in the web UI (user's action), and the comment below assumes it has been.
If it is still a draft when this goes out, drop the last paragraph.

Verified 2026-09-04:
  - branch merges cleanly; base has not moved since the branch was cut
  - diff is 1 file, +43 −1
  - `main` carries the same defect in a different place:
    vesuvius/src/vesuvius/ink_detection/inference/inference_runtime.py::maybe_compile_model
    wraps only the compile_fn(...) call in try/except, so the same unreachable-except applies

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

One design question, and one thing I found while checking this still applies.

**The question.** The obvious alternative to a first-forward wrapper is to compile and then
immediately run a synthetic warmup tensor, so the failure surfaces inside the `try` where
the existing `except` already is. I deliberately did not do that: the warmup needs a shape,
and a wrong guess turns a working Linux install into a silent eager fallback — trading a
loud Windows crash for a quiet slowdown everywhere. The wrapper instead lets the real first
batch be the probe, warns once, and returns the eager result for that batch. If you would
rather have the warmup, or would rather the fallback be silent instead of a warning, say
which and I will change it.

**What I found.** The same defect is on `main`, one directory over:
`inference/inference_runtime.py::maybe_compile_model` also wraps only the `compile_fn(...)`
call, and `torch.compile` returns lazily, so `TritonMissing` — which is what every native
Windows install raises, since Triton has no Windows build — is thrown at the first forward,
outside that `try`. The `except Exception` there is unreachable for the failure it exists to
catch. That copy is better factored than the one I patched, so the fix would be smaller
there and would cover every caller. I have asked on #1608 whether these should be targeting
`main` rather than `merge-ink-pipelines`; if the answer is `main`, I would rather rewrite
this against `inference_runtime.py` than land it here.

For what it is worth on the current diff: with a broken backend both forwards now return
eager results that match the uncompiled values, and with a working backend all three
compile-path runs still compile, with zero warnings; the suite is 19 passing.

(This sat as a draft only because GitHub caps open pull requests per author at three and I
was at the cap — it is finished, not in progress.)
