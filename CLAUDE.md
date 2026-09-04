# CLAUDE.md — vesuvius-challenge

새 세션은 이 파일 + `README.md` 만 읽으면 컨텍스트 없이 이어갈 수 있게 자기완결로 유지할 것.

## 이 프로젝트가 뭔가

Vesuvius Challenge **Progress Prizes** 트랙 진입 프로젝트. 헤르쿨라네움 탄화 두루마리 CT→판독을 돕는 오픈소스 기여로 월간 상금($1k~$20k)을 노림. 2026-07-19 착수(사용자가 후보 5개 중 Vesuvius 선택 — 롤링이라 9월 병목 파이프라인에 안 얹힘이 결정 이유).

## 핵심 사실 (2026-07-19 공식 검증, 근거 docs/)

- **트랙**: Progress Prizes = 월간 롤링. 리더보드 아님. 심사 3축 = 조기공개 / 커뮤니티 채택 / 문서화.
- **상금**: $500 · $1k · $2.5k · $5k · $10k · $20k (6단계). 월 "최고 제출 $20k" 보장, **월 복수 제출·복수 수상 허용**. (2026-08-29 6단계 확인 → **2026-08-30 재확인: 변경 없음**. ⚠️ Papyrus/Sestertius/Denarius/Aureus 같은 **등급 이름은 이제 페이지에 없다** — 7월 수상 통보 메일의 호칭일 뿐이니 문안에 쓰지 말 것.)
- **마감**: 롤링(다음 라운드 = **7/31 23:59 PT** → 8/31 → …). **타깃 = 7/31 스트레치**(2026-07-19 결정, ~12일), 못 맞추면 8/31로 이월.
- **제출**: Google Form. ⚠️ **폼 URL은 라운드마다 새로 발급되고 지난 폼은 닫힌다**(2026-08-29에 7월 폼 `forms.gle/xoF5C3QsYutKP97x7`이 "응답 받지 않음"으로 막힌 걸 발견). 매달 https://scrollprize.org/prizes 에서 새 링크를 받을 것. 8월분 = https://docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform . **8월 폼은 6문항** — 7월에 있던 "Pull request submitted!" 체크박스가 사라져 PR은 4번 칸으로만 증빙한다.
- **라이선스**: 수상 수락 시 permissive(MIT 등) 오픈소스 필수. 제출 시점 비공개 OK.
- **위시리스트**: github.com/ScrollPrize/villa issues (label: "help wanted") + scrollprize.org/2026_open_problems
- **진입 과제**: Ink Detection(주말 스코프) / Virtual Unwrapping / Surface Reconstruction.

## 컨벤션 (사용자 환경 정합)

- 시스템 Python 3.10 + cu128 (torch 2.7.0+cu128·CUDA·5090 네이티브 검증됨), `requirements.txt` 패턴. **`uv`·`hf` CLI는 이미 설치돼 있음**(구 메모의 "uv 미설치"는 오류). venv 쓰면 `.venv`.
- 컴퓨팅 = 집 RTX 5090 (로컬). 클라우드 기본값 금지.
- git: `khj1222/vesuvius-challenge` (푸시 대기). 데이터·체크포인트·TIFF는 커밋 금지(.gitignore 처리).
- 코드 스타일: 주변 코드 관례 따를 것. 스텁엔 `# TODO(week0):` 마커로 미완 지점 표시.

## 현재 상태 / 다음 액션 (2026-07-25 갱신)

- ✅ **기여 #2 = held-out 검증 하네스 완성(2026-07-25, 커밋 `8370471`, 로컬만 — 푸시 대기).** 튜토리얼은 **검증 세트가 0개**로 학습됨(배포 세그먼트에 `_validation_mask` 없음 → `val_every`가 빈 루프, `evaluation/metrics/`의 DRD·pFM 미실행). 이걸 메우는 툴 4종 + config + 문서를 만듦. 상세 = `docs/09_validation_harness.md`.
  - `tools/make_validation_mask.py` — **주석 영역 단위** held-out 생성. ⚠️ supervision은 연속 리본이 아니라 **글자 박스 15개**(면적 1.5~20.7%, 잉크밀도 0.114~0.440, 4개는 이웃과 패치(256px)보다 가까움) → 사각 밴드로 자르면 글자가 반으로 쪼개져 인접 픽셀 누수. 그래서 영역 통째 배정 + 패치거리 내 영역은 그룹 병합 + 부분집합 완전탐색. 결정론적. `--folds K` 지원.
  - `tools/eval_validation.py` — 임계값 스윕(누적 히스토그램) + DRD/pFM(저장소 metric 클래스 호출) + **영역별 분해**.
  - `tools/sweep_checkpoints.py` — ckpt별 채점(`infer --mask-path`로 166블록만, ~30초) + CSV + PIL 곡선.
  - `tools/run_cv_folds.py` — k-fold 무인 실행 드라이버.
  - **실측**: 검증 패치 0→1,337(학습 2,710→2,240). 클린 20k런 **F1 0.8232 / IoU 0.6995**(step 20000, threshold 146), 누수 기준선 0.8594. 영역별 F1 **0.796~0.895** → 단일 split에서 ~0.05 미만 차이는 노이즈.
  - **새 함정**: ①`create_label_zarrs`는 **tiled TIFF만 스트리밍**(striped면 25GiB 할당 후 사망) ②패치 캐시가 **파일 경로 기준**이라 마스크 갈아끼워도 낡은 split 재사용(새 out_dir 필수) ③`out_dir`은 cwd 기준(학습은 `--directory`, 툴은 `--project`).
- ✅ **3-fold 교차검증 완료(2026-07-25, 5h25m, 커밋 `5a176b4`)**: fold별 best F1 = 0.8497 / 0.8537 / 0.8383, **평균 0.8472 · spread 0.0154**(`runs/ink_fold_cv_summary.json`). 단일 split(0.8232)까지 합치면 **동일 config 4회 평가가 0.823~0.854** → **~0.03 F1 미만 개선 주장은 노이즈**(후보 B ablation의 판정 기준선). 그리고 **3런 중 2런이 step 17000에서 정점 후 20000에 하락**(단일 런도 18000 딥) → 튜토리얼 20k 스케줄은 최적을 살짝 지나침. fold 2가 잉크밀도 최고 영역(0.2748)을 떼고 최저점 → 점수차의 주원인은 학습량이 아니라 **held-out 구성**.
- **사용자 결정(2026-07-25)**: ①**7/31 라운드에 제출**(스트레치 아님, 확정) ②3-fold 돌림 ③메인테이너 문의는 **결과 나온 뒤 사용자가 직접 게시**(초안 = 세션 스크래치패드; 질문 2개 = val mask 부재가 의도인지 + striped TIFF OOM PR 받을지). Claude는 GitHub 인증 없음 → 게시 불가·금지.
- ✅ **푸시 완료(2026-07-25)**: 커밋 `8370471`+`deb23a4` → https://github.com/khj1222/vesuvius-challenge
- ✅ **업스트림 이슈 게시(2026-07-25, 사용자 직접)**: https://github.com/ScrollPrize/villa/issues/1231 — 질문 2개(①배포 세그먼트에 `_validation_mask` 없는 게 의도인지 ②`create_label_zarrs`의 striped TIFF OOM에 PR 받을지). 본문 원본 = `submission/maintainer_issue.md`. **답변 오면 방향에 반영할 것**(이미 내부 마스크가 있다면 하네스의 포지셔닝을 바꿔야 함).
- ✅ **업스트림 PR 제출(2026-07-25)**: https://github.com/ScrollPrize/villa/pull/1234 — `create_label_zarrs`가 striped TIFF를 스트리밍하도록 수정(1파일 +54−8, base `merge-ink-pipelines`, mergeable, 리뷰 대기). 로컬 브랜치 `external/villa` `fix/stream-untiled-label-images`(`a5179a8`), 패치 사본 `submission/villa-pr-stream-untiled-labels.patch`. ⚠️ base를 `main`으로 잘못 열면 231파일 diff가 되니 반드시 `merge-ink-pipelines`. 검증 = 합성 이미지 6레벨 바이트 동일 + 실제 32249×51380 striped 83초 변환.

## 🏆 7월 라운드 **수상** (2026-08-04 통보)

