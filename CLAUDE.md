# CLAUDE.md — vesuvius-challenge

새 세션은 이 파일 + `README.md` 만 읽으면 컨텍스트 없이 이어갈 수 있게 자기완결로 유지할 것.

## 이 프로젝트가 뭔가

Vesuvius Challenge **Progress Prizes** 트랙 진입 프로젝트. 헤르쿨라네움 탄화 두루마리 CT→판독을 돕는 오픈소스 기여로 월간 상금($1k~$20k)을 노림. 2026-07-19 착수(사용자가 후보 5개 중 Vesuvius 선택 — 롤링이라 9월 병목 파이프라인에 안 얹힘이 결정 이유).

## 핵심 사실 (2026-07-19 공식 검증, 근거 docs/)

- **트랙**: Progress Prizes = 월간 롤링. 리더보드 아님. 심사 3축 = 조기공개 / 커뮤니티 채택 / 문서화.
- **상금**: $500 · Papyrus $1k · Sestertius $2.5k · **$5k** · Denarius $10k · Gold Aureus $20k. 월 "최고 제출 $20k" 보장. (⚠️ 2026-08-29 확인: 등급표에 **$5,000과 $500이 추가**됨 — 7월 기준 4단계가 아니라 6단계.)
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

**남은 것 = 9월 라운드.**  (9월 폼 URL은 08-30 확인 시점에도 아직 8월 것 — 라운드가 넘어가면 https://scrollprize.org/prizes 에서 새로 받을 것.)
그날 순서(전부 완료) = ①#1535 상태 확인 → 무변화라 라벨 갱신 불필요 ②stantheman0128 채점 반영(08-28) ③문안 링크 재검증 → 10개 전부 200 ④사용자 폼 복붙 제출 ⑤`submission/2026-08_progress_prize.md`를 제출본과 동기화(완료, 동결).

✅ **코멘트 2건 게시 완료(08-28 03:25/03:26 UTC, 사용자 직접, 게시본 = 로컬 초안과 바이트 동일 확인)** — [#1608](https://github.com/ScrollPrize/villa/pull/1608#issuecomment-5448016030) · [#1611](https://github.com/ScrollPrize/villa/issues/1611#issuecomment-5448022908). 원본 = `submission/pr1608_reply_bullo27.md`, `submission/issue1611_reply_bullo27.md`.

✅ **8월 제출 사전점검 완료(08-28)** — field 4 링크 **10개 전부 200**, field 5 수치를 원 아티팩트(`external/villa/ink-detection/runs/*.json`)에서 **전건 대조 일치**(v2/v3/v4 0.844091/0.847853/0.809759, 격차 0.038094, 7월 2D 0.847243, 30k 0.038263→0.036076, w02 0.82625/0.728672 + 완전 순서). #1535·#1434 확인 결과 **우리가 답할 것 없음**(#1535는 사람 코멘트 0건, #1434엔 포인터 코멘트가 08-19에 이미 게시됨). **판정 = 주말에 그대로 제출.**

**8월 문안 내용 수정은 불필요 — 08-26에 점검 완료.** 오늘 철회한 domain match 주장은 8월엔 애초에 안 들어가 있었고(ink_9um 문단은 docs/14 스코어카드만 인용), #1434 인용도 "닫히고 #1535로 갔다"는 의도된 서술이라 그대로 두면 됨.

⚠️ **[#1608](https://github.com/ScrollPrize/villa/pull/1608)은 9월용으로 남길 것** — 08-26에 열었으니 날짜상 8월 작업이지만, 8월은 이미 머지 PR 2건(#1234·#1249)으로 6번 요건이 충족돼 있고 #1608의 서사(오픈 문제 #7)는 9월 본문과 붙어야 값이 산다. 양쪽에 쓰면 이중청구.

**9월 남은 결정**: ~~WSL2/Docker 설치 → B안 렌더 경로~~ → ✅ **08-26 설치·실행 완료, 결과는 음(아래 절, docs/16).** 남은 건 절반-세그먼트 라벨효율 등 폴드인(문안 notes) 정도. **등급을 $1k 밖으로 밀 후보였던 렌더 경로는 소진됐다** — 경로는 뚫렸으나 글자가 안 나온다.

**상금 기대치(2026-08-26 평가)**: 7월 실측 환율 = "잘 만들고 잘 문서화된 도구 = $1k"(같은 달 $20k는 메싱, $2.5k는 언래핑). 8월은 **음의 결과 + 핵심 PR 미머지**라 $1k 아니면 0이고, 수상한다면 근거는 결과가 아니라 **머지된 PR 2건**. 9월은 **이름 붙은 오픈 문제(#7)의 첫 수치 + 관측된 커뮤니티 견인**이라 더 나음($1k, 잘 되면 $2.5k). **둘 다 $10k/$20k의 형태는 아님** — 큰돈은 "읽히는 글자가 느는" 쪽으로 간다.

#### 2026-08-30 — UDA 사다리 완주(B·C), 피라미드 풀링 실측, 업스트림 회신 2건

**1. 🔬 docs/18 사다리 완성 — 세 팔 전부 사전등록 → 실행 → 보고**

- **arm B(TENT, 엔트로피 최소화)**: 헤드라인 14칸 **평균 F1 0.4916 → 0.4504(−0.0412)**, **개선 0칸**, 7세그 전부 두 시드 모두 악화. 노이즈 0.03을 넘으므로 "효과 없음"이 아니라 **해롭다**. 사전등록 예측 +10~40% → 실제 **−12.9%**로 **부호까지 빗나감**(사다리 중 첫 예측 실패).
  - **붕괴 서명 그대로**: batch의 p>0.5 비율이 100~200 step에 0, 14칸 중 4칸이 자명하한과 0.002 이내, 중앙값도 하한 +0.006. 임계값이 base 72–112 → 30–66으로 내려감.
  - **8비트 아티팩트 아님**(`tools/float_rank_check.py` 신규): float과 uint8 best-F1이 0.001 이내 일치, 대신 **AUC가 0.66 → 0.59(200) → 0.48(1600)**로 무작위 아래. 1600 step F1은 자명하한과 소수 4자리까지 동일.
  - **⚠️ 가장 실무적인 함의**: **엔트로피는 끝까지 단조 감소**하는데 품질은 단조 하락 → **목적함수 기반 무라벨 조기종료가 원리적으로 불가**. 궤적(4 프로브): 50 step에서 +0.003~+0.012(노이즈 안), 100에서 평평, 200에서 −0.03~−0.05, **400부터 전 칸이 자명하한**.
  - 원수치 `runs/ink9um_scorecard/armB_tent_matrix.csv`(34칸)·`armB_tent_summary.json`·`armB_rank_check_*.json`, 궤적 `runs/ink9um_tent_s4{2,3}/tent_trajectory.json`.
- **arm C(의사라벨 자가학습)**: **seed 42만 완료(2026-08-30 12:38 시점), seed 43 재학습 중.** s42 7세그 = **평균 Δ +0.0211, 7/7 전부 개선**이지만 **노이즈 0.03 미만** → 현재로선 "효과 없음(양의 부호)". 갭 회수 중앙값 **+3.3%**, 평균 +6.8%로 **사전등록 −10~+15% 안**. 세그별 편차 큼(w01 +0.042 / w09 +0.034 vs w06 +0.001). ⚠️ **두 시드 요건이 아직 미충족이라 확정 보고 금지** — s43이 붙어야 docs/18에 결과 절을 쓴다.
- **사전등록 규율**: arm B 파라미터 커밋 `3bff82f` **07:43:18** = 적응 드라이버가 첫 step을 돌기 전(첫 step 07:50:06, 첫 채점 07:56:45). docs/18에 타임스탬프 명기.
- ⚠️ **arm C 설계 축소(결과 나오기 전 기록)**: 8세그 전부 의사라벨 → 패치탐색이 세그당 13분·예상 1h32m·RSS 10GB로 불가 → **w00 1세그로 축소**. 그 결과 config가 지도 FT arm과 **`datasets`·`description`·`out_dir` 3키만** 차이 = 라벨 출처만 바뀐 순수 대조. 포기한 것(채점 세그 자체에 적응하는 transductive 이점)은 문서에 명시.

**2. 🔬 피라미드 풀링 실측 → docs/15 부록 3 (`tools/check_pyramid_pooling.py`)**

nerln이 #1582에서 "aligned가 여러 취득의 평균이라 SNR이 높다"는 기제를 제시하며 **"피라미드가 평균인지 데시메이션인지 미확인"**이라고 스스로 유보 → 공개 데이터로 확인 가능하므로 확인함. 3스크롤×2레벨전이×3윈도우×3평면 = **18칸 전부 2×2 평균**(최대편차 **0.50 그레이레벨** = uint8 평균의 반올림 한계, 87% 정확일치) vs 데시메이션 16~98. 게다가 **피라미드는 XY 전용**(OME scale이 `[2.4,2.4,2.4]→[2.4,4.8,4.8]→[2.4,9.6,9.6]`, z 불변) → prepare의 `POOL_Z=4`가 **독립적인 두 번째 평균** → **aligned 복셀 1개 = 취득 복셀 64개의 평균**, native는 1개. **nerln의 16배는 in-plane 절반이고 실제는 64**. ⚠️ SNR 8배는 주장 안 함(잡음 독립성 미측정) — 대신 "평균되는 필드가 평평하지 않다"만 실측(2×2 블록 내 표준편차 1.7~5.8).

**3. 🟠 업스트림 회신 2건 초안(사용자 게시 대기)**

- **[#1582](https://github.com/ScrollPrize/villa/issues/1582) → nerln**(`submission/issue1582_reply_nerln.md`): 위 풀링 실측 + 64배 정정 + arm A가 그 기제를 지지한다는 점(스펙트럼을 맞춰도 F1이 안 움직임 = 애초에 안 찍힌 측정을 필터로 복원할 수 없다) + 그쪽 bullet 3(계열 강제 금지)에 동의.
- **[#1611](https://github.com/ScrollPrize/villa/issues/1611) → Bullo27**(`submission/issue1611_reply_bullo27_round2.md`): 저쪽이 레지스트리에서 읽은 리비전이 **우리 이미지와 정확히 일치**함을 `docker image inspect`로 확인(`1e3f4c021f4e53bea3867772ed05f51a7e586a9c`, 2026-05-13, digest `sha256:bad516f6…`). → **우리 "재시도 없음" 주장은 철회**(그 리비전엔 3회 재시도가 있음; 우리가 읽은 건 이 이미지에 없는 `merge-ink-pipelines`의 캐시). 살아남는 건 **무기한 `cv_.wait`**(`render/ChunkCache.cpp:218/:749`)와 "캐시가 클수록 악화"라는 관측. 현재 main 빌드 재시험은 **런타임 이미지가 없어서** 못 함(그쪽 #1619) — 나오면 같은 렌더를 다시 돌리겠다고 약속.
- 로컬 사본 `submission/villa-issue-render-stall.md`에도 정정 절 추가(게시본 편집은 사용자 몫).

**4. 🧹 공개 표면 정리**

- `submission/README.md`가 **한국어 week-0 체크리스트**(닫힌 7월 폼·죽은 `src/infer.py`)였음 → **영어 색인**으로 재작성(라운드별 제출본·업스트림 PR/이슈 대응표). `todo.md`도 같은 이유로 README 포인터로 대체. **규칙 재확인: 제출 링크에서 도달 가능한 것은 전부 영어.**
- 9월 문안 링크 **16개 전부 200**(08-30 확인). 8월 제출본 field 5 sha256 재확인 = 기록과 일치(⚠️ 기록된 해시는 **본문 + 개행 1개**(5,063자) 기준. CLAUDE.md의 "5,101자"는 다른 계산 방식이니 혼동 금지).

**5. ⚠️ 함정 3종(오늘 실측)**

1. **GPU 경합은 이 방 안에서 실재한다** — 다른 프로젝트(`whest-starterkit`)의 CUDA 워커가 GPU를 31.8/32.6GB·99%까지 채우면 우리 추론이 **42 → 5 block/s**로 8배 느려지고, 학습은 **`CUDA error: resource already mapped`**(pin memory 스레드)로 죽는다. 대응 = 죽이지 말고 **재시도 가능한 드라이버**로 넘기기(arm C seed 43이 이걸로 2회 실패 → 별도 재시도 스크립트로 처리).
2. **긴 heredoc은 Bash 도구에서 잘린다** — 150줄쯤 되는 `python - <<'PY'`가 중간에서 끊겨 `unexpected EOF`가 났다. **긴 문서 삽입은 Write로 파일을 만들고 짧은 스크립트로 삽입**할 것.
3. **`OmeZarrBlockDataset`의 meta는 트리마다 길이가 다르다** — `external/villa`는 4필드, `D:/vw2`는 5필드. 언패킹은 `meta[:4]`로.

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

48칸(0139 w035/w039/w040/w041 × seed 2 × step 3). **평균 Δ +0.0052**(노이즈 0.03의 1/6), 17/24 칸에서 필터 우세, **회수율 중앙값 8.4%**(예측 0~20% 안). 4세그 중 3세그가 ±0.002 안, 유의미한 건 w039(+0.019) 하나 → 일관성 요건 미달. **규칙대로 "효과 없음"으로 보고.** ⚠️ 평균 회수율(−19.2%)은 인용 금지 — w041 s42 10k의 분모가 0.0015라 −673%가 섞임.
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
