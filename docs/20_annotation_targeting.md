# Does it matter *where* you annotate? A pre-registered test

**Everything below was written and committed before the arms were built or run.** The
selection rules, the decision rule and the predictions are fixed here so that the result can
only be read one way. This follows the pattern of [docs/18](18_uda_design.md), where
pre-registration is what let us report an arm that harmed the model instead of quietly
dropping it.

## What this asks, and what it does not

[docs/15](15_loso_cross_scroll.md) part 5 measured *how much* annotation is worth: on
PHerc Paris 4, keeping half of one segment's annotation retains 89.3% of the benefit of the
whole, a fifth retains 70.8%, an eighth 55.8%. It never asked *which* half.

This asks a narrower question than "how should an annotator choose":

> Given a set of candidate areas an annotator could work on, at a fixed annotation budget,
> **how much does the choice between them change the model?** And does ranking the
> candidates by the model's own uncertainty capture any of that?

**It is not a test of where to start on an unread scroll.** The candidate areas here are the
regions that were already annotated on `phercparis4-w00`, because those are the only places
we can construct a label tree from. On a genuinely unread scroll the candidates would be a
grid over the surface, and nothing here shows that the ranking transfers to that setting.
The claim, if the effect exists, is about ranking candidates — not about finding them.

## Why the baseline is not "random"

`tools/make_label_budget.py` does not sample. For each budget it exhaustively searches the
subsets of the previous subset and scores each on two terms: how close its area lands to the
target share, and how close its ink density lands to the segment's global density. So the
published curve was produced by an already-sensible rule, and "uncertainty beats random" is
the wrong comparison. The comparison that means something is between rules at the same
budget, with the spread across them as the ceiling any rule could reach.

## The candidate space

`phercparis4-w00` carries **15 annotated regions**, collapsed into **9 groups** — regions
closer together than one 256 px training patch are kept together, because splitting them
would leak across the boundary. Group areas and ink densities are recorded in
`data/ink_9um/labels/labelbudget/phercparis4-w00_label_budget.json`.

The budget is fixed at the published `keep0250` arm: **20.7% of the annotated area**, which
is where the curve bends (70.8% of the benefit retained). Admitting every subset whose area
lands within ±3 percentage points of that gives **28 candidate subsets** (14 of size 3, 10 of
size 4, 2 of size 5, and 2 of other sizes). That is the space the rules choose from.

## The four arms

| arm | selection rule, fixed in advance |
|---|---|
| `density` | the published `keep0250` subset — groups {3, 4, 5, 8}, area 20.72%, ink density 0.2462. Already trained and scored; no new run |
| `disagree-max` | of the 28, the subset with the **highest** mean seed disagreement of the base model over its supervised pixels |
| `disagree-min` | of the 28, the **lowest** |
| `random` | one subset drawn uniformly from the 28 with a fixed seed (`numpy.random.default_rng(0)`); if it coincides with another arm, draw again |

**The acquisition score uses no labels.** The leave-Paris4-out base checkpoints
(`runs/ink9um_loso_noParis4_s{42,43}/ckpt_020000.pth`) are run over `phercparis4-w00` once
each, and the per-pixel disagreement |p₄₂ − p₄₃| is averaged inside each group's supervised
area. Only the images and the model are used, which is information a real unread scroll also
has. Ties are broken by the lower group index, so the choice is reproducible.

## Protocol

Identical to the label-efficiency run, so the numbers sit beside the published ones:

- fine-tune the same base for **2,500 steps** (the saturation point measured on both
  PHerc Paris 4 and PHerc 1667), seeds 42 and 43;
- score the **7 Paris 4 segments the base never saw**, with the same sweep and the same
  best-F1 selection;
- report the mean over those 7 segments, averaged over the two seeds, plus the per-segment
  table — segment variance was threefold in the label-efficiency run (93.5% against 82.7%),
  so a mean alone would hide it.

Each arm gets its **own `out_dir`**, because the patch cache is keyed on paths and would
otherwise silently reuse the previous arm's split.

## Decision rule

Let **spread** = (highest arm mean) − (lowest arm mean) across the four arms.

