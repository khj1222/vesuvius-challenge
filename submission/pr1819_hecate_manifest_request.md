<!-- Draft comment for ScrollPrize/villa#1819 (giorgioangel, merged into distilled_3d_ink 2026-09-19). Not posted.
     October plan item C: ask once for the split; do not start Hecate follow-up work without it.
     Evidence: planning/2026-09-20_hecate_calibration/report.md (local). Paste only what is below the line. -->

---

A request about the split behind the released weights. `vesuvius/docs/hecate.md` says to use "the original audited manifest and its adjacent `patches.npz`" to preserve it, and that a freshly generated manifest is a new split. As far as I can see, that manifest isn't in the dataset bucket, and the export (correctly) contains no manifests. Could the manifest and `patches.npz` behind `scrollprize/hecate` @ `9cb86e5` be published? Even just the held-out patch coordinates and `excluded_segments` per scroll would do.

Why I'm asking: I compared the 9.6 µm model with the average of the released `ink_9um` seed-42 and seed-43 step-020000 checkpoints. The comparison used six small regions inside the published validation masks of PHerc0139 w016, PHerc1667 w029 and PHerc0814 46527, which `ink_9um` did not train on. The input was the 2.4 µm surface volume pooled to 9.6 µm, and each model's threshold was fixed on three separate calibration regions. The result is mixed. Hecate is ahead in 2 of 6 regions and on all pixels pooled, and behind in 4. The largest gap is one PHerc1667 region, AP 0.869 → 0.668. Without the split I can't tell whether those regions were training, validation or unseen for Hecate, so I can't say whether that is a generalisation gap or something else. With the coordinates I would rerun it on regions that are held out for both models and report back here.
