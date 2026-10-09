<!--
Hugging Face discussion draft for Qualzz20/afv_fiber_9um (2026-10-06). NOT posted — the user posts it.
  where: https://huggingface.co/Qualzz20/afv_fiber_9um/discussions → "New discussion"
         (a discussion, not a card PR: we offer the numbers and let Qual decide; the PR is offered at the end)
  title (paste into the title field):
    Measured on an unseen scroll: PHerc0139 at 9.362 µm vs a 2.4 µm reading (numbers for the card, if useful)

Checked before drafting:
  - Card at revision 365e7800ac (2026-09-30) = the revision docs/28 measured; card has no metric, says
    "Only evaluated on native ~9 µm scans"; the repo has 0 discussions.
  - Every number below is from docs/28's results section / runs/fiber9/fiber9_summary.json:
    B 0.685 [0.664, 0.706] null 0.439; A 0.691 [0.672, 0.709] null 0.453; B−A −0.005 [−0.021, +0.009];
    per class vertical 0.49/0.49, horizontal 0.59 (B) / 0.58 (A); fiber fraction B 0.30, A 0.31, R 0.42;
    B precision 0.81, recall 0.61. Revisions: fiber_hz_vt 0905e68f14, afv_fiber_9um 365e7800ac,
    fiber_ink_4class_selfdistill ec9bbc4dbc. TTA (mirroring) on for A and B, as the card's default.
  - PHerc0139 is not in the card's training scans (0125, 0191, 0211, 0257, 0358, 0175A, 0268, 0306B,
    0800, 1447) nor validation (0813).
  - 10-09: card rewritten upstream (commits d104e288e3, e189af7507, 2026-10-07; new training repo
    github.com/Qualzz/afv-fiber-9um-training). checkpoint_final.pth LFS oid unchanged (6837f3fe8f), so the
    weights we measured are the current ones. New card: "No independent test accuracy is claimed";
    mirroring no longer "recommended", only "allowed" -> draft wording adjusted. Training list unchanged
    in substance (0125 0175A 0191 0211 0257 0268 0306B 0358 0800 1447; validation 0813 + separate 1447
    regions); PHerc0139 appears nowhere in the training repo. Still 0 discussions.
  - All numbers re-checked 10-06 against fiber9_summary.json (47um_t1, per_class_t1) and fiber9_tiles.csv
    (47um means: fiber frac A 0.311 B 0.304 R 0.422; B prec 0.810 rec 0.610).
  - No AI-disclosure line, matching our earlier HF discussions (PHerc.1667 card PRs); add one if the
    user prefers.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

Hi @Qualzz20, the card says no independent test accuracy is claimed, so here is one measurement on a scroll this model never saw, in case it is useful for the card.

**Setup.** PHerc0139 (not in your training or validation scans). Five segments (w035, w039, w040, w041, w044) have a tifxyz mesh on both the 9.362 µm scan (`20250728140407`) and the 2.399 µm scan (`20260102150214`), so the same papyrus surface can be read in both. 100 tiles of about 0.9 mm. Reference: `scrollprize/fiber_ink_4class_selfdistill` on the 2.399 µm scan. Compared on the 9.362 µm scan: this model (revision `365e7800ac`; the checkpoint is unchanged in the current `e189af7507`) and its base `scrollprize/fiber_hz_vt` (`0905e68f14`), both with test-time mirroring on. Measure: fiber-presence F1 per tile with a 1-pixel tolerance over a ±47 µm depth window. The null scores each map against the reference of a different tile, which keeps fiber densities but removes the spatial match.

| | F1 vs the 2.4 µm reading [95% CI] | null |
|---|---|---|
| `afv_fiber_9um` | 0.685 [0.664, 0.706] | 0.439 |
| `fiber_hz_vt` | 0.691 [0.672, 0.709] | 0.453 |

- Difference (this model − base): −0.005 [−0.021, +0.009], so no measurable difference on this scroll in this measure. I had predicted at least +0.03 before running it.
- Per class: vertical 0.49 for both, horizontal 0.59 vs 0.58.
- Both 9 µm models mark less of the surface as fiber than the 2.4 µm model (0.30 and 0.31 vs 0.42). For this model, precision is 0.81 and recall 0.61, so what is lost is mostly fiber that is not marked.

**What it is not.** It is agreement with a model-made 2.4 µm reference, not accuracy. It is one scroll at 9.362 µm, so the 8.64 µm scans in your training set are untested. And it compares voxel presence maps only, so it says nothing about separating touching fibers, tracing, or the fiber volumes you build on top of the model. The fine-tune's benefit may well show there.

The protocol was committed before any model was run, and the write-up, per-tile scores and every scored map are public: [write-up](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/28_fiber_9um_agreement.md), [raw results](https://github.com/khj1222/vesuvius-challenge/tree/main/runs/fiber9).

If you want it on the card, something like this would be accurate:

> **Agreement on an unseen scroll.** On PHerc0139 (9.362 µm, 100 tiles on five segments), fiber presence agrees with a 2.399 µm reading of the same surface by `fiber_ink_4class_selfdistill` at F1 0.685 (0.439 with the spatial match removed; 1-pixel tolerance), about the same as `fiber_hz_vt` (0.691). This is agreement with a model-made reference, not accuracy. [Details](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/28_fiber_9um_agreement.md).

I can open a PR with that, or you can leave this as a note. Either is fine.
