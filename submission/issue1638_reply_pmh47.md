# Reply draft — villa #1638, after pmh47 closed it

**Thread:** https://github.com/ScrollPrize/villa/issues/1638
**Closed by:** `pmh47` (Paul Henderson, Research Team Lead), 2026-08-29 12:05 UTC, with:

> "validation mask is disjoint from the supervision mask" -- indeed, so there is no actual
> issue. Provided one interprets results carefully in terms of what is intra-segment /
> inter-segment / inter-scroll results (which one always should!), and does not make overly
> broad claims, there is no problem.

**Assessment before replying.** He is right on the substance that matters most: disjoint
means those pixels were never trained on, so there is no label leakage, and an intra-segment
held-out number is a legitimate thing to report as long as it is named that. Our own docs/17
already says the corpus is not wrong and keeps the claim directional — but the issue *title*
said "leak-free", which presupposes a leak, and that is what he pushed back on. The framing
overran the body.

What he did not address is the measured part: the adjacency demonstrably pays, +0.14 F1 on
w016 against a flat control. That is not a contradiction of his answer — it is a size for
the distinction he says one should always make.

**Tone rule for this reply:** concede first and plainly, add exactly one thing, ask for
nothing, do not argue for reopening. He closed it; that stands.

Paste only what is below the `---`.

---

Fair, and the wording was mine to fix — "leak-free" presupposes a leak and there isn't one:
those pixels were never trained on. Intra-segment held-out is a legitimate number, and
naming it that is the answer.

The one thing I'd leave on the record, since "interpret carefully" turns out to have a size
here: on `pherc0139-w016`, a model that trained on the segment gains +0.14 F1 more on
held-out pixels within 64 px of its training pixels than on those 128–256 px away, while a
model that never saw the scroll is flat across the same strata (0.536 / 0.540 / 0.579). That
is the intra-versus-inter distinction you name, measured on this corpus. The script that
does it is linked above if it is ever useful for reporting alongside a held-out number.

Thanks for the correction.
