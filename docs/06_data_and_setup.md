# 06 — 데이터 접근 & 환경 셋업

**검증: 2026-07-19 · 출처: scrollprize.org/get_started**

## 데이터 접근

- **전부 공개**: "스캔·렌더·복원 텍스트 모두 오픈." 별도 유료/승인 게이트 없음.
- **Data Browser**로 45개 두루마리·조각 탐색·다운로드. (get_started 페이지에 링크)
- **데이터 로더**: GitHub `ScrollPrize` org에 공식 로더 제공.
- Ink Detection 진입은 **잉크 라벨(마스크) 있는 fragment**부터. 튜토리얼(scrollprize.org/tutorial5)이 어떤 fragment를 쓰는지 지정.

> ⚠️ 데이터 대용량(surface volume = 고해상 TIFF 레이어 다수). 다운로드 전 디스크 확인. **`data/`·`*.tif`·체크포인트는 절대 커밋 금지**(.gitignore 처리됨).

## 환경 (사용자 환경 정합)

- 시스템 Python 3.10 + **cu128** + `requirements.txt` (uv 미설치).
- 컴퓨팅 = **집 RTX 5090** (로컬). 클라우드 기본값 쓰지 말 것.
- 설치:
  ```
  pip install -r requirements.txt
  # torch는 cu128 인덱스에서 설치 (requirements.txt 주석 참조)
  ```

## 커뮤니티 리소스

| 리소스 | 용도 |
|---|---|
| **Discord** | 메인 협업 허브 (벽에 부딪힌 사람들이 도와줌). 조기공유·채택신호 확보 채널 |
| **GitHub ScrollPrize** | 코드·데이터로더·VC3D 소프트웨어 |
| **튜토리얼** | virtual unwrapping / spiral fitting / **ink detection** 가이드 |
| **Hugging Face** | 공개 모델 호스팅 |
| **Weights & Biases** | 실험 트래킹 |

## 관련 스택 재사용

- **trace-the-ace**: CV 데이터로더·학습루프·OOF 패턴 그대로 이식 가능.
- **ComfyUI(5090 검증)**: 잉크맵 후처리·시각화·업스케일 재활용 가능.
