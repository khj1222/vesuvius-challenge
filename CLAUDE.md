# CLAUDE.md — vesuvius-challenge

새 세션은 이 파일 + `README.md` 만 읽으면 컨텍스트 없이 이어갈 수 있게 자기완결로 유지할 것.
**7~9월 상세 이력은 2026-10-02에 로컬 `planning/history_2026-07_09/CLAUDE_full_2026-10-02.md`로 옮겼다**
(gitignore, 원문 그대로; 커밋 `827e216`의 CLAUDE.md와도 동일). 옛 결정의 이유·수치 출처가 필요하면 거기서 찾을 것.
새 기록은 아래 "현재 상태" 절을 갱신하고, 날짜별 로그는 짧게 "최근 기록"에만 쌓는다.

## 현재 상태 (2026-10-02 기준, 이 절이 최우선)

**10월 = 머지 달**(09-18 사용자 결정). 새 연구 없음, 열린 PR 머지에 집중. 10-15 중간 판정: 10월에 새로 머지된 게 없으면 10월 미제출.
9월 라운드는 **09-20 v30으로 제출 완료**(`submission/2026-09_form_answers.md`, 동결). 수상 통보 대기.

### 업스트림 PR/이슈 (ScrollPrize/villa)

| 번호 | 내용 | 상태 |
|---|---|---|
| #1249 | 커뮤니티 툴 목록에 하네스 등재 | 머지 07-31 |
| #1234 | `create_label_zarrs` striped TIFF 스트리밍 | 머지 08-14 (`merge-ink-pipelines`) |
| #1701 | 패치 캐시 지문(F4, main) | 머지 09-21 (hendrikschilling) |
| #1703 | `torch.compile` 첫 forward eager 폴백(F2, main) | **머지 09-28** (hendrikschilling, `795ca2b`) |
| #1705 | staged publish Windows 재시도(F3, main) | open, 리뷰 0 → **10-03 16:00 KST 28일 자동 종료, 재개설 안 함** |
| #1796 | Copy TTA 방향 벡터 | open, 리뷰 0 → 무활동 종료 10-10 16:00 KST, 28일 상한 10-14 16:00 KST |
| #1893 | (남의 이슈) 렌더 voxel 단위 | **BioMarco #1831이 09-30 먼저 머지** → 우리 PR 취소. 마무리 코멘트 게시 10-02 [issuecomment-5941647899](https://github.com/ScrollPrize/villa/issues/1893#issuecomment-5941647899)(게시본=초안). 닫힘은 메인테이너 몫 |
| #1231 | (우리 이슈) 배포 세그먼트에 검증 마스크 없음 + 평가 진입점 질의 | open, erdpx 배정, 무응답 |
| HF `scrollprize/PHerc.1667-iteration-{0..5}/discussions/1` | 카드 `/255` 수정 6건 | open, 09-15 이후 무활동 (스윕 밖, 직접 확인) |

닫힌 것: #1535·#1608(봇 자동 종료), #1661·#1662·#1663(main 버전으로 대체), #1803(#1886 중복), #1638(연구 리드가 닫고 잠금), #1611(완료).

### 남은 할 일
1. #1893: 신고자·메인테이너 반응만 확인(우리 쪽 할 일 없음).
2. #1796: 10-10 전 리베이스 푸시 한 번(리뷰 0이라 10-14엔 어차피 닫힘).
3. 10-15 판정: #1703 머지(09-28, 9월 문안엔 open으로 들어감)를 10월 근거로 쓸지 사용자 결정. 새 소형 후보 공석.
4. external/villa 미추적 76GB(ckpt 65개 등)는 **당분간 유지**(10-02 사용자 결정; 디스크가 필요해지면 재논의, 지우면 재학습 GPU ~16h). (docker 볼륨 vc1893·vc1893base·vc1893main은 10-02 사용자가 삭제.)
5. 스윕: `python tools/upstream_sweep.py --hours 96` 주 2회 + HF 6건 직접. 리뷰가 오면 24시간 내 반영.

### 작업 트리 (villa = `external/villa` 저장소의 워크트리)
- `D:/vw9` = F2/F3 브랜치(#1703 머지됨, #1705 종료 후 제거 가능) · `D:/vw10` = #1796 · `D:/vw12` = #1893 브랜치 `ca4a5bd68`(로컬 미푸시, 보존용).
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
- **Discord**: #rules가 AI 생성 글 게시 금지 → 나는 Discord 문안을 쓰지 않는다(번역만). 읽기만 하고 입력창에 키보드 입력 금지(포커스를 뺏음).

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
`docs/20` 주석 타겟팅 · `docs/21–23` 표현 격차 시도 · `docs/24` 의사라벨 검증 · `docs/25` 스카우팅 · `docs/26` 고정 임계값 · `tools/README.md`(툴 설명).
비공개 계획: `planning/2026-10_merge_month_plan.md`, `planning/2026-10_working_plan.md`.

## 최근 기록

- **10-02**: 스윕 → #1703 머지(09-28) 확인. #1893 PR 준비 중 #1831 중복 발견 — main `f637f3b35`를 CI 이미지로 빌드해 대조(우리 테스트 5/6, 실제 원격 PHerc0139 `-g 5` micrometer 299.584 동일, 차이는 문서화된 `--voxel-unit` 설계뿐, 근거 `planning/2026-09-29_issue1893_build/results/*main_f637f3b*`) → 푸시·PR 없음. 10-01 정리 실행: 워크트리 8개 제거, CLAUDE.md를 이 형태로 축소(원본은 history 폴더), #1893 마무리 코멘트 게시, docker 볼륨은 사용자가 삭제, 76GB는 당분간 유지(사용자 결정, E: 여유 348GB·Z: 131GB), `planning/`(4,308파일)·AGENTS.md를 Z:\아카이브esuvius-local-only에 재동기화(해시 확인).
- **09-29**: #1893 수정(`ca4a5bd68`) 빌드·검증·로컬 커밋 — 이후 #1831로 불필요해짐.
- **09-26~28**: #1703 리뷰 반영 푸시(`3e56ca418`), #1705 ready, #1796 리베이스, #1582·#1893·#1819·#1898 코멘트 게시. #1803은 #1886 중복으로 종료. #1819 manifest 요청 무응답 → Hecate 후속 없음.
