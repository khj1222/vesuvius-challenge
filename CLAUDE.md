# CLAUDE.md — vesuvius-challenge

새 세션은 이 파일 + `README.md` 만 읽으면 컨텍스트 없이 이어갈 수 있게 자기완결로 유지할 것.
**7~9월 상세 이력은 2026-10-02에 로컬 `planning/history_2026-07_09/CLAUDE_full_2026-10-02.md`로 옮겼다**
(gitignore, 원문 그대로; 커밋 `827e216`의 CLAUDE.md와도 동일). 옛 결정의 이유·수치 출처가 필요하면 거기서 찾을 것.
새 기록은 아래 "현재 상태" 절을 갱신하고, 날짜별 로그는 짧게 "최근 기록"에만 쌓는다.

## 현재 상태 (2026-10-09 기준, 이 절이 최우선) — 주말 일정은 10-09에 당겨 처리함

**10월 = 머지 + 소형 연구 + 10월 제출.** 10월 연구 두 건 모두 사전등록·실행·공개 완료:
- **docs/27 라벨 없는 임계값 선택**(두 번 사전등록): ① LOSO 322칸(`1b5917e` → `93c5f50`) ② 공개 체크포인트 × 새 공개라벨 스크롤 3개 70칸(`72c7679` → `393ab46`). **방법(같은 모델로 채점 가능한 스크롤에서 빌리기)은 두 번 통과, 숫자(84–92, "128 쓰지 마라")는 철회**(공개 모델 최적값 98–141, 공개 모델엔 128로 충분). 도구 `tools/borrow_threshold.py`(`b6da7af`).
- **docs/28 9µm 섬유 일치도**(사전등록 `735404f` → 결과 `1b781bf`): PHerc0139, `fiber_hz_vt` F1 0.691 / Qual `afv_fiber_9um` 0.685 vs 2.399 µm 기준(영가설 0.45), 미세조정 차이 없음(−0.005), 손실은 재현율. 일치도이지 정확도 아님.
- **공개**: README 13·14절 + Status, docs/27 정정 배너, Discord #robots 두 글(사용자 게시; docs/27 스레드 제목 10-04 수정). **10-09 확인: 두 스레드 모두 남의 답글 0.**
- **10월 제출 초안 v2** = `planning/2026-10_submission_draft.md`(10-09, field 5 통독 1회). 폼 = `docs.google.com/forms/d/e/1FAIpQLSc4flEfgK2nyjoczz2_U_XrIGMlgrnSknWatLqrFPnbtKfZwg/viewform`. 확정: docs/27(+도구) + docs/28 + **#1796(10-08 머지)** + **#1703**("09-20 9월 제출 뒤 09-28 머지라 9월엔 없었다" 명시), kartoun 맥락 줄 없음, Discord 이름 `jamiolrangmalrang4936`. villa threshold PR이 열리면 field 4·5에 한 줄 추가 검토. 제출 직전 `submission/2026-10_progress_prize.md`로 옮겨 커밋·해시. 기대치 $500~$1k(머지 2건 더해 조금 위 가능).
- 9월 라운드는 09-20 v30 제출(`submission/2026-09_form_answers.md`, 동결). **10-09 기준 9월 수상 발표 아직 없음**(#announcements 최신 = 10-09 First Letters $50K PHerc.343 Erwin Nieuwlaar 수상, 남은 대상 21개 스크롤; 09-26 YoussefNader 9µm 레시피로 PHerc1447이 First Letters 대상에서 빠짐).

### 업스트림 PR/이슈 (ScrollPrize/villa)

| 번호 | 내용 | 상태 |
|---|---|---|
| #1249 | 커뮤니티 툴 목록에 하네스 등재 | 머지 07-31 |
| #1234 | `create_label_zarrs` striped TIFF 스트리밍 | 머지 08-14 (`merge-ink-pipelines`) |
| #1701 | 패치 캐시 지문(F4, main) | 머지 09-21 (hendrikschilling) |
| #1703 | `torch.compile` 첫 forward eager 폴백(F2, main) | 머지 09-28 (hendrikschilling, `795ca2b`) |
| #1796 | Copy TTA 방향 벡터 | **머지 10-08 15:43Z** (bruniss, 리뷰 0, `12f21236a`). 워크트리 `D:/vw10`은 이제 정리 가능 |
| **#2012** | `vesuvius.ink_detection.inference.threshold` (docs/27 도구의 villa판) | **open 10-09 06:35Z**(사용자 개설, ready, 리뷰어 자동 jrudolph·bruniss). 헤드 `096760d7c` = 포크 `feat/ink-borrow-threshold`(`D:/vw15`). 게시본=초안(그림 자리만 업로드 이미지로 바뀜). Why = 사용자 말 번역("내 생각 맞다" 확인), 체크박스 끔(테스트는 내가 돌림). 14일 무활동 10-23, 28일 상한 11-06 저녁 KST. 앱 PR 모니터에 bind |
| #1705 | staged publish Windows 재시도(F3) | 10-03 봇 자동 종료, 재개설 안 함 |
| #1893 | (남의 이슈) 렌더 voxel 단위 | #1831 먼저 머지, 작성자가 10-01 닫음. 끝 |
| #192 | (남의 이슈) 3D 잉크 라벨 | kartoun이 우리 Frag1 결과를 자기 결과표에 올려도 되는지 물음(10-07) → **사용자 허락, 답글 게시 10-09 05:56Z(issuecomment-6075223909), 게시본=초안 462자 일치** |
| #1231 | (우리 이슈) 배포 세그먼트에 검증 마스크 없음 | open, erdpx 배정, 무응답 |
| HF `scrollprize/PHerc.1667-iteration-{0..5}/discussions/1` | 카드 `/255` 수정 6건 | open, 09-15 이후 무활동 (스윕 밖, 직접 확인) |

닫힌 것: #1535·#1608(봇 자동 종료), #1661·#1662·#1663(main 버전으로 대체), #1803(#1886 중복), #1638(연구 리드가 닫고 잠금), #1611(완료).

### 남은 할 일 (다음 세션)
0. **사용자 몫**: ① ~~kartoun 답글~~ 10-09 게시·대조 완료 ② ~~Qual HF 토론~~ 10-09 06:02Z 게시(`Qualzz20/afv_fiber_9um/discussions/1`), 제목·본문 2,909자 초안과 일치 — 다음 스윕에서 답 확인(스윕 밖, HF API) ③ ~~villa threshold PR~~ #2012로 개설 완료. 게시 뒤엔 게시본=초안 대조.
1. **#2012 관리**: 스윕에 #2012 추가(tools/upstream_sweep.py 목록), CI(python 테스트 zarr 2.18.7/3.2.1) 결과 확인, 리뷰 오면 답. 10월 제출 초안 field 4·5에 "open PR #2012" 한 줄 넣을지 사용자 결정(열린 PR은 머지 전이라 청구는 약하게).
2. **스윕**: `python tools/upstream_sweep.py --since 2026-10-09T03:30:00Z` + HF 6건 + Qual 토론(게시했다면) + Discord #robots 두 스레드·#announcements(Chrome, 읽기만). 마지막 스윕 10-09 ~03:30Z(GitHub·HF), Discord 10-09 ~05:30Z.
3. **10월 제출**: 마감 10-31 23:59 PT. 사용자 일정에 맞춰 최종 통독·링크 200 확인·해시 → 사용자 제출.
4. 선택: `D:/vw10`(#1796 머지됨)·`D:/vw14`(Frag1 점검 끝) 워크트리 정리, 빈 폴더 `E:/envs` 삭제(가드가 막아서 사용자 몫). external/villa 미추적 76GB는 당분간 유지(10-02 사용자 결정).
5. docs/28 재실행 필요 시: 재채점만이면 커밋된 `runs/fiber9/fiber9_maps.npz`로 충분. 전체 재실행이면 ① `uv venv E:/envs/fiber9 --python 3.12` + torch(cu128 인덱스) + `nnunetv2 zarr==2.18.7 s3fs tifffile scipy huggingface_hub pynrrd` ② 체크포인트는 docs/28에 적힌 HF 리비전으로 재다운로드 ③ `git -C external/villa worktree add --no-checkout --detach D:/vw13 5a4388f08` → `git -C D:/vw13 sparse-checkout set --no-cone 'vesuvius/*' 'scripts/fiber_5class/*'` → `git -C D:/vw13 read-tree -mu HEAD`(Git Bash에선 `MSYS_NO_PATHCONV=1`). 타일 508MB 원본은 `Z:/아카이브/vesuvius-runs/fiber9/tiles`.

### 작업 트리 (villa = `external/villa` 저장소의 워크트리)
- `D:/vw15` = villa threshold PR(`feat/ink-borrow-threshold`, 10-09) · `D:/vw2` = ink_9um 추론용(10-02 sparse 재생성, `feat/flat-depth-targets`) · `D:/vw10` = #1796(머지됨, 정리 가능) · `D:/vw14` = Frag1 점검용 main `e0bbb8b40`(끝, 정리 가능) · `D:/vw12` = #1893 브랜치 `ca4a5bd68`(로컬 미푸시, 보존용).
- 10-02 제거: vw2·vw3·vw4~vw7·vw8·vw11. 브랜치는 로컬·포크에 남아 있고, 미커밋 수정 3건(vw2 `extra_blur`=docs/23 코드, vw6·vw7=#1471 검증 패치)은 `planning/2026-10-02_cleanup/*.patch`(적용 확인).
- ⚠️ ink_9um config는 `external/villa`(스키마 이전 체크아웃)로는 못 돌린다. 예전엔 `D:/vw2/ink-detection`에서 `uv run --project E:/vesuvius-challenge/external/villa/ink-detection --no-sync python -m ...`로 돌렸다 → 필요하면 `feat/flat-depth-targets`로 워크트리를 다시 만들고 `vw2_uncommitted.patch` 적용.
- `external/villa` 본 작업트리는 `fix/stream-untiled-label-images` + 미커밋(train/infer/test 구버전, pyproject/uv.lock cu128 핀) — **체크아웃 전환 금지**.
- `D:/shots`(PR 증거 이미지 스크립트), `D:/docker`(Docker 디스크)는 E: 이전 때 안 옮김.

## 이 프로젝트가 뭔가

Vesuvius Challenge **Progress Prizes**(월간 롤링, 리더보드 아님) 진입 프로젝트. 헤르쿨라네움 탄화 두루마리 CT→판독용 오픈소스 기여.
2026-07-19 착수. 심사 3축 = 조기 공개 / 커뮤니티 채택 / 문서화. 저장소 `khj1222/vesuvius-challenge`(public, MIT).

**라운드 이력**
- **7월**: held-out 검증 하네스(`docs/09`) → **$1,000 수상**(Substack "$33.5k awarded in July"에 실명), 송금 08-21 종결.
- **8월**: villa #192 측정 3D 라벨 = 음의 결과(측정 밴드 0.8098 < 고정 0.8478, `docs/10–12`) → 08-29 제출, 공개 명단에 없음(이유 미공개).
- **9월**: ink_9um 스코어카드·LOSO cross-scroll(`docs/14–18`, `20–26`) → 09-20 제출(v30). 핵심: 공개 모델 정직 상한 0.74–0.77, 1세그 FT가 Paris4 격차 82% 봉합하나 1667에선 24%(스크롤 특수), 라벨 없는 최선(arm D) 14%, 스카우팅 43타깃 후보 0.

## 핵심 사실 (상금·제출)

- 등급 $500·$1k·$2.5k·$5k·$10k·$20k, 월 최고 $20k 보장, **월 복수 제출·복수 수상 허용**. 등급 이름(Papyrus 등)은 페이지에 없으니 쓰지 말 것.
- 마감 매월 말 23:59 PT. **폼 URL은 라운드마다 새로 발급, 옛 폼은 결국 닫힘** → 매번 https://scrollprize.org/prizes 에서 받을 것. 새 폼은 전월 수상 발표 후에야 뜬다(Discord, Paul 09-04).
- 심사 Core Requirements: ①VC 데이터의 특정 문제 + 구현·시연 + 기존 대비 이점 ②문서화 + 사용 예 ③표준 포맷(OME-Zarr/tifxyz) 수용·모듈식 통합.
- 상금 이력상 $2.5k 위는 전부 "남이 매일 돌리는 소프트웨어"(머지된 수정 묶음 $5k 1건, 도구 $10k, 파이프라인 묶음 $20k). 측정·음의 결과는 $1k대.
- 수상 수락 시 permissive 라이선스 필수 → MIT라 충족.

## villa 기여 규칙 (어기면 닫힌다)

- **PR 전에 `main`의 `CONTRIBUTING.md`와 `.github/pull_request_template.md`를 읽을 것**(작업 브랜치엔 없을 수 있음). 템플릿 순서: In one sentence → One real example → Before → After this PR → Proof → Why / where this is useful → 체크박스 → `## Details`. 실제 스크롤 데이터 예시, 버그픽스는 실패+정상 출력 증거.
- **Why 문단은 사람이 쓴다**(CONTRIBUTING: LLM PR엔 사람이 쓴 코멘터리). 사용자가 사실을 주고 나는 문장만 옮긴다. 본문엔 **Disclosure 문단**(AI 코딩 도우미가 대부분의 작업, 문제·데이터·결정은 사용자) + 푸터.
- 1인칭은 프로젝트가 실제로 한 일에만. 사용자가 하지 않은 디버깅 장면을 지어내지 말 것. **체크박스("I personally verified")는 사용자가 직접 돌린 PR만** 켠다.
- 이슈·PR 본문은 짧고 직접적으로, 기존 용어로(jrudolph가 #1898을 "불명확·직접 쓰라"며 닫음). 제목이 본문보다 앞서 나가지 말 것(#1638 "leak-free" 제목 → 당일 닫힘·잠금).
- **남의 이슈를 고치기 전에 같은 파일을 건드리는 열린·최근 머지 PR을 먼저 볼 것**: `gh pr list --repo ScrollPrize/villa --state all --search "<파일명>"` + `git log origin/main -- <파일>`. 경쟁 PR이 이슈를 인용하지 않을 수 있다(#1831 → #1893 작업 1주일 중복).
- **자동 종료 봇**(매일 00:00 PT = 16:00 KST): 14일 무활동 **또는** 개설 28일(활동 무관, draft 포함) → 종료. `keep-open` 라벨 면제지만 우리 권한으론 못 붙임. 닫힌 PR은 reopen 안 될 수 있음 → 같은 브랜치로 새 PR.
- **작성자당 열린 non-draft PR 3건 상한**. draft는 상한 밖이지만 자동 리뷰 요청도 안 간다. 리뷰어(jrudolph·bruniss) 배정은 CODEOWNERS 자동이라 "누가 봤다"는 뜻 아님.
- GitHub은 새 PR/이슈 본문을 템플릿으로 미리 채운다 → 준비한 본문은 열고 덮어쓰되 이슈는 `- [x] I personally encountered or reproduced this…` 줄 포함. 초안 머리말(HTML 주석)은 붙여넣지 않는다(`---` 아래만).
- 게시 후엔 항상 **게시본=초안 대조**(API 원문, `gh`). 게시 직전에 스레드를 다시 읽을 것(남이 먼저 답했을 수 있음).
- 9월 기여는 10월 성과로 중복 계산하지 않는다. 같은 작업을 두 달에 청구 금지.
- **Discord**: #rules가 AI 생성 글 게시 금지 — **예외는 #robots**(Paul 공지: LLM이 크게 관여한 실험 보고용, 모델명 명시·모델 출력과 사람 코멘터리 분리·검증 가능한 주장). 따라서 #robots용 글은 초안을 쓸 수 있고("AI disclosure: run and written by Claude …, Posted with X's approval" 형식이 관례), 다른 채널 글은 쓰지 않는다. 게시는 사용자가. 읽기만 하고 입력창에 키보드 입력 금지(포커스를 뺏음).

## 저장소 규칙

- **`git commit -a` / `git add -A` 금지.** 워킹트리의 `runs/` 삭제 135건은 Z: 아카이브 흔적이라 커밋하면 제출 증거 링크가 사라진다. 커밋은 항상 경로 명시. 옛 runs 파일은 `git show HEAD:runs/...`로 읽는다.
- `runs/*`는 gitignore. 큐레이션한 증거만 **개별 경로로 `git add -f`**(`git add runs/`로 1.1GB를 올렸다 force-push로 걷어낸 전례).
- `planning/`·`AGENTS.md`는 gitignore(비공개, Z:\아카이브\vesuvius-local-only에 백업). `docs/`·README·submission은 제출에서 링크되는 공개 경로 → 영어 유지, 상금 산술·경쟁자 메모·개인정보 금지.
- 제출 문안(field 5 등)을 고친 날은 그날 안에 한 번 통독. field 4 카운트는 실험 커밋 때마다 재산출. 해시 규약 = 본문 + 개행 1개.
- "X가 없다/안 된다" 주장은 **심사자가 볼 ref(main)**에서 다시 확인.
- 데이터·체크포인트·TIFF는 커밋 금지.

## 환경·실행

- 트리 = **`E:\vesuvius-challenge`**(09-12 D:에서 이전). 시스템 Python 3.10 + torch 2.7 cu128, RTX 5090 로컬(클라우드 기본값 금지). `uv`·`hf`·`gh`(`C:\Program Files\GitHub CLI\gh.exe`, PATH에 없음) 설치됨.
- 잉크 파이프라인 = villa `koine_machines`(`external/villa/ink-detection`, uv 환경 torch 2.10 cu128). Windows 추론은 **`--no-compile`** 필수(Triton 없음). 추론 경로는 Windows 형식 `E:/...`(Git Bash `/e/...`면 무출력 종료).
- 깊이 타깃 런 채점은 `infer --z-window 16:48` 필수(없으면 F1 0.80→0.53).
- VC3D(C++) 빌드 = PR CI 이미지 `ghcr.io/scrollprize/vc3d-deps/linux:sha-0c371b1d472c5281b703d65517e980d945da693f`(로컬에 있음, 5.26GB), CI 플래그로 타깃만, 15초. 스크립트·명령 = `planning/2026-09-29_issue1893_build/README.md`.
- 렌더는 WSL의 Linux AppImage(`/opt/vc3d/squashfs-root`, `tools/render_wsl.sh`) — Windows 렌더러는 종료 단계에서 안 죽는 좀비가 된다. 렌더 방향은 `--flip-normals`가 팀 볼륨과 일치.
- 데이터 `data/ink-dataset/`, `data/ink_9um/`, `data/first_letters/`. 표면볼륨 ~86GB/세그먼트.

## 함정 모음

- 셸: heredoc에 정규식·백슬래시 경로를 태우지 말 것(`[\\/]`→`[\/]`, `\v`→수직탭). 경로 작업은 리터럴 바이트로. Git Bash에서 `git show origin/main:.github/...`·Windows exe 인자는 `MSYS_NO_PATHCONV=1`. 긴 heredoc은 잘리니 Write로 파일 만들 것. `cd` 후 저장소 쓰기는 절대경로로.
- PowerShell 5.1엔 `&&` 없음, `Out-File -Encoding utf8`은 BOM(파이썬은 `utf-8-sig`). `taskkill`은 Git Bash에서 조용히 실패 → `Stop-Process`. CommandLine 패턴으로 프로세스를 죽이면 내 셸도 죽는다.
- 워크트리에서 `git fetch origin main`이 `origin/main`을 안 갱신할 수 있다 → `git fetch origin +refs/heads/main:refs/remotes/origin/main`. 수정마다 `origin/main`에서 새 브랜치.
- `.venv`의 editable finder가 옛 경로를 물 수 있다 → 이사 후 `koine_machines.__file__`·`vesuvius` import 확인. pytest는 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -p no:cacheprovider`.
- 패치 캐시는 경로 기준 → 마스크를 바꾸면 새 `out_dir`. 실패한 런의 빈 캐시(2바이트)는 지우고 재실행. Windows DataLoader `error 1455`면 워커 6 + 여유 메모리 대기.
- zarr 청크 바이트는 프로세스 간 재현 안 됨 → 동일성은 디코드한 배열로. 예외 정체는 메시지가 아니라 `type(e).__mro__`로.
- GPU를 다른 프로젝트가 쓰면 추론 10배 느려지고 학습이 `resource already mapped`로 죽는다 → 재시도 드라이버. 장시간 백그라운드 런은 주기적으로 진행 확인. 세션 크론은 믿지 말 것.
- WebFetch 요약은 문자 단위 검증에 부적합 → `gh api`/curl 원문. 비인증 GitHub API는 60회/시간(gh는 5,000).
- 스윕은 수정된 코멘트도 잡도록 고쳐져 있음. #1819·#1893 등 남의 스레드는 스윕 목록에 있는지 확인.

## 문서 색인

`README.md`(공개 랜딩) · `docs/08` Windows 재현 · `docs/09` 검증 하네스 · `docs/10–12` 깊이 라벨(8월) · `docs/13` 9월 정찰 ·
`docs/14` 스코어카드 · `docs/15` LOSO 4부작 · `docs/16` First Letters 렌더 · `docs/17` held-out 감사 · `docs/18` UDA 사다리 ·
`docs/20` 주석 타겟팅 · `docs/21–23` 표현 격차 시도 · `docs/24` 의사라벨 검증 · `docs/25` 스카우팅 · `docs/26` 고정 임계값 · `docs/27` 라벨 없는 임계값 선택 · `docs/28` 9µm 섬유 일치도 · `tools/README.md`(툴 설명).
비공개 계획: `planning/2026-10_merge_month_plan.md`, `planning/2026-10_working_plan.md`.

## 최근 기록

- **10-09 (저녁) docs/29 완료**: 사용자 "더 할 만한 분야 3번 하자" → v8-in·Reader v2는 우리 라벨 데이터로 시험 불가(Reader v2는 0009B·0500P2 학습, v8-in은 0500P2 학습+24층 원본 렌더 입력) → 사용자 승인 하에 **KLAVIS ink9um-dense 4개(대조군 포함) + Nieuwlaar dense-native**로 대체. 서드파티 pickle은 `weights_only=True`/safetensors로만 읽어 `data/ink_9um/models_ext/clean/`에 재저장(`tools/convert_thirdparty_ckpts.py`, sha256 기록). 사전등록 `a2a187c` → 25예측(각 0.5분) → 결과 `cff3061`·`361a586`. **dense 4개 합산: R1b(빌린 값) 0841 0.011 / 0009B 0.002 / 0500P2 0.062 → 실패, 128도 0500P2 0.062, R3(분위수) 0.010/0.004/0.003 통과, Otsu도 통과. 대조군(수동라벨 재학습)은 R1b 통과, 128은 0500P2 0.032.** 예측 4개 중 3개 실패(문서 명시). 0500P2 최적 94–106 vs 다른 두 스크롤 ~126(사후 관찰: 공개 ckpt도 0500P2가 가장 낮았으나 차이 10). docs/27 상단 Update 배너·Tool 절 한계, README 13절 단락·Status 2줄, borrow_threshold.py docstring, tools/README 2행 갱신. **점검(`0da72b2`, 사용자 "제대로 확인해봐")**: 25칸 TIFF 직접 재계산 차이 ≤4.9e-7, villa #2012 calibrate로 15조합 전부 일치, 변환본=원본 텐서 동일, **KLAVIS 공개 검증 수치 6개 재현(AUC 차 ≤0.0007, w016 완전 일치)** → 0500P2 실패는 채점·로딩 오류 아님. Nieuwlaar는 공개 수치가 다른 입력이라 약한 점검만(sha·판독 수준). **#2012는 R1b만 구현** → PR 스레드에 결과 알리기·R3 추가 여부는 사용자 결정. 10월 제출에 docs/29 넣을지도 사용자 결정.
- **10-09 (오후)**: Discord 확인(Chrome, 읽기만): #robots 두 스레드 남의 답글 0. #announcements 새 글 = 10-09 First Letters $50K PHerc.343(Erwin Nieuwlaar), 남은 대상 21개; 09-26 PHerc1447 First Letters 제외(YoussefNader 9µm 레시피). 9월 Progress Prize 결과는 아직. CLAUDE.md '현재 상태' 절 전면 갱신.
- **10-09 (주말 일정 당겨 처리)**: 스윕(10-07 12:00Z~). ① **#1796 머지(10-08 15:43Z, bruniss, 리뷰 0, `12f21236a`)** → README 머지 표기·Status 추가, README의 "3.6e-7 vs 3.04"는 서로 다른 실행 수치가 섞인 것이라 커밋된 콘솔 로그(6.08→3.6e-7)로 정정(`9b84be7`). ② kartoun #192 답글(10-07 12:37Z, issuecomment-6038055753): 우리 Frag1 결과를 자기 저장소 결과표에 외부 항목으로 올리겠다며 허락 요청 → **사용자 허락**, 답글 초안 `submission/issue192_reply_kartoun3.md`(게시는 사용자). ③ **Qual이 10-07 카드 재작성**(`e189af7507`, 학습 저장소 Qualzz/afv-fiber-9um-training 공개, 가중치 LFS oid 동일 6837f3fe8f, "No independent test accuracy is claimed", 0139 미사용 확인) → HF 토론 초안 문구 갱신(첫 문장·리비전·미러링). HF 6건 변화 없음. **사용자 결정**: 10월 제출에 #1796 + #1703 포함(#1703은 "09-20 9월 제출 뒤 09-28 머지라 9월엔 없었다" 명시), kartoun 맥락 줄 미포함, Discord 이름 `jamiolrangmalrang4936` → 초안 v2(`planning/2026-10_submission_draft.md`, field 5 통독 1회, Qual 카드 문장 갱신). villa PR(borrow_threshold) 착수 결정 → main에서 ink 파이프라인은 `vesuvius/src/vesuvius/ink_detection/`(koine_machines 아님). 경쟁 PR 없음, 인접 #1872(Danishk2445 checkpoint·depth·direction sweep, AUC, open). `merge_predictions.py`의 128은 투표 기준이라 손댈 근거 없음. ⚠️ 공개 체크포인트에선 빌린 값이 128보다 낫지 않음(이득은 자체 학습 LOSO 모델뿐) + LOSO 예측은 Z:에만 있고 Z: 미연결 → **사용자 결정: Z: 연결 후 LOSO로 증거**. 그 사이 `D:/vw15`(브랜치 `feat/ink-borrow-threshold`, main `a329895ea`, sparse vesuvius/) 로컬 커밋 `096760d7c`(미푸시): `vesuvius.ink_detection.inference.threshold` calibrate/apply(value 규칙만), 테스트 6/6, docs/ink_detection.md 새 절(Labeling loop 앞, #1872와 다른 hunk)·README 한 블록. 우리 도구와 14/14 체크포인트 완전 일치(임계값·F1·빌린 값·손실). 실행 = ink-detection .venv + `PYTHONPATH=D:/vw15/vesuvius/src`. docstring은 검증한 경우(안 본 스크롤의 세그먼트)로 한정, validation mask 보정은 미검증이라 뺌. **Z: 연결 후 증거 완료(`7467660`)**: LOSO step 10k·20k 각 46칸을 CLI로 돌려 docs/27 `labelfree_cells.csv`와 전부 일치(빌린 값 손실 0.004–0.019, 128 손실 0.052–0.176), 그림 pherc0139-w028(128 F1 0.522 → 90 F1 0.607, 맞음/오탐/놓침 색), 공개 ckpt s42 20k에선 128로 충분(0.000–0.023)도 본문에 명시. 증거 `runs/villa_threshold_pr/`, 본문 초안 `submission/pr_ink_threshold.md`. **남은 것(사용자)**: Why 문단 작성, 체크박스는 직접 실행 시에만, 그 뒤 vw15 브랜치 포크에 푸시 → PR 개설. 첫 그림(w041, 크롭이 라벨 없는 영역)은 설득력 없어 폐기.

- **10-07**: 스윕(10-06 13:30Z~, 10:55Z 실행). 새 글 1건 = **#192 kartoun 답글**(10-06 14:08Z, issuecomment-6018077755): 홀드아웃 행(3298–4432)은 기복이 오히려 작음(sd 2.55 vs 3.38) → 0.40은 추적이 아니라 국소 효과로 해석. Frag1을 안 본 occluder(Frag2–6 학습, AUC 0.65)로 같은 레시피를 돌리니 밴드 중심이 z 32.6 → 17.5로 15층 이동, 상관 −0.07. 결론 "occlusion 깊이 = 그 모델이 증거를 얻는 곳, 잉크 위치 아님". 더 강한 2D 체크포인트가 있으면 세 번째 occluder로 돌려 주겠다고 제안. 답할지·docs/12 보강할지는 주말 결정. HF 6건 open·09-15 이후 무활동, #1796 변화 없음(28일 상한 10-14 16:00 KST), #robots 두 스레드 남의 답글 0. #announcements는 이번엔 안 봄.
- **10-07 (밤)**: 사용자 결정 "세 번째 판독 모델 제안 수락, 단 검증 후". w00 판독 모델(`ink_holdout_20k/ckpt_020000.pth`)이 villa main `e0bbb8b40`(`D:/vw14` sparse 워크트리)에서 키 전부 일치·출력 동일(diff 0.0) 확인, 옵티마이저 뺀 배포본 `runs/release/`(564MB). **Frag1 검증(사전 규칙 `planning/2026-10-07_w00_occluder_frag1/PREREG.md`): kartoun `score_3d` (a) 전체 AUC 원해상도 0.521·7.91µm 리샘플 0.565(사후 Z 뒤집기 0.578/0.553) < kartoun LOFO 0.654 → 더 강하지 않음, 넘기지 않음**(예측 지도에 글자 없음). 사용자 "제대로 확인했나" 질문 뒤 대조군 추가: 채점 래퍼 평가 집합 = kartoun JSON과 픽셀 수 동일, IR 어두움 AUC 0.974, **같은 추론 루프로 w00 가려 둔 영역 AUC 0.952**(양성 대조) → 낮은 Frag1 점수는 코드가 아니라 모델. 릴리스 안 만듦. **답글 사용자 게시 12:23Z(issuecomment-6037820818)**, 게시본=초안(차이는 `score_3d.py`·`w00` 백틱 4개 빠진 것뿐, 1,294 vs 1,298자). kartoun 이후 다른 댓글 없었음. 답글 초안 v2 `submission/issue192_reply_kartoun2.md`(수치 보고·체크포인트 없음) = 미게시, 사용자 검토 대기. Frag1 데이터 `data/fragments/Frag1`(6.4GB), kartoun 저장소 클론 `D:/kartoun_frag`. 함정: TaskStop이 `xargs` 자식 curl을 안 죽여 고아 프로세스가 파일을 덮어씀 → PID로 트리 종료 후 해당 층 재다운로드·전체 크기/디코드 검증.
- **10-06 (밤)**: Qual HF 카드 제안 초안 `submission/hf_afv_fiber_9um_discussion.md`(토론 글, 카드 PR은 제안만; 수치는 fiber9 원자료로 재확인). 게시는 사용자. 진행 현황 문서 = claude.ai Docs "10월 Progress Prize 준비 현황"(https://claude.ai/code/artifact/45c8a04a-7b87-40e1-8ce8-3c3551e158cb).
- **10-06 (밤)**: `tools/borrow_threshold.py` 작성·검증·푸시(`b6da7af`), docs/27 끝에 Tool 절, README 13절·tools/README 한 줄. 10월 초안 v1 작성(planning) 후 도구 반영.
- **10-06**: 스윕(10-03 12:00Z~). **#192에 kartoun(Claude Code 사용, AI 공개)이 우리 `make_3d_labels.py`를 IR 라벨 조각 Frag1로 포팅**(저장소 kartoun/vesuvius-fragment-ink-depth, MIT, 기본값 일치 확인): v4 측정 밴드 중심이 CT 표면을 상수 밴드보다 더 잘 따라가지 않음(상관 0.16, 홀드아웃 행 0.40). → 우리 08-31 "기하는 맞는데 진다" 해석이 과했음 → **docs/12에 Correction 문단 + README 한 줄(`eff21cf`)**, 답글 `submission/issue192_reply_kartoun.md` 사용자 게시(13:46Z, issuecomment-6017644321, 게시본=초안 2,187자 일치, AI 공개 줄 없음=사용자 결정). 10월 폼 열림(위 4번). HF 6건·#1796·#robots 두 스레드 변화 없음.
- **10-04 (밤)**: docs/28 #robots 게시(사용자) → Chrome에서 게시본=초안 대조 일치, 태그 unrolling·analysis 확인.
- **10-04 (밤)**: docs/27 #robots 스레드 제목 수정안 3개 중 사용자가 1안 선택·적용, Chrome에서 게시본=결정안 확인(위 '공개' 줄).
- **10-04**: docs/28 실행. G1 5/5(NCC 0.60–0.84), 타일 100개(약 1분/타일, 오류 0), G2·G3 통과, 결과 위 4번. 결과 절 통독에서 모델 카드의 "visibly better"가 TTA 얘기인데 미세조정 얘기로 잘못 쓴 문장 발견·수정, 크롭 범위 추정치(267–558)도 로그 실측(256–623)으로 정정. 증거 7개 링크 200.
- **10-03 (토)**: #1705 봇 종료(16:21 KST) 확인 → `D:/vw9` 제거(깨끗, 브랜치 `fork/fix/eager-fallback-at-first-forward`=`3e56ca418` 확인 후). 스윕 96h: 새 글 3건 — #1893 Sartoshirelli 동의·종료(답할 것 없음), #192 stantheman0128이 pmh47의 08-13 지적에 답하며 "khj1222's per-pixel band is geometrically coherent" 언급(우리 몫 질문 없음 → 답 안 함), #1705 봇. HF 6건 open·무활동. Discord #robots 우리 스레드 = 원글+정정 2개뿐, 남의 답글 0. ⚠️ 스레드 **제목이 아직 "Don't binarize ink_9um at 128…"**(정정으로 철회된 주장) → 제목 수정은 사용자 몫으로 제안. 같은 날 Bullo27 "v8-in on a 12 GB GPU…PHerc0841"(10-02) 글 있음(0841 겹침, 미독). #1796: 같은 파일 건드린 main 커밋·경쟁 PR 없음 확인 → `be112851f`→`a104fd70d` 리베이스(충돌 없음), 로컬 pytest 13/13(import 경로 vw10 확인), `--force-with-lease` 푸시. CI 진행 중, Vercel 실패는 늘 그렇듯 배포 권한 문제. 밤: 섬유 9µm 1단계(공개 여부) → Qual이 이미 9µm 모델·AFV 데이터·PR 3건 → 측정으로 방향 전환, docs/28 사전등록 `735404f`(모델 추론 전). 공개 섬유 모델·예측은 전부 2.4µm(Paris4 학습), `fiber_hz_vt`만 7.91µm 사람 추적 학습.

- **10-02 (오후~저녁) B′ 재현 완료 → docs/27 권고값 철회**: B(판독기 비교)는 Reader v2가 이미 해서 중단, 대신 공개 ink_9um이 안 본 새 공개라벨 스크롤 3개(0841×3·0009B·0500P2)에서 재현. 사전등록 `72c7679`(추론 전) → 70예측 → 결과 `393ab46`. **docs/27 고정값 87(R1a)은 세 스크롤 모두 실패(0.09–0.12)**, 공개 모델의 최적값은 98–141이고 128이 오히려 노이즈 안(0.006–0.027). 같은 모델로 다른 스크롤에서 빌려오기(R1b 0.003–0.009)·분위수(R3)는 통과. → "84–92/128 쓰지 말라"는 LOSO 모델 한정으로 철회, 방법만 유지. README 13절·Status·tools/README·docs/27 상단 정정. **#robots 정정 답글 게시 완료(10-02, 사용자)**, 초안 `submission/discord_robots_docs27_correction.md`. 데이터 `data/ink_9um/{surface-volumes,labels}/openlabels9/`, 예측 `runs/ink9um_openlabels/preds/`(70장). 도구 `tools/prepare_open_label_segments.py`·`run_open_label_replication.py`. `D:/vw2` 워크트리를 sparse로 재생성(ink_9um 추론은 이 브랜치에서만).
- **10-02 (늦은 밤)**: 사용자가 docs/27 소개 글을 Discord **#robots에 게시**(초안 `submission/discord_robots_docs27.md` v2, 1,457자 + 본인 코멘트). 반응은 다음 스윕 때 확인(스윕 도구 밖, 직접).
- **10-02 (밤)**: #show-and-tell·#robots·#announcements도 읽음. 임계값 선택 중복 없음. 주목: YoussefNader **v8-in**(09-29, 새 9µm 모델, 1447 zero-shot AUC 0.86), KLAVIS **Reader v2**(09-28, 116keV에서 AUC 0.834, 같은 재현율에서 오탐 10% vs 43~58%), lightsgoblack ink-placebo-check·사전등록 해시 로그, Bullo27(Matteo Bulloni) PHerc0841 시험. #announcements 최신 = 8월 수상 15명(09-07, 최고 $20k Will Stevens); 9월 결과·10월 폼 아직 없음. docs/27은 ink_9um 레시피 한정이라 v8-in·Reader v2엔 미검증.
- **10-02 (저녁)**: Discord #ink-detection 읽기(입력 없음). 라벨 없는 임계값 선택을 다룬 글 없음 = docs/27 중복 아님. 0.5 고정 사용 사례: KLAVIS(08-18, 균형정확도@0.5), freek_cool(09-01, p>0.5 면적), Danilo(#1708, "threshold는 따로 보정 필요"). ⚠️ **KLAVIS가 08-18에 공개 9µm 체크포인트 14개를 영역별로 채점해 올렸다**(github DomRusso2/ink9um-dense) → 우리 docs/14(08-22)·README의 "first quantitative scoring / First numbers" 표현은 틀림 → **10-02 정정 완료**(docs/14 상단에 KLAVIS 크레딧 정정문, README 6·7절, docs/15; #7 수치도 "first" 대신 "가려 둔 주석으로 채점한"으로 범위 축소). 9월 제출본의 "first scorecard"는 이미 제출돼 못 고침. **교훈: 중복 확인은 Discord까지.**
- **10-02 (오후)**: 10월 연구 착수. 중복 검색(villa threshold/otsu/binarize/calibration) 0건 → docs/27 사전등록(`1b5917e`, 실행 전 푸시) → `tools/score_label_free_threshold.py`로 Z: 저장 LOSO 예측 322칸 CPU 재채점(약 25분) → R1·R3 통과, 128·Otsu 실패 → 결과 `93c5f50` 푸시. 원수치 `runs/ink9um_scorecard/labelfree_{summary.json,cells.csv,hists.npz}`(히스토그램만으로 재감사 가능). 채점 도구의 bbox 중복 계수와 픽셀 1회 계수를 둘 다 계산, 판정 동일(평균 차 ≤0.0015).
- **10-02**: 스윕 → #1703 머지(09-28) 확인. #1893 PR 준비 중 #1831 중복 발견 — main `f637f3b35`를 CI 이미지로 빌드해 대조(우리 테스트 5/6, 실제 원격 PHerc0139 `-g 5` micrometer 299.584 동일, 차이는 문서화된 `--voxel-unit` 설계뿐, 근거 `planning/2026-09-29_issue1893_build/results/*main_f637f3b*`) → 푸시·PR 없음. 10-01 정리 실행: 워크트리 8개 제거, CLAUDE.md를 이 형태로 축소(원본은 history 폴더), #1893 마무리 코멘트 게시, docker 볼륨은 사용자가 삭제, 76GB는 당분간 유지(사용자 결정, E: 여유 348GB·Z: 131GB), `planning/`(4,308파일)·AGENTS.md를 Z:/아카이브/vesuvius-local-only에 재동기화(해시 확인).
- **09-29**: #1893 수정(`ca4a5bd68`) 빌드·검증·로컬 커밋 — 이후 #1831로 불필요해짐.
- **09-26~28**: #1703 리뷰 반영 푸시(`3e56ca418`), #1705 ready, #1796 리베이스, #1582·#1893·#1819·#1898 코멘트 게시. #1803은 #1886 중복으로 종료. #1819 manifest 요청 무응답 → Hecate 후속 없음.
