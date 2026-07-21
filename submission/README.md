# Submission 패키지

Progress Prize 제출 시 여기에 산출물을 모아 Google Form에 링크한다.
제출 폼: https://forms.gle/xoF5C3QsYutKP97x7 · 타깃 라운드: **8/31**

## 제출 체크리스트 (심사 3축 대응 → docs/03_submission.md)

- [ ] **결과물**: 잉크 예측 이미지(`ink_pred.png` 등) 또는 툴 데모 (`src/infer.py` 산출)
- [ ] **공개 repo**: github khj1222/vesuvius-challenge (permissive/MIT, 조기 공개)
- [ ] **방법 설명**: 무엇을·왜·어떻게. before/after 이미지 포함 (문서화 축)
- [ ] **채택 유도**: Discord에 공유, 남이 재현 가능한 워크스루/튜토리얼 (채택 축)
- [ ] **조기성**: 완성 대기 말고 초안 단계에서 일찍 공개 (조기공개 축)

## 무엇이 "수상 가능한" 제출인가

튜토리얼 단순 재현 ❌. 그 위에 **남이 실제로 쓸 개선/툴/문서** 한 겹 ✅.
(예: 데이터로더 개선, 시각화 툴, 도메인 augment, VC3D good-first-issue 해결 + 잘 된 문서)

> 이 폴더의 `*.png`는 기본 .gitignore 처리됨 — 최종 제출 이미지는 `git add -f`로 명시 추가.
