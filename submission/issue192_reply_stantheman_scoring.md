<!--
Draft reply to stantheman0128 on villa issue #192 "Accurate 3d ink labels".
target: https://github.com/ScrollPrize/villa/issues/192
replying to: their scoring result of 2026-08-25
  https://github.com/ScrollPrize/villa/issues/192#issuecomment-5412366718

⚠️ We asked for this scoring, they did it, and we have not answered for a week while using
the numbers in a submission. The reply opens by saying so rather than burying it.

Numbers quoted here are theirs, copied from that comment; nothing is recomputed on our side.

POST ONLY WHAT IS BELOW THE --- LINE.
-->

---

@stantheman0128 Thank you — and sorry for the slow reply. You ran this at my request, posted the numbers a week ago, and I used them before I answered you here, which is the wrong order.

**What it settled for me.** Before you ran it I wrote down the two readings it could separate: either the estimator's geometry is wrong, in which case my negative result says nothing about #192's premise, or the geometry is sound and the measured band still loses to a fixed one, which is the stronger claim. Median D of 2 voxels with 118 of 157 anchors inside 3 puts it on the second branch. On the sliver you can see, the band is sitting near a surface that was independently observed at 1.129 µm — so "the per-pixel wander is estimator noise" is not the explanation for why `v4` lost, and the comparison stands as a statement about the labels rather than about a broken estimator.

That is the measurement my own experiment could not produce, because everything in it descends from the same model. It went into my August submission as the independent check on that result, credited to you by name and pointing at your repository and hashes rather than restating your numbers as mine.

**What I am not taking from it**, in your words as much as mine: this is distance to an independently observed surface, not an ink-identity test; it covers region 15 alone, because the 1.129 µm scan does not reach the other fourteen; and it says nothing about why `v4` loses in training. @pmh47's objection — that a gradient peak in a 1 µm scan need not be the recto surface, and that ink need not sit on it — is untouched by any of this.

I also want to flag the part of your result that does not flatter my hypothesis, since it would be easy for me to quote only the first table. Adjacent-cell |ΔD| has the same median as random pairs, so your run does not support "smooth sheet" any more than it supports a random field; you said so plainly and you were right to. And `corr(offset_from_plane, D) ≈ 0` is the check I should have thought to ask for — it rules out the reading where D merely echoes how far the band moved from z = 32.

**Where this leaves #192.** My result remains a narrow negative: on this segment, a band measured per pixel from a depth-blind model loses to a fixed band by 0.038 F1 across three folds, replicated on a second segment at 0.098, and the schedule is not the explanation. It does not say #192 is wrong — it says this route to a 3D label does not beat the constant one, and now, thanks to your scoring, it says that without the escape hatch that the geometry was simply bad.

If you ever extend the footprint to other regions I would be glad to export anchors for whichever segment helps. The exporter is `tools/export_depth_anchors.py` and it takes any segment with a measured band, so the cost on my side is minutes.
