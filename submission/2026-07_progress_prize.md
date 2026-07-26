# July 2026 Progress Prize — submission package

**Form:** https://forms.gle/xoF5C3QsYutKP97x7 ("July 2026 Progress Prizes")
**Deadline:** 2026-07-31 23:59 PT
**Order matters:** the form has a required "Pull request submitted!" checkbox, so do **step 1 first**.

---

## Step 1 — PR to awesome-scroll-tools ✅ done

**Submitted:** https://github.com/ScrollPrize/villa/pull/1249 (2026-07-26)
**File:** `scrollprize.org/docs/20_community_projects.md` on `ScrollPrize/villa` **`main`**
**Section:** `### 🖋️ Scroll segments-based Ink Detection` → `#### ⚙️ Tools`
**Branch:** `khj1222/villa` `add-ink-validation-harness` (`2aba59a`, 1 file +3), cut from `main` tip `650076f`.

Entry added (matching the existing `- [name](url) by Author. Description.` style):

```markdown
- [Ink detection validation harness](https://github.com/khj1222/vesuvius-challenge) by khj1222. The ink-detection tutorial trains with no held-out data, so improvements cannot be told apart from noise. This generates a `_validation_mask` for a labeled segment by holding out whole annotated regions (splitting by pixels cuts letters in half), scores predictions inside it (threshold sweep, DRD / pseudo-F-measure, per-region breakdown), sweeps checkpoints, and runs k-fold. Also includes a native-Windows walkthrough of the tutorial.
```

PR title: `Add ink-detection validation harness to community projects`

---

## Step 2 — Form answers

**1. Email**
```
<FILL IN — the address the prize team should reply to>
```

**2. Your full name**
```
<FILL IN — the form asks for a real name; the repo/commits use khj1222>
```

**3. Team description**
```
Individual submission — no team.
```

**4. URL to your open source / publicly available contribution**
```
https://github.com/khj1222/vesuvius-challenge
Walkthrough: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/09_validation_harness.md
Upstream PR (fixes an OOM this work surfaced): https://github.com/ScrollPrize/villa/pull/1234
Upstream issue: https://github.com/ScrollPrize/villa/issues/1231
Community projects listing PR: https://github.com/ScrollPrize/villa/pull/1249
```

**5. Short description of how your contributions substantially increase the probability of reading complete scrolls**

```
Reading complete scrolls depends on many small ink-detection improvements compounding.
Right now the community cannot tell which of them are real: follow tutorial 5 exactly and
you train with no held-out data at all. The published segments ship no `_validation_mask`,
so `val_every` iterates an empty loader, `val_previews/` stays empty, and the DRD and
pseudo-F-measure implementations already in koine_machines/evaluation/metrics/ never
execute. Every "this helps" claim built on the tutorial is currently unfalsifiable.

This contribution supplies the missing piece, without forking the pipeline: a tool that
carves a leak-free held-out set (the supervision mask on these segments is 15 disconnected
letter regions, so a naive rectangular split trains on one stroke and scores the one beside
it), an evaluator that reports a threshold sweep plus DRD / pseudo-F-measure and a
per-region breakdown, a checkpoint sweep, and an unattended k-fold driver.

Running it on w00_20231016151002 turned 0 validation patches into 1,337 and produced three
results nobody could previously see: the practical noise floor is ~0.03 F1 (3 folds plus a
20% split of one unchanged config span 0.823-0.854), so smaller reported gains are not
evidence; the tutorial's 20k schedule overshoots, with 2 of 3 folds peaking at step 17000
and falling by 20000; and the F1-optimal threshold drifts between 122 and 198 across
checkpoints, so fixed-threshold comparisons partly measure calibration, not quality.

It also surfaced two pipeline defects: create_label_zarrs OOMs on striped TIFF input (fixed
in PR #1234, verified byte-identical to the existing tiled path), and the patch cache is
keyed by asset paths, so replacing a mask silently reuses the old split. Anyone proposing
an ink-detection improvement can now be asked for a number that means something.
```

**6. Pull Request Submission** → check "Pull request submitted!" (step 1 done → PR #1249)

**7. Terms and conditions** → "Yes, I agree"
(Award acceptance requires permissive open-sourcing; the repo is already MIT.)

---

## Evidence backing the claims above

| claim | source |
|---|---|
| 0 → 1,337 validation patches | `runs/ink_tutorial/flat_ink_patches_*.json` vs `runs/ink_holdout_20k/…` |
| single split F1 0.8232 / IoU 0.6995 | `runs/ink_holdout_20k/validation/summary.csv` |
| 3-fold 0.8497 / 0.8537 / 0.8383, mean 0.8472, spread 0.0154 | `runs/ink_fold_cv_summary.json` |
| leakage baseline 0.8594 | `runs/eval_leaky_regions.json` |
| per-region F1 0.796–0.895 | `runs/ink_holdout_20k/validation/final_full.json` |
| 15 supervised regions, 4 within one patch of a neighbour | `docs/09_validation_harness.md` |

(Run artifacts live under the gitignored `external/villa/ink-detection/`; the numbers are
reproduced in `docs/09_validation_harness.md`.)
