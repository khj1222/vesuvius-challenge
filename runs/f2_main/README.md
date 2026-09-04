# F2 against `main`: falling back to eager at the first forward

The same defect as [#1662](https://github.com/ScrollPrize/villa/pull/1662), rewritten where
`main` keeps this code. On `merge-ink-pipelines` the compile policy is inline in
`inference/infer.py`; on `main` it is
`vesuvius/src/vesuvius/ink_detection/inference/inference_runtime.py::maybe_compile_model`,
shared by both inference commands (`infer.py` and `infer_full3d_tifxyz.py`) through
`prepare_model_for_inference`.

Branch: `khj1222:fix/eager-fallback-at-first-forward`, one commit on top of `main`
(`5479453`), 2 files, +121 −5. PR body draft: `submission/pr_f2_main_eager_fallback.md`.

## The defect

`maybe_compile_model` wraps the `torch.compile` call in `try/except`. But `torch.compile`
compiles nothing when called — it returns a wrapper, and the backend runs on the **first
forward**. The `except` therefore cannot see the failure it exists to catch, and inference
dies part way through a run instead of continuing eagerly.

## Measured here, not asserted

`torch 2.10.0+cu128`, Python 3.12, Windows 11, `triton` not importable:

| path | `torch.compile` raises? | first forward raises | after the fix |
|---|---|---|---|
| CUDA | no | `Cannot find a working triton installation` | warns once, returns the eager result |
| CPU | no | `Compiler: cl is not found.` | warns once, returns the eager result |

Both forwards match the eager output exactly (`allclose`, atol 1e-6) in both cases, and the
compiled module is dropped after the first failure so it is not retried per call.

⚠️ Note for our own writing: the failure the CUDA path raises is a `RuntimeError` whose text
names Triton, **not** an exception class called `TritonMissing` — earlier notes in this
repository said the latter. The code comment names neither; it describes the condition.

## Evidence

| file | what |
|---|---|
| `pytest.txt` | four tests: the repository's pre-existing compile test, unmodified, plus the three added |
| `real_cuda_backend.json` | the real CUDA backend failing on the first forward and the wrapper catching it |
| `real_cpu_backend.json` | the same on the CPU backend, with the full warning text |
| `real_check.py`, `real_check_cuda.py` | the scripts that produced them |
| `patch_f2_main_eager_fallback.patch` | the commit |
| `pytest_conftest_stub.py` | how the tests were run here — see below |

## Deliberately not done

**No synthetic warmup tensor.** Compiling and then immediately running a made-up batch would
move the failure inside the existing `try`, which is tidier. It also needs a shape, and a
wrong guess turns a working Linux install into a silent eager fallback — trading a loud
Windows crash for a quiet slowdown everywhere. The real first batch is the probe.

**`models/training/train.py::_maybe_compile_model` is untouched**, though it has the same
shape. The crash was observed in inference, this fix is verified in inference, and the
training path deserves its own measurement rather than a matching edit.

## Running the tests here

`import vesuvius` pulls optional dependencies (`nrrd`) not installed on this machine, so
`pytest_conftest_stub.py` registers the parent packages as empty modules and loads
`inference_runtime.py` (and the `input_padding` module it imports) from their real files. The
test bodies are the committed ones, extracted verbatim; only the import path is stubbed. In
villa's own CI the normal import works and the stub is unnecessary.
