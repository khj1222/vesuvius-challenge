# 미지 스크롤 렌더 경로 실행: PHerc1447 (2026-08-26)

docs/13 §6이 "경로가 실존하고 막는 건 환경 하나(WSL2/Docker 부재)뿐"이라 적어둔 B안을
환경 해소 후 끝까지 실행한 기록. **결론: 경로는 전 구간 작동하고, 직행 추론으로는
글자가 읽히지 않는다** — docs/15가 예측한 그대로다.

## 경로 (전 구간 실측)

```
S3 mesh 0.6MB  →  vc_render_tifxyz 원격 스트리밍 25분  →  표면볼륨 389MB(L0–L5)
   →  공개 ink_9um 체크포인트 추론 47초/개  →  예측 TIFF
```

| 단계 | 실측 |
|---|---|
| 이미지 | `ghcr.io/scrollprize/villa/volume-cartographer:edge` **12GB** |
| 입력 mesh | `mesh/intermediate/tifxyz_original/{meta.json,x,y,z.tif}` = **0.6MB** |
| 볼륨 | `PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr`, 24297×8343×8343 u1, chunk 128³ 무압축 — **다운로드 없이 `--remote-url` 스트리밍** |
| 렌더 산출물 | `[28, 3700, 5460]`, chunk `[28,128,128]`, **389MB**, 피라미드 L0–L5 완비 |
| 렌더 시간 | 재개 체인 포함 **~25분** (30청크/분) |
| 추론 | 3,112블록 **47초** (66 block/s) |

**렌더러 출력이 우리 추론 파이프라인에 무수정으로 꽂힌다**는 docs/13의 예측은 맞았다.
피라미드 레벨 수·청크 형태가 native9 계약(`[28,6400,7980]`, chunk `[28,128,128]`, L0–L5)과
동일하다.

## 타깃 선정

1447의 auto-grown 세그먼트 15개 전부의 `meta.json`을 받아 면적 순위를 실측했다
(docs/13의 수치와 일치하나 그때는 ID를 안 남겼었다).

| 순위 | 세그먼트 | 면적 |
|---|---|---|
| **1** | `20250703034159-auto_grown_20250703034159599` | **7.40 cm²** |
| 2 | `20250703025628-auto_grown_20250703025628283` | 6.57 |
| 3 | `20250502184845-auto_grown_20250502164121265` | 4.92 |
| 4 | `20250502182456-auto_grown_20250502161202782` | 4.74 |
| 5 | `20250502183421-auto_grown_20250502161744358` | 4.51 |
| 6 | `20250502184658-auto_grown_20250502163923577` | 4.46 |

1위를 골랐다(First Letters 창 4cm² 초과, `max_gen` 200, `partial_review` 태그로 사람이 한 번 본 세그먼트).
bbox 2551×2709×3523 복셀, 격자 scale 0.05.

## 결과: 판독 불가

공개 체크포인트 4개(seed 42·43 × step 10k·20k — docs/15에서 LOSO 정점이 3 arm 모두 10–20k)로
직행 추론.

| 체크포인트 | mean | **>128** | p50 | p99 | max |
|---|---|---|---|---|---|
| s42 / 10k | 77.3 | **21.3%** | 91 | 193 | 246 |
| s42 / 20k | 68.8 | 13.9% | 79 | 185 | 221 |
| s43 / 10k | 71.9 | 14.3% | 85 | 171 | 219 |
| s43 / 20k | 62.7 | **6.5%** | 76 | 170 | 211 |

**수치가 먼저 말한다** — 세 가지 모두 "신호 없음"의 서명이다:

1. **체크포인트 간 >128 비율이 6.5%~21.3%로 3배 차이.** 같은 픽셀을 두고 모델들이 크게 엇갈린다.
2. **max가 어느 것도 255에 못 미친다**(211–246). 확신을 가진 픽셀이 하나도 없다.
3. **p50이 76–91** — 표면 절반이 중간 회색대. 진짜 신호가 있을 때 나오는 이봉분포
   (대부분 0 근처 + 잉크는 255 근처)가 전혀 아니다.
4. non-zero가 네 개 모두 **67.034%로 동일** — 이건 모델 출력이 아니라 렌더 유효영역이다
   (캔버스의 33%는 시트 바깥). 이 숫자를 "탐지율"로 오독하지 말 것.

**이미지도 같은 말을 한다.** 4배 다운샘플 프리뷰와 원해상도 700×700 크롭 모두에서:

- 둥근 무정형 얼룩(100–200px)이 지배적이고 **연결된 선형 획 구조가 없다.**
- 같은 좌표를 두 체크포인트로 보면 **굵은 배치는 일치하고 세부만 다르다** → 두 모델이
  같은 것에 반응하는데 그게 잉크가 아니라 표면 기하·섬유 구조다.
- 표면 경계의 밝은 테두리는 유효영역→공백 전이의 엣지 아티팩트, 직선적 밝은 선과
  계단 모서리는 128청크 경계. 둘 다 잉크가 아니다.

