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

## 다음 액션 (2026-07-26 재개 지점 — 제출 마무리)

1. ✅ **awesome-scroll-tools PR 완료(2026-07-26)**: https://github.com/ScrollPrize/villa/pull/1249 — `scrollprize.org/docs/20_community_projects.md`의 `#### ⚙️ Tools`에 하네스 1줄 추가(base `main`, 1파일 +3). 브랜치 `khj1222/villa` `add-ink-validation-harness`(`2aba59a`, main tip `650076f`에서 분기). ⚠️ `gh` CLI는 **미설치**(구 메모 무관) — git push는 GCM 자격증명으로 되고, PR 생성만 사용자가 웹에서. 작업은 sparse worktree `D:\vw`에서 함(`external/villa` 작업트리 보존 목적; 불필요하면 `git worktree remove --force D:/vw`).
2. **폼 제출 ← 지금 여기** — https://forms.gle/xoF5C3QsYutKP97x7 (필수 7칸). 답변 전문 = `submission/2026-07_progress_prize.md` 2단계. **사용자가 채울 칸 = 이메일·실명 2개뿐**(공개 저장소라 비워둠). 6번 체크박스는 PR #1249로 충족.
3. (선택) 이슈 #1231 / PR #1234에 반응 오면 반영. "내부에 val mask 있다"는 답이 오면 폼 5번 서술의 전제를 조정.
- **마감 7/31 23:59 PT.** 롤링이라 놓쳐도 8/31 재제출 가능.

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
