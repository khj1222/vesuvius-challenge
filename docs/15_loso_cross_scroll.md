# Cross-scroll 일반화 실측: leave-Paris4-out (2026-08-23)

9월 A안 2단계이자 **오픈 문제 #7("cross-scroll ink generalization")의 첫 체계적 수치**.
공개 ink_9um 레시피에서 PHercParis4 8개 표현만 제거하고 나머지를 그대로 재학습한 뒤
(seed 42·43, 각 78,125 step), Paris4 8세그먼트의 주석 전체(supervision mask)를
정직한 held-out으로 채점했다. 참조군은 공개 체크포인트(= Paris4를 **학습한** 모델,
같은 픽셀이 train 데이터).

## 방법 요약

- **LOSO arm**: `tools/make_ink9um_config.py --exclude-scroll Paris4`로 생성
  ([configs/ink9um_loso_noParis4_s42.json](../configs/ink9um_loso_noParis4_s42.json), s43 동일).
  21 rep(0139×14, 1667×6, 0814×1), 배치 쿼터 재정규화 {0139:35, 1667:27, 0814:2}.
  학습 실측 s42 2h54m / s43 3h14m @ RTX 5090 (~7–8 it/s).
- **채점**: 예측 1장당 임계값 전스윕 → best F1. 4 arm × 7 step(10k…75k) × 8 seg
  = **224칸**, 원자료 `runs/ink9um_scorecard/paris4_matrix.csv`,
  집계 `paris4_matrix_summary.json`.
- **자명 하한(floor)**: 세그먼트의 잉크 비율 p에서 "전부 잉크" 분류기의 F1 = 2p/(1+p).
  cross-scroll 점수는 이 하한 **위로 얼마나 올라갔는지**로 읽어야 한다
  (실제로 일부 (arm, step)은 best threshold=0 — 자명 분류기가 최적).

## 결과 (best-of-grid, 세그먼트별)

| seg | floor | loso42 | loso43 | **LOSO best** | **하한 대비** | ref best | ref−LOSO |
|---|---|---|---|---|---|---|---|
| w00 | 0.374 | 0.420 | 0.426 | 0.426 | +0.052 | 0.918 | 0.492 |
| w01 | 0.415 | 0.468 | 0.462 | 0.468 | +0.053 | 0.914 | 0.447 |
| w02 | 0.379 | 0.418 | 0.417 | 0.418 | +0.039 | 0.916 | 0.498 |
| w03 | 0.512 | 0.528 | 0.536 | 0.536 | **+0.023** | 0.905 | 0.369 |
| w05 | 0.348 | 0.386 | 0.397 | 0.397 | +0.049 | 0.858 | 0.461 |
| w06 | 0.474 | 0.501 | 0.498 | 0.501 | +0.027 | 0.874 | 0.373 |
| w07 | 0.478 | 0.554 | 0.555 | 0.555 | +0.077 | 0.866 | 0.313 |
| w09 | 0.442 | 0.588 | 0.598 | 0.598 | **+0.156** | 0.889 | 0.291 |
| **평균** | | | | **0.487** | **+0.060** | **0.893** | **0.405** |

step별 LOSO 평균(16곡선): 10k 0.464 · **20k 0.482(정점)** · 30k 0.463 · 40k 0.451 ·
50k 0.457 · 60k 0.451 · 75k 0.446.

## 판정

1. **Cross-scroll 격차의 규모**: 정직-대-정직으로 비교하면 — 공개 모델이 자기
   스크롤 val 마스크에서 0.74–0.77(docs/14), Paris4를 뺀 같은 레시피가 Paris4에서
   best-of-grid **0.49** — **약 −0.26**. train 픽셀 대비로는 0.89 vs 0.49 = −0.41.
2. **자명 하한 위 마진은 평균 +0.06**: 세그먼트 점수 차이(0.40~0.60)는 대부분
   잉크 비율 차이가 설명하고, 진짜 전이 신호는 얇다. 다만 **0은 아니다** —
   w09(+0.156)·w07(+0.077)은 유의한 신호, w03(+0.023)·w06(+0.027)은 노이즈 수준.
   전이 신호 자체가 세그먼트에 따라 3~7배 출렁인다는 것이 두 번째 발견.
3. **seed가 아니라 구조다**: LOSO의 seed 간 |차이| 평균 **0.011**(최대 0.057).
   in-scroll heldout에서 seed 격차가 0.22까지 갔던 것(docs/14)과 대조적 —
   낮은 cross-scroll 성능은 복권이 아니라 재현되는 구조적 한계다.
4. **여기서도 75k는 과학습**: LOSO 정점은 20k, 75k까지 가면 평균 −0.036.
   in-scroll(암기)만 계속 오르고 어떤 held-out 축도 75k를 정당화하지 않는다.
5. **재현 타당성**: LOSO 런의 online val(공식 마스크 3개, 유지 스크롤)은
   bal_acc 0.69–0.76 대역으로 공개 런들의 heldout 대역과 일치 —
   "우리 재학습이 약해서"가 아니라는 통제.

## 유보/카베앗

- Paris4는 라벨을 2.4µm 볼륨에 전사한 aligned 계열 + ref조차 train 픽셀 0.91에
  머무는(다른 스크롤은 0.98+) **가장 어려운 홀드아웃**일 수 있다. 이 격차가
  Paris4 특수성인지 보려면 **leave-1667-out / leave-0139-out arm**이 다음 실험
  (본 하네스로 config 한 줄이면 됨).
- best-of-grid 비교라 양쪽 모두에 관대함(체크포인트 선택 오라클). 고정 step
  비교는 원자료 CSV로 재구성 가능.
- 채점은 임계값 오라클 포함(per-image sweep). 실전 배치는 임계값 이전이 추가로 필요.

## First Letters(B안)에 주는 함의

미지 스크롤(PHerc0800/1447) 직행 추론은 **자명 기준선 +0.02~0.16 수준의 신호**로
글자 판독 기대가 낮다 → B안은 "렌더 → 그대로 추론"이 아니라
"렌더 → **도메인 적응**(타깃 스크롤 무라벨 fine-tune 등) → 추론"으로 설계해야 한다.
이 필요성의 정량 근거가 이 문서다. 렌더 경로 자체는 docs/13 §6.

## 재현

```bash
# 1) arm config (짝 seed는 --seed 43)
python tools/make_ink9um_config.py --exclude-scroll Paris4 \
  --out configs/ink9um_loso_noParis4_s42.json --run-dir runs/ink9um_loso_noParis4_s42
# 2) 학습 (villa tip 트리 + ink-detection venv, cwd = villa/ink-detection)
python -m koine_machines.training.train configs/ink9um_loso_noParis4_s42.json
# 3) 채점 (세그먼트 통째 held-out이므로 supervision_mask 영역으로)
python tools/eval_validation.py <pred.tif> <labels>/phercparis4-w00 \
  --region-kind supervision_mask --no-image-metrics
```
