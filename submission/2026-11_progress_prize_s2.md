# November 2026 Progress Prize — submission S2 (measurements) package

**Form:** https://docs.google.com/forms/d/e/1FAIpQLSeB6MC_--4UCCEGc3zalX57-uE4puRcE_vJoYJCrEt4uYaaaw/viewform
("November 2026 Progress Prizes", taken from https://scrollprize.org/prizes; the form URL is round-specific.)
**Deadline:** 2026-11-30 23:59 Pacific = 2026-12-01 16:59 KST.
**Status:** ready (2026-11-14). Not submitted yet: the user will submit S1 and S2 together shortly before the deadline;
re-check links and the form right before.

This is the second of two November submissions, split as villa #2102 asks (new methods, models and
measurements separately). S1, the tool (docs/37), is submitted separately.

Final pre-submit check, 2026-11-14: fields 4 and 5 read through; all 25 field-4 links (other than
Discord) returned HTTP 200; docs/33–35 carry result banners in their first lines (pushed `114f513`).

## Form answers

**Your full name**
```
Hyojun Kwon
```

**Team description**
```
Individual submission — no team.
```

**Discord display name**
```
jamiolrangmalrang4936
```

**4. URL of your open source / publicly available contribution**
```
https://github.com/khj1222/vesuvius-challenge
Does the team's Paris4 3D ink model read other scrolls? Pre-registered, verdict partial: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/34_paris4_3d_ink_cross_scroll.md
  Pre-registration, committed before any test-segment inference: https://github.com/khj1222/vesuvius-challenge/commit/f9037dc2f36358e9a0c255c106ddc4affb2fe3e5 (addendum before inference: https://github.com/khj1222/vesuvius-challenge/commit/1c05f2dd1916d3598e23774e3e198ffb8c691188)
  Tool and raw results: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/paris4_3d_cross_scroll.py , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/paris4_3d
The same model fine-tuned at 9.6 µm, pre-registered, invalid by its own validation rule: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/35_paris4_3d_ink_9um_finetune.md
  Pre-registration, committed before any fine-tune: https://github.com/khj1222/vesuvius-challenge/commit/80411bb21cc2bdc855e5249fb41579ceda4f0b0f (addendum before training: https://github.com/khj1222/vesuvius-challenge/commit/8fc17c5acd0f78c47513e256fe036d6aa4ee8e95)
  Tool and raw results: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/paris4_3d_9um_finetune.py , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/paris4_3d9
Do 9 µm models learn the ~7 px offset of labels resized from 2.4 µm maps (villa #2243)? Pre-registered, no measurable shift: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/33_label_offset_9um.md
  Pre-registration, committed before any measurement: https://github.com/khj1222/vesuvius-challenge/commit/e1e4af26fa8dc1c89c61f62cd414933dd9631ed5
  Tool and raw results: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/label_offset_shift.py , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/label_offset
A pre-registered augmentation study withdrawn before any run, because its premise was wrong: https://github.com/khj1222/vesuvius-challenge/blob/main/docs/36_main_default_augmentation.md
  Graph dump that showed it: https://github.com/khj1222/vesuvius-challenge/blob/main/tools/check_augmentation_graphs.py , https://github.com/khj1222/vesuvius-challenge/tree/main/runs/presetab
Which open ink-labelled segments the released dinovol checkpoints saw in pretraining (27 of 28): https://github.com/khj1222/vesuvius-challenge/blob/main/tools/check_dinovol_ink_labels.py , https://github.com/khj1222/vesuvius-challenge/blob/main/runs/dinovol_ink_labels/teacher_step_640000.json
Correction (an ink_9um case number is not the public w-number; w045 is a training segment): https://github.com/khj1222/vesuvius-challenge/commit/bb3517763eba94fec8cb88786f4e652af470024c
Discord #robots: https://discord.com/channels/1079907749569237093/1564220183931912192 (dinovol ink labels)
Data used: PHerc0841, PHerc0009B, PHerc0500P2 (open reviewed ink labels, set 20260918), PHerc0139, PHerc1667, PHercParis4, PHerc0814 (ink_9um labels), PHerc0343P (canvas offset check); 2.4 µm CT and 9.366 µm / 9.362 µm scans with tifxyz meshes
Models measured: https://huggingface.co/scrollprize/ink_paris4_3d_4.8um_gambiarra , https://huggingface.co/scrollprize/ink_9um , KLAVIS Reader V3 and Reader v2 (https://github.com/DomRusso2/reader-v3 , https://github.com/DomRusso2/reader-v2), KLAVIS ink9um-dense, Nieuwlaar dense-native
```

