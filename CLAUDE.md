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

## 현재 상태 / 다음 액션 (2026-07-21 갱신)

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
- **다음(핵심, 미완)**:
  4. **제출**: (b) Google Form 제출(https://forms.gle/xoF5C3QsYutKP97x7) — repo 링크 + before/after 이미지 + 방법 설명. 타깃 8/31(스트레치 7/31). 선택: villa help-wanted 이슈/Discord에 워크스루·툴 공유(조기공개 축).
- ⚠️ 함정 불변: 점수경쟁 아님. 재현 위에 **남이 쓸 개선/툴/문서** 한 겹 필수. docs/05_strategy.md 참조.

## 관련 프로젝트

- trace-the-ace (DrivenData, CV·인코더 스택 겹침) — 데이터로더/학습루프 패턴 재사용 가능.
- ComfyUI 환경(5090 검증) — 시각화/후처리 재활용 가능.
