<!-- Draft reply to hendrikschilling's P2 review on ScrollPrize/villa#1703 (2026-09-18).
     Fix pushed 2026-09-26 as 3e56ca418. Paste only what is below the line. -->

---

Thanks, that is a real hole, and your reproduction is exactly the case the first version missed: with `dynamic=False` the final partial batch (or a TTA group of a different size) compiles again, and by then the guard had already switched itself off.

Pushed 3e56ca418:

- every compiled call is now guarded, not just the first one;
- only compiler failures take the eager path: `BackendCompilerFailed`, plus `TritonMissing`, which Inductor raises directly on some installs instead of wrapping it. Ordinary model errors, including OOM, now propagate unchanged and are not rerun eagerly (the previous version caught `Exception`, which also hid those);
- the existing first-forward test now raises `BackendCompilerFailed`, which is what the real backend raises.

New tests in `tests/ink_detection/test_compile_fallback.py` use real `torch.compile` dispatch with a backend that fails on its first or on its second compilation, running batches of 4, 2, 1, 4 and checking the outputs against eager. They also cover model errors before and after a successful batch. The 17 compile tests pass on Python 3.10 / torch 2.7 and on Python 3.12 / torch 2.10. On the previous head, the second-compilation case and the four error-scope cases fail. I have not run them on the declared Python 3.14 / torch 2.12.
