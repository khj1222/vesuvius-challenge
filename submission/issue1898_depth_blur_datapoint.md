<!-- Draft comment for ScrollPrize/villa#1898 (AndreasHad04, 2026-09-25). Not posted.
     Evidence: docs/23 (public), configs/ink9um_blurexp_s4{2,3}.json, D:/vw2 koine_machines/data/ink_dataset.py extra_blur,
     koine_machines/augmentation/default_augmentations.py (recipe blur). Memo: planning/2026-09-26_andreashad04_blur_vs_ours.md.
     Paste only what is below the line. -->

---

One data point on the root fix you suggest at the end, training-side depth-blur augmentation. I ran a weak form of it on 09-01, and it did nothing.

**What it was:** the leave-0139-out `ink_9um` recipe, two seeds, plus one extra `GaussianBlurTransform(blur_sigma=(0.39, 1.16), synchronize_axes=False)` at probability 0.5. It is applied to the `(1, 17, 128, 128)` image patch, so it blurs depth as well as in plane, with an independent sigma per axis. It was scored at step 20,000 on the four PHerc0139 segments published in both families (w035, w039, w040, w041), F1 against the organisers' labels:

| | arm | baseline | change |
|---|---|---|---|
| native 9.362 µm | 0.6219 | 0.6340 | −0.0122 |
| pooled 2.399 µm | 0.6693 | 0.6857 | −0.0165 |
| gap | 0.0474 | 0.0517 | −0.0043 |

Both changes are inside the seed noise on this corpus, and the two seeds disagree in sign on native (+0.0090 / −0.0333). Write-up and pre-registration: [docs/23](https://github.com/khj1222/vesuvius-challenge/blob/main/docs/23_blur_exposure.md).

Why it is weak rather than a counterexample:
- The sigma range came from an **in-plane** calibration: the Gaussian that brings a pooled plane's high-frequency residual down to a native one's (median 0.776). I never measured depth sharpness, which is the axis you found matters. Your adjacent-layer correlation (0.812 against 0.699) is a better target than mine was.
- Depth blur came along as one of three independently drawn axes, not as a dedicated depth transform at a calibrated strength.
- The recipe on `merge-ink-pipelines` already contains the same transform on all three axes (sigma 0.5–3.0, inside a `OneOf` with noise at probability 0.2). If the released checkpoints were trained with that recipe, as the published config suggests, they already saw some depth blur on about one patch in ten. A depth fix on the training side has to beat that, not zero.

One more point of agreement from earlier: an in-plane test-time fix did nothing for me either. Matching the native input's radial power spectrum to the pooled one gave +0.005 F1 on the same four segments, alongside your −0.0018. I never tried a depth-axis filter at test time, so your depth-sharpening result is on an axis I had not looked at.
