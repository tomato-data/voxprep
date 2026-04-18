# Phase 11 — Rich 진행률 표시

## 문제

현재 `prep` 파이프라인은 장시간 실행 시 비주얼 피드백이 전혀 없음. 7분 이상 걸려도 진행 상황을 알 수 없어 사용자가 "잘 되고 있는 건지" 판단 불가.

## 구현 범위

### slice_step
- Rich `Progress`로 파일별 진행률 표시 (현재 파일명 + N/M)
- 이미 `commands/slice.py`에 Progress가 있으므로 `pipeline/runner.py`의 `slice_step`에도 동일하게 적용

### asr_step
- 파일별 진행률 + 현재 처리 중인 파일명
- 예상 소요 시간이 긴 작업이라 특히 중요

### prep 전체
- 단계별 상태 표시: `[1/3] Slicing...`, `[2/3] Transcribing...`, `[3/3] Review`
- Rich `Live` 또는 단순 `console.print`로 단계 전환 시 안내

### 향후 Phase 13/14에도 적용
- 특징 추출 3단계, 학습 시 epoch 진행률

## 참조

- `commands/slice.py` — 이미 Rich Progress 사용 중
- Rich Live: https://rich.readthedocs.io/en/stable/live.html
