# todo.md — Week0 관통 (첫 Progress Prize 제출까지)

목표: **데이터 다운 → 잉크 예측 이미지 → 튜토리얼 위에 개선 한 겹 → 7/31 스트레치(실패 시 8/31) 제출.**

> ⚠️ **2026-07-19 갱신 — 아래 Phase 0/1 일부는 낡음.** scrollprize.org/tutorial5가 2026-07-10 재작성돼 데이터가 **zarr + `ScrollPrize/villa`의 `koine_machines` 파이프라인**으로 바뀜(더 이상 `inklabels.png`/번호 TIFF/`src/train.py` 아님). "튜토리얼 재현"의 새 의미 = villa 파이프라인으로 `predictions/w00_20231016151002.tif` 생성. 공식(WSL2+uv) vs 자작 `src/` 개조 **경로 미결정**(조사 중). 근거: memory `tutorial5-rewritten-zarr-pipeline` + CLAUDE.md 현재상태. 아래 체크리스트는 경로 확정 후 재작성 예정.

## Phase 0 — 셋업 (반나절)
- [ ] `pip install -r requirements.txt` (5090, cu128 torch 확인)
- [ ] Discord 가입 + 공식 튜토리얼(scrollprize.org/tutorial5 Ink Detection) 통독
- [ ] Data Browser에서 잉크 라벨 있는 fragment 1개 선정·다운로드
- [ ] `src/data.py` 상단 `DATA_ROOT`/fragment 경로 TODO 채우기

## Phase 1 — 튜토리얼 재현 (주말)
- [ ] `src/data.py`: surface volume(TIFF 레이어 스택) + ink/mask 라벨 로딩 검증 (shape 출력)
- [ ] `src/train.py`: 베이스라인 2.5D 세그멘테이션 학습 (작은 fragment, 몇 epoch)
- [ ] `src/infer.py`: 타일 추론 → 잉크 확률맵 PNG 저장 = **첫 시각 산출물**
- [ ] OOF/holdout로 눈으로 글자 보이는지 확인 (metric보다 가독성)

## Phase 2 — 수상 가능한 한 겹 (핵심)
- [ ] 위시리스트/Open Problems에서 "help wanted" 이슈 1개 스캔 → 재현 위에 얹을 개선 선택
      (예: 더 나은 레이어 정규화, 시각화 툴, 데이터로더 개선, 도메인 특화 augment 등)
- [ ] 개선을 **문서화**: README + 워크스루 + before/after 이미지 (심사 3축 중 2축)
- [ ] 리포지토리 정리, permissive(MIT) LICENSE 추가

## Phase 3 — 제출
- [ ] 산출물 패키지(`submission/`): 예측 이미지 + 방법 설명 + repo 링크
- [ ] Google Form 제출 (https://forms.gle/xoF5C3QsYutKP97x7), 타깃 = 8월 라운드(8/31 마감)
- [ ] github khj1222/vesuvius-challenge 푸시 (public)

## 규율 / 함정
- ⚠️ **점수경쟁 아님** — "튜토리얼 재현 = 수상"이 아니라 "실제로 쓰이는 기여 = 수상". 채택·문서화가 반.
- ⚠️ 데이터/TIFF/체크포인트 커밋 금지 (.gitignore 확인).
- ⚠️ 조기 공개가 유리 — 완성 후 공개보다, 초안이라도 일찍 repo 올리고 Discord에 공유.