- **Progress Prize 수상.** Paul Henderson(Research Team Lead, `paul@scrollprize.org`) 메일로 통보(2026-08-04 02:18, 리마인더 2026-08-07 02:01). 대상 = 7/26 제출한 held-out 검증 하네스.
- ✅ **지급 폼 제출 완료(2026-08-10, 사용자 직접 — 지급·개인정보 입력은 Claude가 처리하지 않음).**
- ✅ **금액 확정 = $1,000(Papyrus 등급, 2026-08-18 확인)**: 공식 발표 포스트 https://scrollprize.substack.com/p/335k-awarded-in-july ("$33.5k awarded in July")에 **"Hyojun Kwon — an update to the ink tutorial that includes proper validation data"**로 실명 등재. 7월 총 수상 = $20k 1건(ScrollFiesta, 메싱) + $2.5k 1건(Will Stevens, 언래핑) + $1k 다수(우리 포함; TAUIL Abd Elilah도 $1k — 재현성 감사 니치도 같은 등급). ✅ **전신송금 도착(2026-08-18)** — 송금인 = **Curious Cases Inc**(EIN 92-1989282, SF 소재 미국 비영리로 scrollprize.org 운영 법인, GuideStar 확인). 수취 사유("미국 비영리재단 Curious Cases Inc. 주최 연구 경진대회(Vesuvius Challenge) 상금 수령") 제출 완료. **은행이 참가·수상·금액 증빙을 추가 요구** → 16쪽 PDF 일괄 자료 작성 완료(`C:/Users/bluek/Documents/vesuvius_prize_wire_evidence.pdf`: 표지 + 발표문/상금규정/법인등록 각각 '주소창 URL 보이는 화면캡처 + 전체 인쇄본' + 수상통보·지급안내 메일 2건). 빌더 스크립트는 세션 스크래치패드. ✅ **원화 입금 확인(2026-08-21, 사용자 통보) → 7월 상금 건 완전 종결.**
- 수락 조건인 permissive 라이선스 = 저장소 MIT라 이미 충족.
- 8월 제출에 미치는 영향: "수상한 하네스를 **써서** #192의 라벨 품질 주장을 실제로 검증했다"는 연속성이 생김. 이슈 [#1231](https://github.com/ScrollPrize/villa/issues/1231)이 무응답인 것과 별개로, 하네스의 전제(배포 세그먼트에 val mask 부재)는 사실상 인정받은 셈.

## 🏁 7월 라운드 제출 완료 (2026-07-26)

- ✅ **Google Form 제출 완료(2026-07-26, 마감 7/31 23:59 PT 대비 5일 여유).** 제출 명의 = Hyojun Kwon / bluekgssk@gmail.com, 개인 자격. **답변 7칸 전문 = `submission/2026-07_progress_prize.md`**(제출본과 동일하게 유지 중 — 심사 문의 오면 이 파일이 근거).
- ✅ **awesome-scroll-tools PR**: https://github.com/ScrollPrize/villa/pull/1249 — `scrollprize.org/docs/20_community_projects.md`의 `#### ⚙️ Tools`에 하네스 1줄 추가(base **`main`**, 1파일 +3, 저자 표기 `by khj1222`). 브랜치 `khj1222/villa` `add-ink-validation-harness`(`2aba59a`, main tip `650076f`에서 분기). 폼 6번 필수 체크박스를 이걸로 충족.
- ⚠️ **`gh` CLI 미설치**(bash/PowerShell 둘 다). git push는 GCM 자격증명으로 됨 → **브랜치 푸시까지는 Claude가 가능, PR 생성/이슈 게시는 사용자가 웹에서.** villa 쪽 작업은 sparse worktree(`git worktree add --no-checkout --detach D:/vw <ref>` + `sparse-checkout set --cone scrollprize.org/docs`)로 할 것: `external/villa` 작업트리는 `merge-ink-pipelines` + 수정된 `pyproject.toml` 상태라 체크아웃 전환 금지. 경로가 길면 `Filename too long`으로 실패하니 **짧은 경로**(`D:/vw`) 필수.
- 📌 **제출 문안 정확성**: 5번의 "threshold 122–198"은 `ink_holdout_20k` 20체크포인트 기준이고 fold 런 포함 시 61–203 → 제출본은 둘 다 명시하도록 수정됨(커밋 `21a27c1`). 향후 수치 인용 시 근거는 `runs/*/validation/summary.csv`의 `threshold` 열.

## 9월 라운드 정찰 완료 (2026-08-18)

- 상금판·데이터 인벤토리·후보 3안 전문 = **`docs/13_september_scouting.md`**. 요지: $1M 직행은 체급 밖, First Letters $50k는 PHerc0800/1447(mesh만 존재)이 최근접 경로, **진짜 기회 = 08-14 공개된 신규 공식 데이터셋 `ink_9um`**(4스크롤 29세그먼트, 검증 마스크 3개뿐 = 하네스 빈틈 재현, villa merge-ink-pipelines 소비, 네이티브 표면볼륨 1.7GB/세그먼트라 디스크 증설 불필요). 추천 = A안(하네스 확장 + leave-one-scroll-out으로 오픈 문제 #7 수치화) 먼저, B안(First Letters 렌더 경로)은 부산물로.

## 🔬 9월 트랙 실행 완료 (2026-08-22~24, GPU ~26h 무인 완주)

A안(docs/13)을 끝까지 실행. **9월 제출감 완성** — 상세는 docs/14(스코어카드)·docs/15(4부작), 문안 = `submission/2026-09_progress_prize.md`(v2, 커밋 `7d7d5fe`). 원수치는 `runs/ink9um_scorecard/`의 CSV/JSON 9종(커밋됨). 요지:

- **docs/14 스코어카드**: 공개 ink_9um 체크포인트 14개 첫 정량 채점 — 정직 상한 F1 0.74–0.77 vs train 0.98+(암기 격차 0.22–0.45), 만능 step 없음, seed 격차 최대 0.22. ⚠️ 8월 문안에도 한 문단으로 실림(`dcc4317`) → 9월에선 groundwork로만 인용(이중청구 금지).
- **docs/15 4부작 (LOSO cross-scroll, 오픈 문제 #7 첫 수치)**:
  1. 측정 — LOSO 3-arm(레시피 재학습 6회): 자명하한(2p/(1+p)) 대비 마진 **+0.060(Paris4)/+0.131(1667)/+0.169(0139)**. 절반 코퍼스(no0139)가 최고 전이 = **타깃 성질이 소스 크기를 지배**. 같은 물리 세그먼트에서 **aligned 표현 > native 4/4**. ⚠️ 이걸 처음엔 domain match로 읽었으나
     **2026-08-26 사전등록 arm이 기각**(아래) — 지침은 "학습과 같은 계열"이 아니라 **"aligned 계열로 렌더"**.
  2. 성질 — **편향이지 분산이 아님**: seed |차| 0.01–0.03(in-scroll 0.22와 대조), seed 앙상블 회수 +0.005–0.009뿐(`loso_ensembles.csv`).
  3. 수리 비용 — **타깃 1세그먼트(w00) fine-tune = 미학습 7세그 0.496→0.822(격차 82% 봉합), 2,500 step(≈7분)에 포화**(`ft_paris4_matrix.csv`).
  4. First Letters 플레이북: 렌더(같은 표현) → 직행추론은 스카우팅 → 1세그 주석 → 분 단위 FT → 재추론. 단계별 기대값 전부 실측.
  - 전 arm에서 LOSO 정점 10–20k(75k는 과학습). 정직-대-정직 낙폭: Paris4 −0.26, 1667 −0.17(w029 0.758→0.589).
- **재현 인프라**: `tools/make_ink9um_config.py`(arm 생성기, 쿼터 재정규화), `tools/eval_validation.py`에 `--region-kind supervision_mask`+단일레벨 폴백 추가. 정렬 9.6µm 입력 24개는 villa `prepare_9um_isotropic_input.py`로 **S3 level-2 직스트리밍**(86GB 다운로드 불필요, `data/ink_9um/surface-volumes/aligned9/`).
- **함정(재발 방지)**: ①prepare 스크립트는 Windows에서 마지막 dir rename에 죽지만 `tiles=N/N`이면 데이터 완전 — rename만 대신 ②S3 순단(500/disconnect)은 **잡 단위가 아니라 타일 단위 재시도**(6회 백오프)로만 뚫림, 동시성 ≤2×6 ③채점은 반드시 세그먼트별 자명하한과 함께 읽을 것(임계값 0 = 자명분류기 신호) ④학습 크래시는 full-state resume 재시도(체인 스크립트 패턴, 이번엔 미발동).

## 다음 액션 (대기/선택)

1. **업스트림 반응 (2026-08-02 확인)**:
   - ✅ **PR [#1249](https://github.com/ScrollPrize/villa/pull/1249) 머지됨**(2026-07-31, erdpx가 main으로). 하네스가 scrollprize.org 커뮤니티 툴 목록에 실제로 등재됨 → 제출 문안의 "PR 제출" 표현은 "머지 완료"로 갱신 가능.
   - ✅ **PR [#1234](https://github.com/ScrollPrize/villa/pull/1234) 머지됨(2026-08-14, erdpx가 `merge-ink-pipelines`로, 추가 코멘트 없이)** — #1249에 이어 2번째 머지 업스트림 PR. 리뷰 반영은 2026-08-09(커밋 `fc6d9a7`). erdpx 요청(*"2D 피라미드만 메모리에 만들고 각 레벨을 `DEFAULT_LABEL_SLICE`에 바로 써라"*)대로 `_build_downsample_levels_from_zarr` 호출을 걷어내고 2D 레벨을 메모리에서 유도하도록 변경. **실측 114.5s → 66.5s(1.7배), 피크 RSS 1.61 → 1.99 GiB.** `mean` 모드는 `_downsample_mean`의 float64 누산기(출력의 8배)를 피하려 행 밴드로 나눠 평균 — 밴드가 짝수 소스 행에서 시작하므로 결과는 바이트 동일. 검증 = 합성 4케이스(binary/grayscale × 짝수/홀수 크기)에서 tiled 경로·원본 in-memory 경로와 6레벨 바이트 동일 + 실제 32249×51380 striped 파일 6레벨 일치. 패치 사본 = `submission/villa-pr-stream-untiled-labels.patch`. **리뷰어 회신 코멘트는 사용자가 직접** (초안 아래 "PR #1234 회신").
   - 🔄 이슈 [#1231](https://github.com/ScrollPrize/villa/issues/1231) — 텍스트 답변은 아직 없지만 **2026-08-03경 `pmh47`(Paul Henderson)이 `erdpx`를 담당자로 배정**함(2026-08-08 확인). 즉 무시가 아니라 **트리아지 완료** 상태이고, 수상 통보(08-04) 직전 시점이라 이슈가 심사에 반영됐을 가능성이 높음. **"내부엔 이미 val mask가 있다"는 답이 오면 하네스 포지셔닝과 제출 서술의 전제를 조정**해야 하는 건 그대로.
2. **8월 라운드(8/31) 타깃 = villa [#192](https://github.com/ScrollPrize/villa/issues/192) "Accurate 3d ink labels" + 하네스 업스트림화(보조)** — 2026-07-26 재조사 후 결정. 계획·근거·마일스톤·리스크 전문 = `docs/05_strategy.md` 하단 "8월 라운드" 절.
   - 핵심 논리: 7월에 만든 held-out 하네스가 **"z복사 라벨 vs 3D 라벨"을 같은 fold·시드로 비교**하게 해줌 → 15개월간 아무도 증명 못 한 라벨 품질 주장을 수치로 세울 수 있음. 판정 기준선 = ~0.03 F1 미만은 노이즈.
   - ⚠️ **순환성 리스크**: 깊이 프로파일을 z복사 라벨로 학습한 모델에서 뽑음 → self-distillation **대조군 arm 필수**(이게 없으면 결과 무의미).
   - ⚠️ **니치 혼잡**: 7월 마감 직전 TAUIL-Abd-Elilah가 재현성 감사로 8건, Jinhojeong이 라벨 품질 측정 툴(#193)을 냄. "측정 툴 하나 더"는 중복 → 하네스를 **쓰는** 쪽으로 갈 것.
   - ✅ **1단계 깊이 국소화(2026-07-27)** → ✅ **2단계 측정된 3D 라벨(2026-07-27)** → ✅ **3단계 학습 소비 경로 + 3 arm 자산(2026-07-31)** → ✅ **4단계 9런 매트릭스(2026-08-09)**. 각각 `docs/10` · `docs/11` · `docs/12`. **실험은 끝났고 결과는 음의 결과** — 아래 "매트릭스 완료" 절.
3. 수상 시 permissive 라이선스 필수 → 저장소는 이미 MIT라 조건 충족.

### ▶ 🏁 8월 라운드 제출 완료 (2026-08-29)

✅ **8월 폼 제출 완료(2026-08-29, 사용자 직접, 마감 8/31 23:59 PT 대비 2일 여유).** 접수 확인 메일로 6칸 전부·Terms 체크까지 확인. 제출본 = `submission/2026-08_progress_prize.md`(**field 4·5가 제출본과 바이트 동일**, field 5 sha256 `b2910b90c6a573c767a07d49b9b4138daffe87f265e4a43cd72ac27d34d117d0` / 70줄 — 7월 파일처럼 이 상태로 동결. ⚠️ **해시는 field 5 본문 + 개행 1개(5,063자) 기준**이다. 2026-08-30 재검증에서 이 규약으로 일치 확인). 타깃 = villa #192 측정 3D 라벨의 음의 결과.

⚠️ **폼 URL은 라운드마다 새로 발급되고 지난 폼은 닫힌다** — 08-29에 7월 폼(`forms.gle/xoF5C3QsYutKP97x7`)이 "응답 받지 않음"으로 막힌 걸 제출 직전에 발견했다. 8월분 = `docs.google.com/forms/d/e/1FAIpQLSev2vJobu521iB6OuyehDktzYTEo131F4iUGwt3Qxa9a1fk6A/viewform`, 출처는 https://scrollprize.org/prizes. **9월분은 거기서 새로 받을 것.** 8월 폼은 **6문항**(7월의 "Pull request submitted!" 체크박스가 사라짐 → PR은 4번 칸으로만 증빙). 상금 등급도 **6단계로 확장**($500·$1k·$2.5k·$5k·$10k·$20k).

**제출 당일(08-29) 최종 점검 결과**: #1535 open·mergeable·사람 코멘트 0·리뷰어 0(08-19 이후 무변화, 유일한 코멘트는 Vercel 봇) / #1231 무변화(코멘트 0, erdpx 배정) / #192는 stantheman 08-25 이후 새 코멘트 없음 / field 4 링크 10개 전부 200 / field 5 수치 전건 원 아티팩트 재산출 일치. **당일 수정 4건**: ①독립 밴드 채점을 `docs/12`에 기록(field 4가 가리키는 문서에 없어서 심사자가 근거를 못 찾는 상태였음) ②그 채점의 평활성 카베앗을 field 5에 반영 ③w02 비교의 "within 0.001 of w00's"가 두 문장 앞의 0.8472(3-fold)로 오독될 수 있어 0.8232(단일 split) 명시 ④증거표 3행이 30k 재스윕에 덮인 CSV를 가리켜 fold-CV JSON으로 재지정. 커밋 `d38aed8`·`b37c12d`·`24db100`.

**남은 것 = 9월 라운드.** 문안은 **v8로 감사까지 끝나 동결**(`submission/2026-09_progress_prize.md`), 제출 당일 순서는 그 파일의 **Step 3** 참조. 9월 폼 URL은 08-30 시점에도 아직 8월 것 — 라운드가 넘어가면 https://scrollprize.org/prizes 에서 새로 받을 것.
그날 순서(전부 완료) = ①#1535 상태 확인 → 무변화라 라벨 갱신 불필요 ②stantheman0128 채점 반영(08-28) ③문안 링크 재검증 → 10개 전부 200 ④사용자 폼 복붙 제출 ⑤`submission/2026-08_progress_prize.md`를 제출본과 동기화(완료, 동결).

✅ **코멘트 2건 게시 완료(08-28 03:25/03:26 UTC, 사용자 직접, 게시본 = 로컬 초안과 바이트 동일 확인)** — [#1608](https://github.com/ScrollPrize/villa/pull/1608#issuecomment-5448016030) · [#1611](https://github.com/ScrollPrize/villa/issues/1611#issuecomment-5448022908). 원본 = `submission/pr1608_reply_bullo27.md`, `submission/issue1611_reply_bullo27.md`.

✅ **8월 제출 사전점검 완료(08-28)** — field 4 링크 **10개 전부 200**, field 5 수치를 원 아티팩트(`external/villa/ink-detection/runs/*.json`)에서 **전건 대조 일치**(v2/v3/v4 0.844091/0.847853/0.809759, 격차 0.038094, 7월 2D 0.847243, 30k 0.038263→0.036076, w02 0.82625/0.728672 + 완전 순서). #1535·#1434 확인 결과 **우리가 답할 것 없음**(#1535는 사람 코멘트 0건, #1434엔 포인터 코멘트가 08-19에 이미 게시됨). **판정 = 주말에 그대로 제출.**

**8월 문안 내용 수정은 불필요 — 08-26에 점검 완료.** 오늘 철회한 domain match 주장은 8월엔 애초에 안 들어가 있었고(ink_9um 문단은 docs/14 스코어카드만 인용), #1434 인용도 "닫히고 #1535로 갔다"는 의도된 서술이라 그대로 두면 됨.

⚠️ **[#1608](https://github.com/ScrollPrize/villa/pull/1608)은 9월용으로 남길 것** — 08-26에 열었으니 날짜상 8월 작업이지만, 8월은 이미 머지 PR 2건(#1234·#1249)으로 6번 요건이 충족돼 있고 #1608의 서사(오픈 문제 #7)는 9월 본문과 붙어야 값이 산다. 양쪽에 쓰면 이중청구.

**9월 남은 결정**: ~~WSL2/Docker 설치 → B안 렌더 경로~~ → ✅ **08-26 설치·실행 완료, 결과는 음(아래 절, docs/16).** 남은 건 절반-세그먼트 라벨효율 등 폴드인(문안 notes) 정도. **등급을 $1k 밖으로 밀 후보였던 렌더 경로는 소진됐다** — 경로는 뚫렸으나 글자가 안 나온다.

**상금 기대치(2026-08-26 평가)**: 7월 실측 환율 = "잘 만들고 잘 문서화된 도구 = $1k"(같은 달 $20k는 메싱, $2.5k는 언래핑). 8월은 **음의 결과 + 핵심 PR 미머지**라 $1k 아니면 0이고, 수상한다면 근거는 결과가 아니라 **머지된 PR 2건**. 9월은 **이름 붙은 오픈 문제(#7)의 첫 수치 + 관측된 커뮤니티 견인**이라 더 나음($1k, 잘 되면 $2.5k). **둘 다 $10k/$20k의 형태는 아님** — 큰돈은 "읽히는 글자가 느는" 쪽으로 간다.

### ▶ 9월 라운드 상태 (2026-08-31 갱신) — **백로그 3건 전부 완료, 문안 제출 준비 완료**

**제출물은 이미 완결이고 문안은 v8로 동결**(`submission/2026-09_progress_prize.md`, 감사 완료).
아래는 "더 할 수 있는 것"이지 "해야만 하는 것"이 아니다. 마감 9/30까지 한 달 남았고 필요한
GPU는 다 합쳐 하루 남짓.

**📋 상금 체계 재확인(2026-08-30, scrollprize.org/prizes 원문)** — **변경 없음**:
- Progress Prize 등급 = **$20,000 / $10,000 / $5,000 / $2,500 / $1,000 / $500** (6단계 유지)
- "Best Submission of the Month: **$20,000**, guaranteed every month"
- "Submissions are evaluated monthly, and **multiple submissions/awards per month are permitted**"
- 페이지의 마감 문구는 아직 **8/31** — 라운드가 안 넘어갔다. 9월 폼 URL은 넘어간 뒤 여기서 받을 것.
  **2026-09-03 재확인: 마감이 3일 지났는데도 여전히 8/31 문구이고, 링크된 폼도 여전히 `August 2026 Progress Prizes`이며 아직 응답을 받고 있다.** 즉 이 팀은 라운드 롤오버가 늦고, **옛 폼이 곧바로 닫히지도 않는다**(7월 폼은 결국 닫혔지만 8월 폼은 마감 후에도 열려 있음). 9월분을 이 URL로 내면 8월 접수함에 들어갈 위험이 있으니 **반드시 새 URL을 확인하고 낼 것.**
- ⚠️ 등급 **이름**(Papyrus/Sestertius/…)은 이제 페이지에 없다. 7월 수상 통보 메일 기준의 호칭일 뿐이니 문안에 쓰지 말 것.

**📋 심사 Core Requirements (페이지 원문, 지금까지 우리가 기록해 두지 않았던 것)** —
제출 전 문구 검토 때 **이 세 항목에 우리 문안을 대조**할 것:
1. **Problem Identification and Solution** — ①VC 스크롤 데이터로 특정 문제를 다룰 것 ②**명확한 구현 경로와 사용 시연** ③**기존 해법 대비 유의미한 이점 입증**
2. **Documentation** — 포괄적 문서 + **사용 예시**
3. **Technical Integration** — **표준 커뮤니티 포맷 수용**(OME-Zarr/zarr, tifxyz 등) + 출력 포맷 일관성 + **모듈식 통합 설계**

→ 우리 현 문안은 1①②·2는 강하지만, **1③("기존 해법 대비 이점")과 3(통합)은 사실상 충족하는데 문장으로 드러나 있지 않다.** 실제로는: 공개 모델에 **평가가 아예 없었고**(docs/14), 공개 레시피는 **그대로는 안 돌아가며**(#1608), 우리 산출물은 전부 파이프라인 자기 포맷으로 나온다(의사라벨은 코퍼스 라벨 계약대로, 적응 체크포인트는 `infer`가 무수정 로드). **제출 전 검토에서 이 두 줄을 넣을지 판단할 것.**

**🔵 #1608 상태(2026-08-30 확인, API 원문)**: open · not merged · mergeable **true** ·
`mergeable_state: unstable` · 08-28 이후 무변화 · **리뷰어/담당자/라벨 없음**.
CI는 전부 통과(`CI`/`Gate`/`analyze_fast`/`Detect changes` success, `analyze_deep` skipped);
`unstable`의 원인은 **Vercel "Authorization required to deploy."** 하나뿐으로, 외부 기여자
PR에서 나는 봇 실패라 우리 코드와 무관하고 메인테이너 머지를 막지 않는다.
**사용자 결정(08-30): 재촉하지 않고 대기.** 머지되면 문안 field 4·5 라벨을 "merged"로.

**🔭 해볼 만한 것 (가치×실현성 순)**

1. ✅ **완료(2026-08-30) — arm C의 transductive 변형 = arm D.** 사전등록 `923895d`(실행 전) → 결과: **평균 +0.0457, 14/14칸 개선, 7/7 세그 두 시드 모두, 갭의 14.3% 회수**(arm C는 9.5%). 사전등록 구간 **+5~30% 안**, "50% 안 넘는다"는 약속도 유지. 랭크 체크 **AUC 0.659 → 0.742**(arm C 0.700)로 **자기오류 고착 서명은 안 나타남**. ⚠️ **arm D − arm C = +0.0154(11/14칸 우세)는 노이즈 0.03 미만** → "transductive가 낫다"는 확정 못 함, 확정된 건 "둘 다 직접전이보다 낫고 D는 노이즈를 넘는다"까지. 상세 = docs/18 arm D 절. 원수치 `armD_pseudoT_matrix.csv`(18칸)·summary·`armD_rank_check_w01_s42.json`.
   - **이 연구가 가리키는 한 문장**: base·레시피·step 고정 시 **사람 주석 1세그 = +0.320, 최고의 라벨 없는 방법 = +0.046 → 주석은 약 7배**. 그리고 그 14%는 **주석이 아직 불가능한 스크롤이 오늘 당장 가질 수 있는 몫**이다.
   - 실무 메모: 감독 솎기(3×3에 1블록)로 패치탐색이 세그당 13분 → 7세그 합쳐 2.5분. 학습 시드당 17~18분. 감독 면적 8.8~8.9%(실제 주석 8.4%와 유사).
2. ✅ **완료(2026-08-31) — 1667 복제 + step 곡선. 그리고 이게 우리를 반증했다.** 사전등록 `cd07b16`·`5468ac5` 둘 다 실행 전. 90칸, 실패 0건. **주석 1세그 = Paris4 +0.320(82%) vs 1667 +0.104(24%)**, arm C는 전 step 노이즈 안, **arm D는 전 step 음수**. step 곡선이 "일찍 끊었다" 탈출구를 죽임(1667 FT도 2,500 정점 후 단조 하락). → **Paris4 수치 전부 스크롤 특수로 라벨링 완료**. 상세는 아래 08-31 절.
3. ✅ **완료(2026-08-30 밤) — arm D를 PHerc1447에 적용.** 기준 사전등록(`1da7685`) 후 실행, **0/3 미달**. 상세는 아래 08-30(밤) 절. 남은 것: 반복 라운드·다른 베이스·나머지 14세그는 미시도이나 "증폭할 신호가 없다"는 진단을 바꾸진 않을 것으로 판단.

**🚫 하지 않는 편이 나은 것**: 추가 PR(#1608 대기 중 분산), "절반 예산의 세그먼트 3배 편차"
규명(작고, 문안에 이미 정직하게 미해결로 남김), 결과 없는 문안 재작성.

**⚠️ 제출 전 최종 문구 검토(별도 작업으로 반드시 1회)**: Step 3 체크리스트 + 위 Core
Requirements 대조 + 링크 재확인 + 검증 스크립트 재실행. 새 실험이 들어가면 field 4/5 해시를
다시 기록할 것.

**기대치(2026-08-30 재평가)**: 7월 실측 환율은 "$20k=메싱, $2.5k=언래핑, $1k=잘 만든 도구·문서"다.
9월 제출물은 품질은 두껍지만 **범주가 같다(측정·음의 결과)** → **$1k가 최빈값, $2.5k가 현실적 상단,
0도 실재하는 가능성**. ①~③를 다 해도 $2.5k 확률이 오르는 정도지 $10k대로는 안 간다. 그쪽은
**새로 읽히는 글자**가 필요하고, 우리가 가진 유일한 문이 ①이다.

#### 2026-09-05 — 🔴 **stale 워크플로 원문 확인: 규칙이 둘이었고, 우리 PR 4건은 전부 마감 전에 죽는다**

`gh`가 생겨 `.github/workflows/pr-time-limits.yml`을 직접 읽었다. **매일 00:00 America/Los_Angeles 실행**,
`gh pr list --state open`이라 **draft도 대상**.

```bash
inactive_cutoff=$(date -u -d '14 days ago' +%s)   # updatedAt 기준
age_cutoff=$(date -u -d '28 days ago' +%s)        # createdAt 기준
```

1. **14일 무활동** → 종료 (우리가 알던 것)
2. 🔴 **개설 후 28일** → **활동과 무관하게** 종료 ← **몰랐던 것. 코멘트로 못 막는다.**
3. **`keep-open` 라벨이면 완전 면제** — 실재하는 라벨이고 설명이 *"Exempt this PR from automatic time
   limits"*. ⚠️ **우리 권한으로는 못 붙인다**(`repos/ScrollPrize/villa` 권한 = `pull:true`, `push/triage/
   maintain/admin` 전부 false). 현재 이 라벨이 붙은 열린 PR은 0건.

| PR | 개설 | 14일 | **28일 상한** | 실사망 |
|---|---|---|---|---|
| #1608 | 08-26 | 09-18 | **09-23** | 09-18 |
| #1661 | 08-31 | 09-14 | 09-28 | 09-14 |
| #1662 | 08-31 | 09-18 | 09-28 | 09-18 |
| #1663 | 08-31 | 09-16 | 09-28 | 09-16 |

🔴 **네 건 전부 28일 상한이 9/30 마감 이전이다.** "무활동 PR에 코멘트를 달아 살려둔다"는 전략은 **28일 벽
앞에서 무효**. → **주말 교체가 선택이 아니라 시한 사항이 됐다**: 09-06에 새로 열면 28일 상한이 **10-04**로
마감 이후이고, 14일 쪽만 09-19경 한 번 건드리면 제출 시점에 셋 다 열려 있다.

**#1608은 남는 문제** — main에 대체본이 없어 유지하기로 했는데 **09-23에 강제 종료된다.** 선택지 = ①그대로
두고 문안에 사실대로(추천, #1535에 이미 같은 문장을 썼다) ②9월 하순 같은 브랜치로 새 PR(=`createdAt` 리셋,
#1434→#1535 전례가 있으나 정책 회피로 읽힐 수 있음) ③#1608에서 `keep-open`을 요청.

📌 **자동종료가 제출 자격에 영향을 주는지는 여전히 미확인** — `chriski`가 08-27 Discord에서 정확히 그걸
물었고 답을 못 봤다. 다만 **제출의 산출물은 우리 저장소이고 PR은 증빙**이므로, 영향이 있더라도 치명적이지 않다.

📌 **닫힌 것(#1535)을 다시 올릴 필요는 없다(2026-09-05 판단)**: 내용은 이미 저장소(docs/12·패치·브랜치)에
있고 8월 문안이 인용한다. **이 저장소는 PR을 정책적으로 덜어내도록 설계돼 있다**(열린 PR 54건 + 28일 무조건
종료) → **미리뷰 PR의 기대값이 구조적으로 낮다.** 개수를 늘리는 것보다 **F2/F3/F4 중 하나를 머지시키는
쪽**이 낫다. #1535 재작성은 그중 하나가 움직인 뒤에 자리를 쓴다.

#### 2026-09-05 — 🔵 **Discord에 처음 들어가서, 막혀 있던 것 두 개가 한 번에 풀렸다**

서버 = `discord.gg/V4fJhvtaQn`(scrollprize.org·prizes 양쪽에 있는 공식 링크). ⚠️ **우리 `docs/06`이 7월에
이미 "메인 협업 허브, 조기공유·채택신호 확보 채널"이라고 적어놓고 석 달을 GitHub만 썼다.** 첫 열람에서
한 달 묵은 답 두 개를 찾았다.

**1. base 브랜치 질문은 한 달 전에 공개로 답이 나와 있었다.** `err`(= erdpx, 우리 #1234를 머지한 사람),
2026-08-10 #ink-detection: *"sorry about that, we're **merging the ink pipeline into main this week**"*
→ **`merge-ink-pipelines`는 방치된 게 아니라 흡수된 것**이고, 마지막 커밋이 08-14인 건 작업이 옮겨갔기
때문이다. **우리가 git 메타데이터로 3주간 추론한 게 채팅 한 줄이었다.** F2/F3/F4를 main으로 옮긴 판단은
맞았고, **#1608의 답을 기다릴 필요가 없다.**

**2. 9월 폼도 어제 답이 나왔다.** `FrankTheRope`가 09-04 22:45에 우리와 똑같은 질문(폼이 8월 것이고 닫혔다,
9월 건 언제?)을 했고 **Paul(admin)이 23:01에**: *"it's not available yet, **will be up once august prizes
are announced**"*. 그리고 09-03에 Paul: *"in a few days. **we've got almost 100 of them to review!**"*
→ **메일 불필요, 트리거 설정 불필요.** 8월 결과 발표와 함께 폼이 뜨고, 자리는 **#announcements**다.

**3. 전략적으로 큰 것 — `err`의 ink_9um 공개 글(08-10)**: 그 모델들이 *"far from optimized"*이고
***"improving them would make a great Progress Prize submission"***, 나아가 **$50,000 First Letters**의
좋은 출발점이며 *"you're still early"*라고 명시. **우리 9월 제출물이 정확히 그 모델들을 측정·진단·가격매김한
것**이다.

**4. 경쟁 밀도**: 8월 제출이 **~100건**(7월 수상 13명). 그리고 `FrankTheRope`(09-04 신규)가 **ScrollScout** —
잉크 예측의 4cm² 창을 순위매기는 CPU 툴 — 을 만드는 중이라 **우리 주석 타겟팅(docs/20)과 인접**하다.

🔴 **규칙 2개(반드시 지킬 것)**:
- **#rules, Paul 2026-07-30**: *"Please don't post **AI-generated answers in place of your own reasoning
  or participation**... The only exception is #robots"* → **Claude는 Discord 메시지 초안을 쓰지 않는다.**
  (이 규칙을 읽기 전에 초안 제안을 했다가 철회함.) 읽고 보고하는 것까지가 역할.
- 서버에 올리는 모든 것은 **CC BY-NC 4.0**으로 라이선스되고 *"경쟁자가 Grand Prize 시도에 쓸 수 있음"*이 명시돼 있다.

⚠️ **운영 함정**: Discord는 **메시지 입력창이 포커스를 쉽게 가져간다** — 검색창 클릭이 빗나가면 타이핑이
채널로 들어간다. 09-05에 실제로 그럴 뻔했고(**게시된 것은 없음, 입력창 비어 있음 확인**), 이후 **Discord에서
키보드 입력은 하지 않기로** 했다.

**못 읽고 남긴 것**: `chriski`가 08-27 #general에서 *"PR이 14일 워크플로로 자동종료되면 제출 폼에 적어도
상금 대상이 되나?"*를 물었다. 답은 확인 못 했고, 서버에서 한 번만 열어보면 된다.

#### 2026-09-05 — 🟢 **F4도 `main` 기준으로 재작성**: 캐시 정체성이 한 모듈에 모여 있다

`main`엔 **`data/patch_cache.py`** 한 모듈이 캐시 정체성을 전부 갖고 있다(mip은 `common/common.py` ·
`data/ink_dataset.py` · `data/segment.py` 3파일에 흩어짐). → 수정이 **그 파일 안에서 끝나고 `Segment`
타입은 아예 안 건드린다**. 브랜치 **`khj1222:fix/patch-cache-fingerprints-labels`**(`596e865`),
base **`main`**, 2파일 **+131 −1**, fork 푸시됨. 본문 = `submission/pr_f4_main_patch_cache.md`,
증거 = `runs/f4_main/`.

- **결함은 동일**: `load_patch_cache`가 `(dataset_idx, segment_relpath, scale, inklabels_path,
  supervision_mask_path, validation_mask_path)` = **전부 경로**로 매칭 → 다른 트리는 잡고 **제자리 재생성은 못 잡는다.**
- **수정**: 라벨 자산을 **상대 파일명 + 크기**로 지문화해 record와 조회 키에 넣음 → **기존 거부 경로가 그대로 작동**
  (새 무효화 로직 0). 청크 내용은 안 읽는다.
- **실측(실제 w00 라벨 자산 12,619파일 = 잉크 3,459 + 감독마스크 9,160)**: 지문 **22.5~32.4 ms**(5회),
  같은 걸 `Path.stat()`으로 짜면 **187.4~270.5 ms**. 차이의 전부가 **`os.scandir`가 크기를 같이 준다**는 것.
  테스트 4개 통과(저장소의 기존 round-trip 테스트 **무수정 포함**).
- ⚠️ **타이밍은 재실행마다 흔들린다**(첫 측정 23.7/200.6 → 재측 23.0/189.5) → **5회 반복 범위로 기록**하고
  커밋 메시지도 범위로 **amend**(포크 브랜치·PR 미개설이라 force-push 안전). **단일 측정치를 정확한 수치처럼 쓰지 말 것.**
- **한계 3개를 본문에 먼저 명시**: 같은 이름·같은 크기로 압축되는 다른 라벨은 구분 못 함 / 바이트 동일 복사본은
  같은 지문(의도) / **구 캐시는 지문이 없어 1회 미스 후 재빌드**(마이그레이션 없음).
- **#1661을 대체한다.**

**main 기준 재작성 완료: F2 ✅ · F3 ✅ · F4 ✅** — 각각 #1662 · #1663 · #1661을 대체한다.
브랜치 3개 전부 `origin/main` 위 커밋 1개씩이고 fork에 있다. **남은 것은 전부 사용자 몫**:
PR 3건 개설(**전부 draft** — 비-draft 3건 상한) + 각 본문의 "Why this matters to me" 작성.

⚠️ **오늘 두 번 밟은 함정**: **`cd` 뒤 상대경로로 저장소에 쓰면 딴 데 간다.** F3 때 겪고 기록해 놓고
F4에서 또 밟았다(`cd /d/vw9` 상태로 `runs/f4_main/README.md`를 썼더니 vw9 아래로 감). **긴 체인에서
저장소에 쓸 땐 무조건 절대경로.**

#### 2026-09-05 — 🟢 **F2도 `main` 기준으로 재작성**: 첫 forward를 지킨다

`main`에선 컴파일 정책이 **`inference/inference_runtime.py::maybe_compile_model`**에 공용으로 있고
**추론 명령 두 개**(`infer.py`, `infer_full3d_tifxyz.py`)가 `prepare_model_for_inference`로 공유한다
(mip에선 `infer.py` 인라인). 브랜치 **`khj1222:fix/eager-fallback-at-first-forward`**(`3365213`),
base **`main`**, 2파일 **+121 −5**, fork 푸시됨. 본문 = `submission/pr_f2_main_eager_fallback.md`,
증거 = `runs/f2_main/`.

- 🔑 **실측이 결론이다** — `torch.compile`은 **예외 없이 반환**하고 첫 forward에서 터진다:
  **CUDA `Cannot find a working triton installation`**, **CPU `Compiler: cl is not found.`**
  → 기존 `except`는 잡으려던 실패를 **구조적으로 못 본다**. 수정 후 두 경로 모두 **양쪽 forward가
  eager와 정확히 일치**(allclose 1e-6), 정상 백엔드는 3/3 컴파일 경로·경고 0, **저장소의 기존
  컴파일 테스트는 무수정 통과**. 테스트 3개 추가(총 4 passed).
- ⚠️ **우리 기록 정정**: CUDA 실패는 **`TritonMissing`이라는 예외 클래스가 아니라** Triton을 언급하는
  `RuntimeError`다. 이전 메모(docs/08 계열 서술 포함)가 클래스명처럼 적어 왔으니 인용 시 주의.
  코드 주석에서도 클래스명을 빼고 조건으로 서술했다.
- **일부러 안 한 것 2가지(본문에 명시)**: ①**합성 warmup 텐서 안 씀** — 실패를 기존 `try` 안으로
  옮길 수 있지만 shape을 찍어야 하고 잘못 찍으면 **정상 리눅스에서 컴파일이 조용히 꺼진다**
  ②**`models/training/train.py::_maybe_compile_model`은 안 건드림** — 같은 모양이지만 크래시는
  추론에서 관측했고 검증도 추론에서 했다.
- `maybe_compile_model`의 bool 의미가 "컴파일 **성공**"에서 "컴파일 **설정됨**"으로 바뀐다(백엔드가
  나중에 도니 원래 그 뜻일 수밖에 없다). docstring에 명시. 호출자 2곳은 무변경.
- **#1662를 대체한다.** 본문에 명시. 🔴 **PR은 draft로 열어야 한다**(비-draft 3건 상한).

⚠️ **함정(오늘 밟음): 워크트리에서 브랜치를 만든 뒤 그대로 다음 수정을 커밋하면 앞 수정 위에 얹힌다.**
F2를 F3 브랜치 위에 커밋해 버렸고, `git checkout -b <새브랜치> origin/main` + `cherry-pick` +
`git branch -f <앞브랜치> <원래sha>`로 분리했다. → **수정마다 반드시 `origin/main`에서 브랜치를 딸 것.**
현재 두 브랜치는 각각 `origin/main` 위 커밋 **1개**씩이고 둘 다 fork에 있다.

**main 기준 재작성 현황**: F3 ✅ · F2 ✅ · F4는 미작성(`data/segment.py`가 main에도 있으나 204 vs 253줄로
갈려 재작성 필요). 남은 것은 **사용자의 PR 개설 2건(둘 다 draft)**과 #1608 답변.

#### 2026-09-05 — 🟢 **F3를 `main` 기준으로 재작성**: 스크립트 한 개가 아니라 공용 함수 하나

주말 안건 §2.2 실행. `merge-ink-pipelines`엔 그 rename이 `prepare_9um_isotropic_input` 안에 인라인이지만,
**`main`엔 `vesuvius/src/vesuvius/ink_detection/preprocessing/staged_write.py`가 있고 `publish_staged_output`을
네 개가 import**한다(`clean_labels` · `composite_from_zarr` · `merge_predictions` · `prepare_9um_isotropic_input`).
→ **한 함수로 툴 4개**, diff는 더 작다.

- 브랜치 **`khj1222:fix/retry-staged-publish-on-windows`**(`8ce9725`, fork 푸시됨), base **`main`**(`5479453`), 2파일 **+205 −3**.
  워크트리 **`D:/vw9`**(sparse `vesuvius`, 21MB). PR 본문 = `submission/pr_f3_main_staged_write.md`, 증거 = `runs/f3_main/`.
- **설계**: 재시도를 **`winerror ∈ {5, 32}`로 게이트** → 그 속성이 Windows에만 있으므로 **POSIX 동작은 완전 불변**.
  끝내 안 풀리면 `add_note`로 "staging은 완성, 재계산 불필요 + 두 경로"를 붙이고 **원 예외를 그대로** 올린다
  (라이브러리라 기존 브랜치의 `SystemExit`은 부적절 — 호출자 3개가 실패 시 `discard_staged_output`을 부르는 구조).
  `attempts`/`retry_delay`는 keyword-only 기본값이라 **기존 호출부 4곳 무변경**.
- **실측(목이 아니라 진짜 Windows 실패)**: 안의 파일 열림 → **WinError 5**, cwd가 트리 안 → **WinError 32**, 둘 다
  게이트 진입. 끝내 안 풀리면 **staging 온전 · 출력 미생성**. 핸들 닫히면 **0.0초 발행**. 테스트 8개 전부 통과
  (실제 핸들을 다른 스레드가 0.4초 뒤 놓는 Windows 전용 케이스 포함).
- ⚠️ **기존 브랜치의 `del target, group`(핸들 선해제)은 뺐다** — **원인으로 측정된 적이 없다**. 측정된 문제의 수정에
  측정 안 된 변경을 끼우는 게 정확히 #1434가 지적받은 지점이라, 본문에도 "일부러 뺐다"로 명시.
- **#1663을 대체한다.** 본문에 그렇게 쓰고 "이쪽을 받으면 #1663을 닫겠다 / 저쪽을 원하면 이걸 닫으라"까지 명시.
  #1608의 base 질의에 대해 **"답이 main일 경우"의 답**이기도 하다.
- 🔴 **PR 개설은 사용자 몫이고, non-draft 3건 상한이라 draft로 열어야 한다.**

⚠️ **새 함정 3종**:
1. **`import vesuvius`가 우리 환경에서 안 된다** — 패키지 `__init__`이 `data`/`install`을 끌고 오고 그게 **`nrrd`**를
   요구한다(sparse checkout 문제가 아님). 해결 = **부모 패키지 3개를 빈 모듈로 스텁하고 대상 모듈만 파일 경로로 로드**하는
   conftest. **커밋할 테스트 파일 자체는 손대지 않고** import 경로만 스텁 → `runs/f3_main/pytest_conftest_stub.py`.
2. **로컬 기본 파이썬 3.10으론 `add_note` 경로를 못 돌린다**(3.11+). 저장소는 `requires-python = ">=3.14,<3.15"`.
   → **`uv run --python 3.12 --with pytest --no-project`**로 검증. ⚠️ `--python 3.14`는 uv가
   *"Missing expected target directory for Python minor version link"*로 **실패**한다.
3. **`cd`한 뒤 상대경로로 저장소에 쓰면 깨진다** — 스크래치패드로 `cd`한 상태에서 `runs/f3_main/`에 복사하려다 실패.
   길게 이어붙인 명령에서는 **저장소 경로를 절대경로로** 쓸 것.

#### 2026-09-05 — ✅ **field 5 전체 통독 = Step 3의 0번 빚 해소** (v18·v19, 그리고 Status 문단 재작성)

08-31 트림 이후 아무도 한 덩어리로 안 읽었던 field 5를 통독. **구조는 멀쩡했다** — 도입부가 약속한 네 가지
(측정/진단/가격/두 번째 스크롤)가 각각 ¶4·¶6·¶7·¶8에 그대로 있고 순서가 뒤집힌 곳 없음. 대신 **나중에 들어온
결과가 카운트를 앞질러 있었다.**

**v18 — 수치 4건 (아티팩트 재산출로 발견)**
- field 4 `1,720 scored cells` → **1,778**, `33 CSV/JSON` → **40**. 차이 58 = **blurexp 16 + annotarget 42**,
  즉 v12에서 1,612→1,720으로 고친 뒤 도착한 두 실험. (재산출법 = `runs/ink9um_scorecard`의 csv 행 합계[헤더 제외] + csv/json 파일 수)
- field 5 마지막 줄 `docs/14–18` → **`docs/14–18 and docs/20–23`**. 본문이 ¶10에서 docs/20을 인용하고 ¶5가
  docs/21~23에 기대는데 범위가 잘라먹고 있었음. ⚠️ **`docs/19`는 존재하지 않으므로 `docs/14–23`도 틀림.**
- field 5 `100 committed evidence files`가 **어떤 정의로도 재현 안 됨**(runs/ 전체 135, csv/json/jsonl 103,
  9월 디렉터리만 123) → **135 files under `runs/`**로 교체.

**v19 — 표기·구조**
- `--` 3개 → em dash. 그 3개가 **전부 ¶5·¶10**(가장 늦게 붙인 두 문단)에 몰려 있었다 = 늦은 편집의 지문.
- 전 문서 유일한 **전부 대문자** 한 구절을 소문자로. 판단 근거: 이 문안의 신뢰는 자기 결과를 스스로 반증하는
  **고른 톤**에서 오는데 한 곳만 외치면 판매문구로 읽히고, 바로 앞 `+0.32 vs +0.046`이 이미 강조를 하고 있다.
- **¶13 분할**(1,532자에 결과 3개 = TENT / 자가학습+7배 / 1447+1667) → "seven times" 뒤에서 끊음. 문단 15→16.
- **중복 결론 삭제**: ¶13 끝의 *"what survives is the ordering and the saturation point…"*는 ¶8이 이미
  *"the saturation point replicates, the magnitude does not"*로 한 말.
- ¶14 `Both have survived outside hands` → **`Numbers and apparatus have both survived…`**(선행사가 두 문장 뒤였음).
- 편집으로 줄바꿈이 깨져(107자/33자) 두 문단만 재감쌈 — **감싸기 전후 단어 단위 동일 확인 후** 반영.

**새 해시(본문+개행 1개 규약)** — ⚠️ field 4는 **길이가 안 변했지만 해시는 바뀐다**(`1,720`→`1,778`, `33`→`40`이 같은 글자수):
- field 4 — 2,015자 `ff5eb3d3ec8bea2b4fbfc32ced261f4608f05baa5727b76198dfd4752a6f4c9a`
- field 5 — **11,422자**(−81) `554d07d18594759925b0d6bafc16f3f5d26bbb05b6ccb60720e33bf936d58977`

검증: 헤더 글자수·해시블록·실제 블록 **3자 일치**, **아티팩트 기반 수치 37개 전건 잔존**, 주장·수치·인용 변경 0.

**Status 문단 재작성 → v19**: 7번째 줄이 아직 `DRAFT v12`였고 그날 들어온 것들의 나열이라 이후 일곱 개정을
반영 못 하고 있었다. ①두 칸은 확정이고 해시가 아래 있다 ②뒷받침 작업은 끝났고 대기 중인 런이 없다
③v18·v19가 0번 빚을 해소했고 주장은 안 건드렸다 ④남은 건 폼 미발급과 당일 체크리스트, 로 재작성.
사전등록 커밋 해시는 docs로 넘기고 본문에서 뺌. **Status는 제출 블록 밖이라 해시 불변.**

⚠️ **재발 방지**: **field 4의 두 카운트는 실험을 커밋할 때마다 낡는다.** 새 매트릭스를 `runs/ink9um_scorecard`에
넣으면 그 자리에서 두 수를 재산출할 것. 이번엔 08-31 이후 두 실험이 들어오는 동안 아무도 안 세서 어긋났다.

#### 2026-09-04 — 🔴 **PR이 봇에 죽는다**: #1535 자동 종료, base 브랜치는 3주째 정지, #1471은 종료 검토

오늘 스윕에서 두 개가 움직였고 **둘 다 계획의 전제를 바꾼다.**

**1. #1535는 사람이 아니라 봇이 닫았다(2026-09-03T07:18Z, `closed_by: null`).** 코멘트 원문 =
*"Closed automatically under the repository PR time limits because this PR has had no activity
for **14 days**."* 거절이 아니라 **우리가 몰랐던 저장소 정책**이다. 마지막 활동 08-19 → 15일 뒤 종료.

- 🔴 **우리 열린 PR 4건 전부가 시한부**: #1608(08-28 활동) **~09-11** · #1661·#1662(08-31) ~09-14 ·
  #1663(09-02) ~09-16. **전부 9/30 마감 전에 죽는다** → 08-30의 "재촉 않고 대기" 결정은 지금 그대로
  두면 제출 시점에 PR 4건이 전부 닫혀 있게 된다는 뜻. 코멘트 한 줄이면 `updated_at`이 갱신돼 시계가
  리셋된다(단, 봇이 `updated_at` 기준인지는 미검증 — 그렇게 보일 뿐).
- ⚠️ **#1434는 닫힌 뒤 reopen이 안 됐다** → 죽으면 새 PR을 열어야 하고, 그건 다시 3건 상한에 걸린다.
- 🟢 **슬롯 1개 확보**: 열린 non-draft가 #1608·#1661 둘로 줄어 **#1662나 #1663 중 하나를 ready로 올릴 수 있다**(웹, 사용자 몫).

**2. base 브랜치가 죽어 있다.** `origin/merge-ink-pipelines` tip = **`3ea17f54a`(2026-08-14) = 우리
#1234**. **3주간 커밋 0건**인데 `main`은 매일 커밋 중(tip `5479453a7`, 08-30). 우리 PR 4건이 그 정지한
브랜치를 base로 삼고 있다 → 리뷰어 배정 0의 절반은 이걸로 설명된다.

- 🔑 **그리고 F2·F3·F4는 전부 `main`에도 적용되는데, 거기선 더 작은 패치로 더 많은 걸 고친다**:
  - **F3** → main엔 `ink_detection/preprocessing/staged_write.py`가 이미 있고 `publish_staged_output()`이
    우리가 고친 그 `.replace()`를 그대로 쓴다. **호출자 4개**(`clean_labels` `composite_from_zarr`
    `merge_predictions` `prepare_9um_isotropic_input`). merge-ink-pipelines엔 **이 모듈이 아예 없다**.
    → 한 함수 고치면 툴 4개가 동시에 낫는다(우리 #1663은 스크립트 인라인 패치).
  - **F2** → main `inference/inference_runtime.py::maybe_compile_model`이 **똑같이 `compile_fn(...)`만
    try로 감싼다** = 같은 도달불가 `except`. 공용으로 빠져 있어 패치가 더 작다.
  - **F4** → `data/segment.py`는 main에도 있으나 204 vs 253줄로 갈려 리베이스가 아니라 재작성.
  - 파일 격차 실측: `segment.py` 204/253, `infer.py` 1400/2019, `prepare_*.py` **170/113**(main이 더 큼),
    `create_label_zarrs.py` 585/840.
- → **물어볼 것은 "리뷰해 달라"가 아니라 "base를 main으로 옮길까"**이고, 그 질문 자체가 시계를 리셋한다.

**3. [#1471](https://github.com/ScrollPrize/villa/pull/1471)에 hendrikschilling이 종료 의향(09-04 09:44Z)** —
*"…I'm not sure we should add much complexity vs just converting to tiled tiffs beforehand. So without
some good counter arguments I tend to close this."* + LLM 리뷰 4건 첨부. **그 P1 2건이 정확히 우리가
08-31에 이미 게시한 것**이다(P1#2 = 1행 스트립 크래시, P1#1 = 블록별 재디코드).

- 우리가 이미 측정해 둔 반론: 리뷰가 요구하는 remedy(strip-major 1회 디코드)를 적용하면 **195.84s →
  104.38s**이고 이건 **같은 코드가 tiled 사본을 읽는 143.27s보다 빠르다**(RSS 0.881 vs 0.884 GiB).
  즉 P1#1은 설계 비용이 아니라 **블록 모양 선택**.
- ⚠️ **우리에게 불리한 것도 초안에 넣었다**: 우리 테스트는 `rowsperstrip=1024`였고 리뷰가 말하는
  **단일 전체-이미지 스트립 최악 케이스는 안 재봤다**(그쪽이 더 나쁘다). P2#4(multipage)는
  **jaideepsaipadhi의 발견**이고 우리 머지 사본에도 있다.
- 25 GiB 수치 검증: 65 × 16125×25690 uint8 = **25.1 GiB** = #1231이 터진 그 할당.

**4. 9월 폼 아직 미발급** — `scrollprize.org/prizes` 원문이 마감 4일 지난 지금도 **"The next deadline is
11:59pm Pacific, August 31st, 2026!"**이고 링크된 폼도 8월 것 그대로. 등급 6단계·복수 제출 허용·Core
Requirements 3항목 무변화.

**5. 초안 5건 작성 완료(전부 미게시, 게시는 사용자)** — 수치는 전건 아티팩트 재산출 검증, 링크 200,
플레이스홀더 0, 머리말은 `---` 아래만 붙여넣기:

| 초안 | 대상 | 언제 |
|---|---|---|
| `pr1471_reply_hendrikschilling.md` | #1471 (남의 PR, 결정은 저쪽) | **오늘** — 지금 판단 중 |
| `pr1608_base_branch_question.md` | #1608 base 질의 | **오늘** — 09-11에 죽음 |
| `pr1661_f4_followup.md` | #1661 지문 강도 설계 질문 | ~09-10 |
| `pr1662_f2_followup.md` | #1662 warmup vs first-forward 질문 | ~09-10 |
| `pr1663_f3_followup.md` | #1663 **main의 staged_write로 옮기겠다는 제안** | ~09-10 |

⚠️ **4건을 하루에 몰아 달면 압박으로 읽힌다** → #1608·#1471만 오늘, 나머지 셋은 09-10~09-12.

✅ **게시·승격 완료(2026-09-04 14:57~14:59Z, 사용자 직접)** — [#1471](https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5542304769)(4,680자) ·
[#1608](https://github.com/ScrollPrize/villa/pull/1608#issuecomment-5542316614)(2,567자) 게시, 게시본이 로컬 초안과 **공백 정규화 기준 완전 일치**
(raw 차이는 CRLF뿐), **머리말 유출 0**. 그리고 **#1662를 ready로 승격**(draft: False).

**시계 갱신(2026-09-05 기준)**: #1608 **~09-18**(13일) · #1662 **~09-18**(13일) · **#1661 ~09-14(9일, 가장 급함)** ·
#1663 ~09-16(11일, draft). 코멘트도 ready 승격도 `updated_at`을 갱신해 시계를 리셋한다는 게 실측으로 확인됨.

🔴 **열린 non-draft가 다시 3건(상한)** = #1608·#1661·#1662 → **#1663은 지금 ready로 못 올린다.** 하나가 머지/종료돼야 자리가 난다.

📌 **남은 초안 3건은 묵혀 둘 것**: #1608의 base 질의에 답이 오면 나머지 셋의 내용이 바뀐다(main으로 옮길지 여기 둘지).
특히 #1663 초안은 "main의 `staged_write.py`로 옮기겠다"는 **사실상 같은 질문**이라 지금 내면 이중 질문이 된다.
다만 **#1661이 09-14에 죽으므로 답이 없어도 ~09-11에는 게시**할 것. 순서 = #1661(09-10~11) → #1663(~09-13) → #1662(여유).

**6. 문안 갱신(해시 불변)** — #1535 라벨 3곳을 "봇이 09-03에 무리뷰로 자동 종료"로, Step 3에 **"이
저장소는 14일 무활동 PR을 자동으로 닫는다, 당일 상태를 기억이 아니라 API로 확인"** 경고 추가,
08-31에 게시된 #1471 회신이 "게시 대기"로 남아 있던 것 정정. **세 곳 모두 field 4/5 밖**이라 재검증에서
field 4 = 2,015자 `39a669d5…`, field 5 = 11,475자 `ea82e595…`로 **기록값과 동일** 확인.

⚠️ **함정(오늘 내가 밟음)**: 우리 `runs/pr1471_striped_check/README.md`의 **"18/18"은 "비교 가능한 출력"
이지 "크래시에서 구제된 변형"이 아니다**(그건 **16**: head 크래시 25 − 양쪽 공통 실패 9). 초안에 처음
"18 of 18 previously-crashing"이라 썼다가 아티팩트 재산출에서 잡았다. **두 수를 섞지 말 것.**

⚠️ **`runs/`가 워킹트리에서 사라졌다** — 사용자가 **Z: 드라이브로 의도적으로 아카이브**한 것(Z:는 지금
미마운트). 135개가 tracked deletion으로 떠 있고 **origin/main엔 그대로**라 제출 링크는 전부 무사.
**복원 불필요**: `git show HEAD:runs/...`로 읽으면 된다. 🔴 **절대 `git commit -a` / `git add -A` 금지** —
그 삭제가 커밋되면 8월(제출 완료)·9월 문안의 증거 링크가 GitHub에서 통째로 사라진다. **커밋은 항상 경로 명시.**

#### 2026-09-03 — 두 번째 업스트림 스윕: **09-01 이후 새로운 것 0건**, 그리고 스윕의 사각지대 1건

72시간 창(08-30 15:33Z~)으로 13스레드 전수. **남이 단 것은 Vercel 봇 3건뿐**이고 셋 다 08-31에 연 PR에 자동으로 붙은 것이라 09-01 스윕에서 이미 본 것 = **정말로 아무것도 안 움직였다.**

- 무반응 일수: **#1535 15일**(08-19 이후) · #1608 6일(08-28 이후) · #1661·#1662·#1663은 개설 이래 봇 코멘트만. **우리 PR 5건 전부 리뷰어 배정 0**(#1471·#1580엔 `jrudolph`·`bruniss`가 붙어 있는 것과 대조).
- 우리 이슈 3건은 **전부 우리 코멘트가 마지막이고 답이 없다** — #1231(F5 질의), #1611(우리 이슈를 닫자는 제안), #192(stantheman0128에게 보낸 회신). 셋 다 08-31~09-01 게시라 아직 이르다.
- ⚠️ **스윕 도구의 사각지대**: #1547의 `updated_at`이 08-31 07:58로 튀었는데 스윕은 아무것도 못 잡았다. 확인해 보니 nerln이 **08-29 코멘트를 제자리 수정**한 것이고(본인이 코멘트 안에서 "세 번째 버전을 밑에 쌓지 않고 제자리에서 고친다"고 명시), 스윕은 `created_at` 기준이라 **수정된 코멘트를 원리적으로 못 본다**. 내용은 우리 코퍼스와 무관(w045/w046 미포함)이라 대응할 게 없지만, 규칙으로: **`updated_at`이 컷오프 이후인데 새 코멘트가 0이면 그 스레드는 직접 열어볼 것.**
  → ✅ **2026-09-05에 도구를 고쳐 이 사각지대를 닫았다** — 수정된 코멘트를 `comment EDITED (posted …)`로 보고한다. **그 #1547 건으로 회귀 검증 통과.** 이제 위의 수동 규칙은 불필요.
- ⚠️ **API 예산 실측**: 스윕 1회 = 30~40콜, 끝나고 잔여 **20/60**. 여기에 개별 스레드 확인 2~3건을 더하면 한도가 바닥난다 → **시간당 스윕 1회가 상한.**
  → ✅ **2026-09-05 해소**: 사용자가 `gh` CLI를 설치·로그인(`khj1222`, 스코프 `repo`/`workflow`)했고 스윕이 **`gh`를 우선 사용**하도록 고쳐졌다. 예산이 **60 → 5,000/시간**이라 이 상한은 사라졌다. `gh`가 없으면 기존 curl 경로로 자동 폴백(헤더에 어느 쪽인지와 잔여 예산을 찍는다). ⚠️ **Windows에서 gh는 PATH에 없다** — 도구가 `C:\Program Files\GitHub CLI\gh.exe`를 직접 찾고, 셸에서 쓸 땐 `export PATH="$PATH:/c/Program Files/GitHub CLI"`.

**부수 확인(같은 패스)**: `scrollprize.org/prizes`가 마감 3일이 지난 지금도 **8/31 문구 그대로**이고, 링크된 폼도 여전히 8월 것(title = `August 2026 Progress Prizes`, **아직 응답 수신 중**). 등급 6단계·"월 복수 제출 허용"·Core Requirements 3항목 전부 변경 없음. → **9월 폼은 아직 발급 전, 대기.**

**오늘 상태**: 저장소 미커밋 0·원격 동기, 9월 문안 **v17 동결**(빚 = Step 3의 0번, field 5 전체 통독 1회), 마감 9/30까지 약 27일. 사용자가 **#1663 체크박스를 켰다**(API 원문 `- [x]` 확인, `updated_at` 2026-09-02T15:37:54Z) → **우리 쪽에서 열려 있는 작업은 없고, 남은 건 전부 메인테이너 반응 대기.**

#### 2026-08-31 (오전~) — 계획 실행 개시: F2·F3 푸시 + S1 사전등록·기동

**F2 (Windows `infer` 크래시)**: `torch.compile()`은 예외 없이 반환되고 `TritonMissing`은 **첫 forward**에서 나온다 → `maybe_compile_model`의 `except`는 도달 불가 죽은 코드. 재현 완료(`runs/f2_compile_fallback/repro_lazy_compile.json`). 첫 forward만 감싸는 래퍼로 수정: **전 두 forward 모두 크래시 → 후 경고 후 eager 결과 반환(값 일치)**, 정상 백엔드는 3/3 컴파일 경로·경고 0, 테스트 19통과. ⚠️ 합성 워밍업 텐서는 **일부러 안 씀**(shape 오판 시 리눅스에서도 컴파일이 꺼짐). 브랜치 `fix/compile-fallback-at-first-forward`(`66c7e19`), 본문 `submission/pr_f2_compile_fallback.md`.

**F3 (prepare 스크립트 rename 사망)**: 조건별 실측 — 아무것도 안 잡음 rename 성공 / **안의 파일 1개 열림 → WinError 5**(우리 실패와 동일) / scandir 미완 성공 / cwd 안쪽 → WinError 32. 수정 후 0.001초 발행, 0.8초 뒤 핸들 해제 시 재시도로 1.5초 발행, 끝내 안 풀리면 **"재계산 필요 없음"을 말하는 메시지**로 종료·staging 보존. 합성 84×300×260 end-to-end 바이트 일치. 브랜치 `fix/publish-staged-zarr-on-windows`(`df799c4`), 본문 `submission/pr_f3_publish_staged_zarr.md`.
⚠️ **둘 다 사용자 몫 2가지에 막힘**: PR 생성(웹) + villa CONTRIBUTING이 요구하는 **사람이 쓴 코멘터리**(#1434가 이걸로 닫혔음). 각 본문 하단 "Why this matters to me" 자리 비워 둠.

**S1 = `docs/20_annotation_targeting.md` 사전등록(09:16:25 커밋 `33d8be8`, 예측 읽기 전)** → 6런 기동(09:28, ~7h).
- ⚠️ **설계가 바뀐 이유**: 기존 라벨예산 기준선은 **무작위가 아니라 면적·밀도 정합 전수탐색**이었다. 그래서 질문을 "어느 규칙이 이기나"에서 **"어디를 주석하느냐가 애초에 얼마나 중요한가"**(= 모든 획득 규칙의 상한)로 바꿈.
- 20.7% 예산 ±3%p 안의 **28개 조합** 중 4 arm: `density`(발표본, 재사용) · `disagree-max` · `disagree-min` · `random`(시드 0). 순위는 **라벨 없이** 베이스 두 시드의 불일치로 매김 — 예측이 이미 디스크에 있어 **선택에 GPU 0**.
- **학습 전에 기록해 둔 것 2가지**: 그룹 간 불일치 폭이 0.0791~0.1091로 좁아 **순위가 쥘 신호가 약함**; ±3%p 때문에 실제 예산이 19.20~23.49%로 갈려 **`disagree-max`가 불리·`random`이 유리**. 어느 방향으로 나오든 읽는 법을 문서에 미리 적음.
- ✅ **채점 경로를 밤새 돌리기 전에 검증**: 발표된 라벨예산 셀을 재채점해 **필드 단위 완전 일치**(F1 0.7731 @122, P 0.7927, R 0.7545, 8,268,843/2,163,941). 두 매트릭스는 셀 대 셀로 비교 가능.
- 신규 도구: `tools/score_annotation_candidates.py`(라벨 없는 후보 순위), `tools/run_annotation_targeting.py`(재시도 드라이버), `make_label_budget.py`에 `--groups/--name` 추가(기존 체인은 **동일 재현** 확인).

#### 2026-08-31 (밤) — PR 3건 개설, 그리고 **GitHub 열린 PR 개수 제한을 처음 밟음**

| PR | | 상태 |
|---|---|---|
| [#1661](https://github.com/ScrollPrize/villa/pull/1661) | F4 패치 캐시 | ✅ ready, 체크박스 ✓, 본문 = 초안(체크박스 한 글자 차이) |
| [#1662](https://github.com/ScrollPrize/villa/pull/1662) | F2 compile 폴백 | 🟡 **draft로 묶임**, 체크박스 ✓ |
| [#1663](https://github.com/ScrollPrize/villa/pull/1663) | F3 staged 발행 | 🟡 **draft로 묶임**, ✅ 체크박스 ✓(2026-09-03 사용자) |

- 셋 다 base `merge-ink-pipelines`, mergeable, diff가 우리 커밋과 일치(+64 / +43−1 / +38−2), **HTML 머리말 유출 0**.
- "Why this matters to me"는 **사용자가 직접 작성**(F4는 한글로 써서 내가 번역만, F2·F3은 영어로 직접). ⚠️ **이 문단은 내가 대신 쓰지 않는다** — CONTRIBUTING이 요구하는 건 사람이 쓴 코멘터리이고 그게 LLM PR을 거르는 장치라, 대신 쓰면 형식만 통과시키는 것. #1434가 이 지점에서 닫혔다.
- 🔴 **새 제약(계획의 전제를 깸): GitHub이 작성자당 열린 PR 수를 제한한다.** non-draft 3건(#1535·#1608·#1661)에서 막혀 draft 2건을 ready로 못 바꾼다("Author has reached the open pull request limit", ready 버튼 비활성). **$5k 패턴은 "머지된 수정 묶음"인데 동시 3건 제한이면 묶음을 한 번에 못 낸다** — 한 건이 머지/닫혀야 다음이 들어간다.
- **사용자 결정(A안): 그냥 draft로 둔다.** #1535를 닫아 자리를 비우는 안은 기각 — 9월 문안이 #1535를 참조하고, #1434에서 **닫은 PR은 reopen이 안 됐던** 전례가 있다. #1608은 Bullo27 리뷰까지 끝나 CI 초록이라 머지에 가장 가깝고, 그게 움직이면 자리가 난다.
- ~~남은 사용자 작업: #1663의 체크박스 켜기~~ → ✅ **2026-09-03 완료**(API 원문에서 `- [x]` 확인). 이로써 PR 3건 전부 체크박스 요건 충족이고, **남은 건 우리 쪽이 아니라 메인테이너 쪽**이다.

#### 2026-08-31 (밤) — ✅ **코멘트 3건 게시 완료(사용자 직접), 게시본 = 초안 일치**

12:54~12:55 UTC 게시. **머리말(HTML 주석) 유출 0** — #1580·#1582 때 raw에 남았던 문제 재발 없음. 본문도 공백 정규화 기준 초안과 일치 확인(`scratchpad/compare_posted3.py`).

| 스레드 | 게시본 | 내용 |
|---|---|---|
| [#1471](https://github.com/ScrollPrize/villa/pull/1471#issuecomment-5478665794) | 11,145자 | 저쪽 요청(08-27)대로 우리 하네스로 odd-extent 검증 → **42/42 동일 + 1행 스트립 크래시 발견·수정 검증**, 피라미드 read-back 트레이드 실측 |
| [#1611](https://github.com/ScrollPrize/villa/issues/1611#issuecomment-5478672201) | 3,963자 | 현재 빌드에서 **정지 재현 안 됨(3/3 완주)** → **우리 이슈를 닫자고 우리가 제안** |
| [#1231](https://github.com/ScrollPrize/villa/issues/1231#issuecomment-5478677042) | 3,428자 | 평가 진입점을 원하는지 **만들기 전에 질의**(F5) |

**남은 사용자 몫 = PR 3건 개설**(F2 `66c7e19` · F3 `df799c4` · F4 `b3288a5`, 전부 fork에 푸시됨). base는 **`merge-ink-pipelines`**, 연 뒤 본문 덮어쓰기, 각 본문 하단 "Why this matters to me"는 사람이 작성(CONTRIBUTING 요구, #1434가 이걸로 닫힘).

#### 2026-09-01 — ✅ #192 회신 게시(사용자 직접) — 일주일 늦은 답장

- 스윕에서 발견: stantheman0128이 **08-25에 채점 결과를 올렸는데 우리 마지막 코멘트는 08-15**였다. **우리가 부탁해서 남이 해준 작업이고 그 수치를 8월 제출문에 실었으면서 스레드에는 7일째 무응답.** 초안 = `submission/issue192_reply_stantheman_scoring.md`, 늦은 것부터 인정하고 시작.
- 게시본 확인(사용자가 붙여준 렌더링 페이지 기준, API는 한도 소진 상태였음): 머리말 유출 없음, 문단 5개·특징 문구 전건 일치, **정정본이 반영됨**("September" → **"August" submission").
- 내용: 이 채점이 **사전등록한 두 분기 중 "기하는 멀쩡한데도 v4가 진다"** 쪽에 떨어져 우리 음의 결과에서 *"추정기가 헤맸을 뿐"* 탈출구가 사라졌다는 것. 그리고 **우리에게 불리한 절반도 인용**(인접 셀 |ΔD|가 무작위 쌍과 같아 "매끄러운 시트"를 지지하지 않음), region 15 한정·기하일 뿐 잉크 아님·pmh47 반론 유효를 그대로 승인.
- ⚠️ **API 한도 함정**: 인증 없는 GitHub API는 **시간당 60회**인데 13스레드 스윕 한 번이 30~40회를 쓴다. 오늘 스윕+검증으로 소진돼 게시 확인을 못 했다. **이슈 페이지 HTML은 클라이언트 렌더링이라 `curl`로 코멘트 본문을 못 읽는다**(기존 작성자명조차 안 잡힘) → 대체 확인 수단이 아님. **스윕은 하루 1~2회로 아껴 쓸 것.**
- 📌 **주말 논의 재료 하나 추가**: 저장소에 **열린 이슈 75건·PR 54건**. 우리 PR 5건이 그 안에서 경쟁 중이고, #1535 13일·#1608 4일 무반응의 절반은 이 부하로 설명된다. "재촉할지 기다릴지"를 이 맥락에서 판단할 것.

#### 2026-09-01 — 업스트림 스윕 도구 + 첫 스윕(사람 반응 0)

**`tools/upstream_sweep.py`** — 우리가 관여한 13개 스레드(우리 PR 5 · 우리 이슈 3 · 남의 스레드 5)를 한 번에 훑어 상태와 **컷오프 이후 남이 단 코멘트·리뷰**만 뽑는다. 인증 불필요. `python tools/upstream_sweep.py --hours 24`.

**첫 스윕(08-30 이후) 결과: 사람 반응 0.** 새로 잡힌 4건은 Vercel 봇 3건(오늘 연 PR)과 이미 답한 Bullo27의 08-30 #1582 코멘트뿐.

- 우리 PR 5건 **전부 CI 초록**(5개 체크 통과), 실패는 **Vercel 배포 권한 하나뿐**으로 외부 기여자 PR에서 나는 봇 실패라 머지를 막지 않음.
- #1661 ready · #1662/#1663 draft(작성자당 열린 PR 상한) · #1608은 08-28 이후 무변화 · #1535는 08-19 이후 무변화(**13일**).
- #1471·#1580에는 리뷰어 `jrudolph`·`bruniss`가 배정돼 있으나(08-24부터) 우리 PR들에는 **리뷰어 배정 0**.
- 📌 **주말 전까지 간간히 이 스윕을 돌릴 것**(사용자 요청). 새 반응이 있으면 답할지 판단하고, 없으면 한 줄만 보고.

#### 2026-09-01 — 📌 **주말에 사용자와 함께 전체 리뷰 예정**

오늘까지의 것을 문서·메모리에 전부 반영하고 멈춤. 주말 논의 때 꺼낼 것들:

1. **9월 문안 통독**(Step 3의 0번 빚) — 하루에 다섯 군데를 고쳤고 한 덩어리로 읽은 사람이 없음. 순서·중복만 보면 됨. → ✅ **완료(2026-09-05, v18·v19)**
2. **PR 3건의 처리** — #1661만 ready이고 #1662·#1663은 **GitHub 작성자당 열린 PR 제한**에 막혀 draft(체크박스는 09-03에 전부 충족). #1608이 움직이면 자리가 남. 재촉할지, 기다릴지, #1535를 정리할지.
3. **남은 30일을 어디에 쓸지** — 마찰 6건은 우리 쪽에서 다 끝났고(F1~F6), 격차 연구는 4연속 정지로 닫혔음. 새 실험을 열지, 채택 축(문서·도구 패키징)에 붙을지, 아니면 제출 준비만 할지.
4. **기대치 재조정** — $5k 패턴은 "머지된 수정 묶음"인데 동시 3건 제한이 그 형태를 막는다는 걸 오늘 알게 됨. 계획 4절의 전제가 바뀜.

**오늘 상태**: 저장소 미커밋 0·원격 동기, 문안 v17(field 4 `2,015자` / field 5 `11,475자`, 해시 기록), README 섹션 11·12 추가 + 71% 정정, 메모리 갱신 완료.

#### 2026-09-01 — 9월 문안 v15~v17: 오늘 결과 3건 반영 + 트림 2회, **전체 재검토는 빚으로 남김**

- **v15**: 네 번의 시도(격차 문단 뒤 한 단락) + field 4에 docs/23 링크 + 증거표 1행.
- **v16 (−909자)**: arm A 스펙트럼 수치(바로 위 문단이 요약 + 증거표에 원형 존재), 타겟팅의 시드별 세부, #1471의 복셀 수 — **전부 링크된 문서·표에 남아 있는 것만** 제거.
- **v17 (−128자)**: ⚠️ **내 추정이 틀렸음** — 마스크 감사(970자)·1447 렌더(697자)를 후보로 꼽았는데 실제로 걷힌 건 128자뿐. 그 문단들은 문장 대부분이 **재진술이 아니라 독립적 주장**이었다. 다만 렌더 문단 끝의 *"unsupervised adaptation이 선행해야 한다"*를 제거한 건 길이보다 값이 큼 — **네 번의 시도가 그걸 반증했으므로 제출문이 약속하면 안 되는 말**이 됐다.
- **현재 field 5 = 11,475자**(08-31 착지 9,822보다 +1,653). 여기서 더 줄이려면 **주장을 버려야** 하므로 사용자 결정으로 **중단**.
- 📌 **빚: 제출 전 field 5 전체 통독 1회.** 하루에 다섯 군데를 고쳤는데 08-31 트림 이후 **한 덩어리로 읽어본 사람이 없다** — 순서·중복만 보면 됨. **문안 Step 3의 0번 항목으로 박아 뒀다.**
- 해시 최종: field 4 `2,015자 / 39a669d5…`, field 5 `11,475자 / ea82e595…`. 인용 경로 31건·field 4 링크 16개 전부 확인.

#### 2026-09-01 (새벽) — 블러 **노출** arm(docs/23) 완주: **효과 없음**, 그리고 자기 베이스라인을 정정

01:46 완료. 16칸(4세그 × 2표현 × 2시드, step 20,000). 원수치 `runs/ink9um_scorecard/blurexp_matrix.csv` + `blurexp_summary.json`.

| | arm | 베이스라인 @20k | 차이 |
|---|---|---|---|
| native | 0.6219 | 0.6340 | **−0.0122** |
| aligned | 0.6693 | 0.6857 | −0.0165 |
| 격차 | 0.0474 | 0.0517 | −0.0043 |

- **판정 = 효과 없음.** native 이득이 **−0.0122**로 부호부터 반대고, 노이즈 0.03 안이며, **두 시드에서 부호가 갈림**(s42 **+0.0090** / s43 **−0.0333**). aligned 손실 −0.0165도 floor 안이라 "거래" 조항도 발동 안 함. 격차가 0.0043 줄었지만 그건 **aligned가 더 많이 떨어져서**지 좁힌 게 아님.
- **사전에 이름 붙여둔 실패 모드가 그대로 발생**: "둘 다 0.03 미만이면 그건 노이즈이고, 이 코퍼스의 시드 편차(0.011~0.032)면 그 정도는 만들어낸다." 실제 두 시드의 native 차이가 **0.042**로 효과보다 큼.
- ⚠️ **내 사전등록 문서의 베이스라인 오류를 자진 정정**: 문서 상단이 인용한 native 0.6545 / aligned 0.7079는 docs/15에서 가져온 **전-step 최고값**인데 arm은 step 20,000 한 점만 채점한다. 같은 조건 베이스라인은 **0.6340 / 0.6857**. 판정은 어느 쪽이든 동일(최고값 기준이면 arm이 더 나쁨: native −0.0326)하지만, **결과가 반대로 나왔다면 7개 step 중 최고를 바(bar)로 쓴 게 우리에게 유리한 비교가 될 뻔했음.**
- 📌 **같은 격차에 대한 사전등록 시도 4건 종결**: arm A(입력 필터, 실행 +0.005 무효) · docs/21(잡음, 부호 반대라 정지) · docs/22(블러 세기, 이미 레시피 안이라 정지) · docs/23(블러 노출, 실행 **−0.012 무효**). **둘은 실행해서 아무것도 못 얻었고, 둘은 GPU 쓰기 전에 자기 보정에 멈췄다.** 이 격차는 라벨 없이 안 움직인다 → docs/15 지침("aligned 계열로 렌더") 유지.
- ⚠️ **실행 함정**: `WinError 1455`(Windows 커밋 한계)로 **3회 사망** — 기동 시, 10,200 step, 6,600 step. **워커 12→6으로도 안 막혔고**, 막은 건 **각 시도 전 여유 메모리 25GB 대기**였다. 원인은 우리 설정이 아니라 이 기계의 다른 프로세스. `tools/run_blur_exposure.py`에 메모리 게이트 + 8회 재시도로 반영.

#### 2026-08-31 (밤) — 블러 arm(docs/22): **또 중단 조건 발동, GPU 0시간**

사전등록 `docs/22_blur_augmentation.md`(커밋 `31c4d5b`, 계산 전) → 보정 결과 **중단**.

- 정규화된 aligned 패치의 고주파가 native 중앙값까지 떨어지는 **가우시안 σ = 0.696·0.856·0.649·0.916 → 중앙값 0.776**, ±50%면 **0.39~1.16**.
- 🔴 그런데 레시피가 이미 `blur_sigma`를 **0.5~3.0**에서 뽑는다 → 보정값이 **그 범위 안, 중간값(1.75) 아래** = 사전등록한 exit 조건 그대로. **"레시피가 잘못된 세기로 블러한다"는 거짓.**
- **exit이 정리하지 못한 것 = 노출량**: 블러가 걸리는 패치는 10%(노이즈와 `OneOf`, p=0.2), 그중 보정 대역에 드는 σ는 26.6% → **현재 보정세기 블러를 보는 패치는 2.7%**. arm은 이걸 **50%**로 만들었을 것(19배). 즉 **확률만 바꾸는 arm은 무의미하진 않으나 더 약한 가설**이라, 강한 가설의 이름으로 돌리지 않기 위해 exit을 걸어둔 것.
- 📌 **같은 0.0534 격차에 대한 사전등록 시도 3연속 정지**: arm A(입력 필터링, 실행됨 +0.005 무효) → docs/21(잡음, 부호가 반대라 정지) → docs/22(블러, 세기가 이미 레시피 안이라 정지). **둘은 GPU를 쓰기 전에 자기 보정에 의해 멈췄다.**
- 이 격차를 실제로 움직이는 건 여전히 **사람 주석**(docs/18: 옆 문제에서 라벨 없는 최고 방법의 약 7배).
- 원수치 `runs/ink9um_scorecard/blur_calibration.json`.

#### 2026-08-31 (밤) — S2: **보정이 전제를 반증해서 arm을 안 돌림** (GPU 0시간)

사전등록 `docs/21_snr_augmentation.md`(커밋 `02d415b`, 측정 전) → **중단 조건 발동 → 학습 미실행**.

- **표적**: 두 표현이 다 있는 0139 4세그의 **aligned−native 격차 평균 0.0534**(0.0315~0.0696). 기제는 docs/15의 "aligned 복셀 1개 = 취득 복셀 64개 평균".
- **가설**: 그게 SNR 효과라면 단일취득 수준 잡음으로 학습시키면 native에서 덜 잃어야 함.
- 🔴 **보정 측정이 정반대를 말함**: 트레이너 정규화 후 **native가 aligned보다 고주파 에너지가 적다**(0.45~0.57배). 즉 aligned를 native처럼 만들 추가 잡음은 **0**. 프록시 아티팩트도 아님 — 정규화 2종 × 블러 3종 = **24/24 셀 전부 native가 매끄러움**(비율 0.373~0.768, 1을 넘는 셀 없음).
- 🔑 **우리 발표 기제의 정정**: 64복셀 평균은 **구성상 사실**이고 docs/15는 SNR 비율을 주장하지 않도록 이미 조심했었다. 여기에 실측이 더해짐 — **모델이 보는 차이는 "native가 noisy"가 아니라 "native가 smooth"**. 따라서 "aligned가 이기는 건 잡음이 적어서"는 개입을 세울 수 있는 모양이 아니다. docs/15 부록3에 이 포인터를 달아 둠.
- **그리고 올바른 방향의 개입은 이미 레시피에 있다**: 방향이 매끄러움이면 필요한 증강은 잡음이 아니라 **블러**인데, `create_training_transforms`가 `GaussianBlurTransform(0.5~3.0)`을 잡음과 **같은 `OneOf`, 확률 0.2**로 이미 적용한다. 그 레시피가 만든 게 0.0534 격차다.
- ⚠️ 발견 하나 더: **레시피는 이미 `GaussianNoiseTransform(noise_variance=(0.0124, 0.0277))`으로 학습 중**이다. "잡음 증강 미시도"가 아니었음 — 사전등록에 이 사실을 넣어 귀무가설을 "더 세게"로 좁혔다.
- **블러 arm은 별도 사전등록 사안으로 남김**(데이터를 본 뒤 개입을 바꿔 끼우지 않음). 신규 도구 `tools/measure_representation_noise.py`, 원수치 `runs/ink9um_scorecard/representation_noise.json`.
- 📌 **설계에서 가장 값진 조항이 중단 조건이었다** — 쓰는 데 10 GPU 시간이 걸렸고 지키는 데는 0이 들었다.

#### 2026-08-31 (밤) — F6 완결: **우리 이슈는 닫혀야 한다** (재시험 결과)

공식 릴리스 Windows 빌드(`VC3D-5479453-2026-08-30-win64`, main tip, 캐시 재작성 이후)를 받아 docs/16과 **같은 렌더를 `--timeout`/`--resume` 없이** 재실행.

| | 원 보고 | 지금 |
|---|---|---|
| 바이너리 | `:edge` `1e3f4c0`(2026-05-13) | 릴리스 `5479453`(2026-08-30) |
| 정지 | **4/4** (10·17·20·27%) | **0/3** |
| 소요 | 체인 합쳐 ~25분 | **5m55s · 3m56s · 3m50s**, exit 0 |

- 3회 산출물이 **서로 바이트 동일**, 피라미드 6레벨 형태도 구본과 동일 → 렌더러는 이 빌드에서 결정적.
- ⚠️ **"고쳐졌다"고 주장하지 않음**: 원 정지는 원격 fetch 유실이 원인이고 오늘 네트워크는 5월과 다르다. 말할 수 있는 건 **"재작성 이후 빌드에서 3회 시도 중 0회 재현, 구 빌드는 4/4 실패"**까지. 초안에 그대로 씀.
- **무한 대기는 남아 있다**(main 4곳 1788·1873·2404·2529, 구본 2곳). `persistChunkBlocking`은 완료 세팅 경로가 `weakState.lock()` 안이라 만료 시 아무도 안 깨움 → **버그로 파일링하지 않음**(재현 못 했고 빌드도 못 함). 관찰로만 남김.
- 🔑 **docs/16 결론은 그대로**: 새 렌더가 구본과 복셀 2.6% 다르지만(85%가 10계조 초과) 잉크 추론은 **>128 23.38→23.69%, max 214→215, 중앙값 101→102**. 글자는 여전히 없음. docs/16에 재검증 절 추가.
- 초안 = `submission/issue1611_retest_reply.md`(**미게시**), 증거 = `runs/f6_render_retest/`. **우리 이슈를 닫자고 우리가 제안하는 내용** — 자기 보고의 실무 부분을 철회하는 것이므로 묻지 말고 앞세워 쓸 것.
- ⚠️ 부수: GHCR `:main`·`:edge`가 아직 05-13(빌더 이미지는 07-24 재빌드, 릴리스는 08-30 최신) → **컨테이너로 가면 이 이슈의 버전을 그대로 받는다**. 초안에 한 문단으로만 넣음(별도 이슈 아님).

#### 2026-08-31 (밤) — F6 조사: **우리 보고 대상은 아무도 재빌드하지 않는 바이너리였다**

C++를 건드리기 전에 "우리가 보고한 게 아직 존재하나"부터 확인. 전부 대조 가능한 사실 4건:

1. **무한 대기는 살아남았고 늘었다.** 우리 바이너리의 리비전(`1e3f4c0`, 2026-05-13)에서 `core/src/render/ChunkCache.cpp`는 **755줄에 `cv_.wait` 2곳(218·749)** — Bullo27이 인용한 바로 그 줄. 현재 main은 **5,672줄에 4곳**, 전부 타임아웃 없음.
2. **그중 하나는 완료 구멍이 소스에 보인다.** `persistChunkBlocking`이 `operation->completed`를 기다리는데, 그걸 세팅할 유일한 경로가 `[weakState,…]{ if (auto state = weakState.lock()) … }` 안에 있다 → **weak_ptr 만료 시 아무것도 안 돌고 아무도 깨우지 않으며 빠져나갈 타임아웃도 없다.**
3. **그사이 캐시가 재작성됐다**("Rewire local remote cache" #1554, 2026-08-21). 우리 정지는 이제 그 형태로 존재하지 않는 코드에서 관찰된 것. **성질은 살아남았지만 우리 정지가 살아남았는지는 미지.**
4. **컨테이너는 2026-05-13 이후 재빌드 안 됨.** GHCR의 애플리케이션 태그 `:main`·`:edge` 둘 다 `1e3f4c0`인데, **빌더 이미지는 계속 재빌드**된다(`builder-ubuntu-26.04`, 2026-07-24). 빌드하는 CI는 도는데 사용자용 산출물만 3개월 반 묵음.

⚠️ **그리고 이걸 오보로 만들 뻔한 정정**: **GitHub 릴리스는 최신이다.** `latest`(2026-08-30)가 **오늘의 main `5479453`**로 Linux·macOS·**Windows** 바이너리를 배포하고, First Letters 포스트도 컨테이너가 아니라 **릴리스 페이지**를 가리킨다. 따라서 "배포본이 낡았다"는 **컨테이너에만** 참이고 문서상 설치 경로는 최신. 반대로 썼으면 메인테이너에게 허위 보고가 될 뻔했다.

→ **다음 단계는 패치가 아니라 측정**: 오늘 main의 공식 Windows 빌드(`VC3D-5479453-2026-08-30-win64.zip`)가 있으므로, 우리가 컴파일할 수 없는 소스를 건드리는 대신 **재작성된 캐시에 대고 정지를 직접 재현**할 수 있다. 어느 쪽이 나와도 게시할 값이 있음(여전히 정지 → #1611이 현재 코드에 대해 살아 있음 + 무한 대기 4곳 지목 / 정상 완주 → 재작성이 고쳤고 우리가 그렇게 말하고 우리 이슈를 닫음).
⚠️ 다운로드·실행은 사용자 승인 사항이라 **대기 중**.

#### 2026-08-31 (밤) — F5: **묻기만 하고 만들지 않음** (초안 `submission/issue1231_f5_question.md`, 미게시)

계획의 F5 규칙이 "만들기 전에 묻는다"였고 이유는 #1638(제목이 본문보다 앞서 나가 당일 닫히고 잠김). 그래서 산출물은 PR이 아니라 **질의 초안**이고, 대상은 우리 자신의 열린 이슈 #1231.

- ⚠️ **또 코드를 먼저 읽어서 주장이 좁아졌다.** 우리 메모는 "파이프라인에 평가 경로가 **아예 없다**"였는데 현재 tip에선 **틀렸다** — `Confusion`·`BalancedAccuracy`는 `train.py`가 실제로 import해서 validation pass에서 돈다. 사실인 건: ①**`DRD`·`PFMWeighted`는 트리 전체에 호출자 0**(학습·추론·테스트 어디에도 없음) ②`evaluation/__init__.py` 둘 다 비어 있고 `__main__`도 console script도 없음 ③도는 두 메트릭도 **학습 안에서만**, 그것도 코퍼스에서 3세그만 주는 검증 split 위에서. → 정확한 문장은 **"라벨 옆에 놓인 예측을 이 저장소의 무엇으로도 채점할 수 없다"**.
- 초안은 **두 가지 모양을 제시하고 둘 다 안 만듦**: ①미사용 메트릭 2개를 기존 validation에 연결(`BinaryImageMetric`이 `compute_per_sample`을 이미 구현 → `per_sample=True`로 배선만 하면 됨) ②`python -m koine_machines.evaluation.score` 진입점(우리 7월 하네스의 업스트림화).
- 🔑 **둘 중 무엇이 필요한지를 가르는 사실도 같이 넘김**: `BinaryImageMetric.threshold` 기본값이 **0.5**인데 우리 **126셀에서 F1 최적 임계값은 68~153/255** → 학습 중 로그된 값과 스윕에서 나온 값은 **같은 수가 아니다**.
- ⚠️ **자진 정정 1건**: 그 범위를 처음에 "95~153"으로 썼는데 아티팩트는 68~153이었다. 게시 전에 CSV에서 재산출해 잡음. **초안의 모든 수치는 커밋된 매트릭스와 대조 완료.**
- **F5는 이제 답변 대기 상태가 정상** — 원하면 그쪽 답이 모양을 정하고, 원치 않으면 리뷰 대신 코멘트 하나를 쓴 것으로 끝난다.

#### 2026-08-31 (밤) — F4 완료: 버그는 우리 기록보다 **좁았다**

우리 메모는 "패치 캐시가 경로 기준이라 마스크 갈아끼우면 낡은 split 재사용"이었는데, **로더를 읽어보니 절반만 맞다** — 캐시 레코드가 라벨·마스크 경로를 들고 있고 현재 세그먼트와 안 맞으면 거부하므로 **다른 트리를 가리키는 건 잡힌다**. 안 잡히는 건 **경로는 같고 내용만 바뀐 경우**(= 7월에 우리가 한 일: 마스크 제자리 재생성).

- **실세그먼트 재현**: 1,266 패치 탐색 → `_supervision_mask.zarr`를 **제자리에서 절반으로** → 같은 out_dir 재실행 **1,266(바운딩박스까지 동일)**, 새 out_dir의 진실은 **1,162**. **104 패치가 사라진 감독 위에서 계속 학습**되고 겉보기엔 정상.
- **수정**: 라벨 자산의 상대 파일명+크기 해시를 `Segment.cache_key`와 캐시 레코드에 넣음 → 기존 거부 경로가 그대로 작동(새 무효화 로직 없음). 수정 후 같은 재현이 **1,162**로 나오고 새 out_dir과 바운딩박스 동일.
- **빠른 경로 보존이 관건이었고 지켜짐**: 미변경 트리 2회차 **0.02초**(1회차 3.03초), 바이트 동일 복사본도 동일 지문으로 적중. 지문 비용은 6,429파일 라벨 배열당 **8 ms**(`os.scandir`가 크기를 같이 주기 때문 — `Path.stat()`이면 320 ms). 61테스트 통과.
- 브랜치 `fix/patch-cache-notices-changed-labels`(`b3288a5`), 본문 `submission/pr_f4_patch_cache_fingerprint.md`, 증거 `runs/f4_patch_cache/`.
- ⚠️ **한계 2개를 본문에 명시**: 같은 이름·같은 크기로 압축되는 서로 다른 라벨은 구분 못 함(청크 내용을 안 읽음); 내용 동일 복사본은 같은 지문(의도된 동작).
- 📌 **첫날에 마찰 6건 중 3건(F2·F3·F4)이 작성·검증·푸시 완료.** 셋 다 **PR 개설이라는 같은 하나**에 막혀 있음.

#### 2026-08-31 (저녁) — S1 결과: **주석 위치는 중요하다, 그런데 우리 규칙은 부호가 반대였다**

17:37 완료, **42셀·6런·재시도 0·실패 0**. 전문 = `docs/20_annotation_targeting.md`, 원수치 `runs/ink9um_scorecard/annotarget_matrix.csv`+`annotarget_summary.json`(커밋됨).

| arm | keep | 잉크밀도 | 불일치 | s42 | s43 | **평균** | 세그 승 |
|---|---|---|---|---|---|---|---|
| `disagree-min` | 19.67% | 0.3017 | 0.0813 | 0.7397 | 0.7781 | **0.7589** | **7/7** |
| `disagree-max` | 19.20% | 0.3071 | 0.0880 | 0.7233 | 0.7540 | 0.7387 | 0 |
| `random` | 23.49% | 0.2301 | 0.0868 | 0.7210 | 0.7522 | 0.7366 | 0 |
| `density`(발표본) | 20.72% | 0.2462 | — | 0.7045 | 0.7386 | 0.7216 | 0 |

- **사전등록 규칙 적용**: 격차 **0.0373 > 0.03** → "어디를 주석하느냐가 결과를 바꾼다". 획득 규칙은 **실패**하고 부호까지 반대 — `max − min`이 **−0.0165 / −0.0241**(모델이 **덜** 헷갈려한 쪽이 이김). 둘 다 노이즈 안이라 규칙대로 **"포착 못 함"으로 보고**(역효과 입증 아님).
- **크기가 아니라 일관성이 근거**: 두 시드에서 **순서 동일**, `disagree-min`이 **7/7 세그 최고**. arm 내부 시드차(0.031~0.038)가 arm 간 격차만큼 크므로 개별 셀은 노이즈, 반복되는 순서는 아님.
- **사전 명시한 교란 2건이 유리한 쪽으로 해소**: 주석을 **가장 많이** 쓴 `random`(23.49%)이 3위, 승자는 **19.67%**로 발표본(20.72%)보다 적게 씀.
- 🔑 **우리 자신의 발표 수치가 수정됨**: docs/15는 "주석 1/5이 이득의 **70.8%** 유지"라고 했는데, 같은 척도(base 0.5029, full 0.8118)에서 다른 부분집합이 **더 적은 예산으로 82.9%**. → **70.8%는 그 예산의 성질이 아니라 그 부분집합의 성질**이었고, 그 예산의 실현 범위는 최소 70.8~82.9%. docs/15 5부를 "1/5이면 30%를 잃는다"로 읽으면 안 됨.
- ⚠️ **사후 관찰(주장 아님)**: 잉크밀도가 순서를 따라감(0.30 이상 두 arm이 1·2위). 쌍 내부에서는 역전되므로 2점 우연과 구분 불가 → **별도 사전등록 실험거리**로만 기록.
- 신규 도구: `tools/summarise_annotation_targeting.py`(판정 규칙 자동 적용, 불완전 매트릭스면 판정 거부).

#### 2026-08-31 (저녁) — **$5k 타겟 30일 계획 수립** (전문 = `planning/2026-09_five_k_plan.md`, **비공개**)

사용자 지시로 남은 30일을 $5k에 겨눈 계획을 작성. ⚠️ **문서는 `planning/`에 두고 gitignore** — `docs/`는 제출 문안 field 4에서 도달하는 공개 경로이고, 08-29에 같은 이유로 docs/05에서 상금 산술·경쟁자 표를 걷어냈다. 아래가 그 계획의 실행 요지(문서가 유실돼도 이걸로 재구성 가능).

**📊 상금 이력 실조사(substack 발표문 6건, 2026-08-31)** — 총액이 등급 카운트로 정확히 복원돼 추출 신뢰 확인($41,000·$42,500·$33,500):
- **$5,000은 기록 전체에 단 1건**(2025-05, Philip Allgaier): VC3D **프리빌트 Docker 복구 + 메모리 누수 수정 + 컨테이너 CI + Ubuntu/Qt 호환 + 콘솔 출력** = **메인테이너 이슈 목록에서 떼어낸 머지된 수정 묶음**. 새 방법도 연구도 아님.
- **$10,000 = 매일 쓰는 도구**(2024-08 3건: Segment Browser·Napari 3D·Khartes / 2024-04: Khartes OME-Zarr). 수개월짜리 제품이지 한 달 스프린트 아님.
- **$20,000 = 한 달치 파이프라인 성과 묶음**(2024-03 Giorgio: 고속 렌더+새 평탄화+파인튜닝+튜토리얼) 또는 메싱(2026-07).
- **$2,500·$1,000 = 방법·도구·측정.** 2025-04, 2025-02는 상위 등급이 **아예 없었음**.
- → **$2,500 위는 전부 "남이 돌리는 소프트웨어"에 갔다. 연구를 더 잘해도 등급은 안 오른다.**

**🎯 결론: Track F(마찰 제거)가 본진, 연구는 별건 제출로.** 팀이 지금 미는 경로는 추측이 아님 — 2026-08-18 Paul Henderson의 First Letters 워크플로 포스트(VC3D → 나선 피팅 → 렌더 → 잉크탐지). **우리는 그 후반부를 docs/16에서 완주하며 깨진 곳을 이미 기록해 뒀다.**

| # | 마찰 | 우리가 가진 증거 | 크기·리스크 |
|---|---|---|---|
| F1 | 공개 레시피가 그대로 안 돌아감 | #1608 (open, CI green) | 작성 완료, 메인테이너 주목만 필요 |
| F2 | Windows `infer`가 Triton 없어 첫 forward에서 사망(`--no-compile` 필수) | docs/08 | 작음·낮음 |
| F3 | `prepare_9um_isotropic_input`이 Windows 최종 rename에서 사망(데이터는 완전), S3는 **타일 단위** 재시도 필요 | 24개 입력 준비 실측(6회 백오프, 동시성 ≤2×6) | 작음~중간·낮음 |
| F4 | 패치 캐시가 경로 기준 → 마스크 갈아끼워도 낡은 split 재사용(틀린 실험이 맞아 보임) | docs/09, 7월에 하루 날림 | 중간·중간 |
| F5 | 파이프라인에 평가 경로가 **아예 없음**(metric 클래스는 있는데 호출부 없음) | 7월 하네스, #1231(무응답)·#1638(닫힘) | 중간~큼 · **만들기 전에 #1231에서 물어볼 것** |
| F6 | `vc_render_tifxyz`가 원격 청크 끊기면 무한 대기 | #1611 + Bullo27의 위치 특정 | 큼·높음(C++, 다른 트리) — 스트레치 |

**순서**: F2·F3 먼저(작고 머지 확률 높고 팀이 릴리스하는 플랫폼을 살림) → F1은 응답성만 → F4 → F5는 승낙 후 → F6은 여유 있을 때. ⚠️ **#1471의 전폭 블록 최적화(195.84→104.38s)는 목록에서 제외** — 그건 그쪽 PR 저자 것이고 회신으로 넘긴다.

**Track S(연구, 별건 제출용 — 월 복수 제출 허용을 처음으로 씀)**: **S1 주석 타겟팅**(무작위 절반=이득 89% 기준선이 이미 있음, FT 2,500 step≈7분 → arm당 1h. 이기면 주석 노동 절감 도구, 져도 "아무 데나 주석해도 된다"는 지침) · **S2 SNR 맞춤 증강**(aligned 복셀=취득 64개 평균이라는 측정된 기제. arm A는 *테스트 시 입력 필터*였고 이건 *학습 시 불변성*이라 다른 개입. arm당 8h·2시드, 성공률 자체추정 30~40%).

**주간 게이트**: 9/1~7 F2·F3 열고 #1231에 F5 의향 질의 + S1 4 arm → **9/12까지 리뷰어 안 붙으면 리뷰 기대를 접고 S 쪽에 무게** / 9/8~14 F4 + S1 잔여 → **S1 첫 4 arm이 전부 노이즈 안이면 6개에서 멈추고 null 보고** / 9/15~21 F5 또는 F6 + S2 / 9/22~30 마감·2건 제출·동결. **미응답 PR은 후속 2회까지만.**

**기대치(정직하게)**: $2,500 확률은 확실히 오르고, **$5,000은 실재하지만 소수 확률**(그리고 그건 *한 달 안에 머지되느냐*라는 우리 통제 밖 변수에 달림 — 관측 가능한 6라운드 중 1건뿐). **$10,000은 사거리 밖**(매일 쓰는 도구 = 수개월 제품). 바닥은 안 변함 — 9월 연구 제출은 무슨 일이 있어도 그대로 나간다.

#### 2026-08-31 (오후) — #1471 요청 수행: 그쪽 브랜치에서 **크래시 1건 발견 + 수정 검증**

jaideepsaipadhi가 08-27 코멘트로 **우리 하네스의 striped 마스크, 특히 odd-extent로 자기 경로를 돌려달라**고 직접 요청(스트립 경계가 다운샘플 스텝과 어긋나는 게 자기 코드의 미검증 리스크라고 자진 신고). 수행 완료. 초안 = `submission/pr1471_reply_jaideepsaipadhi.md`(**미게시** — 게시는 사용자), 증거 = `runs/pr1471_striped_check/`(커밋 `cbaed26`, 푸시됨, 링크 200).

- **비교 설계**: head `6cec011` vs 부모 `aab644c`(= 현재 main과 해당 2파일 바이트 동일, 재확인). 55 variant(8 extent × 5 layout + mean 모드 + uint16 + 코덱 4종).
- **정확성 42/42 동일** — 252 레벨 비교, 96.6억 복셀, 불일치 0. **그쪽이 걱정한 지점은 구조적으로 안전**: `_write_downsample_block`이 *타깃* 격자로 주소를 잡고 `source[:, block_y*2 …]`를 읽으므로 2×2 창은 스트립 위치와 무관하게 항상 짝수 소스 행에서 시작.
- 🔴 **진짜 버그 = 1행짜리 스트립**: `page.decode()`가 `(depth, rows, cols, samples)`를 주는데 `rows==1`이면 `_normalize_to_2d`의 `np.squeeze`가 **행 축까지 날려** 1-D가 되고 2D 가드가 거부 → `ValueError: Expected a 2D image`. 발동 조건은 **내용이 아니라 extent**: `rowsperstrip == 1` 또는 `height % rowsperstrip == 1`. 55개 중 13개, 표적 재실행 27개 중 25개. **타일은 절대 못 걸림**(TIFF 타일 높이는 16의 배수) → `is_tiled` 게이트가 가려온 이유. **오늘 변환되는 파일이 PR 후 죽으므로 회귀**.
- ✅ **수정안 검증**: `_decoded_block_to_2d`로 축을 명시 인덱싱(`block[0,:,:,0]`). head 25 크래시 → 수정본 9(전부 사전존재분), **18/18이 부모 출력과 전 레벨 동일**. ⚠️ `np.atleast_2d`는 금물 — 1행은 고치고 **1열을 조용히 전치**함.
- **사전존재 결함(그쪽 책임 아님)**: 1×N·N×1·1×1은 **양쪽 트리 모두** `_normalized_2d_shape`에서 죽음. 초안에 "이건 당신 것 아님"으로 명시.
- **실스케일**(실제 w00 검증마스크 32249×51380을 striped로 재인코딩 — 우리 하네스는 지금 `tile=(256,256)`을 씀, 그 사실도 초안에 명시): 6레벨 전부 0 불일치. **tiled 143.27s/0.884GiB vs striped 195.84s/0.881GiB**(+37%). 원인은 **스트립이 전폭이라 1024폭 블록마다 재디코드(여기선 51회)**.
- **피라미드 트레이드 실측**(그쪽이 "주장 말고 측정하고 싶다"던 것): 이 PR 195.84s/0.881GiB · **전폭 블록 적용 104.38s/0.881GiB** · **우리 머지본 #1234 64.62s/1.929GiB**. → 시간 3.0배 손해, 메모리 2.2배 이득, 그리고 **시간 손해의 70%는 read-back이 아니라 재디코드**. 오늘 잰 1.929는 #1234 당시 기록 1.99와 일치(방법론 교차검증).
- 🔑 **결정적 맥락**: **#1234의 리뷰 전 버전이 정확히 그쪽 설계였고 erdpx가 바꾸라고 요청**했다("build only the 2d pyramid in memory … instead of rereading the zarr levels from disk"). 당시 수치 114.5s/1.61GiB → 66.5s/1.99GiB. 초안에 원문 인용 + "그러니 리뷰어 앞에 내밀 논거는 read-back 자체가 아니라 **메모리 상한이 이미지에 안 묶인다는 것 + 전폭 블록으로 속도차가 1.6배로 준다는 것**"으로 정리. 통합 여부는 **메인테이너 대신 답하지 않음**.
- ⚠️ **새 함정(일반적)**: **zarr 청크 바이트는 프로세스 간 재현되지 않는다** — 같은 코드·같은 입력이 두 번 다른 바이트를 씀(blosc). 첫 패스에서 55개 전부가 "다름"으로 나왔고 전부 압축이었다. **저장소 동일성 판정은 반드시 디코드된 배열로.**
- ⚠️ 그쪽 테스트 14개는 양쪽 트리에서 통과 = **이 케이스를 안 건드림**. 초안에 1행 스트립 픽스처 추가를 제안.
- 검증 스크립트 `runs/pr1471_striped_check/verify_numbers.py`가 **초안의 38개 수치를 원 아티팩트에서 재산출해 전건 대조**(통과). 아티팩트의 로컬 경로는 `<scratch>`로 치환함.
- 🔴 **부수 발견(같은 점검에서): 8월 문안의 증거표가 가리키는 `runs/*.json` 9개가 저장소에 없었다.** 실체는 `external/villa/ink-detection/runs/`(미추적)에만 있었고, 그쪽은 **68.3GB ckpt 65개를 포함한 76GB 미추적 트리**다. 파일당 4KB뿐이라 **전부 `runs/`로 복사**(+`runs/depth_contrast/` 100KB) → **8월 17개·9월 23개 인용 경로가 전건 해소**됨. 문안 파일은 손대지 않았으므로 동결 유지. 복사본이 인용 수치를 실제로 담고 있는지도 대조 완료(0.847243·0.844091·0.847853·0.809759·0.82625·0.728672, ext30k 격차 0.038263→0.036076).
- ⚠️ **함정(오늘 실제로 밟음): `git add runs/`는 미추적 GPU 산출물 전체를 스테이징한다.** 의도한 9개 대신 **1,506파일 1.1GB**(패치 캐시 `flat_ink_patches_*.json`이 개당 50~95MB)가 커밋·푸시됐다. 사용자 승인 후 **force-push로 그 커밋을 제거**(tip이고 포크 0이라 영향 없음)하고, `.gitignore`에 **`runs/*` 전면 무시 + 큐레이션 파일만 `git add -f`** 규칙을 넣었다. → **앞으로 runs/ 아티팩트는 반드시 개별 경로로 `-f` 추가할 것.**
- ⚠️ **재생성 가능성 정리**: `D:/vw2~vw7`은 전부 커밋+원격 존재라 재생성 가능(vw6·vw7의 미커밋 수정은 patch로 export, `git apply --check` 통과). **재생성 불가한 건 `external/villa` 하나** — 미커밋 5파일(train/infer/test = 리베이스 전 flat_depth_targets 로컬본, pyproject/uv.lock = cu128 인덱스 핀)과 미추적 76GB(ckpt·predictions·runs). 정본 코드는 `D:/vw2`(`8922c5e`, fork에 푸시됨)이고 env 핀은 CLAUDE.md에 절차가 있으니, **이제 external/villa가 사라져도 잃는 건 재실행 편의와 ckpt뿐**(재학습 GPU 16h).
- 📌 **검증 워크트리 4개를 9월 라운드까지 유지**(사용자 결정 2026-08-31): `D:/vw4` head · `D:/vw5` base · `D:/vw6` head+1행수정 · `D:/vw7` head+수정+전폭블록. 각 21MB 스파스(`vesuvius/`만), D 여유 283GB. **vw6·vw7의 수정은 미커밋**이라 `runs/pr1471_striped_check/patch_*.patch`로 각각 export 해 둠 → 트리가 사라져도 재현 가능. PR이 정리되면 `git worktree remove`.

#### 2026-08-31 (오전) — 문서 반영 + 문안 트림 v12 (**제출 준비 완료**)

밤샘 결과를 전 문서에 반영하고 문안을 정리했다. 남은 절차는 폼이 열린 뒤 Step 3 체크리스트뿐.

- **스크롤 라벨링 반영**: docs/18(1667 결과 절 + 사다리 표·결론에 "Paris4 한정" 경고), **docs/15 4b**(82%에 경고 블록 + 24% 병기), **README**(사다리 표·수리비용). 수치 **9건 재검증 통과**.
- **문안 v12 — field 5를 12,294 → 9,820자로 트림**(−20%). 자른 것은 **링크된 문서에 있는 세부**뿐: arm A 스펙트럼 수치, 풀링 측정 방법, #1638 서사, 렌더 바이트 수. **핵심 수치 43개 전건 잔존 검증.** ⚠️ **1667 복제는 의도적으로 손대지 않음** — 우리 헤드라인을 우리 후속 실험이 반증한 대목이라 field 5에서 가장 강하다.
- **트림 부작용 2건 발견·수정**: ①"arm C/D"를 소개(사다리 문단)보다 4문단 앞선 1667 문단에서 쓰고 있었음 → 그 문장을 사다리 문단 끝으로 이동(검증: `arm C` 첫 등장 8,547 > 사다리 시작 6,818) ②그 과정에서 빠진 마침표.
- **field 4 카운트 갱신**: 채점 셀 1,612 → **1,720**, scorecard 파일 27 → **33**, 전체 증거 파일 63 → **68**.
- field 4/5 **sha256 재기록**(본문+개행 1개 규약), 파일과 일치 확인. field 4 1,500자 / field 5 9,821자.

#### 2026-08-31 (새벽) — 1667 복제 + step 곡선: **Paris4는 일반화되지 않는다** (판정 확정)

백로그 2번 완결. 사전등록 `cd07b16`(복제)·`5468ac5`(step 곡선 해석규칙) 둘 다 실행 전 커밋. 총 **90칸**(3팔 × 3스텝 × 5세그 × 2시드), 실패 0건. 원수치 `r1667_matrix.csv`·`r1667_stepcurve_summary.json`.

베이스 = leave-1667-out `ckpt_010000`, 주석 세그 = w018, 채점 = w013/w023/w028/w029/w031. base 평균 0.5472, train-pixel ref 0.9799.

| arm | 2,500 | 5,000 | 10,000 | 정점 |
|---|---|---|---|---|
| **FT**(사람 주석) | **0.6517 (+0.1044)** | 0.6392 (+0.0920) | 0.6195 (+0.0723) | **2,500** |
| C(w018 의사라벨) | 0.5550 (+0.0078) | 0.5573 (+0.0101) | **0.5638 (+0.0166)** | 10,000 |
| D(채점 세그 자신) | 0.5315 (**−0.0157**) | 0.5330 (−0.0143) | 0.5419 (−0.0053) | 10,000, **끝까지 음수** |

**🔑 교란요인이 죽었다**: "2,500에서 끊은 게 불리했나"가 유일한 탈출구였는데, **1667의 FT도 2,500에서 정점 후 단조 하락**(Paris4와 같은 모양). 따라서 중단 시점은 무죄이고 **차이는 스크롤 자체**. 사전등록 규칙대로 **Paris4 수치는 스크롤 특수로 라벨링**했다.

- **주석 1세그의 값**: Paris4 **+0.320(ref까지의 82%)** vs 1667 **+0.104(24%)** — 같은 레시피·같은 step에서 **3배 차이**.
- **자가학습은 건너오지 못함**: arm C는 모든 step에서 노이즈 안(+0.008~+0.017), **arm D는 모든 step에서 음수**(Paris4에선 +0.046, 14/14칸). 더 긴 학습도 못 살림.
- **살아남는 것**: ①포화 지점(2,500)은 두 스크롤에서 재현 ②"주석 ≫ 추측" 순서는 두 스크롤 모두 유지. 죽는 것: 크기.
- ⚠️ **함정**: arm C의 "갭 회수율"이 7.4%→11.0%→23.0%로 오르는데 **2/3는 분모(FT 갭)가 0.104→0.072로 줄어서**다. 분모가 움직일 땐 **절대 ΔF1**로 말할 것.

**반영 완료**: docs/18(1667 결과 절 + 사다리 표·결론에 "Paris4 한정" 경고), docs/15 4b(82%에 경고 블록 + 24% 병기), README(사다리 표·수리비용), **9월 문안 v11**(repair-price 문단에 복제 서술 추가, 사다리 문단에 "건너오지 못한다", 증거표 1행, 해시 재기록). 수치는 **9건 전건 재검증 통과**.

⚠️ **문안 field 5가 12,294자로 너무 길다** — 하루에 결과 3개(arm D·1447·1667)를 넣고 아무것도 안 뺐다. **제출 전 ~9,000자로 트림 필요.** 자를 순서는 문안 머리말에 적어 뒀고, **1667 복제는 자르지 말 것**(우리 헤드라인을 우리 후속 실험이 반증한 대목이라 가장 강함).

#### 2026-08-30 (밤) — arm D를 PHerc1447에 겨눔: 세 기준 모두 미달

docs/18 §6이 예고한 **채점 불가 최종 검사**. 채점할 정답이 없으므로 **무엇을 성공으로 볼지 먼저 커밋**(`1da7685`)한 뒤 실행: ①블롭이 아니라 **연결된 획** ②두 시드가 **획의 위치**에 동의 ③**양봉 분포**. 셋 중 둘이 같은 자리에서 나와야 인정.

- 베이스 = **공개 체크포인트** seed42/43 step-020000, 의사라벨은 그 예측 자신에서, 2,500 step 적응 후 재추론.
- **결과 0/3.** 대비만 크게 올라가고 구조는 그대로: 크롭에서 여전히 둥근 덩어리(획의 결합·일정 굵기 없음), 분포는 **양봉이 아니라 바닥 한쪽으로 붕괴**(시트의 91~98%가 하위 1/3, `>128`이 23.0%→3.7% / 10.6%→0.9%), 시드 상관은 0.476→0.865로 올랐지만 **상위 10% 겹침(=잉크 위치 동의)은 0.173→0.177로 제자리**.
- **해석**: 자가학습은 모델이 이미 믿는 것을 증폭한다. Paris4에선 그 믿음이 우연보다 나아서 14.3%를 벌지만, 1447에선 docs/16이 "믿는 게 없다"를 측정해 둔 상태라 증폭할 게 없다. → docs/16의 "무라벨 적응 선행" 전제가 **측정으로 닫힘**: 값싼 방법은 다 막혔고 남은 건 사람 손이다.
- ⚠️ **내 지표 오류 1건(자진 보고)**: 첫 bimodality 지표를 "중간 1/3 바깥 비율"로 짜서 **한쪽 붕괴를 0.93 양봉으로 오독**했다. 3분할로 교체. **기준을 미리 못 박아 두지 않았으면 이걸 성공으로 읽었을 것.**
- ⚠️ **docs/16 통계 정정**: docs/16은 예측이 **쓰인 영역(캔버스의 67.03%)**을 "렌더 유효영역"이라 적었는데, 실제 유효영역은 **21.05%**이고 **쓰인 픽셀의 68.9%가 시트 밖 패딩**이다(추론이 저해상 점유 스캔으로 블록 단위 스케줄링 + hann 블렌딩을 하기 때문). 시트 위에서 재산출해도 결론은 유지(>128 10.6~32.3%, max 211~237, 중앙값 88~113)되고, 오히려 **패딩(입력이 0)에서의 분포가 시트 위와 거의 같다는 것**(중앙값 86~109 vs 88~113)이 "출력이 데이터로 구동되지 않는다"의 더 날카로운 증거가 된다. 원수치 `runs/first_letters/pherc1447_base_on_sheet.json`·`pherc1447_armD_compare.json`, 도판 `docs/images/pherc1447_armD_before_after.png`.
- 문안 **v10**(field 5에 이 문단 + 증거표 1행, 해시 재기록).

#### 2026-08-30 (저녁) — arm D(사전등록) 실행: 라벨 없이 갭의 14.3%

사용자 요청으로 백로그 1번을 그날 바로 실행. **설계·예측·판정규칙을 커밋(`923895d`)한 뒤에** 라벨 생성·학습·채점. 결과·수치는 위 "해볼 만한 것" 1번과 docs/18 arm D 절. 요지 셋:

1. **읽으려는 시트를 스스로 라벨링하는 쪽이 낫다** — 갭 회수 9.5% → **14.3%**, 14/14칸 개선, 노이즈 초과. 다만 **arm C 대비 차이(+0.0154)는 노이즈 미만**이라 "transductive 우위"는 확정 안 함.
2. **랭킹이 실제로 좋아진다** — AUC 0.659 → 0.742. 사전등록한 고착 실패 서명(F1 정체 + 확신 증가)은 안 나타남.
3. **주석의 값이 확정됨** — 사람 주석 1세그가 라벨 없는 최고 방법의 **약 7배**. 뒤집어 말하면 **주석이 불가능한 스크롤도 14%는 오늘 가질 수 있다** → 다음 후보가 이걸 PHerc1447에 겨누는 것(백로그 3번).

⚠️ 5000 step은 arm C와 똑같이 **시드가 갈림**(s42 하락, s43 상승) → 사전등록 2500 유지.
⚠️ 문안은 **v9**로 갱신(field 5에 arm D 문장 + 증거표 1행). field 5가 10,461자로 늘어 **field 4/5 해시 재기록 필요**(제출 전 최종 검토 때).

#### 2026-08-30 — UDA 사다리 완주, 문안 감사, 업스트림 회신 2건 게시

**1. 🔬 docs/18 사다리 완성 — 세 팔 전부 사전등록 → 실행 → 보고**

| arm | 예측 | 실측 | 판정 |
|---|---|---|---|
| A 스펙트럼 매칭 | 0~20% | +0.005 F1, 중앙값 **9.1%** 회수, 17/24칸 | 효과 없음 |
| **B 엔트로피 최소화(TENT)** | 10~40% | **−0.041 F1, 개선 0/14칸**, AUC 0.66→0.48 | **해로움 — 예측 기각(부호까지)** |
| **C 의사라벨 자가학습** | −10~+15% | **+0.030 F1, 14/14칸 개선, 갭 9.5%** | 효과 있음(노이즈 경계선) |

- **arm B가 오늘의 최대 수확이자 가장 이식성 높은 발견**: 붕괴 서명이 사전등록대로 나옴(p>0.5 비율이 100~200 step에 0, 4칸이 자명하한 ±0.002, 400 step부터 프로브 전 칸이 하한, 임계값 72–112 → 30–66). **8비트 아티팩트 아님**(`tools/float_rank_check.py` 신규: float/uint8 best-F1이 0.001 이내 일치, 대신 AUC가 0.62–0.66 → 0.48–0.55). ⚠️ **엔트로피는 끝까지 단조 감소하는데 품질은 단조 하락** → **목적함수 기반 무라벨 조기종료가 원리적으로 불가**. 궤적: 50 step +0.003~+0.012(노이즈 안) → 100 평평 → 200 −0.03~−0.05 → 400부터 하한. 타깃 라벨로 고른 best-of-grid조차 +0.0057.
- **arm C가 주석 가격을 매김**: base·세그먼트·레시피·step 고정하고 **w00 라벨 출처만** 바꾸면 사람 주석 **+0.3202(82%)** vs 모델 자기추측 **+0.0303(9.5%)** → **주석은 자기추측의 약 10배**. 랭킹도 실제로 개선(AUC 0.6593 → 0.7002 → 0.7102) = arm B와 정반대. 5000 step은 시드가 갈려(s42 +0.013 / s43 −0.018) 사전등록 2500 유지. **시드 차(0.018)가 step 차보다 큼.**
- **사전등록 규율**: arm B 파라미터 커밋 `3bff82f` **07:43:18** = 적응 첫 step(07:50:06)·첫 채점(07:56:45) 이전. docs/18에 타임스탬프 명기.
- ⚠️ **arm C 설계 축소(결과 나오기 전 기록)**: 8세그 전부 의사라벨 → 패치탐색 세그당 13분·예상 1h32m·RSS 10GB로 불가 → **w00 1세그**로. 그 결과 config가 지도 FT arm과 **3키만**(`datasets`·`description`·`out_dir`) 차이 = 라벨 출처만 바뀐 순수 대조. 포기한 것(채점 세그 자체에 적응하는 transductive 이점)은 문서에 명시.
- ⚠️ `tools/make_pseudo_labels.py --probe`가 부산물로 낸 사실: **미학습 스크롤에서 모델 출력 전 범위가 0.17~0.89**(시트 픽셀 13억 개) → 사전등록한 0.9/0.1 규칙은 **양쪽 다 공집합**. 교차스크롤 실패는 "자신 있게 틀리는" 게 아니라 **자신감의 부재**. 규칙을 모델 자신의 0.5±0.1로 재중심화.
- 원수치: `armB_tent_matrix.csv`(34칸)·`armC_pseudo_matrix.csv`(18칸)·각 summary·`arm{B,C}_rank_check_*.json`·`runs/ink9um_tent_s4{2,3}/tent_trajectory.json`.

**2. 🔬 피라미드 풀링 — 우리가 늦었고, 그래서 배운 게 있다**

nerln이 #1582에서 "aligned가 여러 취득의 평균이라 SNR이 높다"는 기제를 내놓으며 **"피라미드가 평균인지 데시메이션인지 미확인"**이라 자기 유보 → 공개 데이터로 확인 가능하므로 확인함(`tools/check_pyramid_pooling.py`, 3스크롤×2레벨전이×3윈도우×3평면 = 18칸).

🔴 **그런데 Bullo27이 먼저 답했다(08-30 01:23 UTC, 우리가 쓰기 전)**, 그것도 더 정확하게. 두 가지를 우리가 놓쳤다: ①**per-level 반올림(round-half-up)을 모델링하면 max|diff| = 0**인데 우리 첫 판은 반올림을 안 넣어 0.50/87%를 "근사"처럼 적었다 — **데이터가 아니라 우리 측정의 결함** ②**zarr가 `multiscales[0].metadata.downsampling_method: "mean"`으로 스스로 선언**하는데 툴이 그 필드를 안 읽었다. 둘 다 반영해 재실행 → **18칸 전부 byte-exact(0, 100%)**, 데시메이션은 16~98.

- 남은 우리 몫: **피라미드가 XY 전용**(OME scale z가 모든 레벨에서 2.4 불변) → prepare의 `POOL_Z=4`가 **독립적인 두 번째 평균** → **aligned 복셀 1개 = 취득 복셀 64개의 평균**, native는 1개. **nerln의 16은 in-plane 절반.** ⚠️ SNR 8배는 주장 안 함(잡음 독립성 미측정) — 평균되는 필드가 평평하지 않다는 것만 실측(2×2 블록 내 sd 1.7~5.8).
- ⚠️ **교훈: 게시 직전에 스레드를 다시 읽을 것.** 초안 그대로 냈으면 남이 이미 올린 결과를 뉴스처럼 내는 꼴이었다.

**3. ✅ 업스트림 회신 2건 게시 + #1611 본문 정정 완료(사용자 직접)**

게시본이 로컬 초안과 **블록·수치 전건 일치** 확인(공백 정규화 대조, `scratchpad/compare_posted.py`; 머리말 유출 없음).

- **[#1582](https://github.com/ScrollPrize/villa/issues/1582#issuecomment-5466851322)**(05:09:36Z, 10블록·수치 75): Bullo27 결과 재현·크레딧 → 우리가 틀린 두 가지 인정 → 스레드에 없는 것만 추가(XY 전용 → 64배, arm A의 F1 증거).
- **[#1611](https://github.com/ScrollPrize/villa/issues/1611#issuecomment-5466851805)**(05:10:06Z, 8블록·수치 70): `docker image inspect`로 우리 바이너리가 그쪽이 지목한 리비전(`1e3f4c021…`, 2026-05-13, `sha256:bad516f6…`)임을 확인 → **"재시도 없음" 주장 철회**(그 리비전은 3회 재시도). 살아남는 건 무기한 `cv_.wait`(`render/ChunkCache.cpp:218/:749`)와 "캐시 클수록 악화".
- ✅ **약속한 이슈 본문·제목 수정까지 완료**: 제목에서 `with no retry or error` → `with no error`, 한 줄 요약을 "parks forever … instead of failing"으로, "What I expected"를 **bounded wait** 요청으로, 본문 최상단에 리비전·철회·`:edge` 정체 상태를 적은 Update 블록. **API 원문으로 검증**(인용 블록 `>` 유지, 죽은 앵커 `#issuecomment-latest` → 실제 ID `5466851805`). `submission/villa-issue-render-stall.md`가 게시본과 **블록 20/20 일치**.
- ⚠️ **초안에 플레이스홀더 링크를 두면 그대로 게시된다** — 실제 ID는 게시 후에만 알 수 있으니, 초안에 남길 때는 "게시 후 교체" 지시를 같이 적을 것.

**4. 🧾 9월 문안 최종 감사 → v8 (`submission/2026-09_progress_prize.md`)**

field 5의 **아티팩트 기반 수치를 전건 재산출**. 대부분 통과했고 **2건이 재현 불가라 원본에서 고침**:

- **arm A 회수율**: 기존 summary의 중앙값 8.4%/평균 −19.2%가 **어떤 분모로도 재현 불가**. 나머지(평균 Δ 0.0052, 범위, 17/24, 세그별)는 전건 재현되고 `−673%` 이상치가 w041 s42 10k(분모 0.0015)로 정확히 일치 → 분모 정의는 확정. **중앙값 9.1%/평균 −8.4%로 재계산**하고 정의와 셀 24개를 JSON에 저장. 판정 불변.
- **"스펙트럼 거리 38%"**: 뒷받침 아티팩트가 없었음 → 재산출(볼륨별 27.6~54.1%, **평균 37.7%** = 인용값, 풀링 35.7%)해 `runs/spectra/filter_effect_native0139.json`에 저장하고 docs/18에 정의 명기.
- 그 외: docs/14 상한을 정확값(0.755/0.758/0.765) 병기, arm B의 AUC·"자명하한" 서술을 실제 측정 범위로 축소, 증거 파일 수 60·채점 셀 1,612로 갱신, **링크 17개 전부 200**, 업스트림 라벨 4개 실제 상태와 일치 확인.
- **Step 3 "제출 당일 체크리스트"** 추가(폼 새로 받기 → 업스트림 라벨 재확인 → push → 검증 스크립트 재실행 → 복붙 → 제출본과 동기화·동결). field 4/5 sha256도 파일에 기록(본문+개행 1개 규약).

**5. 🧹 공개 표면 정리**

`submission/README.md`가 **한국어 week-0 체크리스트**(닫힌 7월 폼·죽은 `src/infer.py`)였음 → **영어 색인**으로 재작성(라운드·PR·이슈 대응표). `todo.md`도 README 포인터로 대체. README에 **절 10(적응 사다리)** 추가, docs/16 결론에 사다리 포인터, `tools/README`에 신규 툴 4종 문서화.

**6. ⚠️ 함정 4종(오늘 실측)**

1. **GPU 경합은 이 방에서 실재하고 양상이 둘이다** — 다른 프로젝트(`whest-starterkit`) CUDA 워커가 카드를 31.8/32.6GB·99%까지 채우면 추론이 **42 → 4~5 block/s**(2.5분짜리가 50분)로 떨어지고, 학습은 **`CUDA error: resource already mapped`**(pin memory 스레드)로 죽는다. 남의 잡을 죽이지 말고 **재시도 가능한 드라이버**로 넘길 것(arm C seed 43이 2회 실패 후 카드가 비자 19분에 완주).
2. **긴 heredoc은 Bash 도구에서 잘린다**(~150줄): `python - <<'PY'`가 중간에서 끊겨 `unexpected EOF`. **긴 문서는 Write로 파일 만들고 짧은 스크립트로 삽입.**
3. **`OmeZarrBlockDataset`의 meta 길이가 트리마다 다르다** — `external/villa` 4필드, `D:/vw2` 5필드. `meta[:4]`로 언패킹.
4. **WebFetch 요약은 문자 단위 질문에 신뢰할 수 없다** — 같은 URL에 대해 "`>`로 시작하는가"에 상반된 답을 냈다. **서식·바이트가 걸린 검증은 `curl`로 API 원문을 받아 직접 파싱할 것.**

#### 2026-08-29 (오후) — 9월 트랙 4개 전선

**사용자 결정(08-29)**: 9월은 **①코퍼스 검증 인프라 먼저 → ②남는 시간 UDA**. 실행 순서 = 문서 영어화 → 누수 감사 업스트림 → 라벨효율 결과 → UDA.

**1. 🚨 문서 언어 — 오늘 찾은 것 중 상금 기대치를 가장 크게 움직임**

7·8월 심사 대상(docs/08~12)은 전부 영어인데 **9월 문서(13~16)는 전부 한국어**였고, 더 중요하게 **README가 136/180줄 한국어**였다 — **field 4의 첫 링크가 저장소 랜딩 페이지**이므로 7월·8월 심사자도 한국어 페이지를 봤다. ✅ **docs/13·14·15·16·17 + README 전부 영어**(`a85121e`·`d448c96`·`1a8fa44`). 번역 검증은 눈이 아니라 **원문과 숫자 토큰 다중집합 대조**(차이는 한국어 서수·`2.5k`→`2,500` 표기뿐). docs/01~04·06·07은 사실 문서라 **한국어 유지(사용자 결정)**. → **규칙: 제출 링크에서 도달 가능한 것은 전부 영어.**

- 같은 패스로 **`docs/05_strategy.md` 정리**(`65528fc`): 공개 파일인데 ①**실명 경쟁자 표**(Bullo27 포함 — 그 사람은 이후 우리 수치를 재현하고 우리 PR을 리뷰해줌) ②상금 등급 산술 ③개인 정보(다른 대회 일정·`pcbviewer`·`ETRI`)를 싣고 있었다. 전부 제거, 실명은 docs/12·15에 **크레딧으로만** 남김. ⚠️ **git 히스토리엔 옛 내용이 남아 있다** — 재작성 안 함(제출에 인용된 공개 저장소를 force push하는 게 더 나쁨).

**2. 🔬 held-out 마스크 감사 → [#1638](https://github.com/ScrollPrize/villa/issues/1638) 게시 완료**

`docs/17` + `tools/audit_holdout_masks.py`(`ab4a64a`·`37ddec5`). ink_9um 29세그 중 **검증 마스크는 3개뿐**이고 **3개 전부 주석 영역 *내부*를 가른다**(w016 3영역 중 2개, 0814는 주석 전체가 1영역, w029 8개 중 1개). **w016은 누수 없는 held-out을 아예 만들 수 없다** — held-out의 99.1%가 학습픽셀 256px 이내이고 그 바깥 1,595px엔 잉크가 0개.

- **누수가 점수를 올리는지를 GPU 없이 판정**: 캐시된 예측에 (a)그 세그를 학습한 공개 ckpt와 (b)그 스크롤을 통째로 안 본 우리 LOSO arm이 둘 다 있다. 같은 거리 계층으로 채점 → **대조군은 평평한데(w016 0.5356/0.5399/0.5786) 공개 모델만 가까울수록 이득이 커짐** → 인접 계층 **초과 이득 +0.1375(w016)/+0.0733(w029)**. 체크포인트별 20/28이라 **주장은 directional까지만**: "docs/14의 0.74–0.77은 보수적이 아니라 낙관적 읽기". 정확한 보정치는 주장 안 함.
- 게시 전 검증: 기하표 21값·거리표 15값·계층표 35값 **전건 일치**, 링크 5개 200, villa 검색상 중복 없음. 게시본에 머리말 유출 없음.
- 🔴 **#1638은 게시 당일 닫히고 잠겼다(2026-08-29, `pmh47` = Paul Henderson, Research Team Lead).** 코멘트: *"disjoint니까 실제 이슈가 아니다. intra-segment / inter-segment / inter-scroll을 구분해 신중히 해석하고 과도하게 넓은 주장을 안 하면 문제없다."* **그가 맞다** — disjoint면 그 픽셀로 학습한 적이 없고, intra-segment held-out 수치는 그렇게 이름 붙이면 정당하다. **문제는 우리 제목의 "leak-free"**가 누수를 전제한 것(본문은 그렇게 주장 안 했는데 제목이 앞서 나감). `state_reason: not_planned` + **`locked: true`** → 회신 불가이고, **다른 스레드로 옮기지도 말 것**(잠근 직후 우회는 답을 안 받는 모양). 회신 초안은 `submission/issue1638_reply_pmh47.md`에 **미게시 기록**으로만 보존. 닫힘이 건드리지 않은 것 = **인접성이 실제로 점수를 올린다는 측정**(+0.14, 대조군 평평) → docs/17·9월 문안을 "0.74–0.77은 **intra-segment 상한**"으로 재프레이밍함.
- ✅ **#1231에 포인터 코멘트도 게시**(초안과 바이트 동일). #1231의 원래 질문(마스크 없는 26세그가 의도인지)은 **닫지 않고 살려둠**. 새 이슈로 간 이유 = 주장이 다름(#1231 "마스크가 **없다**" vs #1638 "**있는** 마스크가 영역을 가른다").
- ⚠️ **함정: GitHub 프리필 본문을 덮어쓰면 이슈 템플릿이 통째로 사라진다.** 초안에 `- [x] I personally encountered or reproduced this…`를 안 넣어서 게시 후 편집으로 추가했다. **앞으로 villa 이슈 초안엔 이 줄을 반드시 포함.**

**3. ✅ 라벨효율 곡선 — 완료(10:20~20:59, GPU 10h40m)**

`tools/make_label_budget.py`로 w00 주석의 **중첩 부분집합** 3개(achieved 50.3%/20.7%/13.5%, 잉크밀도 0.2284/0.2462/0.1956 vs 전체 0.2303). 100% arm과 **config 차이가 `datasets`·`out_dir`·`description` 셋뿐**. 검증 = 패치 수 6,308 → 3,174(정확히 비율 일치). 6런 × 10k step + 7 미학습 세그 × step 2500·5000 = **84칸**.

| arm | 주석량 | 이득 유지율 | ΔF1 vs 100% | 노이즈 초과 |
|---|---|---|---|---|
| keep0500 | 50.3% | **89.3%** | **−0.0333** | 6/7 |
| keep0250 | 20.7% | 70.8% | −0.0902 | 7/7 |
| keep0125 | 13.5% | 55.8% | −0.1386 | 7/7 |

**판정: "절반이면 충분"이 아니라 "절반은 싸다".** 주석 절반이면 F1 0.033 잃고 이득 89% 유지 — 노이즈 위지만 주석 노동이 반이 되는 값으론 쌈. 그 아래로 꺾임(1/5에서 71%, 1/8에서 56%). **세그먼트별 편차가 3배**(w09 93.5% vs w07 82.7%)인데 자명하한으론 설명 안 됨. **주석이 적을수록 빨리 과적합**(13.5%만 step 5000이 2500보다 −0.027). → `docs/15` **5부**, 원수치 `labelbudget_matrix.csv`+`labelbudget_summary.json`.
⚠️ 20.7% s43이 step 1,455에서 DataLoader `MemoryError`로 사망 → 드라이버 재시도로 완주. 런당 38~67분(3.3~8.8 it/s).

**4. 🔭 UDA 사전등록 = [docs/18](docs/18_uda_design.md)** (`ecd6a41`, **arm 실행 전** 커밋)

프레임 = **LOSO를 UDA 테스트베드로**: 타깃 **이미지만**으로 적응 → 끝까지 감춘 라벨로 채점 → **0.487→0.822 격차의 몇 % 회수**로 보고. 하드 규칙: **타깃 supervision mask를 적응에 쓰면 안 됨**(진짜 미지 스크롤은 어디가 주석됐는지도 모름).

- **표준 수법 둘이 아키텍처상 배제됨**: InstanceNorm2d 62 + 3d 2개에 **running-stats 버퍼 0개**(AdaBN 불가), 입력이 **패치 단위 robust MAD** + InstanceNorm으로 두 번 정규화(밝기 정합 무의미). 남는 건 **정규화 affine 27,712개(34.5M의 0.080%)**와 밝기 아닌 입력 작업.
- 예측 커밋: **A** 스펙트럼 매칭 0~20% · **B** 엔트로피 최소화 10~40% · **C** 의사라벨 자가학습 −10~+15%(**실패 예측** — docs/15가 격차를 편향으로 측정했으므로. 되면 편향 해석이 반증되는 거라 그게 더 흥미로움).
- 🔬 **`tools/spectrum_match.py`가 이미 결과를 냈다**(`02f8e98`·`2ed6507`·`b50c69d`): aligned와 native가 **겹침 없이** 갈린다(aligned 전부 0.0278+, native 전부 0.0262−), 그리고 **PHerc1447 렌더가 native 밴드 안(0.0248)**. 즉 docs/16에서 안 읽힌 그 스크롤이 입력 관점에서 **docs/15가 더 나쁘다고 측정한 계열**이고, **부록2의 "aligned 계열로 렌더하라"는 1447에서 따를 수가 없다** — 8.640µm 스캔 하나뿐이라 풀링할 고해상 원본이 없다. 결핍이 렌더 설정이 아니라 데이터에 있다.
- arm A 테스트베드(0139 w035/w039/w040/w041 = 두 표현 다 존재, 마진 +0.028~0.066이 나흘 전 측정됨)는 **스펙트럼을 본 뒤 선택** → 경위를 docs/18 부록에 기록, **예측은 안 바꿈**. 드라이버는 라벨효율 뒤에 큐잉(`runs/ink9um_armA_driver.log`), raw native 예측은 no0139 매트릭스 것 재사용이라 **필터본만 GPU를 씀**.

**4-결과. arm A = 효과 없음(사전등록 예측 적중)**

48칸(0139 w035/w039/w040/w041 × seed 2 × step 3). **평균 Δ +0.0052**(노이즈 0.03의 1/6), 17/24 칸에서 필터 우세, **회수율 중앙값 9.1%**(예측 0~20% 안). 4세그 중 3세그가 ±0.002 안, 유의미한 건 w039(+0.019) 하나 → 일관성 요건 미달. **규칙대로 "효과 없음"으로 보고.** ⚠️ 평균 회수율(−8.4%)은 인용 금지 — w041 s42 10k의 분모가 0.0015라 −673%가 섞임. ⚠️ **이 두 통계는 2026-08-30에 재계산됨** — 최초 summary의 중앙값 8.4%/평균 −19.2%는 어떤 분모로도 재현이 안 돼 폐기하고, 정의(셀별 `(filtered − raw) / (aligned − raw)`)와 셀 24개 전부를 JSON에 저장했다. 나머지 수치(평균 Δ, 범위, 17/24, 세그별 평균)는 전건 재현되고 판정도 그대로.
→ **스펙트럼 차이는 실재하지만(겹침 없이 분리, 필터가 거리의 38% 닫음) F1은 안 움직인다** = aligned 우위는 우리가 잰 반경 파워 스펙트럼에 담겨 있지 않다. PHerc1447엔 함의가 강해짐: native 계열이 맞고, **고해상 스캔도 없고, 필터로 대체할 수도 없다.** docs/16의 "무라벨 도메인 적응 선행" 결론이 값싼 대안 하나를 제거한 채 살아남음. arm B·C는 미실행. → `docs/18` 말미.

**9월 문안 = v6**(`fd08321`): field 4에 docs/17·감사툴·#1638 추가(**11개 링크 200 확인**), field 5에 감사 문단을 **groundwork 바로 뒤**에 삽입(그 문단이 딛고 선 마스크를 검사한 것이므로), 증거표 2행, field 6을 8월 폼 구조(6문항)로 갱신.

#### 2026-08-28 — 독립 채점 도착, 그리고 #1608 첫 리뷰

- 🔬 **stantheman0128의 D/FWHM 채점 결과(08-25 게시, [#192](https://github.com/ScrollPrize/villa/issues/192))** — 우리 `submission/depth_anchors/` w00 export를 독립 1.129µm 스캔에 대고 채점. 중심셀 5,396개 중 1.129µm footprint에 걸치는 게 164, 평가가능 157(6개 masked-zero, 1개 표면 부적격). **표면거리 D 중앙값 2.0복셀, D≤3이 118/157(75.2%), D≤1이 65개, FWHM 중앙값 2.71**(22개는 48에서 censored). 커버리지는 **region 15 하나뿐**(나머지 14개 영역은 footprint 밖). 본인 명시 = 기하만·잉크 정체 아님·v4가 왜 지는지는 설명 못 함.
  → **8월 문안 notes에 사전등록해둔 두 분기 중 "geometry-valid" 쪽**이므로 더 강한 읽기(정확한 픽셀별 밴드조차 고정 밴드를 못 이김)를 지지. field 5에 세 번째 검사 문단 + 증거표 1행 추가(카베앗 2개 포함), notes의 해당 항목은 resolved로 갱신.
- 🟠 **[#1608](https://github.com/ScrollPrize/villa/pull/1608) 첫 리뷰 = Bullo27(08-26)** — 쿼터 재현·재정규화는 검증 통과, 그러나 **진짜 버그 1건**: `renormalise`가 `batch_size < 생존 스크롤 수`면 전 항목이 `max(1,…)`로 1이 돼 트림 루프의 `max()`가 빈 시퀀스 → `ValueError`. **수정 푸시 완료(`dc9edb6`, +13 −3)**: 가드 + 저쪽 제안 문구(클래스명은 실제 이름 `FixedScrollPriorStratifiedBatchSampler`로). 이유 = `samplers.py:84`가 0 쿼터를 거부하므로 바닥 1은 못 걷어냄 → 쓸 수 있는 config가 없고 거절이 정답.
  - 저쪽이 "미검증"이라 한 브랜치를 **실데이터로 전부 실행**: `--exclude-segment` 4개 = 25 rep·쿼터 동일·`dataloader_workers` 빼고 바이트 동일 / zarr 탐색 **두 분기 모두 실코퍼스에서 발동**(aligned9는 `<seg>.zarr`, native9는 `<seg>/<one>.zarr`) / `--allow-missing`에서 **두 번째 워트 발견** — 아무것도 못 찾으면 `error: every scroll was excluded`(거짓)를 뱉던 걸 루트 2개를 지목하도록 수정. LOSO 3개 config는 수정 후에도 **바이트 동일 재생성**.
  - 템플릿 지적("체크박스 미체크")은 **오해** — 저쪽이 본 건 GitHub 프리필이고 본문은 개설 직후 덮어썼음(현재 body에 `- [x]` 확인). 회신에 사과 한 줄로 처리.
- 📄 **9월 문안 v3(커밋 `5ef99ee`)**: Step 1(6번 칸 PR)이 **#1608로 해소**(OPEN 아님), field 4에 링크 추가, field 5에 문단 1개 추가 — *레시피는 그대로 안 돌아가고 그 조인이 #1608이며, 같은 기여자가 원 매트릭스로 공개 수치를 재계산한 뒤 생성기를 리뷰해 크래시를 찾았다*(⚠️ Bullo27 **동일인**임을 명시, 두 사람인 척 금지). 증거표 2행 + notes(“stantheman 채점은 8월 것, 9월에 반복 금지”).
- ⚠️ **과거 게시 코멘트에 초안 머리말이 HTML 주석으로 딸려 들어가 있음**(#1580·#1582). 렌더링엔 안 보이나 raw엔 남음 — 수정할 필요는 없고, **앞으로는 오늘 방식(`---` 아래만 붙여넣기)** 유지. 오늘 2건은 바이트 동일 확인됨.
- 🔭 **남은 선택지(9월용, 미착수)**: **라벨 효율 곡선** — `make_validation_mask.py`가 떼어낸 영역을 학습 supervision에서 0으로 만드는 성질을 이용해 w00 주석의 50%/25%만으로 FT(2,500 step 포화, arm당 ~7분) → 미학습 7세그 채점(인퍼런스 회당 ~2분). **총 1.5~2h 무인.** 어느 쪽으로 나와도 씀(절반이면 충분 / 1세그가 하한). 리스크 = ink_9um 마스크 피라미드 레벨 차이로 `--level` 조정 필요할 수 있음 + 패치 캐시 때문에 **새 out_dir 필수**.
- 🟠 **[#1611](https://github.com/ScrollPrize/villa/issues/1611)에도 Bullo27 답**(08-26, 우리 회신 08-28 게시): 청크 fetch는 이미 3회 재시도·60초 타임아웃이 있고 진짜 원인은 `ChunkCache.cpp`의 무기한 `cv.wait` 4곳(weak_ptr 만료 시 아무것도 스케줄 안 되고 `completed`가 false로 남음)이라는 진단. **그런데 우리 체크아웃엔 그 파일이 없다** — `merge-ink-pipelines`의 캐시는 `core/src/cache/`(`TieredChunkCache.cpp` 등)이고 `CURLOPT_TIMEOUT`은 **30**, 재시도 루프는 없으며(`TieredChunkCache.cpp:320` = "Fetch failed — remember so we don't retry"), 조건변수는 캐시에 아예 없음(`wait(lock`은 트리 전체에서 `utils/priority_queue.hpp` 하나). `main`엔 `core/src/cache/` 디렉터리 자체가 없음. → **ref 핀 요청**을 회신의 본체로 삼음(우리가 돈 건 소스빌드가 아니라 `:edge` 이미지라 그쪽 ref도 미상). 캐시 클수록 악화(24GB 100–130청크 vs 8GB 361·540청크, 실 RSS 1.2GiB)는 **동기화 버그 쪽을 지지**한다고 확인해 줌.
- ⚠️ **함정**: `cp -r`로 라벨 트리 사본을 만들려다 2분 타임아웃 — ink_9um 라벨 루트는 통째 복사 금지. 부분 코퍼스 테스트는 **`--volumes-root`를 `aligned9`로만 겨누면** 복사 없이 5개 native rep이 미탐지가 됨. (그때 남은 잔해 `scratchpad/h/partial`은 rm/PowerShell 둘 다 "not empty"로 못 지움 — 세션 임시 디렉터리라 방치.)

#### 2026-08-26 (밤) — First Letters 렌더 경로 실행: 경로는 뚫렸고 글자는 없다

사용자가 WSL2 + Docker Desktop 설치 → docs/13 §6의 B안을 끝까지 실행. **전문 = [docs/16](docs/16_first_letters_render.md).**

- **경로 전 구간 실측**: `S3 mesh 0.6MB → vc_render_tifxyz 원격 스트리밍 25분 → 표면볼륨 389MB(L0–L5) → 추론 47초(66 block/s)`. 이미지 `ghcr.io/scrollprize/villa/volume-cartographer:edge` 12GB. **렌더러 출력이 우리 `infer`에 무수정으로 꽂힌다**는 docs/13 예측 적중(`[28,3700,5460]`, chunk `[28,128,128]`, native9 계약과 동일).
- **타깃**: PHerc1447 15세그 전부의 `meta.json`을 받아 면적 순위 확정 — 1위 `20250703034159-auto_grown_20250703034159599` **7.40cm²**(정찰 땐 수치만 있고 ID가 없었음). 볼륨은 `PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr` 하나뿐.
- **결과 = 판독 불가**(공개 ckpt 4개, seed42·43 × 10k·20k). 신호 없음의 서명 4가지: ①>128 비율이 **6.5%~21.3%로 3배 엇갈림** ②**max가 255에 못 미침**(211–246) ③p50 76–91로 표면 절반이 중간 회색(이봉분포 아님) ④non-zero가 넷 다 67.034% = **모델 출력이 아니라 렌더 유효영역**(탐지율로 오독 금지). 원해상도 700px 크롭에서도 **둥근 무정형 얼룩이지 연결된 획이 아님**; 두 ckpt가 굵은 배치는 일치·세부만 다름 → 둘 다 표면 기하에 반응 중.
- **함의**: docs/15의 cross-scroll 마진(+0.06~0.17)이 이미지로 확인된 셈. ⚠️ **그런데 스카우팅이 3단계로 못 넘어간다** — "유망 세그먼트에 주석"인데 **어디 주석할지 예측이 안 알려줌**. 라벨 없는 스크롤엔 **무라벨 도메인 적응이 선행**돼야 하고 그건 별개 과제. 9월 문안 field 5에 이 음의 결과를 그대로 실었다(레시피가 준비됐다는 인상 금지).
- 🟢 **부산물 = [#1611](https://github.com/ScrollPrize/villa/issues/1611)**(08-26 게시, 체크박스 ✓): 원격 스트리밍 순단 시 **재시도·에러 없이 무한 대기**. 증거 = 진행률 붕괴 로그 + 60초간 청크0/캐시0/CPU 4~6%/메모리 1GB + 4회 모두 **다른 지점**(10/17/20/27%)에서 정지. 우회로(`--timeout`+`--resume` 체인)와 그게 완주시킨 증거 포함. 원본 = `submission/villa-issue-render-stall.md`. 힙 손상은 5회 중 1회라 **별도 파일링 안 함**(재현 안 되는 걸 따로 내면 fishing으로 읽힘).
- ⚠️ **렌더 함정**: ①추론 경로는 **반드시 Windows 형식(`D:/...`)** — Git Bash `/d/...`를 주면 **에러 없이 즉시 종료**(출력 0개) ②**`--cache-gb`는 작을수록 낫다**(24GB: 회당 100~130청크 / 8GB: 361·540청크로 2회 완주). 실사용 RSS는 1.2GiB뿐 ③**피라미드는 증분 생성**되니 타임아웃으로 끊어도 남음 ④`-v` 스테이징 캐시에는 아무것도 안 쌓임 → 없는 경로에 `--resume` 걸면 무출력 정지 ⑤Docker 디스크는 D:로 이전함(`D:\docker`, Settings→Resources→Advanced). 배포판 자체는 여전히 C:.
- **남은 14세그도 개당 ~30분이면 가능**하나 같은 결과일 확률이 높다고 판단, 진행 안 함.

#### 2026-08-26 — 우리 해석이 반증됨(사전등록), 그리고 9월 PR

- 🔬 **domain match 기각.** nerln이 #1580 스레드에서 [#1582](https://github.com/ScrollPrize/villa/issues/1582)를 떼어 열면서 Bullo27의 미해결 caveat("ref arm은 뭘 학습했나")를 물려받음. 우리 답 2단계:
  ①**ref = 공개 체크포인트**이고 계약은 aligned 24 + native 5인데 **native 5개가 정확히 0139의 w035/w039/w040/w041/w044** → ref는 비교 4세그를 두 계열 다 봤음. 그러나 ref는 자기 학습 픽셀에서 채점돼 **가용 헤드룸의 90.7~96.8%를 소진**한 상태라 +0.05가 나타날 자리가 없음 → **통제군으로 무력**.
  ②**그래서 arm을 하나 더.** w035·w039를 **두 계열 모두** 제외(25 rep 학습, native w040/w041/w044 잔류 → native가 **학습 배치의 16.4%**, 기존 arm은 0%). 설계와 각 결과의 해석을 **결과 전에 공개 푸시**(`fb37974`) = 타임스탬프 사전등록. 결과 **Δ +0.058 vs 기존 +0.061**, 즉 −0.003. 선택 규칙 전부·체크포인트 7개 각각에서 2/2.
  → **원인은 계열 일치가 아니라 표현 품질**(aligned = 2.399µm를 z 4배 풀링 vs native 9.362µm 단일 취득). 지침은 **"aligned 계열로 렌더하라, 학습 코퍼스가 무엇이든"**. docs/15 부록 2 · 9월 문안 · [#1582 코멘트](https://github.com/ScrollPrize/villa/issues/1582)(08-26 게시, 스레드 첫 코멘트, 원본 `submission/issue1582_comment.md`)에 전부 정정. ⚠️ **이 코퍼스는 계열 균형 arm을 만들 수 없음**(native 5개가 전부 한 스크롤).
  원수치 = `runs/ink9um_scorecard/segloso_matrix.csv`(56칸) + summary, config = `configs/ink9um_segloso_w035w039_s{42,43}.json`.
- 🟢 **9월용 PR = [#1608](https://github.com/ScrollPrize/villa/pull/1608)**(08-26 오픈, base **`merge-ink-pipelines`** — `ink-detection/scripts/`는 `main`에 없음). `scripts/make_holdout_config.py` 1파일 +211. **공개 레시피는 그대로는 안 돌아감** — `aligned21_hybrid_3d2d.json`의 `datasets`가 `/path/to/` 플레이스홀더 1개뿐이고 29표현은 계약 파일에 따로 있음. 이 조인 + `--exclude-scroll/--exclude-segment`. 증거 = 우리 LOSO arm 3개 config를 **바이트 동일 재생성**, segloso는 `dataloader_workers`만 차이. 본문 사본 = `submission/pr1608_body.md`, 워크트리 `D:/vw3`.
- ⚠️ **새 함정 5종**:
  ①**`external/villa`로는 ink_9um config를 못 돌린다** — 스키마 이전 체크아웃이라 세그먼트 0개로 죽음. `cd D:/vw2/ink-detection && uv run --project <repo>/external/villa/ink-detection --no-sync python -m ...`
  ②실패한 런이 **빈 패치 캐시(2바이트)를 out_dir에 씀** → 지우지 않고 재실행하면 엉뚱한 이유로 같은 실패
  ③**Windows DataLoader가 첫 체크포인트에서 `error 1455`**(ERROR_COMMITMENT_LIMIT)로 죽음 @ `dataloader_workers: 12` → **6이면 통과**(두 시드 각 ~3h55m, 6.5 it/s). 워커는 I/O 파라미터라 결과 무관하나 보고 시 명시
  ④**GitHub은 새 PR 본문을 커밋 메시지 + 빈 템플릿으로 미리 채운다** → 준비한 본문은 **연 뒤에 덮어써야** 함(안 하면 #1434가 닫힌 그 모양)
  ⑤**WebFetch는 URL당 15분 캐시** → 행동 직후 같은 API를 다시 부르면 옛 답이 옴. 쿼리 파라미터를 바꿔 캐시 우회
- 🟢 **커뮤니티 견인 증거**: Bullo27이 `no0139_matrix.csv`를 받아 **공개 수치 전부를 정확히 재계산**하고 선택 규칙 4종에도 살아남음을 보임. nerln은 우리 결과를 "real"이라 하고 #1582를 개설. 채택 축의 실증.

#### 업스트림 정찰 (2026-08-24) — 새 움직임 3건, 코퍼스 무결성 2건 확인

- 🔔 **[#192](https://github.com/ScrollPrize/villa/issues/192): stantheman0128이 채점 착수 선언(08-23)** — `submission/depth_anchors/`의 w00 export에 D/FWHM을 돌리겠다고 명시. 좌표 포맷 질문의 답 = **sidecar 규약(법선 부호·레이어 스텝) 그대로 쓰고, 안 맞으면 변환을 지어내지 않고 말하겠다** → **우리가 준비할 데이터 없음**(앵커 CSV/JSON 둘 다 origin/main에 공개 확인). 저쪽 저장소는 08-13 이후 푸시 없음 = 아직 실행 전. ⚠️ 그 08-13 커밋에 "w00 depth-validated label generator"가 있음 → 저쪽이 검증된 w00 라벨을 내면 **우리 v4가 못 가졌던 비순환 arm**이 되므로 하네스로 바로 태울 것.
- ✅ **코멘트 2건 게시(2026-08-24, 사용자 직접)** — 본문 원본 = `submission/pr1580_comment.md`, `submission/pr1471_comment.md`. 게시본이 로컬 초안과 바이트 동일함을 확인.
  - **[#1580](https://github.com/ScrollPrize/villa/pull/1580)**(nerln, 08-24 오픈): `prepare_9um_isotropic_input` 출력이 레시피 스케일과 어긋나면 리포트. 우리 코멘트 = **aligned(level 2, 9.596µm)와 native(9.362µm)는 둘 다 그 체크를 통과하는데도 전이가 다르다** — 0139 4세그 aligned 4/4 우세(+0.028~0.066 마진), 표는 `no0139_matrix.csv`에서 재계산해 docs/15와 일치 확인. ⚠️ **9월 니치 혼잡 신호**: nerln·Bullo27·TAUIL이 사전등록→독립재현→PR을 하루 단위로 돌리는 중.
  - **[#1471](https://github.com/ScrollPrize/villa/pull/1471)**(jaideepsaipadhi, 우리 #1231 인용): **파이프라인 사본이 둘**이라는 게 핵심 — `main`은 `vesuvius/src/vesuvius/ink_detection/preprocessing/create_label_zarrs.py`(아직 `is_tiled` 게이트 + `build_pyramid_with_mode` = 레벨마다 (65,H,W) 임베딩), `merge-ink-pipelines`는 우리 #1234로 수정됨. **저쪽 strip 스트리밍이 level-0 읽기에선 우리보다 나음**(우리는 이미지를 통째로 읽어 피크 RSS 1.99GiB). 저쪽 멀티페이지 버그가 우리 머지 사본에도 있음을 재현((5,40,60)→(5,40)). 게시 시점에 리뷰어 `jrudolph`·`bruniss` 배정돼 있음.
- 🟢 **우리 코퍼스 무결성 2건 확인 — 둘 다 무영향**:
  - [#1547](https://github.com/ScrollPrize/villa/issues/1547) PHerc0139 **w045/w046 중복**(정점 81.5% 동일) → 우리 0139는 w016/17/28/29/35/39/40/41/43(+native w044)이라 **미포함**. w044는 인접 대조군 <5%로 깨끗.
  - [#1551](https://github.com/ScrollPrize/villa/issues/1551) `ink/1667/*` 메타의 `scroll_source: P.Herc. 0009b` → Bullo27이 **6개 전부 잘못된 템플릿이고 실제론 1667**임을 검증(volume 필드 + Scroll 4 레지스트리). 우리는 `PHerc1667/segments/...` 경로에서 받았으므로 **no1667 arm 라벨링 정상**. → 둔 건 모두 **docs/15 말미 "부록: 코퍼스 무결성 확인" 절에 기록함**(2026-08-24).
- ⚪ [#1231](https://github.com/ScrollPrize/villa/issues/1231) 여전히 코멘트 0(erdpx 배정 유지). 우리 저장소: 이슈 0·포크 0·스타 1.

0. 🔬 **추가 기여 3종 완료(2026-08-15~16)** — 상세는 memory `ink-pipeline-status` + `docs/12` 말미 2개 절:
   - **30k 연장**: 격차 +0.038→+0.036, fold별 개선 ≤+0.008 → "일찍 끊음" 반론 종결. 원수치 `runs/ink_depth_ext30k_summary.json`.
   - **w02 재현**: 전체 파이프라인을 w02(86.8GB, `data/ink-dataset/phercparis4_w02/`로 격리 — ⚠️`segments_path`는 폴더 안 모든 세그먼트를 잡으므로 부모 분리 필수)에 그대로 반복. 2D 베이스라인 **0.8235**(w00 0.8232와 0.001 차), QC 리본 합격. **v3 0.8263 vs v4 0.7287 = 격차 +0.098(w00의 2.5배), 완전 순서(최고 v4 fold < 최저 v3 fold)**. v4 spread 0.147·조기 정점(9000) = 불안정화. 카베앗: 측정 커버리지 64.6%, v4 예산 12% 얇음(클램프). 원수치 `runs/ink_w02_{v3,v4}_fold_cv_summary.json`.
   - **앵커 내보내기**: `tools/export_depth_anchors.py` + `submission/depth_anchors/`(7,005셀, 스크롤 좌표+법선, 미검증 가정은 sidecar 명시) — stantheman 회신 시 링크만 전달.
   - ✅ **#192 후속 코멘트 게시 완료(2026-08-16, 사용자 직접)** — 본문 원본 = `submission/issue192_followup_w02.md`. 30k+w02 결과 공유 + stantheman에게 앵커 준비됐음을 알림. 다음 = 회신 대기.
   - ✅ 디스크 정리 완료(08-16, 사용자 승인): 비최적 ckpt 437개 삭제·493GB 회수 → **537GB 여유**. 보존 = 요약에 인용된 best step 전부 + 각 런의 20000(resume·깊이측정 베이스).
   - 📌 **제출 8/24 재확인(2026-08-16, 사용자)**: "미리 내자" 논의 후 stantheman 채점·#1434 리뷰에 기회를 주기 위해 8/24 유지로 결정. 그날 = 업스트림 최종 확인 → 라벨 갱신 → 사용자 폼 복붙 제출 → 파일을 제출본과 동기화.

1. 🔔 **#192에 새 코멘트 2개(2026-08-13, 2026-08-14 발견)** — 우리 코멘트(08-09 게시, `submission/issue192_comment.md`)에 대한 직접 답변은 아니지만:
   - **stantheman0128**: #1295가 닫힌 사유("독립 3D 레퍼런스 검증")를 구현 — `transform.json` 어파인 체인으로 canonical↔독립 1.129µm 볼륨을 ~1복셀 정합(NCC 0.950), ink3d 예측 앵커의 표면거리 D·FWHM을 채점(142앵커 중 99개 D≤3복셀, p=4.1e-24; 52.8% localized+thin). 저장소 = stantheman0128/vesuvius-ink3d-depth-validation(MIT, CPU). **@khj1222 직접 멘션: "당신의 v4 measured band에 D/FWHM 채점을 돌려주겠다"** — 학습 없이 밴드 기하를 독립 스캔과 대조 가능. 본인 명시 경계 = 기하만 검증, 잉크 정체는 아님.
   - **pmh47 반박**: "1µm 스캔의 gradient peak ≠ 잉크 국소화 — 급격한 밝기 변화가 recto 표면이 아닐 수 있고, 잉크가 표면에 딱 붙지도 않는다(peeled away)."
   - ✅ **수락 답장 게시 완료(2026-08-14, 사용자 직접)** — 본문 원본 = `submission/issue192_reply_stantheman.md`. 논리: 채점 결과가 우리 음의 결과의 두 해석(①추정기 기하가 틀렸다 → #192 전제 생존 ②기하가 맞는데도 진다 → 더 강한 주장)을 가르는 유일한 비순환 검사. pmh47 카베앗은 "잉크 인증이 아니라 기하 일관성 확인 용도"로 수용. 실무 질문 1개 포함(앵커 좌표 포맷 — 표면볼륨 z를 `x/y/z.tif`로 스크롤 좌표 변환 필요). **다음 = 회신 대기, 포맷 정해지면 v4 밴드 데이터(CSV/zarr) 준비는 Claude 몫.**
2. ✅ **PR #1234 머지됨(2026-08-14 01:18 UTC, erdpx, 추가 코멘트 없이)** — 회신(08-09, `submission/pr1234_reply.md`)에 무응답이다가 그대로 머지. 제목·본문이 구버전 구현을 설명하는 문제는 머지로 소멸. **8월 문안의 #1234 라벨은 "merged 2026-08-14"로 갱신 완료(2026-08-14).**
3. ✅ **`flat_depth_targets` PR = [#1535](https://github.com/ScrollPrize/villa/pull/1535)(2026-08-19 오픈, 사용자 직접)** — base `merge-ink-pipelines`, 2커밋 3파일 **+112 −13**, mergeable. **선행 [#1434](https://github.com/ScrollPrize/villa/pull/1434)는 erdpx가 2026-08-18 머지 없이 닫음**(①`villa/CONTRIBUTING.md`를 따를 것 ②`mean` 축약 미검증이니 증거 없으면 빼라) → 둘 다 반영: `--z-reduce`·`_Z_REDUCTIONS` 삭제(항상 `max`) + 전체깊이 축약 시 경고 추가(커밋 `8922c5e`, 유닛테스트 7 passed), 본문은 실데이터 before/after 도판(`docs/images/w00_z_window_before_after.png` = held-out π, 같은 v4 fold1 step 17000을 z0–64 vs z16–48로 축약, F1 0.499 vs 0.814 — 디스크의 기존 예측 TIFF로 만들어 GPU 재실행 없음)과 함께 재작성. ⚠️ **#1434는 reopen이 불가능했음**(브랜치를 닫힐 당시 커밋으로 되돌려도 버튼 없음) → 같은 브랜치에서 새 PR로 감. ⚠️ **남은 것 = 본문의 "Why this matters to me" 문단**(CONTRIBUTING이 LLM 보조 PR에 사람 코멘터리를 명시 요구 — 사용자가 직접 작성 중) + #1434에 새 번호 알리는 포인터 코멘트. 절차·문안 전문 = `submission/villa-pr-flat-depth-targets.md`. ⚠️ **CONTRIBUTING.md는 upstream `main` 루트에만 있고 우리 체크아웃(`merge-ink-pipelines` 계열)엔 없어서 못 봤던 것** — 앞으로 villa PR 전에 `main`의 CONTRIBUTING을 먼저 읽을 것. 브랜치 `khj1222:feat/flat-depth-targets`(`8922c5e`) = 업스트림 tip `33c463e` 리베이스 + 충돌 3곳 해소 + 유닛테스트 7 passed + CPU 기능검증(z-window가 창 밖 노이즈 무시하는 것까지 더미로 실행 확인). **리뷰 수정은 워크트리 `D:/vw2`에서 커밋 → `git -C D:/vw2 push fork`** — PR 해소 전까지 D:/vw2 유지. 선택 사항이던 GPU 스모크는 CPU 검증으로 대체됨(남은 GPU 전용 = zarr 읽기·ckpt 로딩·CUDA, 충돌과 무관). ⚠️ vw2에서 테스트 돌릴 땐 `cd D:/vw2/ink-detection && uv run --project <external env> --no-sync ...` (`--directory`는 cwd를 옮겨 엉뚱한 트리 import).
4. ✅ **8월 제출 완료(2026-08-29)** — 아래는 제출 전 기록: 문안의 #1434 인용은 전부 **#1535로 갱신 완료(2026-08-19)**. 체크박스 요건은 #1249 머지로 이미 충족. 제출 직전 확인 = ①#1535 상태가 움직였으면 라벨 갱신 + "Why this matters to me" 문단이 실제로 채워져 있는지 ②stantheman0128의 v4 밴드 채점 결과가 나왔으면 5번 칸에 1문장 고려(파일 하단 notes). **제출 시점 = #1535 움직이면 그날 / 백스톱 08-29~30(2026-08-21 사용자 확정)** — 백스톱까지 반응 없어도 그대로 제출.

**#192 니치 상황(2026-08-09 조사)**: 선행 시도 2건 모두 닫힘 — [#923](https://github.com/ScrollPrize/villa/pull/923)(jonmarrs, 5월, 자칭 sketch, 하류 평가 없음) · [#1295](https://github.com/ScrollPrize/villa/pull/1295)(williamshermer-pixel, **2026-08-06 erdpx가 닫음** — 28쌍 중 2쌍만 제출 + 깊이 독립 검증 없음, CT 밝기로 밴드 배치). **둘 다 라벨 생성법만 냈고 학습해서 재보진 않음** → 우리 기여의 차별점이 "검증"이라는 게 확인됨. erdpx가 #1295에 요구한 게 정확히 "독립 검증된 깊이".

### ▶ ✅ 매트릭스 완료 (9런, GPU 16h, 2026-08-08~09)

재실행이 필요하면 (arm당 ~5.5h, fold당 ~110분 실측):

```bash
uv run --project external/villa/ink-detection python tools/run_cv_folds.py data/ink-dataset/phercparis4/w00_20231016151002 --folds 3 --config configs/ink_depth_v4.json --label-version v4 --prefix ink_depth_v4_fold --z-window 16:48 --sweep-every 2
```
(config·label-version·prefix만 교체. **`--z-window 16:48` 필수** — 아래 참조. **`uv run --project` 필수** — 드라이버가 `sys.executable`로 학습까지 띄우므로 시스템 파이썬으로 돌리면 즉시 실패)

| arm | 3-fold 평균 F1 | fold별 | spread |
|---|---|---|---|
| **v3 constant** | **0.8478** | 0.8455 / 0.8452 / 0.8528 | 0.0076 |
| v2 plane | 0.8441 | 0.8567 / 0.8259 / 0.8496 | 0.0308 |
| v4 measured | **0.8098** | 0.7997 / 0.8192 / 0.8104 | 0.0195 |

### 🔬 판정: 측정된 밴드가 **꼴찌** (v3 − v4 = **+0.0381**, v2 − v4 = +0.0343)

- **3 fold 전부 v4가 최하위.** v3와의 격차는 노이즈 기준선 ~0.03을 넘음(+0.0458 / +0.0260 / +0.0424). v2와의 격차는 fold 1에서 +0.0067까지 좁아지므로 **"v4 < v3"가 주장의 본체**, "v4 < v2"는 보조.
- **v2 ≈ v3 (차이 0.0037 = 무의미)** → **두께는 변수가 아니다.** 1복셀이든 8복셀이든 같은 점수. 손해는 8복셀 밴드를 **픽셀마다 움직일 때**만 발생.
- ⚠️ **v2의 spread가 0.0308**(v3의 4배) — 양성비 0.7%라 Dice+BCE에서 학습이 불안정. **v2 단일 fold 수치는 인용 금지**(fold 0의 0.8567만 보면 v2가 최고인 줄 착각하게 됨. 실제로 세션 중 그렇게 잘못 읽었다가 fold 1에서 뒤집힘).
- **v3 평균 0.8478 ≈ 7월 2D 베이스라인 0.8472**(차이 0.0006) → **깊이 타깃 자체는 무해**하고, 손해는 밴드를 픽셀마다 옮기는 데서 발생.
- **v3의 spread 0.0076**으로 7월(0.0154)보다도 안정적.
- **순환성이 오히려 v4에 유리했어야 함**(v4 밴드는 깊이 없는 라벨로 학습한 모델에서 측정) — 그런데도 졌으므로 self-distillation 변명이 성립 안 됨.
- **스케줄 아티팩트 아님**: 마지막 3,000 step 상승폭이 v3 +0.0075 / v4 +0.0068로 비슷한데 격차는 그 5배. **결정타 = 30k 연장(2026-08-15)**: 6런 전부 ckpt_020000에서 full-state resume로 +10k 연장(GPU 5.8h) → 격차 +0.038(≤20k) → **+0.036(연장 포함)**, fold별 개선 최대 +0.008로 노이즈 안. "일찍 끊었다" 반론 종결. 상세 = `docs/12` 말미 "The stopped too early check", 원수치 = `runs/ink_depth_ext30k_summary.json`.
- → **#192의 전제("정확한 3D 라벨이 성능을 올린다")가 이 세그먼트에서 지지되지 않음.** 단, "#192가 틀렸다"가 아니라 **"이 경로로 만든 밴드가 고정 밴드를 못 이긴다"**로만 주장할 것. 상세·유보 = `docs/12` "The result: the measured band loses".

- ⚠️ **채점에 `--z-window 16:48`이 없으면 결과가 무의미하다**(2026-08-08 실측). 추론이 z를 **0–64 전체 max**로 접는데 supervision은 **z16–48 기둥뿐** → 무감독 32장에서 잉크·배경 모두 0.6~0.93으로 포화, max가 그걸 끌어올림. 같은 ckpt·같은 픽셀에서 **F1 0.535(전체 z) vs 0.802(z16–48)**. 증상 = **best threshold가 254에 못박힘**. v4 첫 실행은 이걸로 0.4708/0.5122/0.5308이 나왔고 재채점으로 위 표가 됨(체크포인트는 무사, 재학습 불필요). 상세 = `docs/12` "The reduction has to match the supervision".
- 전체-z 원본 숫자는 `runs/*/validation/`, 유효 숫자는 `runs/*/validation_z16_48/`에 보존. 종합 = `runs/ink_depth_v4_fold_cv_summary_z16_48.json`.
- **v4 best step이 19000–20000(아직 상승 중)** — 7월 2D 런은 17000 정점 후 하락. 볼륨 타깃이 느리게 수렴. 스케줄은 arm 공정성 때문에 20k 고정 유지.
- ⚠️ **v4의 0.8098을 7월 0.8472와 직접 비교 금지** — 학습 모드(2D 타깃·네트워크 내 z projection)와 라벨이 동시에 다름. 판정은 **v4 − v3**(~0.03 노이즈 기준).
- **디스크**: 9런 합계 ~195GB 소비(ckpt 1.08GB × 20 × 9). 2026-08-09 시점 D 여유 ~520GB.
- ⚠️ `save_every`를 늘려 디스크를 아끼지 말 것 — 최적 step이 17000~20000에 걸쳐 있다.
- ⚠️ **GPU 경합 주의**: 게임 클라이언트 등이 떠 있으면 3.0 → 1.1 it/s로 3배 느려진다(결과엔 무영향, 시간만). fold 0(v3)만 210분, 나머지는 105~125분.
- ⚠️ **`external/villa` 작업트리의 미커밋 변경(train.py·infer.py·test_train.py)은 리베이스 전 구버전** — 커밋된 정본은 워크트리 `D:/vw2`의 `feat/flat-depth-targets`(`8515746`, 2026-08-13 푸시됨). `submission/villa-flat-depth-targets.patch`도 리베이스 후 버전으로 재생성됨(+129 −13). external/villa 쪽은 로컬 재실행용으로만 유효.

## 깊이 국소화 프로토타입 (2026-07-27, 8월 트랙 1주차)

- ✅ **`tools/depth_profile.py`** — 학습된 모델에 z별 잉크 근거를 물음. ①**occlusion**(4장 밴드를 지움 = 필요성) ②**window**(그 밴드만 남김 = 충분성). 둘 다 **잉크픽셀 vs 같은 마스크 안 배경픽셀**로 이중 측정(대조군). 지움값 = robust 정규화 **후** 0.0(패치 중앙값). 블록당 32변형을 같은 패치로 재사용 → 감독영역 전체 ~17분(756블록/2,190만 잉크픽셀). 산출: JSON/CSV + 곡선 PNG + **픽셀별 깊이맵 2종**(occlusion 기반이 유효, window 기반은 노이즈).
- ✅ **`tools/depth_contrast.py`** — **모델 없이** 원본 CT만으로 z별 잉크 vs 배경 대조. 평균차 + **AUC**(공통 드리프트 상쇄). GPU 불필요, ~12분. 순환성 방어의 핵심 축.
- **실측 결론(ckpt_020000, 감독영역 전체)**:
  - 모델: baseline 잉크 로짓 +2.879 / 배경 −3.087. occlusion 잉크특이성 최대 **z24–28**(−0.474), window 분리 최대 **z16–24**(+1.863) 후 깊을수록 단조 감소(z56–64는 +0.08). → 모델의 잉크 근거대 = **z≈16–36**.
  - 영역별(15개) occlusion 기반 픽셀 중앙값 깊이 = **26–38**로 일관. 최적 window는 10개 영역이 z36–44.
  - 모델없는 CT: AUC 최대 **0.546 @ z24**, 최소 0.442 @ z63 → **단일 복셀 밝기로는 잉크 판별 거의 불가**(임계값 기반 3D 라벨 생성은 배제). 양의 봉우리 z16–32가 모델 밴드와 **일치**(독립 측정 2개가 같은 대역).
  - z>40의 큰 음의 드리프트(잉크가 배경보다 어두움)는 **기하 아티팩트로 읽힘** — 모델은 안 씀. 임계값 기반 라벨이 잉크로 오인하기 딱 좋은 신호.
- **함정/주의**: ①window의 절대 로짓은 baseline과 비교 불가(56/64 지움 = 분포 이탈, 배경 로짓이 +2까지 상승) → **잉크−배경 차이만** 유효 ②z풀링 격자(16배) 때문에 window 곡선에 주기 8 톱니 → 추세만 읽을 것 ③`z_projection_mode: max`라 occlusion 절대낙폭은 원래 작을 수밖에 없음.
- **8월 계획에 미치는 영향**: villa에 이미 `mode: full_3d` 경로가 있고 3D 라벨은 표면 기준 **고정 반두께 1.0복셀**(`_DEFAULT_FULL_3D_PROJECTION_HALF_THICKNESS`, `data/ink_dataset.py:53`)로 만들어짐 → **소비처가 이미 존재**(리스크↓). 측정된 대역(z16–36)은 볼륨 중앙(32) 대칭이 아니고 두께도 1복셀보다 훨씬 넓음 → 둘 다 하네스로 검증 가능한 주장. 단 영역별 강도 편차(피크 |AUC−0.5| 0.045~0.155)가 커서 **전역 단일 밴드는 답의 형태로 부적절**.
- ❗ **전제 정정(2026-07-27 실측)**: 라벨은 **z복사가 아니다**. `_inklabels.zarr`(65,H,W)는 **z=32 한 장만** 채워져 있고 나머지 64장은 0(감독 마스크도 동일, level3로 세그먼트 전체 확인). 깊이는 저장 자산에 없고 하류에서 만들어짐 — `flat`은 z를 max로 접어 **2D 타깃**으로 학습(깊이가 손실에 안 들어감), `full_3d`는 그 한 장을 법선으로 **±1복셀** 투영. #192가 문제 삼는 건 이 **제조 단계**. 이전 문서·docstring의 "z복사" 표현은 전부 수정함.

## 측정된 3D 라벨 (2026-07-27, 8월 트랙 2단계)

- ✅ **`tools/make_3d_labels.py`** + `docs/11_measured_3d_labels.md`. 산출물(세그먼트 폴더): `_inklabels3d.zarr`(OME 0.4 피라미드 6레벨, 기존 라벨과 같은 그리드·청크·compressor, 28MB) · `_inkdepth.zarr`(center/half_width 2D float32, 주석 밖 NaN) · `_inklabels3d.json` · `_inklabels3d_qc.png`(영역별 y–z 단면).
- **실측**: 748블록·잉크 2,207만px, 측정된 셀 5,704/6,860(잉크 픽셀 85.9%). **세그먼트 중앙 = center z 32.5 / half-width 4.0(=8복셀 두께)**, 영역별 중심 **29.3–40.3**, 영역 내 중심 spread 7.5–11.2복셀. 라벨 복셀 1.767억, 픽셀당 평균 8.0복셀. → 현행 기본값(3복셀 고정·중앙 대칭) 대비 **두께 8복셀 + 위치가 영역마다 이동**.
- ⚠️ **추정기를 3번 갈아엎음(QC가 잡아냄)**: ①픽셀단위+9px 스무딩 → 한 획 안에서 ±12복셀 요동(시트 기하학상 불가) ②64px 셀+argmax → 영역 내 ±17복셀, 두 영역이 28복셀 차이(16밴드 argmax는 노이즈가 결정) ③**64px 셀 + centroid 중심 + FWHM 폭 + 셀격자 median 필터 + 이중선형 업샘플** → spread 절반, 영역 간 일치, 단면에서 밴드가 시트를 따라가는 리본. centroid의 2차 모먼트 폭은 클램프에 붙어 폐기(꼬리를 잼). `--estimator peak`로 ②재현 가능.
- **QC 판정법**: 평면 프리뷰로는 깊이 라벨 검증 불가 → **y–z 단면(x가로·z세로)에 밴드 오버레이**가 유일한 실검. 리본이면 합격, 컨페티면 불합격.
- ~~아직 소비처 없음~~ → **2026-07-31 해결**(아래 절). 복셀 라벨과 함께 낸 compact form(center/half_width)이 실제 소비 경로의 입력이 됨.

## 깊이 라벨 소비 경로 (2026-07-31, 8월 트랙 3단계)

- ✅ **villa 파이프라인 수정 + arm 자산 생성기 + 스모크 검증 완료.** 문서 = `docs/12_depth_training.md`, 패치 = `submission/villa-flat-depth-targets.patch`(train.py·infer.py·test_train.py, 미커밋 상태로 `external/villa` 작업트리에 적용됨 — 브랜치는 여전히 `fix/stream-untiled-label-images`).
- **막고 있던 것**: `train.py`의 flat 분기가 `torch.amax(batch['inklabels'], dim=2)`로 **z를 손실 전에 접어버림** → 3D 라벨과 평면 라벨이 타깃 단계에서 바이트 동일. flat 모드에서 라벨 깊이 실험이 원천 불가였음(#192가 15개월 방치된 이유의 일부).
- **수정**(`flat_depth_targets: true` config 게이트): ①모델·타깃 z_projection을 native 3D 모드와 같은 방식으로 끔 → 출력 `[B,1,Z,Y,X]` ②손실을 볼륨 대 볼륨으로(supervision을 ignore mask로) ③프리뷰는 `full_3d`가 쓰던 중앙 슬라이스 축약 재사용 ④**추론에 `--z-reduce max|mean`** 추가 → 볼륨 예측을 기존과 같은 2D TIFF로 환원. ④가 있어야 7월 하네스·fold 노이즈 기준선(~0.03 F1)이 그대로 적용됨.
- ✅ **`tools/make_label_version.py`** — 밴드를 **label version**(`_inklabels_vN.zarr` 등, villa `discover_labels`가 이미 아는 규칙)으로 패키징. v1은 손대지 않음. 3 arm: **v2 `plane`**(현행 자산 그대로 = 1복셀) · **v3 `constant`**(중앙 32.47±4 고정 = `full_3d` 방식의 대조군) · **v4 `measured`**(`_inkdepth.zarr` 픽셀별 밴드). 버전당 ~10분.
- ⚠️ **supervision을 기둥(column)으로 바꿔야 실험이 성립**: 세 arm 모두 주석 픽셀에서 **z ±16 기둥**을 감독(기본값 `--supervision-half-depth 16`). 이게 없으면 밴드 밖 복셀이 무감독이라 어떤 밴드든 손실이 동일. 전체 z를 안 쓰는 이유 = z>40의 음의 드리프트(이웃 wrap 가능성, `docs/10`)를 "배경"이라 부를 근거가 없음.
- ⚠️ **검증 마스크도 같은 기둥으로 압출 필수**: 트레이너가 held-out을 **복셀 단위**로 학습 supervision에서 뺌 → 평면만 있는 마스크면 held-out 글자의 평면 밖 복셀이 학습에 남아 **누수**(그것도 정확히 테스트 대상 arm에 유리한 방향으로).
- **실측**: v2/v3/v4 생성 완료(잉크 2,190만px 동일, 라벨 복셀 v2 2,190만(1.00/px) · v3 1억7,522만(8.00/px) · **v4 1억7,533만(8.01/px)**, 감독 복셀 31.7억, held-out 6.30억, v4 fallback 2,814px=0.01%). **v3↔v4가 복셀 예산 0.15% 차이** → 양성 개수 고정하고 위치만 바뀌는 깨끗한 대조. 반면 **v2는 양성비 0.7% vs v3/v4 5.5%**라 Dice+BCE 손실에서 클래스 균형이 섞임 → v2는 "현행 자산의 문자 그대로"일 뿐 대조군 아님. 스모크 200iter: 패치 **2,234/1,337**(7월과 같은 held-out), 패치 캐시 키에 `labels-v2`가 들어가 **arm 간 split 오염 없음**, 3.6 it/s(2D와 동일 → 20k arm = ~1.5h), 모델 출력 `(1,1,64,256,256)`, 추론 166블록 34초로 2D TIFF 정상. villa 유닛테스트 4 passed.
- **다음**: ①`run_cv_folds.py`에 `--label-version` 추가(fold마다 arm별 검증 마스크 재생성 필요) ②3 arm × 3 fold = 9런 ≈ 13.5h GPU ③채점은 기존 `sweep_checkpoints.py` + `eval_validation.py` 그대로(2D 환원 덕분).

## 이전 상태 (2026-07-21)

- ✅ **파이프라인 로컬 end-to-end 완주(2026-07-21).** 다운로드→학습(20k iter, ~1h31m)→추론까지 5090서 다 돌았고, **첫 예측 TIFF에 그리스 대문자가 또렷이 판독됨**. 산출물: `external/villa/ink-detection/predictions/w00_20231016151002.tif`(697MB, 32249×51380 uint8; nonzero 82%·>128 11%) + 프리뷰 PNG `..._preview.png`. **남은 일 = 재현 위 "한 겹"(개선/툴/문서) + 제출**(아래 4번). 나머지 항목은 이 완주의 근거·재현법 기록.

- ⚠️ **튜토리얼이 갈아엎어짐(scrollprize.org/tutorial5, 2026-07-10 갱신).** 기존 `src/`(InkUNet·`inklabels.png`·번호 TIFF 레이어)는 **죽은 2023 Kaggle 포맷**을 재현 중 — 현재 튜토리얼은 **zarr 데이터 + `ScrollPrize/villa`의 `koine_machines` 파이프라인(`uv` 실행) + Linux/WSL2**. 상세·근거·명령은 memory `tutorial5-rewritten-zarr-pipeline` 참조.
- **환경**: 네이티브 Windows에 torch cu128·5090 검증됨. `uv`·`hf` CLI 설치됨. **WSL2는 배포판 미설치**(공식 파이프라인 = `wsl --install` 필요; 5090=sm_120이라 WSL 안에서도 cu128 torch 필요).
- **데이터**: 학습 세그먼트 `w00_20231016151002`를 `data/ink-dataset/phercparis4/`로 다운로드(HF buckets, 익명 접근 OK). ⚠️ **실측 ~86GB**(`hf buckets ls -R`로 85.7GB/147,785파일 확인 — 표면볼륨 `<seg>.zarr` 하나가 85GB, `preds/`는 0.37GB). **튜토리얼의 "25GB"는 오류.** **2026-07-20 세션 종료 시점 ~77GB/86GB(89%) 받음(부분)** — 사용자가 PC 종료해 일시중단(전날 ~31GB에서 이어받아 여기까지). `hf buckets sync`는 **idempotent/이어받기 가능** → 재실행하면 남은 ~9GB 이어받음. 파일: `<seg>.zarr`+`_inklabels.zarr`/`_supervision_mask.zarr`(+각 .tif)+`x/y/z.tif`+`meta.json`.
- **경로 결정(2026-07-19)**: **(a) 공식 villa/uv 파이프라인 채택.** 5090 함정 없음 확인(`pyproject.toml`이 `torch==2.10.0` 핀). **네이티브 Windows 먼저** 시도(`uv sync` → CPU휠이면 `uv pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128` 오버라이드), deps/POSIX 막히면 WSL2 폴백. villa는 `external/villa`(gitignore)에 **`merge-ink-pipelines`(복수!)** 브랜치로 클론(튜토리얼의 단수 표기는 오타). 자작 개조(b)는 폐기(작업량 HIGH·채택 크레딧 손실).
- **셋업 완료 & 검증(2026-07-19)**: `external/villa/ink-detection`에 `uv sync` 성공(네이티브 Windows, uv가 CPython 3.12 자동 fetch, napari/pyqt6/imagecodecs 등 169개 설치). `pyproject.toml`에 `[[tool.uv.index]] pytorch-cu128` 박아 재sync → **`torch 2.10.0+cu128` · CUDA True · RTX 5090 · sm_120 검증**. config `configs/ink_tutorial.json` 작성(2.5D flat, `segments_path=D:/vesuvius-challenge/data/ink-dataset/phercparis4`, `patch_size=[64,256,256]`, batch 2, 20k iter, `save_every=1000`→`runs/ink_tutorial/ckpt_0XXXXX.pth`, `val_every=500`, fp16). `dataloader_workers`가 `spawn` 컨텍스트라 Windows-safe. **WSL 불필요.** **2026-07-20 재확인**: villa 디렉터리·`uv`·config 파일 전부 그대로 존재·정합 → 다운로드만 끝나면 학습 즉시 시작 가능.
- **재현법(2026-07-21 실측 완료, 순서대로)**:
  1. ✅ **데이터**: `hf buckets sync hf://buckets/scrollprize/datasets/ink/phercparis4/w00_20231016151002 D:\vesuvius-challenge\data\ink-dataset\phercparis4\w00_20231016151002` → 85.7GB/147,785파일 완료.
  2. ✅ **학습**: `uv run --directory external/villa/ink-detection python -m koine_machines.training.train configs/ink_tutorial.json` (20k iter, 5090서 ~1h31m @ ~3.4 it/s; OOM이면 `batch_size`→1 or `patch_size`→[64,128,128]). ckpt 20개 저장(`runs/ink_tutorial/ckpt_0XXXXX.pth`). 프리뷰: `runs/ink_tutorial/train_previews/`.
  3. ✅ **추론**: `uv run --directory external/villa/ink-detection python -m koine_machines.inference.infer <abs>/w00_20231016151002/w00_20231016151002.zarr runs/ink_tutorial/ckpt_020000.pth predictions/w00_20231016151002.tif --batch-size 4 --no-compile` (9425블록 ~23분 @ ~6.7 block/s). ⚠️ **`--no-compile` 필수**: infer는 기본으로 `torch.compile(reduce-overhead)`를 켜는데 inductor가 **Triton**을 요구하고 Triton은 **네이티브 Windows 미지원**이라 없으면 첫 forward에서 `TritonMissing` 크래시(학습은 compile 안 써서 무관).
- ✅ **기여 "한 겹" 제작 완료(2026-07-21)**: (②) `tools/ink_viz.py` — 예측 TIFF 시각화 재사용 CLI(`stats`/`preview`/`surface`/`overlay`, +`tools/README.md`). (③) `docs/08_windows_reproduction.md` — 네이티브 Windows 재현 워크스루 + 실측 함정 7종 표. before/after 이미지 `docs/images/{w00_surface,w00_ink_preview,w00_overlay}.png` 생성. 루트 `README.md` 갱신(죽은 src/ 빠른시작 → 실제 파이프라인·결과·산출물 링크). 툴·문서는 **영어**(커뮤니티 채택 축). `.gitignore`가 docs/images는 커밋·data/external/tif/pth는 제외.
- ✅ **GitHub 공개 푸시 완료(2026-07-21)**: https://github.com/khj1222/vesuvius-challenge (public, main, 25파일, 초기커밋 `4a02962`). git identity=`khj1222`/`bluekgssk@gmail.com`. data/external/ckpt/tif는 gitignore 제외 확인. credential=GCM(manager).
- **전략(2026-07-21)**: 현재 공개물(재현 + ink_viz 툴 + Windows 워크스루)은 **토대**. 상금 경쟁력 있는 기여는 help-wanted/오픈 문제를 실제로 푸는 방향이며, **사용자가 그 방향 논의를 다음 세션으로 보류**함. (솔직한 눈금·주의점은 비공개 메모리 [[ink-pipeline-status]] 참조 — 이 파일은 public이라 여기엔 안 적음.)
- **다음(보류 중, 사용자 재개 대기)**:
  4. (A) 이번 라운드에 현재물 제출 여부 = 미정. (B) 더 깊은 기여 타깃 선정 = 다음 대화 주제(먼저 villa help-wanted 이슈 + 2026 오픈문제 조사 → 실현가능·채택가치 높은 후보 2~3개). 제출 시 Google Form(https://forms.gle/xoF5C3QsYutKP97x7), 타깃 8/31(스트레치 7/31).
- ⚠️ 함정 불변: 점수경쟁 아님. 재현 위에 **남이 쓸 개선/툴/문서** 한 겹 필수. docs/05_strategy.md 참조.

## 관련 프로젝트

- trace-the-ace (DrivenData, CV·인코더 스택 겹침) — 데이터로더/학습루프 패턴 재사용 가능.
- ComfyUI 환경(5090 검증) — 시각화/후처리 재활용 가능.
