<!--
PR body draft — F2 against `main`, written to villa's pull_request_template.md.

  head:  khj1222:fix/eager-fallback-at-first-forward  (9d2eb0a, pushed)
  base:  main   ← NOT merge-ink-pipelines
  diff:  2 files, +121 −5

⚠️ Seven template fields below, in the template's order, with ITS checkbox (not the issue
   template's). #1434 was closed for CONTRIBUTING non-compliance; do not paste over the
   prefilled template with something that does not match it.

⚠️ TWO THINGS THE USER SUPPLIES:
   1. **Why / where this is useful** — CONTRIBUTING requires human-written commentary on an
      LLM-assisted PR.
   2. **The screenshots** in Proof — the crash, and the same run continuing afterward.

⚠️ Do not tick the checkbox until the screenshots are attached and you have looked at them.

Supersedes our own #1662. Evidence: runs/f2_main/.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** Inference on a machine whose compiler backend cannot build now falls back
to running eagerly, instead of dying part way through the run.

**One real example:** Starting with the w00 surface volume of PHerc. Paris 4, I ran the
tutorial's `infer` command on native Windows with a released checkpoint. `torch.compile`
returned without complaint and the run started; it then died on the first block with
`torch._inductor.exc.TritonMissing: Cannot find a working triton installation`. Triton publishes no Windows wheel,
so this is what every native-Windows install does.

**Before:** the run stopped with that traceback. `maybe_compile_model` already wraps
compilation in `try/except` so that a compiler problem degrades to eager — but that `except`
cannot see this failure, because **`torch.compile` compiles nothing when it is called.** It
returns a wrapper and the backend runs on the first forward, outside the guard. The documented
workaround has been to remember `--no-compile` on every invocation.

**After this PR:** the first forward is guarded. If the backend fails there, it warns once,
drops the compiled module and returns the eager result — for that batch and every later one.
The run finishes. A working backend is untouched.

**Proof:** measured on this machine, `torch 2.10.0+cu128`, Python 3.12, Windows 11, with
`triton` not importable:

| path | did `torch.compile` raise? | what the first forward raised | after this PR |
|---|---|---|---|
| CUDA | no | `torch._inductor.exc.TritonMissing` | warns once, eager result |
| CPU | no | `Compiler: cl is not found.` | warns once, eager result |

Both forwards match the uncompiled output exactly (`allclose`, atol 1e-6) on both paths, and
the failed backend is called once rather than retried per forward. With a working backend, all
three forwards go through the compiled module and nothing is logged.

![compile fallback, before and after](https://raw.githubusercontent.com/khj1222/vesuvius-challenge/main/runs/f2_main/f2_console.png)

*Console output of the script linked below: `torch.compile` returning without raising, the first forward failing, and the same model continuing eagerly with matching values after this PR.*

Script and raw output: https://github.com/khj1222/vesuvius-challenge/tree/main/runs/f2_main (`f2_shot.py`, `f2_console.txt`, `real_cuda_backend.json`, `real_cpu_backend.json`)

**Why / where this is useful:**

<!-- USER WRITES THIS. Do not draft it. In your own words: that every inference run on this
     machine needed --no-compile before you knew why, and what it looked like the first time it
     died mid-run. Two or three sentences. -->

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

The change is in `ink_detection/inference/inference_runtime.py`, which both inference commands
reach through `prepare_model_for_inference`, so `infer.py` and `infer_full3d_tifxyz.py` are
covered by one edit. The compiled module is wrapped so the first forward is guarded; the eager
module is the registered child, so `.to()` and `.eval()` still reach it, and the compiled
wrapper holds that same module, so registering it as well would only duplicate every parameter.
Cost after the first successful forward is one attribute test per call.

`maybe_compile_model`'s returned flag now means *compilation was set up* rather than
*succeeded*, which is all it could have meant given when the backend runs; the docstring says
so. Both callers are unchanged, and the repository's existing
`test_compile_fallback_returns_eager_model_when_compiler_is_unavailable` passes untouched.
Three tests are added beside it: a backend that fails when it runs, a backend that works, and
the wrapper keeping module behaviour.

The tidier-looking fix is to compile and then immediately run a synthetic warmup batch, so the
failure lands inside the existing `try`. It needs a shape, and a wrong guess would turn a
working Linux install into a silent eager fallback — a quiet slowdown everywhere in exchange
for a loud Windows crash. The real first batch is the probe instead.

`models/training/train.py` has the same shape and is left alone: the crash I hit was in
inference, and that is where this is verified.

This supersedes [#1662](https://github.com/ScrollPrize/villa/pull/1662), which fixes the same
defect inline in `infer.py` against `merge-ink-pipelines`, where this policy is not yet shared.
I will close that one. Same question as on
[#1608](https://github.com/ScrollPrize/villa/pull/1608) about which branch to target; this is
the `main` answer.

Tested at `5479453` (`main`).
