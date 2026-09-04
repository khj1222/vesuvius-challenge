<!--
PR body draft — F2 rewritten against `main`.

  head:  khj1222:fix/eager-fallback-at-first-forward  (3365213, pushed)
  base:  main   ← NOT merge-ink-pipelines
  diff:  2 files, +121 −5

⚠️ Before opening:

1. **"Why this matters to me" is left blank on purpose.** villa/CONTRIBUTING.md asks for
   human commentary on an LLM-assisted PR, and #1434 was closed partly over it. The user
   writes that paragraph, in their own words.

2. **This supersedes our own #1662** (same defect, inline in infer.py on
   merge-ink-pipelines). The body says so and offers to close it.

3. **Open it as a DRAFT.** GitHub caps open non-draft PRs per author at three and we are at
   the cap (#1608, #1661, #1662). Note that #1662 becoming redundant is the natural thing to
   close if a slot is wanted.

⚠️ GitHub prefills a new PR body from the commit message plus the template. Overwrite it
   after opening, and keep the template's checkbox line.

Evidence: runs/f2_main/ (committed). Every figure below is from
runs/f2_main/real_cuda_backend.json, real_cpu_backend.json and pytest.txt.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

- [x] I personally encountered or reproduced this, and the change is verified rather than assumed.

`maybe_compile_model` wraps the `torch.compile` call in `try/except` so that a compiler
problem degrades to eager instead of stopping inference. That `except` cannot fire for the
case it was written for: **`torch.compile` compiles nothing when it is called.** It returns a
wrapper and the backend runs on the first forward, so a backend that cannot build raises
there — outside the guard, part way through a run.

Measured on Windows 11, `torch 2.10.0+cu128`, Python 3.12, with `triton` not importable:

| | `torch.compile` raises? | the first forward raises |
|---|---|---|
| CUDA path | no | `RuntimeError: Cannot find a working triton installation` |
| CPU path | no | `RuntimeError: Compiler: cl is not found.` |

Triton publishes no Windows wheel, so on native Windows this is not an edge case — it is what
happens, and the documented workaround has been to pass `--no-compile`. The result today is a
traceback after the run has started rather than the fallback the warning already promises.

**The change.** Return the compiled module wrapped so that the first forward is guarded: if
it raises, warn once, drop the compiled module, and return the eager result for that batch
and every later one. Verified against both real backends above — both forwards match the
eager output exactly (`allclose`, atol 1e-6) — and against a working backend, where all three
forwards go through the compiled module with no warning emitted. The eager module is the
registered child, so `.to()` and `.eval()` still reach it, and the compiled wrapper holds
that same module, so registering it too would only duplicate every parameter.

`maybe_compile_model`'s bool now means *compilation was set up* rather than *succeeded*,
which is what it could ever have meant given when the backend runs; the docstring says so.
Both callers of `prepare_model_for_inference` are unchanged, and the existing
`test_compile_fallback_returns_eager_model_when_compiler_is_unavailable` passes untouched.

**Tests**: three added next to that one. A backend that fails when it runs (fallback taken,
eager values returned, and the failed backend called exactly once rather than retried per
forward); a backend that works (all forwards compiled, no warning); and the wrapper keeping
module behaviour.

**What I did not do.** The tidier-looking fix is to compile and then immediately run a
synthetic warmup batch, so the failure lands inside the existing `try`. It needs a shape, and
a wrong guess turns a working Linux install into a silent eager fallback — a quiet slowdown
everywhere in exchange for a loud Windows crash. The real first batch is the probe instead. I
also left `models/training/train.py::_maybe_compile_model` alone: it has the same shape, but
the crash I hit was in inference and that is where this is verified.

**This supersedes [#1662](https://github.com/ScrollPrize/villa/pull/1662)**, which fixes the
same defect inline in `infer.py` on `merge-ink-pipelines`, where this policy is not yet
shared. I will close that one if you take this. Same question as on
[#1608](https://github.com/ScrollPrize/villa/pull/1608): if ink-detection work should be
going to `main` now, this is that version; if not, say so and I will keep the other branch.

## Why this matters to me

<!-- USER WRITES THIS PARAGRAPH. Do not draft it. Suggested substance, in your own words:
     that every inference run on this machine needed --no-compile before you knew why, and
     what it looked like the first time it died mid-run. -->
