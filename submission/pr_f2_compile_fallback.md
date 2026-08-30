<!--
Body for a villa PR against `merge-ink-pipelines`.
Branch: khj1222:fix/compile-fallback-at-first-forward   Worktree: D:/vw8
Base tip when written: 3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e

⚠️ BEFORE OPENING
  1. villa/CONTRIBUTING.md requires human-written commentary on any LLM-assisted PR.
     The section marked "Why this matters to me" is left for the user to write, as on #1535.
  2. GitHub prefills a new PR body with the commit message and the template. Open the PR
     first, then REPLACE the body with everything below the --- line.
  3. Tick the verification checkbox after pasting.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**In one sentence:** Inference no longer dies part-way through a run on any machine without a working Triton — it falls back to eager execution, which is what the code already says it does.

**One real example:** Starting with a trained ink checkpoint and a surface-volume zarr on native Windows, I ran `koine_machines.inference.infer` without `--no-compile`, and it set the model up, opened the volume, scheduled the blocks, and then raised `TritonMissing` on the first forward instead of predicting.

**Before:** `maybe_compile_model` guards the call to `torch.compile`, but that call compiles nothing — it returns a wrapper and the backend runs on the first forward. So the `except` never fires, and inductor's "no working Triton" failure lands in the middle of the inference loop. Triton publishes no Windows wheel, so this is every native-Windows install; the workaround is to know to pass `--no-compile`.

**After this PR:** the first forward is guarded as well. The failure produces the warning the function already promises — `torch.compile failed on the first forward (...). Continuing without compilation.` — and the run continues eagerly and produces the same numbers.

**Proof:** the same script against the same commit, before and after the change, on `torch 2.10.0+cu128`, CUDA available, Triton absent:

```
BEFORE                                   AFTER
returned_type: OptimizedModule           returned_type: _CompiledWithEagerFallback
forward_1:  RAISED TritonMissing         forward_1:  ok, matches eager output
forward_2:  RAISED TritonMissing         forward_2:  ok, matches eager output
warnings:   "Enabled torch.compile"      warnings:   "Enabled torch.compile",
                                                     "torch.compile failed on the first
                                                      forward (Cannot find a working triton
                                                      installation...). Continuing without
                                                      compilation."
```

And with a backend that works — `torch.compile` stubbed to return a counting module, so the compiled path is exercised — the wrapper stays out of the way: 3 of 3 forwards go to the compiled module, no fallback warning, outputs unchanged. That is the case this must not regress.

`koine_machines/inference/tests/` and `koine_machines/common/tests/`: 19 passed.

**Why / where this is useful:** anyone following tutorial 5 on Windows currently hits a stack trace after the setup work is already done, and the fix is a flag that is not mentioned where the failure appears. It also covers the general case: any backend that builds lazily and fails at runtime now degrades instead of aborting a long run.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

The change is one class and one return statement.

```python
compiled = torch.compile(model, mode=..., fullgraph=False, dynamic=False)   # returns immediately
out = compiled(x)                                                            # backend runs HERE
```

`maybe_compile_model` wraps only the first line, so the existing `except Exception` is unreachable for backend failures. The PR returns a small `nn.Module` that calls the compiled model, and on the first exception logs the existing warning and falls back to the eager module for the rest of the run. After the first *successful* forward it sets a flag and stops guarding, so the steady state is one attribute test per call and no `try` around the hot path.

Two deliberate choices:

- **Not a synthetic warm-up.** Forcing compilation with a fabricated `torch.zeros(...)` at setup time needs the model's exact input layout, and getting it wrong would silently disable compilation for everyone, including the platforms where it works. Guarding the real first forward needs no shape assumption.
- **The eager module is the registered child**, and the compiled wrapper is held in a plain attribute. `torch.compile` wraps the same module object, so registering both would duplicate every parameter in `state_dict`. `.to()`, `.eval()` and `repr` behave as before; parameter count is unchanged (verified: 2 and 2 on the test model).

Scope: `main`'s copy of this logic, `vesuvius/src/vesuvius/ink_detection/inference/inference_runtime.py:150`, has the same structure and the same defect. I have not touched it here — happy to follow up in a second PR, or to widen this one if you would rather they move together.

**Why this matters to me:** <!-- TO BE WRITTEN BY THE USER before opening. CONTRIBUTING.md
asks for human commentary on LLM-assisted PRs: a couple of sentences on running the tutorial
on Windows, hitting this, and having to rediscover --no-compile. -->
