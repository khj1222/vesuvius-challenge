<!--
Draft for the project Discord, #robots forum (2026-10-26). NOT posted — the user posts it.
Conventions as in discord_robots_docs30_31.md. Why #robots: #rules forbids AI-written posts outside
#robots. Optional: the user can drop a one-line pointer to this post in sean's #show-and-tell thread
"dinovol pretrained models", in their own words.

Numbers, from tools/check_dinovol_ink_labels.py -> runs/dinovol_ink_labels/teacher_step_640000.json
(and planning gate doc §7–§8):
  - 640k checkpoint config: use_metadata_meshes True, ink_weight 0.1,
    output_dir .../pretrain_8_9um_objects_meshes_ink_160k; 39 training volumes.
  - 305k (dinovol_ps8_9.6um_101626): same output_dir and ink_weight, read 10-23 from data.pkl via
    HTTP range (full file not downloaded, so the tool was NOT run on it).
  - metadata.json: Last-Modified 2026-10-20 12:31 GMT, ETag 38dae48a2e8bc8eaf41292552970ec04.
  - 28 ink-labelled segments; 27 used: 0139 8, 1667 6, Paris4 8, 0841 3, 0500P2 1, 0814 1, all via
    tifxyz-transformed (checked 0841, 0500P2, 0814 individually). Not used: PHerc0009B
    20250919125754 (= our ag055), original volume 20250521125136, training volume 20260319104112.
  - Our test set (docs/30, docs/31): 0841 w00/ag144/ag174, 0009B ag055, 0500P2 s1.
  - KLAVIS #general 2026-10-25 07:01 KST: frozen dinovol features (tokens + full-res skips),
    ink vs no-ink points AUC 0.59, raw CT 0.50.
  - sean's own post (#show-and-tell, 10-23) lists "an ink prototype consistency loss" — so the
    ink term is not news; the per-segment list is.

Re-read 2026-10-26 (#show-and-tell "dinovol pretrained models", 27 messages):
  - Forrest 10-24 07:06 KST asked for early checkpoints; sean 08:39: "i might, let me take a look.
    i dont keep them around for long because they are gigantic". No follow-up yet.
  - Captain Canada 10-25 06:54 asked which scrolls/meshes were labels; sean 08:07: "every single
    8/9um scan was used, and all of the meshes which map to their volumes and their surf preds,
    along with ink labels". -> the draft now credits that and adds only the per-segment list.
  - Jordi 10-26 05:20: contrastive loss may inject mesh inaccuracies. Not our topic.
  - #robots, #ink-detection, #show-and-tell lists: no post on dinovol ink labels or on running ink
    from VC3D. Re-check right before posting.
Mention: @sean.
Suggested tags: ink-detection, datasets.
Title (forum post title field):
  Which open ink labels the released dinovol checkpoints saw in pretraining (27 of 28)

The last line is the human part. Write it yourself, or delete it.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** planned, run and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

**Why:** we wanted to compare an ink head on the released dinovol encoder with ink_9um, on open-label segments neither had trained on (PHerc0841 w00/ag144/ag174, 0009B ag055, 0500P2 s1).

**Found:** sean said in his thread (10-25) that every mesh mapping to the 8/9 µm volumes was used, with its ink labels. This makes that a per-segment list. Replaying the loader's rule in `object_labels.py` (a segment's `ink-labels` are attached when it can be placed on a training volume: a `tifxyz-transformed` mesh, or its original volume / a transform to it) on the 640k checkpoint's own config (`ink_weight` 0.1) and today's `metadata.json` (2026-10-20):
- 27 of the 28 ink-labelled segments reach pretraining: PHerc0139 8, 1667 6, Paris4 8, 0841 3, 0500P2 1, 0814 1
- the one that does not: PHerc0009B 20250919125754 (no mesh or transform onto the 2.4 µm training volume)

So four of our five test segments are not held out for these encoders; only 0009B is.

**Limits:** replays today's metadata, not the copy cached at training time. The 305k checkpoint has the same run name and `ink_weight`. Not a claim the encoder learned ink: KLAVIS's frozen-feature probe in #general (AUC 0.59, raw CT 0.50) suggests it holds little.

**Question for @sean:** is there a checkpoint from a run without the ink term? If the early checkpoints you mentioned to Forrest turn up, were they trained with it? If neither, is this the right list to exclude?

Tool and per-segment list:
https://github.com/khj1222/vesuvius-challenge/blob/main/tools/check_dinovol_ink_labels.py
https://github.com/khj1222/vesuvius-challenge/blob/main/runs/dinovol_ink_labels/teacher_step_640000.json
