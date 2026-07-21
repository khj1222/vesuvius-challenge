# 04 — 과제 & 위시리스트

**검증: 2026-07-19 · 출처: scrollprize.org**

## 진입 과제 비교

| 과제 | 난이도 | 5090 적합 | 우리 우선순위 |
|---|---|---|---|
| **Ink Detection** | 중 (주말 스코프) | ✅ 세그멘테이션 학습 | ★ **1픽** |
| Virtual Unwrapping | 상 | 부분 | 관망 |
| Surface Reconstruction (autoseg) | 최상 (Grand Prize급) | 지오메트리 | X |

### Ink Detection (우리 진입점)
- 입력: 펼친 파피루스의 **surface volume** = 표면 깊이 방향 TIFF 레이어 스택(수십 장) + 잉크 라벨 마스크 + 파피루스 마스크.
- 과제: 레이어 스택 → 픽셀별 **잉크 확률** 세그멘테이션. 2.5D/3D UNet·SegFormer 계열.
- 공식: "다운로드→첫 예측까지 주말 하나." 튜토리얼 = scrollprize.org/tutorial5.
- 산출물 = 잉크 확률맵 이미지(눈으로 글자 보이는지가 실질 지표).

## 위시리스트 / Open Problems (제출 주제 소스)

- **공식 위시리스트**: https://github.com/ScrollPrize/villa/issues?q=is%3Aissue+state%3Aopen+label%3A%22help+wanted%22
- **Open Problems 페이지**: https://scrollprize.org/2026_open_problems
- **VC3D 소프트웨어** 개선(good-first-issue 태그 포함)

> Week0 Phase2에서 여기를 스캔해 "재현 위에 얹을 개선 1개"를 고른다. 후보 방향(우리 강점 기준):
> - 데이터로더/전처리 개선(레이어 정규화, 정렬) — CV 실무 강점
> - 도메인 특화 augmentation / 시각화 툴 — 시각형 산출물
> - 학습 파이프라인 재현성·문서화 — trace-the-ace/ETRI 연구 정합(재현성)
> - VC3D good-first-issue 처리 — 채택 신호 확보 쉬움

## 데이터 규모 참고

공식상 "45개 두루마리·조각 스캔됨" (Data Browser). 전부 오픈 공개. 잉크 라벨 있는 fragment부터 시작.
