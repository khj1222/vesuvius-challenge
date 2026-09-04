# F3 against `main`: retrying a staged publish Windows refuses

The same failure as [#1663](https://github.com/ScrollPrize/villa/pull/1663), rewritten where
`main` keeps this code. On `merge-ink-pipelines` the rename is inline in one script, so the
fix patches that script. On `main` it is
`vesuvius/src/vesuvius/ink_detection/preprocessing/staged_write.py::publish_staged_output`,
imported by **four** preprocessing tools — `clean_labels`, `composite_from_zarr`,
`merge_predictions`, and `prepare_9um_isotropic_input` — so one function covers all of them
and the diff is smaller.

Branch: `khj1222:fix/retry-staged-publish-on-windows`, one commit on top of `main`
(`5479453`), 2 files, +205 −3. PR body draft:
`submission/pr_f3_main_staged_write.md`.

## What the fix does

Retry a Windows sharing violation with backoff; raise everything else on the first attempt,
so POSIX behaviour is unchanged. If it never clears, attach a note saying the staged output
is complete and naming both paths, so the finished work gets renamed rather than recomputed.

## Deliberately left out

The earlier branch also released the script's own zarr handles before renaming
(`del target, group`). **That was never measured to be the cause** — the handle in the
observed failure was not shown to be the script's — so it is not in this version. The retry
is the part that was measured to work.

## Evidence

| file | what |
|---|---|
| `pytest.txt` | the 8 committed tests, run on Python 3.12 (the repo targets ≥3.14; `add_note` needs ≥3.11, so 3.10 cannot run the give-up path) |
| `real_windows_conditions.json` | real Windows failures, not mocks: which `winerror` each condition raises and whether it reaches the retry gate |
| `real_check.py` | the script that produced it |
| `patch_f3_main_staged_write.patch` | the commit |
| `pytest_conftest_stub.py` | how the tests were run here — see below |

## The three real conditions

Measured on this machine against the patched module, so the `{5, 32}` gate is matched to
what Windows actually raises rather than to what the mocks assert:

| condition | winerror | reaches the retry gate | outcome |
|---|---|---|---|
| a file inside the staged directory held open, never released | **5** | yes | gives up after the configured attempts, **staging intact, output absent** |
| the same directory once the handle closes | — | — | publishes, 0.0 s |
| the process working directory inside the staged tree | **32** | yes | gives up |

The committed test suite also includes a real-handle case (`skipif` off Windows) in which a
thread holds a chunk open for 0.4 s and the retry publishes once it closes.

## Running the tests here

`import vesuvius` pulls optional dependencies (`nrrd`) that are not installed on this
machine, and the sparse checkout has no room for them, so `pytest_conftest_stub.py` registers
the three parent packages as empty modules and loads `staged_write.py` from its real file.
**The test file itself is the committed one, unmodified**, and the module under test is the
real one; only the import path is stubbed. In villa's own CI the normal import works and the
stub is unnecessary.
