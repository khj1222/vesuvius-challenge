<!--
Comment for villa #2012 to keep it from the 14-day stale close (draft 2026-10-20). NOT posted.
  State checked 2026-10-20: last activity 2026-10-11T23:40Z (pmh47 assigned erdpx), 0 reviews,
  head 720a487d4, mergeable=true against main, test-vesuvius-python zarr 2.18.7 / 3.2.1 SUCCESS,
  Vercel FAILURE (deploy authorisation). Files: threshold.py +280, test_inference_threshold.py +161,
  docs/ink_detection.md +25, ink_detection/README.md +8, deletions 0 everywhere.
  Without activity the bot closes it 2026-10-26 00:00 PT (16:00 KST); post before 10-23 to be safe.
  Re-read the thread right before posting (erdpx may have answered).
POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@erdpx, I see this was assigned to you on the 11th. Nothing has changed since the quantile rule was pushed on the 9th: the branch still merges cleanly into current `main`, and both test jobs (zarr 2 and 3) pass. The Vercel failure is the deploy-authorisation step, not the code.

The change only adds code: one new module (`vesuvius/src/vesuvius/ink_detection/inference/threshold.py`), its 8 tests, and short sections in `vesuvius/docs/ink_detection.md` and the ink_detection README. No existing code is modified.

If a smaller PR is easier to review, I can cut it to a single rule. I would keep `quantile` in that case, because it is the one that held on all three test sets (the 0.062 case in the comment above). Is there anything you would like changed first?