- **spread < 0.03** → report *at this budget, which regions you annotate does not change the
  result*. The acquisition idea is dead, and the finding is an instruction to annotators:
  annotate what is convenient. This outcome is not a failure and will be reported as
  prominently as the other.
- **spread ≥ 0.03** → report the ordering, and claim an acquisition effect **only if**
  `disagree-max` beats `disagree-min` **in both seeds** by at least 0.03. Anything weaker is
  reported as "the choice matters but our ranking does not capture it", which is a different
  and weaker claim.

0.03 F1 is the noise floor established in July across four evaluations of one configuration
(0.823–0.854) and used throughout docs/12, 15 and 18.

## Predictions, committed

- spread between arms: **0.02–0.06**;
- `disagree-max` beats `density`: **about 50%** — genuinely uncertain;
- an ordering that survives both seeds at ≥ 0.03: **about 40%**.

Recording these matters because in [docs/18](18_uda_design.md) we predicted arm B's sign and
were wrong: entropy minimisation was predicted to recover 10–40% of the gap and instead cost
0.041 F1. A prediction written afterwards is not a prediction.

## What gets published

Per-arm and per-segment cells as CSV, the subset each rule chose with its area and density,
the group disagreement scores, and the summary with the verdict — under
`runs/ink9um_scorecard/`, alongside the label-efficiency matrix this extends.

---

## What the selection produced

Recorded after running the selection and before training any arm. These are inputs, not
results. Raw numbers: `runs/ink9um_scorecard/annotation_candidates.json`.

Group disagreement, averaged over each group's supervised pixels, spans **0.0791 to 0.1091**
across the nine groups — a narrow band. At the subset level the four arms span 0.0813 to
0.0880, so the ranking is working with a weak signal. That is worth knowing before the
result arrives: if the arms come out inside noise, "the ranking had little to rank on" is a
live explanation alongside "where you annotate does not matter".

| arm | groups | area kept | ink density | mean disagreement |
|---|---|---|---|---|
| `density` (published) | 3, 4, 5, 8 | 20.72% | 0.2462 | — |
| `disagree-max` | 0, 2, 3, 4, 5 | 19.20% | 0.3071 | 0.0880 |
| `random` | 2, 3, 5, 8 | 23.49% | 0.2301 | 0.0868 |
| `disagree-min` | 0, 4, 7 | 19.67% | 0.3017 | 0.0813 |

⚠️ **A confound the ±3 pp tolerance introduced, stated before the result.** The arms do not
spend identical budgets: `disagree-max` keeps 19.20% of the annotated area while `random`
keeps 23.49% — 22% more annotation. The tolerance was fixed in advance and stays fixed, but
the reading has to account for it:

- if `disagree-max` wins, the budget difference worked **against** it, and the finding is
  stronger than it looks;
- if `disagree-max` loses, the budget difference is a live alternative explanation and will
  be reported as one rather than buried.

Ink density also varies with the subset (0.2301–0.3071); the published `density` arm is the
only one selected to match the segment's global 0.2303, which is exactly why it is in the
comparison.

## Reproducing

```bash
python tools/score_annotation_candidates.py     data/ink_9um/labels/aligned-scrollprizeorg-21slices/phercparis4-w00     --predictions runs/ink9um_scorecard/preds/phercparis4-w00_loso42_020000.tif                   runs/ink9um_scorecard/preds/phercparis4-w00_loso43_020000.tif     --target-keep 0.2072 --tolerance 0.03 --reference-groups 3 4 5 8     --out runs/ink9um_scorecard/annotation_candidates.json

python tools/make_label_budget.py <segment_dir> --out-root data/ink_9um/labels/annotarget     --groups 0 2 3 4 5 --name disagreemax          # and the other two arms

python tools/run_annotation_targeting.py --phase all
```

The scoring path was checked against a published cell before any arm ran: rescoring
`keep0250` seed 42 on `phercparis4-w01` at step 2,500 reproduces the label-efficiency matrix
row exactly — F1 0.7731 at threshold 122, precision 0.7927, recall 0.7545, over the same
8,268,843 scored and 2,163,941 ink pixels. The two matrices are therefore comparable cell
for cell.