**스케일 검산**: 8.64µm/px에서 이 세그먼트는 3.2cm × 4.7cm. 글자가 2–5mm면 230–580px,
획 굵기 35–60px로 나와야 한다. 크롭 한 장(700px)에 글자 1–2개가 들어올 크기인데
그 굵기의 연결 구조가 어디에도 없다.

## 판정과 함의

**예측대로다.** docs/15의 cross-scroll 마진(자명 하한 대비 +0.06~0.17)이 말하던 수준이
이미지로 확인됐다. 4탄 플레이북이 직행 추론을 "판독"이 아니라 **"스카우팅"**으로 규정한 것도
맞았다.

⚠️ **그런데 스카우팅이 목적을 달성하지 못한다.** 플레이북 3단계는 "유망한 세그먼트 하나에
주석 → 분 단위 fine-tune"인데, **어디에 주석을 달지 이 예측이 알려주지 않는다.** Paris4에서는
라벨이 있어 fine-tune이 가능했지만 1447엔 정답이 없고, 이 출력만으로는 시작점을 고를 수 없다.
→ **무라벨 도메인 적응이 선행돼야 하며, 그것은 별개의 과제다.** 이 문서가 그 필요성의
정량 근거다(docs/15 1탄 말미의 같은 취지 진술을 미지 스크롤에서 실증).

남은 세그먼트 14개도 개당 ~30분이면 처리 가능하나, 같은 결과가 나올 가능성이 높다고 본다.

## 함정 기록

- ⚠️ **`external/villa`가 아니라 tip 트리에서 돌릴 것** — 추론 명령의 경로는 반드시
  **Windows 형식(`D:/...`)**. Git Bash 형식(`/d/...`)을 넘기면 Windows 파이썬이 못 읽고
  **에러도 없이 즉시 종료**한다(출력 파일 0개). 이걸로 한 번 헛돌았다.
- ⚠️ **렌더러가 힙 손상으로 죽는다** — 첫 실행에서 10% 지점에 
  `malloc(): largebin double linked list corrupted (nextsize)`. 재현 조건 미확정.
- ⚠️ **원격 스트리밍이 순단 시 무한 대기한다** — CPU 4~6%, 메모리 1GB대로 살아 있는데
  60초간 청크·캐시 증가 0. 재시도 로직이 없다. **`--timeout N`(분)으로 끊고 `--resume`으로
  재개하는 체인**이 유일한 우회로.
- ⚠️ **`--cache-gb`를 키우면 오히려 나빠진다** — 24GB로 주면 회당 100~130청크에서 멈추는데,
  8GB로 낮추니 회당 361·540청크로 늘어 2회 만에 완주했다. 실사용 메모리는 1GB대였다.
- ✅ **피라미드는 증분 생성된다** — L1–L5가 L0와 나란히 차오르므로, 타임아웃으로 끊어도
  피라미드가 남는다. 마지막 실행의 정상 종료를 기다릴 필요가 없다.
- `-v`로 준 스테이징 캐시 경로에는 **아무것도 쌓이지 않는다**(0 파일). 렌더러는 원격에서
  직접 스트리밍한다. 그래서 존재하지 않는 캐시 경로에 `--resume`을 걸면 무출력으로 멈춘다.

## 재현

```bash
# 1) 면적 순위와 tifxyz (세그먼트당 0.6MB)
curl -s "https://vesuvius-challenge-open-data.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=PHerc1447/segments/&max-keys=100"
# → 각 세그먼트의 mesh/intermediate/tifxyz_original/{meta.json,x,y,z.tif}

# 2) 렌더 (컨테이너, 원격 스트리밍). 순단 대비로 --timeout + --resume 체인 필수
docker run --rm -e OMP_NUM_THREADS=4 -v D:/vesuvius-challenge/data/first_letters:/work \
  ghcr.io/scrollprize/villa/volume-cartographer:edge \
  vc_render_tifxyz -v /work/cache/1447.zarr \
    --remote-url https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr \
    -g 0 --scale 1 -s /work/pherc1447/<SEG>/tifxyz_original \
    --num-slices 28 --slice-step 1 --zarr-output /work/render/<SEG>.zarr \
    --cache-gb 8 --resume --timeout 8

# 3) 추론 (경로는 Windows 형식으로!)
cd D:/vw2/ink-detection
uv run --project D:/vesuvius-challenge/external/villa/ink-detection --no-sync python \
  -m koine_machines.inference.infer \
  D:/.../render/<SEG>.zarr D:/.../models/hybrid_3d2d-seed42/step-020000.pth D:/.../pred.tif \
  --overlap 0.5 --blend-mode hann --no-compile

# 4) 판단 (프리뷰만 보지 말 것 — 대비 스트레치가 노이즈도 무늬로 만든다)
python tools/ink_viz.py stats pred.tif
python tools/ink_viz.py preview pred.tif --downsample 4
```

산출물 = `data/first_letters/`(gitignore — 389MB zarr + 예측 TIFF 4장 + 프리뷰·크롭 PNG).
