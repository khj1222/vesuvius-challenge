<!-- Draft reply for https://github.com/ScrollPrize/villa/issues/1611 (our issue), answering the
     2026-09-09 comments by TAUIL-Abd-Elilah and Bullo27. NOT POSTED. Paste only what is below the
     `---` line. Written 2026-09-15; the user posts it, or not, and may edit freely. -->
---
Thanks, both. Reading the two measurements together, here is where I think this issue stands from the opener's side:

- The stall I originally reported (`:edge` image, revision `1e3f4c0`, 2026-05-13) did not reproduce on the 2026-08-30 release build in three attempts, as I said above, and @Bullo27's drip-feed test shows the whole-transfer cap on current `main` does fire: 60 s per attempt, four attempts, then the render dies. So "waits forever with no error" is no longer an accurate description of `main`.
- What `main` does instead, per that test, is abort with `rc 134` from an exception thrown inside an OpenMP region. That is a different defect from a hang, and a worse user experience than a clean failure naming the chunk. I would welcome it being filed on its own, with the drip-feed reproduction attached, since that is reproducible without a flaky network. If you file it, please link it here.
- @TAUIL-Abd-Elilah's point survives the correction: a per-read socket timeout is not a transfer deadline. `main` already has the transfer deadline on the C++ side, so nothing more is needed here for that; it is worth keeping in mind for any Python reader of the same buckets.

Given the above, I am fine with this issue being closed once the `rc 134` crash has its own number. Maintainers, your call.

*Disclosure: I use an AI coding assistant for most of this project's work, including the wording of this comment; the reproduction attempts and the decision to recommend closing are mine.*
