<!--
Draft for the project Discord, #robots forum (2026-10-04). NOT posted — the user posts it.
Same conventions as discord_robots_docs27.md: name the model, separate model output from human
commentary, testable claims, under Discord's 2,000-character limit, lists instead of tables.

Checked 2026-10-04 before drafting: no fiber-at-9 µm evaluation on #robots, nothing new in Qual's
"Automated Fiber Volume" thread (#show-and-tell) since 10-03. Re-read both right before posting.
Martian's "Coverage and precision cannot rank a fiber tracer" (#robots) makes the presence-metric
point independently; it is credited in Limits.

Suggested tags: unrolling, analysis.
Title (forum post title field) — kept no stronger than the body:
  Fiber maps at 9 µm vs a 2.4 µm reading of the same surface (PHerc0139, pre-registered)

Optional, your call: mention @Qual (their model is arm B) and/or link the post from the
#unrolling-vc3d question of 10-01. Neither is in the text below.

The last line is the human part. Write it yourself (one or two lines is enough), or delete it.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

**AI disclosure:** planned, run and written by Claude (Anthropic, Claude Opus 5.5) via Claude Code, directed by Hyojun Kwon (khj1222), posted with his approval. Model output; treat it as a proposal to verify.

**Question** (after the 10-01 #unrolling-vc3d thread on fiber algos at 9 µm): how much of what a 2.4 µm fiber model sees on a sheet survives in a 9 µm fiber map?

**Setup:** PHerc0139 w035/w039/w040/w041/w044 have tifxyz meshes on both the 9.362 µm and the 2.399 µm scan on one UV grid (image NCC 0.60–0.84 at mapped points, ≤ 0.16 one vertex off), so no registration step. 100 tiles of 0.9 mm. At 9.362 µm: fiber_hz_vt and its 9 µm fine-tune afv_fiber_9um. Reference at 2.399 µm: fiber_ink_4class_selfdistill. 0139 is in none of their training sets. Pre-registered before any model ran (735404f).

**Fiber-presence F1 vs the 2.4 µm map** (±47 µm depth, 1 px tolerance; null = tiles shuffled):
- fiber_hz_vt: 0.691 (null 0.453)
- afv_fiber_9um: 0.685 (null 0.439)
- difference −0.005 [−0.021, +0.009]: none measurable. I predicted the fine-tune ahead by ≥ 0.03; wrong.

The loss is mostly recall: the 9 µm models mark 30% of the surface as fiber vs 42%, and ~80% of what they mark is within a pixel of reference fiber. They agree with each other (0.89) more than with the reference.

**Limits:** agreement with a Paris 4 model, not accuracy. One scroll at 9.362 µm; 8.64 µm untested. A presence map cannot see whether touching fibers stay separate (Martian's point on coverage/precision applies), so this says nothing about tracing or "squished together". Not a verdict on afv_fiber_9um or its fiber volumes.

Write-up, per-tile CSV, maps, tool: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/28_fiber_9um_agreement.md

**Human (Hyojun):** <!-- write this yourself, or delete the line -->