**5. What is your contribution?**
```
Four pre-registered measurements around reading ink at 9 µm, submitted apart from my tool submission as
#2102 asks. All came out partial or negative, and one was withdrawn before it ran because its premise
was wrong; each document says so in its first lines.

(1) Which scroll data

The five open-label segments used since docs/27: PHerc0841 w00, ag144, ag174, PHerc0009B ag055 and
PHerc0500P2 s1. docs/34 reads their 2.4 µm CT along the tifxyz mesh, with a PHercParis4 segment on the
model's own CT as the positive control. docs/35 fine-tunes on the 24 ink_9um training segments
(PHerc0139, PHerc1667, PHercParis4, PHerc0814) with level-2 CT (9.6 µm). docs/33 uses seven public 9 µm
models on the five segments and checks the canvas offset on seven segments of four scrolls (PHerc0139,
0500P2, 0009B, 0343P).

(2) How it raises the chance of reading these scrolls or others

The team released a 3D ink model trained on PHercParis4 only; a maintainer said nobody had run it on
other scrolls and that it could probably be fine-tuned at 9 µm. Run as released (docs/34), it carries
ink signal elsewhere: AUC 0.66 / 0.86 / 0.64 / 0.73 on the four judged segments, against 0.907 on the
Paris4 control and 0.42–0.50 for negative controls; below ink_9um on three of four by 0.13–0.23, above
it on PHerc0841 ag144 (+0.07). Fine-tuned for 10,000 updates at 9.6 µm (docs/35) it did not become
competitive (0.63–0.75, below ink_9um on all four) and failed its own validation check (0.57 / 0.60
against 0.75), so that run gives no verdict. What it does show: the released weights read 9.6 µm CT
zero-shot about as well as 4.8 µm (mean 0.70 against 0.72), and they beat random initialisation on
PHerc0841 (+0.07 to +0.09). For scrolls with only 9 µm scans, 3D ink cannot yet stand in for the 2D
9 µm readers.

villa #2243 showed that labels drawn at 2.4 µm and resized onto the 9 µm canvas land about 7 px off;
Reader v2 and V3 trained on labels made that way. We replicated the offset (6 of 7 segments at +7.0 to
+8.1 px against a predicted 7.2–7.6) and asked whether models learned it (docs/33). Neither draws ink
measurably displaced (means +1.4/+1.0 and +1.5/+0.7 px, inside the spread of models whose labels share
their input canvas), and shifting their maps back costs every model AUC (0.004–0.009). Do not
"correct" Reader v2/V3 maps for #2243.

The released dinovol encoders were pretrained with an ink term; replaying the loader's rule on the 640k
checkpoint's config shows 27 of the 28 open ink-labelled segments reached pretraining (only PHerc0009B
ag055 did not). Anyone testing a dinovol ink head on the open labels has one held-out segment, not 28.

(3) What it enables that was not possible before

A reproducible way to score a volumetric ink model against 2D human labels on any scroll with a tifxyz
mesh on its CT (sample along the mesh, band maximum along the normal, AUC on the label canvas), and a
sparse fine-tuning loop for it at 9.6 µm; answers, with numbers, to three questions people were asking
(does the 3D model transfer, does it fine-tune at 9 µm, should #2243 maps be corrected); and a list of
which open labels are not held out for dinovol.

(4) Evidence

- Pre-registration commits precede every result: docs/33 e1e4af2 → 1462c20; docs/34 f9037dc (addendum
  1c05f2d) → 3f3c5ab; docs/35 80411bb (addendum 8fc17c5) → e4b3ad7.
- docs/34: CT sampled along the mesh lines up with the published surface volume within 0.1 px on all
  six segments; the control's band units computed from the bucket and from a local copy are
  byte-identical; AUCs recomputed with sklearn are identical.
- docs/35: after the failure, ink_9um on the same validation pixels scores 0.913, so labels, masks and
  scorer are sound.
- What failed, as written in the documents: docs/33's three predictions (two seeds of one recipe differ
  by up to 7 px, so a learned shift under ~4 px cannot be seen; stage 2 not run); docs/34's "if anything
  transfers it is PHerc0841" (it holds the best and the worst segment); four of six docs/35 predictions;
  docs/36 withdrawn before training (I read the augmentation from the file named after its preset
  instead of following the import; both arms build the same graph, dumped byte-identical); and docs/32
  first called PHerc0139 w045 held out for ink_9um, but ink_9um numbers PHerc0139 cases its own way and
  its case w029 is the public w045 (jo-tud pointed it out; corrected in the docs and on Discord).

Limits: five segments of three scrolls, scored as AUC against human labels inside their supervision
masks, not as legibility. The 3D fine-tune is one short recipe. The dinovol list replays today's
metadata, not the copy used at training time.
```

**Terms and Conditions:** read and accepted by the user on the form.

## Checklist

- [x] Re-check the live form on https://scrollprize.org/prizes (2026-11-14: same five questions as October).
- [x] Read fields 4 and 5 straight through; check every field-4 link (2026-11-14).
- [x] Re-check the form and links right before submitting (2026-11-21: same form and five questions; field
  hashes unchanged from 11-14; all 25 links 200).
- [ ] Paste the fenced answers, accept the Terms, and submit (user).
- [ ] Compare the submitted text with this file and mark it submitted (receipt e-mail).

## Field hashes

Calculated over each fenced block body with LF line endings and exactly one trailing newline:

- field 4 — 3,369 chars, `da251522e48172284a20ba859f46c6a1991e0fab96affeb4b820f515217209a9`
- field 5 — 4,683 chars, `d71dfa1e71daf8bfb1e37c9ac929a30209ba4695c440dc14b689b0cf45200d77`

If either field is edited before submitting, recompute these against the actual pasted text.
