# CLAUDE.md — vesuvius-challenge

새 세션은 이 파일 + `README.md` 만 읽으면 컨텍스트 없이 이어갈 수 있게 자기완결로 유지할 것.

## 이 프로젝트가 뭔가

Vesuvius Challenge **Progress Prizes** 트랙 진입 프로젝트. 헤르쿨라네움 탄화 두루마리 CT→판독을 돕는 오픈소스 기여로 월간 상금($1k~$20k)을 노림. 2026-07-19 착수(사용자가 후보 5개 중 Vesuvius 선택 — 롤링이라 9월 병목 파이프라인에 안 얹힘이 결정 이유).

## 핵심 사실 (2026-07-19 공식 검증, 근거 docs/)

- **트랙**: Progress Prizes = 월간 롤링. 리더보드 아님. 심사 3축 = 조기공개 / 커뮤니티 채택 / 문서화.
- **상금**: Papyrus $1k · Sestertius $2.5k · Denarius $10k · Gold Aureus $20k. 월 "최고 제출 $20k" 보장.
- **마감**: 롤링(다음 라운드 = **7/31 23:59 PT** → 8/31 → …). **타깃 = 7/31 스트레치**(2026-07-19 결정, ~12일), 못 맞추면 8/31로 이월.
- **제출**: Google Form https://forms.gle/xoF5C3QsYutKP97x7
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
- ✅ **지급 폼 제출 완료(2026-08-10, 사용자 직접 — 지급·개인정보 입력은 Claude가 처리하지 않음).** 등급·금액은 아직 미통보 — 폼 처리 후 확인될 것으로 보임.
- 수락 조건인 permissive 라이선스 = 저장소 MIT라 이미 충족.
- 8월 제출에 미치는 영향: "수상한 하네스를 **써서** #192의 라벨 품질 주장을 실제로 검증했다"는 연속성이 생김. 이슈 [#1231](https://github.com/ScrollPrize/villa/issues/1231)이 무응답인 것과 별개로, 하네스의 전제(배포 세그먼트에 val mask 부재)는 사실상 인정받은 셈.

## 🏁 7월 라운드 제출 완료 (2026-07-26)

- ✅ **Google Form 제출 완료(2026-07-26, 마감 7/31 23:59 PT 대비 5일 여유).** 제출 명의 = Hyojun Kwon / bluekgssk@gmail.com, 개인 자격. **답변 7칸 전문 = `submission/2026-07_progress_prize.md`**(제출본과 동일하게 유지 중 — 심사 문의 오면 이 파일이 근거).
- ✅ **awesome-scroll-tools PR**: https://github.com/ScrollPrize/villa/pull/1249 — `scrollprize.org/docs/20_community_projects.md`의 `#### ⚙️ Tools`에 하네스 1줄 추가(base **`main`**, 1파일 +3, 저자 표기 `by khj1222`). 브랜치 `khj1222/villa` `add-ink-validation-harness`(`2aba59a`, main tip `650076f`에서 분기). 폼 6번 필수 체크박스를 이걸로 충족.
- ⚠️ **`gh` CLI 미설치**(bash/PowerShell 둘 다). git push는 GCM 자격증명으로 됨 → **브랜치 푸시까지는 Claude가 가능, PR 생성/이슈 게시는 사용자가 웹에서.** villa 쪽 작업은 sparse worktree(`git worktree add --no-checkout --detach D:/vw <ref>` + `sparse-checkout set --cone scrollprize.org/docs`)로 할 것: `external/villa` 작업트리는 `merge-ink-pipelines` + 수정된 `pyproject.toml` 상태라 체크아웃 전환 금지. 경로가 길면 `Filename too long`으로 실패하니 **짧은 경로**(`D:/vw`) 필수.
- 📌 **제출 문안 정확성**: 5번의 "threshold 122–198"은 `ink_holdout_20k` 20체크포인트 기준이고 fold 런 포함 시 61–203 → 제출본은 둘 다 명시하도록 수정됨(커밋 `21a27c1`). 향후 수치 인용 시 근거는 `runs/*/validation/summary.csv`의 `threshold` 열.

## 다음 액션 (대기/선택)

1. **업스트림 반응 (2026-08-02 확인)**:
   - ✅ **PR [#1249](https://github.com/ScrollPrize/villa/pull/1249) 머지됨**(2026-07-31, erdpx가 main으로). 하네스가 scrollprize.org 커뮤니티 툴 목록에 실제로 등재됨 → 제출 문안의 "PR 제출" 표현은 "머지 완료"로 갱신 가능.
   - ✅ **PR [#1234](https://github.com/ScrollPrize/villa/pull/1234) 리뷰 반영 완료(2026-08-09, 커밋 `fc6d9a7` 푸시됨)**. erdpx 요청(*"2D 피라미드만 메모리에 만들고 각 레벨을 `DEFAULT_LABEL_SLICE`에 바로 써라"*)대로 `_build_downsample_levels_from_zarr` 호출을 걷어내고 2D 레벨을 메모리에서 유도하도록 변경. **실측 114.5s → 66.5s(1.7배), 피크 RSS 1.61 → 1.99 GiB.** `mean` 모드는 `_downsample_mean`의 float64 누산기(출력의 8배)를 피하려 행 밴드로 나눠 평균 — 밴드가 짝수 소스 행에서 시작하므로 결과는 바이트 동일. 검증 = 합성 4케이스(binary/grayscale × 짝수/홀수 크기)에서 tiled 경로·원본 in-memory 경로와 6레벨 바이트 동일 + 실제 32249×51380 striped 파일 6레벨 일치. 패치 사본 = `submission/villa-pr-stream-untiled-labels.patch`. **리뷰어 회신 코멘트는 사용자가 직접** (초안 아래 "PR #1234 회신").
   - 🔄 이슈 [#1231](https://github.com/ScrollPrize/villa/issues/1231) — 텍스트 답변은 아직 없지만 **2026-08-03경 `pmh47`(Paul Henderson)이 `erdpx`를 담당자로 배정**함(2026-08-08 확인). 즉 무시가 아니라 **트리아지 완료** 상태이고, 수상 통보(08-04) 직전 시점이라 이슈가 심사에 반영됐을 가능성이 높음. **"내부엔 이미 val mask가 있다"는 답이 오면 하네스 포지셔닝과 제출 서술의 전제를 조정**해야 하는 건 그대로.
2. **8월 라운드(8/31) 타깃 = villa [#192](https://github.com/ScrollPrize/villa/issues/192) "Accurate 3d ink labels" + 하네스 업스트림화(보조)** — 2026-07-26 재조사 후 결정. 계획·근거·마일스톤·리스크 전문 = `docs/05_strategy.md` 하단 "8월 라운드" 절.
   - 핵심 논리: 7월에 만든 held-out 하네스가 **"z복사 라벨 vs 3D 라벨"을 같은 fold·시드로 비교**하게 해줌 → 15개월간 아무도 증명 못 한 라벨 품질 주장을 수치로 세울 수 있음. 판정 기준선 = ~0.03 F1 미만은 노이즈.
   - ⚠️ **순환성 리스크**: 깊이 프로파일을 z복사 라벨로 학습한 모델에서 뽑음 → self-distillation **대조군 arm 필수**(이게 없으면 결과 무의미).
   - ⚠️ **니치 혼잡**: 7월 마감 직전 TAUIL-Abd-Elilah가 재현성 감사로 8건, Jinhojeong이 라벨 품질 측정 툴(#193)을 냄. "측정 툴 하나 더"는 중복 → 하네스를 **쓰는** 쪽으로 갈 것.
   - ✅ **1단계 깊이 국소화(2026-07-27)** → ✅ **2단계 측정된 3D 라벨(2026-07-27)** → ✅ **3단계 학습 소비 경로 + 3 arm 자산(2026-07-31)** → ✅ **4단계 9런 매트릭스(2026-08-09)**. 각각 `docs/10` · `docs/11` · `docs/12`. **실험은 끝났고 결과는 음의 결과** — 아래 "매트릭스 완료" 절.
3. 수상 시 permissive 라이선스 필수 → 저장소는 이미 MIT라 조건 충족.

### ▶ 다음 세션 재개 지점 (2026-08-09 갱신)

**실험 끝, 업스트림 게시도 끝. 남은 건 8월 제출 문안 + 반응 대응.**

1. ✅ **#192 결과 코멘트 게시 완료(2026-08-09, 사용자 직접)** — 본문 원본 = `submission/issue192_comment.md`. **반응 오면 방향 결정 필요**(아래 3번).
2. ✅ **PR #1234 리뷰 반영 + 회신 게시 완료(2026-08-09)** — 커밋 `fc6d9a7`, 회신 본문 = `submission/pr1234_reply.md`. **머지 충돌 없음, CI 4/5 통과**(실패한 Vercel은 외부 기여자 배포에 팀 승인이 필요한 항목이라 코드와 무관). erdpx 응답 대기. ⚠️ PR 제목·본문은 여전히 **구버전 구현을 설명**(“zarr에서 레벨을 다시 읽는다”) — 사용자가 수정 안 하기로 결정(2026-08-09), 회신 코멘트가 실제 구현을 설명하므로 실무상 문제 없음.
3. 🟡 **`flat_depth_targets` PR** — 패치 = `submission/villa-flat-depth-targets.patch`, **제목·본문·제출 절차 초안 = `submission/villa-pr-flat-depth-targets.md`(2026-08-10 작성)**. #192 코멘트에서 *"원하면 PR로 열겠다"*고 명시했으므로 **메인테이너가 원한다고 답하면 즉시, 무응답이면 ~08-24에 선제로 열 것**(CI·리뷰 여유). ⚠️ 패치는 `git diff` 포맷이라 `git am` 불가(`git apply`+수동 커밋) — 절차는 초안 파일에.
4. 🟢 **8월 제출 문안** (마감 8/31 23:59 PT). 7월 답변 7칸 구조 = `submission/2026-07_progress_prize.md` 참고. 재료: 3 arm 음의 결과 + z 환원 함정 + `flat_depth_targets` 경로 + #1234 머지 진행 + 7월 수상 연속성.

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
- **스케줄 아티팩트 아님**: 마지막 3,000 step 상승폭이 v3 +0.0075 / v4 +0.0068로 비슷한데 격차는 그 5배.
- → **#192의 전제("정확한 3D 라벨이 성능을 올린다")가 이 세그먼트에서 지지되지 않음.** 단, "#192가 틀렸다"가 아니라 **"이 경로로 만든 밴드가 고정 밴드를 못 이긴다"**로만 주장할 것. 상세·유보 = `docs/12` "The result: the measured band loses".

- ⚠️ **채점에 `--z-window 16:48`이 없으면 결과가 무의미하다**(2026-08-08 실측). 추론이 z를 **0–64 전체 max**로 접는데 supervision은 **z16–48 기둥뿐** → 무감독 32장에서 잉크·배경 모두 0.6~0.93으로 포화, max가 그걸 끌어올림. 같은 ckpt·같은 픽셀에서 **F1 0.535(전체 z) vs 0.802(z16–48)**. 증상 = **best threshold가 254에 못박힘**. v4 첫 실행은 이걸로 0.4708/0.5122/0.5308이 나왔고 재채점으로 위 표가 됨(체크포인트는 무사, 재학습 불필요). 상세 = `docs/12` "The reduction has to match the supervision".
- 전체-z 원본 숫자는 `runs/*/validation/`, 유효 숫자는 `runs/*/validation_z16_48/`에 보존. 종합 = `runs/ink_depth_v4_fold_cv_summary_z16_48.json`.
- **v4 best step이 19000–20000(아직 상승 중)** — 7월 2D 런은 17000 정점 후 하락. 볼륨 타깃이 느리게 수렴. 스케줄은 arm 공정성 때문에 20k 고정 유지.
- ⚠️ **v4의 0.8098을 7월 0.8472와 직접 비교 금지** — 학습 모드(2D 타깃·네트워크 내 z projection)와 라벨이 동시에 다름. 판정은 **v4 − v3**(~0.03 노이즈 기준).
- **디스크**: 9런 합계 ~195GB 소비(ckpt 1.08GB × 20 × 9). 2026-08-09 시점 D 여유 ~520GB.
- ⚠️ `save_every`를 늘려 디스크를 아끼지 말 것 — 최적 step이 17000~20000에 걸쳐 있다.
- ⚠️ **GPU 경합 주의**: 게임 클라이언트 등이 떠 있으면 3.0 → 1.1 it/s로 3배 느려진다(결과엔 무영향, 시간만). fold 0(v3)만 210분, 나머지는 105~125분.
- ⚠️ **villa 쪽 변경이 아직 `fix/stream-untiled-label-images` 브랜치에 미커밋 상태로 얹혀 있음**(train.py·infer.py·test_train.py). PR 낼 땐 `merge-ink-pipelines`에서 새 브랜치를 따고 `submission/villa-flat-depth-targets.patch`를 적용할 것. 패치는 z-window 포함해 2026-08-08 재생성됨.

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
