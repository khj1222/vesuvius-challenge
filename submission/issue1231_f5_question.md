<!--
Draft comment for villa issue #1231 (ours, open, assigned to erdpx).
target: https://github.com/ScrollPrize/villa/issues/1231

Purpose: ask whether an evaluation entry point is wanted upstream BEFORE building one.
This is the "ask first" step of F5 in planning/2026-09_five_k_plan.md, and the reason it
exists is #1638: we filed an audit whose title outran its body and it was closed and
locked the same day. Nothing is proposed here that has been built.

Checked at `merge-ink-pipelines` tip 3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e.

⚠️ Do not add the issue-template checkbox: this is a comment on an existing issue, not a
new issue.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

A narrower follow-up, and a question before I write anything rather than after.

I am not re-asking the first question in this issue — whether published segments are meant to ship a `_validation_mask` is still yours to answer, and I have stopped guessing at it. This is about the second half of the same gap: once you have a prediction, there is no supported way to score it.

**What I checked**, on `merge-ink-pipelines` at `3ea17f5`:

- `koine_machines/evaluation/metrics/` implements four metrics. Two of them — `Confusion` and `BalancedAccuracy` — are imported by `training/train.py` and run in the validation pass.
- The other two, `DRD` and `PFMWeighted`, have **no callers anywhere in the tree**: not in training, not in inference, not in tests. `grep -rn "DRD\|PFMWeighted"` outside their own two files returns nothing.
- `evaluation/__init__.py` and `evaluation/metrics/__init__.py` are both empty, and the package has no `__main__` and no console script, so there is no entry point either.

Put together: the validation metrics only ever run inside a training loop, over `validation_patches`, which is empty unless a segment ships a `_validation_mask` — and in the `ink_9um` corpus three segments do. A prediction TIFF sitting next to its labels cannot be scored by anything in this repository.

**The question.** Is an evaluation entry point something you want upstream, or is scoring deliberately left outside the pipeline? Either answer is useful to me and I will not push on it. If the answer is "not wanted", I would rather know now than send a PR that costs you a review to decline.

If it is wanted, two shapes, smallest first:

1. **Wire the two unused metrics into the existing validation pass.** `DRD` and `PFMWeighted` are already implemented and already have the shape the pass needs; this is a handful of lines and no new surface. It does nothing for anyone without a validation split, but it stops two metrics from being dead code.
2. **A `score` entry point**: `python -m koine_machines.evaluation.score <prediction> <segment_dir>`, sweeping the threshold and reporting the four metrics plus per-region breakdown as JSON. This is what I have been running outside the repo since July — the harness linked from this issue — so it is not speculative work, and upstreaming it means the numbers people quote come out of your code rather than mine.

I have no preference between them, and I am happy with neither. I have also not written 2 against your interfaces, deliberately: after #1638 I would rather ask than arrive with something built.

One thing I would need from you for either: whether region-level reporting belongs in it at all. My version breaks the score down per annotated region because that is what showed me a single split can move F1 by ~0.03 on this data, but that is my use, not necessarily yours.
