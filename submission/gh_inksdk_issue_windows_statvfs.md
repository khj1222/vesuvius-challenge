<!--
GitHub issue draft for LimeGS/ink-sdk (2026-11-27). POSTED by the user as LimeGS/ink-sdk#43
(2026-11-27T11:05:12Z, khj1222); checked via the API: title equal, body identical (1,394 chars, sha256 8ac6d449).
  where: https://github.com/LimeGS/ink-sdk/issues/new  (no issue template; no CONTRIBUTING)
  title (paste into the title field):
    ink_9um profiles crash on Windows in 0.1.1: os.statvfs does not exist there
  paste: only the text below the --- line.

Facts behind each sentence (checked 2026-11-27, upstream main = 62fa3b9, no newer commit):
  - clean `git archive 62fa3b9` export, Windows 11, Python 3.12.13: the repro line raises
    AttributeError: module 'os' has no attribute 'statvfs' (adapters/ink9um.py:107). hasattr(os, "statvfs") is False.
  - _loader_args is called on every ink9um infer (ink9um.py:253, `command += _loader_args(python_path, module)`).
  - before 7133cfb (a2cdff6 version) _loader_args returned [] when platform != "darwin", before any statvfs.
    7133cfb (2026-11-23, PR #32 Docker/ct-copy) added _shared_memory_bytes and calls it before the Linux check;
    `git tag --contains 7133cfb` = v0.1.1. 63c6c5a (0.1.0) has no _loader_args at all.
  - CI (.github/workflows/ci.yml): every job runs on ubuntu-24.04 or a self-hosted Linux runner. Tests
    (tests/test_ink9um.py:177-194) pass shared_memory= explicitly, so _shared_memory_bytes never runs in them.
  - real runs 2026-11-27 19:49: ink_9um@reader-v3, @argus-v3, @jeff-0846a-sub8 all exit 1 within 4-7 s.
  - with the one-line patch (planning/2026-11-27_inksdk_011/local_statvfs.patch): 0211 Reader V3 map on 0.1.1 is
    byte-identical (max |diff| 0) to the 11-25 map from 0.1.0; argus-v3 x4 controls and jeff reader on 0211 ran, ALIVE.
  - no existing issue/PR mentions statvfs (gh search issues/prs); open #42 edits ink9um.py but not this function.
  - only Unix-only call in src at 62fa3b9 (grep for statvfs/getuid/fork/fcntl/pwd/resource/killpg/...).
  - studio/v8in adapters on 0.1.1 were NOT run on Windows here (they don't call this function) → not claimed.
  - segment name 20261028201525-crop1711-lines123-v9 is a public, already-awarded segment (0211) → fine to name.

Korean (뜻): 0.1.1에서 Windows의 ink_9um 프로필이 전부 시작 전에 죽는다. 7133cfb가 공유 메모리 확인을 플랫폼 검사 앞으로
옮겼고, 이 함수는 Unix에만 있는 os.statvfs를 부르면서 OSError만 잡는다. CI는 리눅스뿐이고 테스트는 값을 직접 넣어 이 경로를
안 탄다. 재현 한 줄, 고치는 방법 두 가지, 고친 뒤 0.1.0과 바이트 동일 확인, 원하면 테스트 포함 PR 가능.
---
On Windows, every `ink_9um@*` profile fails in 0.1.1 before inference starts:

```
File "...\ink_sdk\adapters\ink9um.py", line 107, in _shared_memory_bytes
    stats = os.statvfs(path)
AttributeError: module 'os' has no attribute 'statvfs'
```

`os.statvfs` is Unix-only, and `_shared_memory_bytes` catches only `OSError`. Since 7133cfb (#32), `_loader_args` calls it on every platform, before the Linux check; before that it returned `[]` on anything but macOS. CI runs on Linux only, and the tests pass `shared_memory=` explicitly, so this path never runs there.

Repro (Windows 11, Python 3.12, ink-sdk 0.1.1 / 62fa3b9):

```
python -c "from pathlib import Path; from ink_sdk.adapters import ink9um; ink9um._loader_args(Path('.'), 'x.y')"
```

In real runs, `ink-sdk infer` with `ink_9um@reader-v3`, `@argus-v3` and `@jeff-0846a-sub8` exits within a few seconds with that traceback.

Two possible fixes: catch `AttributeError` as well in `_shared_memory_bytes`, or read shared memory only inside the Linux branch. I applied the first locally. With it, Reader V3 on PHerc0211 (`20261028201525-crop1711-lines123-v9`) gives a map byte-identical to 0.1.0's, and Argus V3 and the 0846A Reader V3 run normally. Happy to send a PR with a test that fakes an `os` without `statvfs`.

AI disclosure: found, checked and written with Claude (Anthropic, Opus 5.5) via Claude Code; I decided to report it.
