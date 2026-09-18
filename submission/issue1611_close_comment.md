<!-- Closing comment for our own villa issue #1611, once #1809 exists (it does, filed by Bullo27 2026-09-16).
     Paste only what is below the --- line, then close the issue. -->
---
Closing, as agreed above. Where this ended up:

- The stall this issue was opened on (`:edge`, `1e3f4c0`, 2026-05-13) does not reproduce on the current release build — 0 of 3 runs on `VC3D-5479453-2026-08-30-win64` against 4 of 4 on the old image — and "waits forever with no error" is no longer an accurate description of current `main`, which caps each fetch at ~61 s and retries.
- What current `main` does instead — abort with `rc 134` after the retries — now has its own number, #1809, with a measured repro and a graceful-exit fix offered there.
- The Python-reader side (a bare `requests.get` with no timeout) is #1774.

Thanks @Bullo27 for pinning the revision and filing #1809, and @TAUIL-Abd-Elilah for the reader cross-check.
