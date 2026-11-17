# CLAUDE.md — vesuvius-challenge

새 세션은 이 파일 + `README.md` 만 읽으면 컨텍스트 없이 이어갈 수 있게 자기완결로 유지할 것.
**옛 상세 이력은 로컬 planning에 원문 그대로 있다**(gitignore): 7~9월 = `planning/history_2026-07_09/CLAUDE_full_2026-10-02.md`,
10월~11-12 = `planning/history_2026-10_11/CLAUDE_full_2026-11-12.md`(11-12 정리 직전 CLAUDE.md 전체, 세션별 요약·최근 기록 포함).
옛 결정의 이유·수치 출처·명령은 거기서 찾을 것. 새 기록은 아래 "현재 상태"를 갱신하고, 날짜별 로그는 짧게 "최근 기록"에만 쌓는다.

## 현재 상태 (2026-11-16 기준, 이 절이 최우선)

**지금은 제출만 남음.** **11-17 사용자 결정 = A안**(G4 기한까지 sean 무응답): I1 브랜치를 포크에 푸시, docs/37에 링크, **S1 패키지 `submission/2026-11_progress_prize_s1.md` 준비됨**(S2 패키지 `…_s2.md`는 11-14). 11월 제출 마감 **11-30 23:59 PT** — **S1·S2를 마감 전 한꺼번에**(사용자). 기다리는 것: LimeGS/ink-sdk #18 답, (늦은) sean 답 — 오면 S1에 한 줄.
**10월 결과(11-13 10:06 KST 발표)**: **$250** "Copy displacement tracer fix"(= #1796만). docs/27–31 측정은 **0**. Paul: 기준을 계속 올림, 사소한 버그픽스·호환성 수정도 다음부터 더 엄격. 같은 달 **ink-sdk**(LimeGS+pscamillo, `github.com/LimeGS/ink-sdk`, $500) = 세그먼트에 여러 잉크 모델을 돌리는 도구(렌더+추론+receipt, 15개 프로필, 예시가 우리와 같은 0841 w00 + Reader V3) — **segment_ink 앞 절반과 겹침(10-28부터 알았고 docs/32가 credit), VC3D 되쓰기는 여전히 없음**(11-14 README 재확인, 마지막 푸시 11-11). reader-v3 $5k("First Letters 대부분이 씀"), Rectina(evilaliv3) 새 9µm 모델.

### 11월 = I1 (VC3D Ink Detection 패널이 객체 저장소 표면의 `ink`/`ink_*` 채널도 보여주게)
- **무엇**: 저장소는 잉크 채널 자리를 문서화(`vc_object_store/README.md` 77행 `--surface-channel UUID ink pred.tif`, 격자당 20px)했는데 패널은 카탈로그 공개 파일만 읽음. 작은 C++ 변경(3파일 +147/−18). 사용자 결정 11-02. 근거·재조사 `planning/2026-11_plan.md` §4i.
- **게이트**(코드 전 고정 `planning/2026-11_i1_store_ink_channel.md`, sha256 `2082e335dea5`): G1 CI 이미지 `test_ink_detection_overlay` 9/9 · G2 0841 w00 + Reader V3 채널 저장소 왕복 픽셀 동일 · G3 **사용자가 직접** VC3D에서 전 0개/후 2개(스크린샷 6장 `planning/2026-11-02_i1_build/results/screens/`) — 모두 통과. **G4 = sean 승인 없으면 PR 안 함, 기한 11-16.**
- **브랜치**: `D:/vw20` `feat/vc3d-ink-surface-channel` = **`bb9ec5e2c`**(villa main `8e21d010f` 위, **11-17 포크 `khj1222/villa`에 푸시**, URL 200). 옛 커밋 보존 브랜치 `…-base-1c638d715`(`bb5623f1d`) · `…-base-fd97a4b`(`0df26c427`) · `…-base-baf5e605b`(`0af58057b`) · `…-base-445fc644c`(`19aa7a474`). **sean이 이 영역을 계속 고침**(#2358·#2440·#2462·#2491) → 매 확인마다 `git merge-tree`로 재확인, 바뀌면 G1 재실행. G1 이력: 11-04 `baf5e605b` · 11-09 `445fc644c`(테스트를 `newRequest`/`CreateObjectOp`/`readStore` 방식으로 옮김) · 11-12 `1c638d715` · 11-14 `97fb9336c`(체리픽만) · 11-17 `8e21d010f`(새 CI 이미지), 모두 9/9. 포크 브랜치를 갱신할지는 사용자 결정(푸시된 것 = `bb9ec5e2c`).
- **빌드**: `planning/2026-11-02_i1_build/README.md`(맨 위 Update들이 최신). CI 이미지 = **`ghcr.io/scrollprize/villa/volume-cartographer@sha256:94077533…`**(11-16 #2564부터 main `vc3d-ci.yml`, deps hash `6309e96d71462b0a`, 로컬에 받음; 옛 `1bebf104edbd…`도 로컬에 있음 — 매번 main과 같은지 확인). G1 = `build_and_test.sh`(fresh docker 볼륨, 마지막 = `vc_i1f`, 실행 래퍼 `run_g1_1117.sh`) · G2 = `g2_roundtrip.sh` · G3 = `build_app.sh`(**이미지 태그를 새 이미지로 바꿔야 함**) + `run_vc3d.sh`(WSLg, 사용자 조작) · G3 가져오기 폴더 `data/a_lite/g3_import/`. 함정: `build_and_test.sh`는 빌드 끝 25줄만 남겨 컴파일 오류가 잘림 → 실패하면 FAILED/error로 grep.
- **G4 갈래**: sean 동의 → **B안 PR**: 새 이미지로 앱 빌드 → 사용자 G3 재확인 → main `CONTRIBUTING.md`·PR 템플릿 재확인 → 본문 초안 `submission/pr_vc3d_ink_surface_channel.md`(미추적, Why 비움, "+141/−17"은 갱신 필요, 체크박스는 사용자가 G3를 직접 했으니 켤 수 있음, gomyway Volume Overlay와의 차이 한 줄) + segment_ink v2 + docs/32 Update. 무응답·반대 → **A안**: 포크 브랜치 푸시 + 스크린샷 공개 + docs/32 Update 게시. **→ 11-17 A안으로 끝남**: 스크린샷은 `runs/vc3d_ink_channel/`(11-14 `114f513`), docs/32 Update 역할은 docs/37(11-14)이 맡고 docs/37 상태 칸·패널 절에 포크 링크와 11-17 G1을 넣음. docs32 초안은 쓰이지 않음.
- **sean 질문**: #robots segment_ink 스레드 `1564220086158495754`에 11-04 20:34 KST 게시(사용자, 게시본=초안, w045 정정 줄 포함). 11-12까지 답 없음.

### 11월 제출
- 폼(11-05부터 열림, villa #2301; #2492 이후 월 전환은 수동) = `docs.google.com/forms/d/e/1FAIpQLSeB6MC_--4UCCEGc3zalX57-uE4puRcE_vJoYJCrEt4uYaaaw/viewform`, 마감 11-30 23:59 PT. 수상 발표와 무관하게 열려 있음.
- **초안 v1** `planning/2026-11_submission_draft.md`(11-14, v0은 `…_v0.md`): 사용자 결정 = **두 건**(S1 도구 = segment_ink v2 + `ink_sdk_channel` + VC3D 패널, 중심 문서 **새 docs/37**; S2 측정 = docs/33–36 + dinovol + w045). S1 field 4 1,755자 / 5 5,705자, S2 3,369 / 4,683. 링크: S2 25개 200, S1은 docs/37·새 runs 폴더(미푸시)와 [A]/[B]만 404. docs/33·34 첫 줄이 아직 "DRAFT pre-registration"이라 결과 배너를 docs/33–35 맨 위에 추가(미커밋). docs/37+증거+배너는 `114f513`으로 푸시됨. S2 패키지 `submission/2026-11_progress_prize_s2.md`(해시 기록, 링크 25개 200, 11-14). **사용자 결정(11-14): S1·S2는 최종 마감 전에 한꺼번에 제출**(같은 November 폼에 두 번). **11-17: A안으로 [A]/[B] 정리 → S1 패키지 `submission/2026-11_progress_prize_s1.md`**(field 4 1,637자 `3e9d0677`, field 5 5,685자 `5fef8569`, 링크 12개 200, field 5 통독 1회; 정리 전 초안 사본 `planning/2026-11_submission_draft_v1_pre_A.md`). 남은 것 = (선택) 최신 커밋 G3(`build_app.sh` 이미지 교체 필요), 제출 직전 폼·링크 재확인 → 사용자 제출 → 영수증=파일 대조. ⚠️ Grand Prize 폼("2027 Vesuvius Challenge Grand Prize")과 헷갈리지 말 것 — Progress 폼 id `1FAIpQLSeB6MC_`.
- (옛) **초안 v0** `planning/2026-11_submission_draft_v0.md`(11-06): A부분 segment_ink(docs/32 + v2 + VC3D 패널 변경, `[A]` 포크/`[B]` PR 두 줄) + B부분 docs/33·34·35 사전등록 측정 + docs/36 철회 + dinovol 27/28 + w045 정정. field 4 4,667자(링크 31개 200, 포크 브랜치·#NNNN·Discord는 미확인), field 5 9,479자, 통독 1회.
- **남은 결정(사용자)**: ~~A/B~~(11-17 A) · ~~한 건 vs 두 건~~(11-14 두 건) · G3를 최신 커밋에서 다시(선택). 그 뒤 링크·숫자 재확인 + 통독 → 사용자 제출 → 영수증=파일 대조 → submitted 표시.

### 11월 연구 갈래 (전부 닫힘 — 새 연구는 안 하기로 11-06 합의: 측정을 더 붙여도 등급이 안 오름, 열쇠는 I1 채택)
- **segment_ink**(`tools/segment_ink.py`, docs/32): 렌더 → 추론 → VC3D 기록. v2(`72bc3c7`) = 객체 저장소 표면 `ink_<이름>` 채널(store-folder 기본 / store / legacy-json, uuid5로 `output_tifxyz` 해결). Reader V3로 PHerc0841 세 세그먼트 AUC 0.772→0.916 / 0.681→0.834 / 0.756→0.853, 3–6배 빠름(`406e153`). **V3 예시에 0139 w045·0814 20250925212701 쓰지 말 것(V3 학습 세트).** #2358 이후 `ink-detections.json`은 Latest VC3D에서 안 읽힘(docs/32 Update).
- **w045 정정**(`bb35177`): ink_9um 0139 케이스 번호 ≠ 공개 w번호(케이스 w016/w017/w028/w029 = 공개 w029/w030/w044/w045) → w045는 학습 세그먼트. 케이스는 `source` 속성으로 매핑.
- 입력 경로 격차(11-06, `planning/2026-11-06_input_gap/`): 값싼 원인 없음, 네이티브 9µm엔 V3.
- 음성·철회: F1 열간 공백(게이트 실패) · F2(#2358로 소멸) · F3′ = docs/33(라벨 7px 어긋남, 보정 무익) · G3 = docs/34(Paris4 3D 모델 교차 스크롤 부분 전이, 0.907 대조) · G3b = docs/35(9.6µm 미세조정 무효) · H1 공간 겹침(접음) · docs/36 preset A/B(학습 전 철회: 두 preset이 같은 그래프 — 파일 이름이 아니라 import를 따라갈 것).
- **B dinovol 보류**: 공개 640k·781k 사전학습이 메타데이터 잉크 라벨 28개 중 27개를 대조 손실로 씀(깨끗한 건 0009B ag055뿐, `tools/check_dinovol_ink_labels.py`) → 시험 세트 오염. sean 질문(무잉크 체크포인트)은 10-26 #robots 글로 해 둠.

### 큰 상 검토 (11-14, 결정 대기)
- 2027 Grand Prize · Paris4 제목상 · First Letters 진입 검토와 제목상 탐침 결과는 **비공개 노트에만** 있다: `planning/2026-11-14_big_prizes_entry_review.md`, `planning/2026-11-14_paris4_title_report.md`(그림 `planning/2026-11-14_paris4_title_probe/figs/`, 데이터 `data/paris4_title/` 약 47 GB). ⚠️ 제목상·First Letters는 **발견물을 수상 발표 전에 공개하면 안 된다** → 이 파일(공개)·docs·Discord·이슈에 내용을 쓰지 말 것. playbook ENTRY §8 행은 사용자 결정 뒤에 기입.

### 10월 (끝남)
- **제출 10-25 18:48 KST**(사용자), 영수증 = `submission/2026-10_progress_prize.md`(`ce44ad6`). 구성: docs/27(+`tools/borrow_threshold.py`) · docs/28 · docs/29 · docs/30 · docs/31 · #1796 · #1703 · #2012(닫힘). 기대 $500. **수상 발표 대기**.
- 핵심 결과: docs/27·29 = 라벨 없는 임계값 선택은 분위수 규칙만 세 시험 모두 통과(빌린 값은 dense 0500P2에서 실패) · docs/28 = 9µm 섬유 일치도 F1 0.69 · docs/30·31 = 표면 어긋남 깊이 증강 음성, 공개 리더는 −5층(≈48µm)에서 F1 0.14–0.17 손실(방향 설명은 sean 10-14).
- **9월 $500 수상**(10-11 발표) → 10-26 입금, 종결. 은행이 증빙을 요구하면 7월 증빙 형식으로(위치는 비공개 메모리).
- 외부: kartoun이 Frag1 결과를 자기 README Findings에 등재(10-09). stantheman #1945(우리 depth_anchors CSV 사용)는 10-21 bruniss가 닫음; 법선 부호는 미검증으로 확정(docs/12 Update).

### 업스트림 PR/이슈 (ScrollPrize/villa) — `tools/upstream_sweep.py`가 전부 본다
| 번호 | 내용 | 상태 |
|---|---|---|
| #2012 | 임계값 calibrate/apply(docs/27 도구 villa판) | 닫힘 10-21 bruniss "we dont recommend binarizing ink predictions", 답글 안 함 |
| #1796 / #1703 / #1701 | Copy TTA / compile eager 폴백 / 패치 캐시 지문 | 머지 10-08 / 09-28 / 09-21 |
| #1249 / #1234 | 커뮤니티 툴 목록 / striped TIFF | 머지 07-31 / 08-14 |
| #1231 | (우리 이슈) 배포 세그먼트에 검증 마스크 없음 | open, 무응답 |
| #1547 | (남의 이슈) 중복 표면 | open, 우리 0139 세트 안 중복 없음 |
| #192·#1582·#1659 | 남의 이슈(우리 관여) | 11-01 bruniss 대량 정리로 닫힘 |
| ink-sdk #18 | (우리 이슈, LimeGS/ink-sdk) ink-sdk → VC3D 저장소 채널 제안 + 캔버스 원점 관찰, 초안 `submission/gh_inksdk_issue_vc3d_channels.md` | 11-14 사용자 게시, 게시본=초안, 스윕 `OTHER_THREADS`에 추가 |
| HF 7건 | `scrollprize/PHerc.1667-iteration-{0..5}/discussions/1`, `Qualzz20/afv_fiber_9um/discussions/1` | open, 무활동 |

### 매일 확인 (루틴)
1. `python tools/upstream_sweep.py --since <지난 확인일>T00:00:00Z` — **다음 = `2026-11-17T00:00:00Z`**(ink-sdk #18도 포함됨).
2. Discord(Chrome, 읽기만): segment_ink 스레드 `discord.com/channels/1079907749569237093/1564220086158495754`(sean 답) · #announcements(10월 수상 발표) · #robots 새 글 훑기. `find`로 ref를 잡고 `read_page`/`get_page_text`, 잘리면 스크린샷.
3. villa main 확인: `git -C D:/vw20 fetch origin +refs/heads/main:refs/remotes/origin/main` → 잉크 오버레이 파일(`volume-cartographer/apps/VC3D/overlays/InkDetectionOverlayController.*`, `core/test/test_ink_detection_overlay.cpp`) 변화 + `git merge-tree --write-tree origin/main feat/vc3d-ink-surface-channel` + 겹치는 열린 PR.
4. 가끔: planning/·AGENTS.md를 `Z:\아카이브\vesuvius-local-only`에 동기화(새·바뀐 파일만 복사 → 해시 대조, 삭제 없음). 마지막 **11-14**(69개 복사, 해시 불일치 0; 스크립트 `planning/sync_z_backup.py`).

### 사용자 몫 (선택, 미결)
- Discord #ink-detection 입력창의 미전송 초안("PHerc.1667-iteration-0..5 model cards…") 삭제.
- `tools/f1_intercolumn_gate.py`(미추적, F1 음성) 공개 여부.
- 빈 폴더 `E:/envs` 삭제, `external/villa` 미추적 76GB는 유지(10-02 결정).

### 재실행 메모
- docs/28: 재채점은 커밋된 `runs/fiber9/fiber9_maps.npz`로 충분. 전체 재실행은 `uv venv E:/envs/fiber9 --python 3.12` + torch(cu128) + `nnunetv2 zarr==2.18.7 s3fs tifffile scipy huggingface_hub pynrrd`, 체크포인트는 docs/28의 HF 리비전, `git -C external/villa worktree add --no-checkout --detach D:/vw13 5a4388f08` → sparse `vesuvius/*`·`scripts/fiber_5class/*` → `read-tree -mu HEAD`. 타일 원본 `Z:/아카이브/vesuvius-runs/fiber9/tiles`.
- docs/29: 서드파티 체크포인트 `data/ink_9um/models_ext/clean/`(재생성 `tools/convert_thirdparty_ckpts.py`, pickle은 weights_only로만), 예측 `runs/ink9um_openlabels/preds_otherrecipes*`.
- docs/34·35 데이터(`data/ink_3d`·`data/ink_3d9`)는 11-05 삭제: CT는 S3, 3D 모델은 HF `4c71198`에서 다시.
- 큰 증거: 넓은 볼륨 `surface-volumes/aligned9_wide`·`openlabels9_wide`(48GB, docs/31), 예측 `runs/ink9um_openlabels/`.

### 작업 트리 (villa = `external/villa` 저장소의 워크트리)
- **`D:/vw20`** = I1 브랜치(위), sparse `volume-cartographer/`·`vc_object_store/`·`vc_reader/`(VC CMake가 `../vc_reader`·`../vc_object_store`를 부름) · `D:/vw21` = main `fd97a4b60` 패치 없음(G3 '전' 빌드용). VC 빌드는 저장소 CLI를 끄니 `vc_object_ingest/export`는 `vc_object_store` 단독 빌드(`/work/build_store`). WSLg 창은 computer-use로 클릭이 안 됨 → VC3D GUI는 사용자가 조작.
- `D:/vw15` = #2012 브랜치(닫힘) · `D:/vw2` = ink_9um 추론용(`feat/flat-depth-targets`, sparse) · `D:/vw12` = #1893 브랜치 `ca4a5bd68`(보존용) · `D:/vw16` = dinovol(B 보류) · `D:/vw17` = villa main `e2254ebe0`(sparse `vesuvius/`, segment_ink 추론: `external/villa/ink-detection/.venv` python + `PYTHONPATH=D:/vw17/vesuvius/src`) · `D:/vw18` = VC3D 잉크 패널 검증(10-25) · `D:/vw19` = Paris4 3D 브랜치 `c9ca2dc52`(docs/34).
- `E:/envs/dinovol`(py3.13, torch 2.11 cu128 — timm 설치가 torch를 CPU판으로 바꾸니 torch+torchvision을 cu128 인덱스에서 함께 재설치; imagecodecs 없음).
- 10-02 제거한 워크트리의 미커밋 수정 3건은 `planning/2026-10-02_cleanup/*.patch`.
- ⚠️ ink_9um config는 `external/villa`(스키마 이전 체크아웃)로는 못 돌린다 → `D:/vw2/ink-detection`에서 `uv run --project E:/vesuvius-challenge/external/villa/ink-detection --no-sync python -m ...`(필요하면 `vw2_uncommitted.patch`).
- `external/villa` 본 작업트리는 `fix/stream-untiled-label-images` + 미커밋(구버전 train/infer/test, cu128 핀) — **체크아웃 전환 금지**.
- `D:/shots`(PR 증거 이미지 스크립트), `D:/docker`(Docker 디스크)는 E: 이전 때 안 옮김.

## 이 프로젝트가 뭔가

Vesuvius Challenge **Progress Prizes**(월간 롤링, 리더보드 아님) 진입 프로젝트. 헤르쿨라네움 탄화 두루마리 CT→판독용 오픈소스 기여.
2026-07-19 착수. 심사 3축 = 조기 공개 / 커뮤니티 채택 / 문서화. 저장소 `khj1222/vesuvius-challenge`(public, MIT).

**라운드 이력**
- **7월**: held-out 검증 하네스(`docs/09`) → **$1,000 수상**(Substack "$33.5k awarded in July"에 실명), 송금 08-21 종결.
- **8월**: villa #192 측정 3D 라벨 = 음의 결과(측정 밴드 0.8098 < 고정 0.8478, `docs/10–12`) → 08-29 제출, 공개 명단에 없음(이유 미공개).
- **9월**: ink_9um 스코어카드·LOSO cross-scroll(`docs/14–18`, `20–26`) → 09-20 제출(v30) → **$500 수상**(10-11 발표, "ink detection experiments with manual and pseudo labels, measuring cross-scroll generalisation"), 10-26 입금. 핵심: 공개 모델 정직 상한 0.74–0.77, 1세그 FT가 Paris4 격차 82% 봉합하나 1667에선 24%(스크롤 특수), 라벨 없는 최선(arm D) 14%.
- **10월**: 임계값 선택·섬유 일치도·깊이 강건성(`docs/27–31`) + 머지 PR 2건 → 10-25 제출, 발표 대기.
- **11월**: I1(VC3D 패널 저장소 잉크 채널) + segment_ink v2 + `docs/32–36` 측정 → 진행 중.

## 핵심 사실 (상금·제출)

- 등급 $500·$1k·$2.5k·$5k·$10k·$20k, 월 최고 $20k 보장, **월 복수 제출·복수 수상 허용**. 등급 이름은 prizes 페이지 frontmatter에 있다(Papyrus $1k / Sestertius $2.5k / Denarius $10k / Gold Aureus $20k, 10-16 확인). #2102(10-14): 작은 수정은 한 제출로 묶고 새 방법·모델·데이터셋은 각각 따로 제출.
- 마감 매월 말 23:59 PT. **폼 URL은 라운드마다 새로 발급, 옛 폼은 결국 닫힘** → 매번 https://scrollprize.org/prizes 에서 받을 것. 09-04 Paul은 "전월 수상 발표 뒤에 뜬다"고 했지만 11월 폼은 발표 전(11-05)에 열렸음(#2492: 월 전환은 수동 컷오프) → 날짜로 가정하지 말고 페이지를 볼 것.
- 심사 Core Requirements: ①VC 데이터의 특정 문제 + 구현·시연 + 기존 대비 이점 ②문서화 + 사용 예 ③표준 포맷(OME-Zarr/tifxyz) 수용·모듈식 통합.
- 상금 이력상 $2.5k 위는 전부 "남이 매일 돌리는 소프트웨어"(머지된 수정 묶음 $5k 1건, 도구 $10k, 파이프라인 묶음 $20k). 측정·음의 결과는 $500–$1k, 머지된 villa PR 묶음은 $250 등급이 다수(9월 명단).
- 메인테이너 기준(11-01 bruniss·11-02 sean): 점검 도구는 머지 안 함, 학습 비교 증거를 원함, 안 쓰는 스크립트 PR은 폐기.
- 수상 수락 시 permissive 라이선스 필수 → MIT라 충족.

## villa 기여 규칙 (어기면 닫힌다)

- **PR 전에 `main`의 `CONTRIBUTING.md`와 `.github/pull_request_template.md`를 읽을 것**(작업 브랜치엔 없을 수 있음). 템플릿 순서: In one sentence → One real example → Before → After this PR → Proof → Why / where this is useful → 체크박스 → `## Details`. 실제 스크롤 데이터 예시, 버그픽스는 실패+정상 출력 증거. AI PR도 "사람이 실제 스크롤 데이터로 쓰다가 생긴 것"이어야 함.
- **Why 문단은 사람이 쓴다**(CONTRIBUTING: LLM PR엔 사람이 쓴 코멘터리). 사용자가 사실을 주고 나는 문장만 옮긴다. 본문엔 **Disclosure 문단**(AI 코딩 도우미가 대부분의 작업, 문제·데이터·결정은 사용자) + 푸터.
- 1인칭은 프로젝트가 실제로 한 일에만. 사용자가 하지 않은 디버깅 장면을 지어내지 말 것. **체크박스("I personally verified")는 사용자가 직접 돌린 PR만** 켠다.
- 이슈·PR 본문은 짧고 직접적으로, 기존 용어로(jrudolph가 #1898을 "불명확·직접 쓰라"며 닫음). 제목이 본문보다 앞서 나가지 말 것(#1638 "leak-free" 제목 → 당일 닫힘·잠금).
- **남의 이슈를 고치기 전에 같은 파일을 건드리는 열린·최근 머지 PR을 먼저 볼 것**: `gh pr list --repo ScrollPrize/villa --state all --search "<파일명>"` + `git log origin/main -- <파일>`. 경쟁 PR이 이슈를 인용하지 않을 수 있다(#1831 → #1893 작업 1주일 중복).
- **자동 종료 봇**(매일 00:00 PT = 16:00 KST): 14일 무활동 **또는** 개설 28일(활동 무관, draft 포함) → 종료. `keep-open` 라벨 면제지만 우리 권한으론 못 붙임. 닫힌 PR은 reopen 안 될 수 있음 → 같은 브랜치로 새 PR.
- **작성자당 열린 non-draft PR 3건 상한**. draft는 상한 밖이지만 자동 리뷰 요청도 안 간다. 리뷰어 배정은 CODEOWNERS 자동이라 "누가 봤다"는 뜻 아님(11-11 #2507로 jrudolph가 `/vesuvius/`에서 빠짐).
- GitHub은 새 PR/이슈 본문을 템플릿으로 미리 채운다 → 준비한 본문은 열고 덮어쓰되 이슈는 `- [x] I personally encountered or reproduced this…` 줄 포함. 초안 머리말(HTML 주석)은 붙여넣지 않는다(`---` 아래만).
- 게시 후엔 항상 **게시본=초안 대조**(API 원문, `gh`). 게시 직전에 스레드를 다시 읽을 것(남이 먼저 답했을 수 있음).
- 같은 작업을 두 달에 청구 금지(9월 기여를 10월로, 8월 작업을 10월로 등).
- **Discord**: #rules가 AI 생성 글 게시 금지 — **예외는 #robots**(Paul 공지: LLM이 크게 관여한 실험 보고용, 모델명 명시·모델 출력과 사람 코멘터리 분리·검증 가능한 주장). 따라서 #robots용 글은 초안을 쓸 수 있고("AI disclosure: run and written by Claude …, Posted with X's approval" 형식이 관례), 다른 채널 글은 쓰지 않는다. 게시는 사용자가. 읽기만 하고 입력창에 키보드 입력 금지(포커스를 뺏음). sean(10-22): 긴 LLM 글은 답이 늦거나 잊힌다 → 2–3줄로. `@sean` 멘션은 자동완성으로(사용자명 bruniss).

## 저장소 규칙

- **`git commit -a` / `git add -A` 금지.** 워킹트리의 `runs/` 삭제 135건은 Z: 아카이브 흔적이라 커밋하면 제출 증거 링크가 사라진다. 커밋은 항상 경로 명시. 옛 runs 파일은 `git show HEAD:runs/...`로 읽는다.
- `runs/*`는 gitignore. 큐레이션한 증거만 **개별 경로로 `git add -f`**(`git add runs/`로 1.1GB를 올렸다 force-push로 걷어낸 전례).
- `planning/`·`AGENTS.md`는 gitignore(비공개, Z:\아카이브\vesuvius-local-only에 백업). `docs/`·README·submission은 제출에서 링크되는 공개 경로 → 영어 유지, 상금 산술·경쟁자 메모·개인정보 금지.
- 제출 문안(field 5 등)을 고친 날은 그날 안에 한 번 통독. field 4 카운트는 실험 커밋 때마다 재산출. 해시 규약 = 본문 + 개행 1개.
- "X가 없다/안 된다" 주장은 **심사자가 볼 ref(main)**에서 다시 확인.
- 데이터·체크포인트·TIFF는 커밋 금지.

## 환경·실행

- 트리 = **`E:\vesuvius-challenge`**(09-12 D:에서 이전). 시스템 Python 3.10 + torch 2.7 cu128, RTX 5090 로컬(클라우드 기본값 금지). `uv`·`hf`·`gh`(`C:\Program Files\GitHub CLI\gh.exe`, PATH에 없음) 설치됨.
- 잉크 파이프라인 = villa `koine_machines`(`external/villa/ink-detection`, uv 환경 torch 2.10 cu128); main에선 `vesuvius/src/vesuvius/ink_detection/`. Windows 추론은 **`--no-compile`** 필수(Triton 없음). 추론 경로는 Windows 형식 `E:/...`(Git Bash `/e/...`면 무출력 종료).
- 깊이 타깃 런 채점은 `infer --z-window 16:48` 필수(없으면 F1 0.80→0.53).
- VC3D(C++) 빌드: 지금 main CI 이미지 = `ghcr.io/scrollprize/villa/volume-cartographer@sha256:1bebf104edbd…`(Ubuntu 26.04, 로컬에 있음, I1 스크립트 `planning/2026-11-02_i1_build/`). 옛 이미지 `ghcr.io/scrollprize/vc3d-deps/linux:sha-0c371b1d…`(5.26GB, `planning/2026-09-29_issue1893_build/README.md`). 테스트 빌드엔 `libsqlite3-dev` 설치 필요.
- 렌더는 WSL의 Linux AppImage(`/opt/vc3d/squashfs-root`, `tools/render_wsl.sh`) — Windows 렌더러는 종료 단계에서 안 죽는 좀비가 된다. 렌더 방향은 `--flip-normals`가 팀 볼륨과 일치.
- 데이터 `data/ink-dataset/`, `data/ink_9um/`(models_ext = 서드파티·dinovol·Reader), `data/first_letters/`, `data/a_lite/`(segment_ink·G3), `data/f1_paris4/`. 표면볼륨 ~86GB/세그먼트.

## 함정 모음

- 셸: heredoc에 정규식·백슬래시 경로를 태우지 말 것(`[\\/]`→`[\/]`, `\v`→수직탭). 경로 작업은 리터럴 바이트로. Git Bash에서 `git show origin/main:.github/...`·Windows exe 인자는 `MSYS_NO_PATHCONV=1`. 긴 heredoc은 잘리니 Write로 파일 만들 것. `cd` 후 저장소 쓰기는 절대경로로.
- PowerShell 5.1엔 `&&` 없음, `Out-File -Encoding utf8`은 BOM(파이썬은 `utf-8-sig`). `taskkill`은 Git Bash에서 조용히 실패 → `Stop-Process`. CommandLine 패턴으로 프로세스를 죽이면 내 셸도 죽는다. TaskStop은 `xargs` 자식 curl을 안 죽인다 → PID 트리로.
- 워크트리에서 `git fetch origin main`이 `origin/main`을 안 갱신할 수 있다 → `git fetch origin +refs/heads/main:refs/remotes/origin/main`. 수정마다 `origin/main`에서 새 브랜치.
- `.venv`의 editable finder가 옛 경로를 물 수 있다 → 이사 후 `koine_machines.__file__`·`vesuvius` import 확인(D:/vw2 밖에서 돌리면 옛 koine를 부름 → `PYTHONPATH`). pytest는 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -p no:cacheprovider`.
- 패치 캐시는 경로 기준 → 마스크를 바꾸면 새 `out_dir`. 실패한 런의 빈 캐시(2바이트)는 지우고 재실행. Windows DataLoader `error 1455`면 워커 6 + 여유 메모리 대기.
- zarr 청크 바이트는 프로세스 간 재현 안 됨 → 동일성은 디코드한 배열로. 예외 정체는 메시지가 아니라 `type(e).__mro__`로.
- GPU를 다른 프로젝트가 쓰면 추론 10배 느려지고 학습이 `resource already mapped`로 죽는다 → 재시도 드라이버. 장시간 백그라운드 런은 주기적으로 진행 확인. 세션 크론은 믿지 말 것.
- WebFetch 요약은 문자 단위 검증에 부적합 → `gh api`/curl 원문. 비인증 GitHub API는 60회/시간(gh는 5,000).
- 빌린 모델을 held-out이라 부르기 전에 그 config·로더의 라벨 출처를 볼 것(dinovol 잉크 라벨, Reader V3 `train_config.json`). 설정 옵션은 실제로 불리는 함수까지 따라갈 것(docs/36).
- 서드파티 pickle 체크포인트는 `weights_only=True`로만(필요하면 전역 목록을 실행 없이 먼저 나열).
- 스윕은 수정된 코멘트도 잡도록 고쳐져 있음. 남의 스레드는 스윕 목록에 있는지 확인.

## 문서 색인

`README.md`(공개 랜딩) · `docs/08` Windows 재현 · `docs/09` 검증 하네스 · `docs/10–12` 깊이 라벨(8월) · `docs/13` 9월 정찰 ·
`docs/14` 스코어카드 · `docs/15` LOSO 4부작 · `docs/16` First Letters 렌더 · `docs/17` held-out 감사 · `docs/18` UDA 사다리 ·
`docs/20` 주석 타겟팅 · `docs/21–23` 표현 격차 시도 · `docs/24` 의사라벨 검증 · `docs/25` 스카우팅 · `docs/26` 고정 임계값 · `docs/27` 라벨 없는 임계값 선택 · `docs/28` 9µm 섬유 일치도 · `docs/29` 임계값 규칙 3차(dense 라벨) · `docs/30` 표면 어긋남 깊이 증강(음성) · `docs/31` 넓은 깊이 jitter(음성) · `docs/32` segment_ink(VC3D 패널) + Reader V3 비교(11월용) · `docs/33` 2.4→9µm 라벨 7px 어긋남을 모델이 배우나(1단계 불명·보정 무익, 2단계 안 함) · `docs/34` Paris4 3D 잉크 모델 교차 스크롤(부분) · `docs/35` 3D 모델 9.6µm 미세조정(무효·ink_9um 아래) · `docs/36` main 기본 증강 A/B(학습 전 철회: 두 preset이 같은 그래프) · `tools/README.md`(툴 설명).
비공개 계획: **`planning/2026-11_plan.md`(11월 후보·재조사 §4b–§4i)**, `planning/2026-11_i1_store_ink_channel.md`(I1 게이트), `planning/2026-11_submission_draft.md`(11월 초안), `planning/2026-10_*`(10월 계획·초안 v5–v7).

## 최근 기록

(11-11 이전 상세는 `planning/history_2026-10_11/CLAUDE_full_2026-11-12.md`)
- **11-17 (화)**: **사용자 결정 A안** → 포크 푸시 `feat/vc3d-ink-surface-channel` = `bb9ec5e2c`(최신 main 체리픽, 커미터를 원래와 같은 noreply로 맞춤; 옛 `bb5623f1d`는 `…-base-1c638d715`, `D:/vw24` 제거), docs/37 상태 칸·패널 절·한계 갱신 + `runs/vc3d_ink_channel/test_ink_detection_overlay_main_8e21d010f.txt`, S1 패키지 작성(`c179567`). README에 18절(docs/37)·Status 한 줄·docs 목록 25–37 추가, 17절에서 docs/37 연결(`c899148`). 그 전 루틴: 스윕(11-16~)·ink-sdk #18·HF 새 글 0. Discord(22시 KST 무렵): segment_ink 스레드 sean 답 없음(마지막 = 우리 11-04 글) → **G4 기한 지남, A/B 사용자 결정 대기**. #announcements 새 글 없음(마지막 11-15), #robots 새 글 없음. villa main `8e21d010f`(#2587 CodeQL 제거, #2593, #2596, #2597): 잉크 파일·`vc3d-ci.yml` 변화 없음, merge-tree 깨끗, 11-16 뒤 갱신된 열린 PR 38건 중 패널 파일 건드리는 것 0, #2523·#2532·#2219 11-13 이후 그대로. **새 CI 이미지 `94077533…` G1 9/9**(임시 워크트리 `D:/vw24` = `8e21d010f` + I1 체리픽 `b04a56595`, 충돌 없음, 볼륨 `vc_i1f`, 빌드 1분 6초, `results/g1_main_8e21d010f/`; 브랜치는 안 옮김). `build_app.sh`는 아직 옛 이미지 → G3 앱 빌드 전에 바꿀 것.
- **11-16 (월)**: 스윕(11-15~)·ink-sdk #18·HF 새 글 0. Discord: segment_ink 스레드 sean 답 없음(G4 기한 오늘), #robots 새 글 없음, #announcements 11-15 = First Letters $50k PHerc.0211(Priyank Aranke, "19 scrolls 남음, 상금 7개 남음"). villa main `f29334cd8`: 잉크 파일 변화 없음, merge-tree 깨끗, 브랜치 `bb5623f1d` 그대로. **`vc3d-ci.yml`이 새 CI 이미지 `sha256:94077533…`로 바뀜**(#2564 Spiral, #2583 packaging) → 새 이미지 G1 미실행. 잉크 패널 draft #2523·#2532·#2219는 11-13 이후 변화 없음, 11-15 뒤 갱신된 열린 PR 중 패널 파일 건드리는 것 없음(#2582 cabbry `--mask-off-surface`는 Python ink_detection).
- **11-15 (일)**: 스윕(11-14~)·ink-sdk #18 새 글 0, Discord segment_ink 스레드 sean 답 없음. villa main `2d3fb38d3`(#2546·#2538) — 잉크 파일·`vc3d-ci.yml` 변화 없음, merge-tree 깨끗 → G1 재실행 불필요. **새 draft 2건이 잉크 패널 파일을 건드림(둘 다 11-13)**: #2523(ChaseHendrick, 로컬 모델 서버 live preview, `InkDetectionOverlayController.cpp`·`ViewerInkDetectionPanel.cpp`) = 우리 브랜치와 병합 깨끗 · #2532(lucasjbyoung, 잉크 라벨 페인팅 + Ink Detection 독 "Add Image..." 로컬 예측 오버레이, `_localOptionsBySegment`) = `refreshOptionsForActiveSurface`에서 **텍스트 충돌**(둘 다 옵션 목록 끝에 덧붙임, 해결은 쉬움). #2219(ChaseHendrick 통합 draft)도 11-13 갱신. 셋 다 저장소 `ink`/`ink_*` 채널은 안 읽음 → I1 기능 중복 없음. B안 PR 본문엔 #2532 "Add Image..."(세션 한정 로컬 파일)와의 차이 한 줄 추가할 것.
- **11-14 (토)**: 스윕(11-12~)·HF 새 글 0. sean 답 없음. **10월 발표: $250(#1796), 측정 0.** ink-sdk 겹침 확인(위). villa main `97fb9336c`(#2531 Delta3D 0.3.2, CI 이미지 digest 같음, `vc3d-ci.yml`에 `vc_object_server_app` 빌드 추가) — 잉크 파일 변화 없음, merge-tree 깨끗, 겹치는 열린 PR 없음. Z: 처음엔 미연결 → 밤에 사용자가 연결, 백업 69개(불일치 0). **G1 9/9 on `97fb9336c`**(임시 워크트리 `D:/vw22` = `db0fda397`, I1 체리픽 충돌 없음, 볼륨 `vc_i1e`, `results/g1_main_97fb9336c/`; 브랜치는 안 옮김). 함정 재발: Git Bash가 `sparse-checkout set /volume-cartographer/`를 `C:/Program Files/Git/...`로 바꿈 → `MSYS_NO_PATHCONV=1`. **ink-sdk → VC3D 다리 `tools/ink_sdk_channel.py`(`9285d99`)**: 영수증+메시로 auto-crop 오프셋·방향·pool·ROI를 되돌려 `ink_*` 채널로. 렌더러가 찍은 crop 2건(w00 (19,19), ag144 (19,39))과 일치(**float32 0.05 → 1/0.05f = 19.9999997 함정**), 배치 테스트 전부 0px, 저장소 왕복 픽셀 동일. 이어서 **실제 ink-sdk 실행**(사용자 OK): `E:/envs/inksdk` + WSL `~/inksdk-venv`, 9µm 레인 = villa `3ea17f54a` 워크트리 `D:/vw23`. 표면볼륨 실행 → segment_ink 맵과 상관 0.99994. 메시+CT 실행(로컬 CT = w00 표면 ±24복셀 청크 1,878개 3.7GiB `data/ct_partial/`) → ink-sdk 자체 auto-crop 렌더를 다리가 (19,19)에 놓음, CT 질감으로 xy 위치 확인, 저장소 왕복 동일. 맵 상관 0.916의 원인은 **깊이 반 층이 아니라 auto-crop의 19px 캔버스 이동**(같은 입력을 전체/잘린 캔버스로 돌리면 0.925/0.862, 캔버스를 맞추면 0.993 — Reader V3가 캔버스 원점에 민감). 처음엔 반 층 탓이라고 잘못 적었다가 검증으로 정정. 기록 `planning/2026-11-14_ink_sdk_bridge/README.md`. **10월 지급 폼**(Paul 메일 11-13): 사용자 제출 완료(세부는 비공개 메모리), 입금 대기. 초안 재검증에서 2건 정정(1/0.05f 값, 0.92 원인 → 캔버스 이동; `3cbeb62`) 후 **ink-sdk #18 게시**(사용자, 게시본=초안 2,549자 동일). **저녁:** 11월 초안 v1(S1/S2 두 건) + docs/37 공개(`114f513`), 큰 상 검토·제목상 탐침은 비공개 노트(위 "큰 상 검토"). VC3D 최신 앱 빌드 완료(`run_vc3d_new.sh`, 화면 확인은 사용자 선택). 사용자 "오늘은 마무리".
- **11-12 (목)**: 스윕(11-11~)·HF 새 글 0. Discord: sean 답·10월 수상 발표 없음, #robots 새 글 = Blucca AFV 섬유 추적 점검기(11-10, 겹침 없음). villa #2491(hendrikschilling, 11-12 머지)이 잉크 오버레이를 다시 고침(공개 파일 목록을 활성 표면 `meta`에서) → I1 체리픽 충돌 없음, **G1 9/9**(볼륨 `vc_i1d`, `results/g1_main_1c638d715/`) → 사용자 결정으로 브랜치를 `bb5623f1d`로 옮김. CLAUDE.md 정리(옛 세션 요약·10월 로그를 history로, `42ae7d1` 푸시). Z: 미연결 → 백업 못 함(밀린 것: history 사본, `g1_main_1c638d715/`, 빌드 README). 사용자 "오늘은 여기까지".
- **11-11 (수)**: 새 글 0. 11월 폼이 11-05(#2301)부터 열려 있음을 발견. villa main `f0e441016`, 잉크 파일 변화 없음.
- **11-09 (월)**: 새 글 0. villa #2462(sean, 11-06 머지)로 I1 충돌 → 재기반 `19aa7a474`, 테스트를 새 저장소 API로 옮김, G1 9/9.
- **11-07·11-05 확인**: 새 글 0. 11-05 사용자 결정 = CLAUDE.md 푸시, `data/ink_3d*` 삭제.
- **11-06 (금)**: segment_ink v2 푸시(`72bc3c7`), 입력 경로 격차 진단(값싼 원인 없음), I1 PR 본문·docs/32 Update 초안, 11월 제출 초안 v0, Z: 백업(56개, 불일치 0).
- **11-04 (수)**: sean 질문 게시(사용자, 게시본=초안). villa #2440으로 I1 재기반 `0af58057b`, 새 CI 이미지로 G1 9/9.
- **11-02 (월)**: w045 정정 푸시(`bb35177`). I1 방향 결정, 게이트 고정, G1·G2·G3 통과(G3는 사용자 직접).
- **11-01·10-31**: sean 781k dinovol = 640k와 같은 잉크 라벨(B 보류 유지, 파일 삭제). docs/36 철회(`47e894f`). H1 접음.
