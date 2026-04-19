# Phase 18 — `review` 루프 통합 (entry_filter로 auto-prune 흡수)

## 문제

현재 `--auto-prune`은 `run_auto_prune_loop`이라는 별도 함수로 구현되어 있어, 오디오 재생·인라인 편집·앞뒤 이동 같은 풀 review UI를 못 쓴다. 플래그된 항목에 대해 `Delete 'text'? (y/N)` 프롬프트만 나오므로, 실제 소리로 판단해야 하는 감탄사/의성어 케이스에서 판단 불가.

**실사용 관찰 (2026-04-18)**:
- 186개 중 63개가 플래그됨 — 적잖은 수
- `" ㅎㅎㅎㅎ"`, `" 음..."` 같이 의도된 웃음/감탄 표현이 `non_korean_noise`로 걸림
- `" 맛있어"`는 공백 제외 3글자라 `too_short`. 듣고 살려야 할 가능성 높음
- y/n만으로는 "편집해서 살리기" 선택지가 없음

## 해결 — 방향 2 통합

Phase 09 문서에서 설계 시점에 (a) 필터 옵션 / (b) 별도 함수 중 (b)를 골랐지만, 실사용 후 (a)가 더 맞다고 판단.

### 새로운 시그니처

```python
def run_review_loop(
    session: ReviewSession,
    dispatcher: Dispatcher,
    key_source: Iterator[str],
    console: Console,
    entry_filter: Callable[[ListEntry], bool] | None = None,
) -> None:
    ...
```

- `entry_filter=None` → 현재 동작 (모든 entry 순회)
- `entry_filter` 제공 → 필터를 통과하는 entry만 내비게이션 대상
- 풀 dispatcher 그대로 — Enter(재생)/e(편집)/d(삭제)/n(다음)/b(이전)/u(undo)/q(종료) 전부 사용 가능

### 네비게이션 동작 변경

- `n` → 다음 플래그된 entry로 점프 (중간 통과 entry 스킵)
- `b` → 이전 플래그된 entry로 점프
- 삭제 후 커서 위치 보정: 플래그된 다음 항목으로

### `ReviewSession` 또는 loop 중 어느 쪽에 필터 로직을 둘지

- **권장: loop 쪽** — session은 전체 데이터셋을 유지, 필터는 "뷰" 개념. 이 분리가 ODP의 Entity(session) vs Service(loop) 구분과 맞음
- session에 필터를 저장하면 여러 경로가 필터를 우회할 위험

### `run_auto_prune_loop` 운명

- 삭제. `--auto-prune` CLI 플래그는 유지하되, 내부적으로는 `run_review_loop(entry_filter=has_issues)` 호출로 변경
- `commands/review.py`:
  ```python
  if auto_prune:
      entry_filter = lambda e: bool(inspect(e))
  else:
      entry_filter = None
  run_review_loop(session, dispatcher, key_source=..., console=..., entry_filter=entry_filter)
  ```

## TDD 시나리오

### RED 1 — 필터가 None이면 기존 동작 유지

기존 `test_loop_quit_on_q` 등이 그대로 통과해야 함 (회귀 방지)

### RED 2 — 필터 있을 때 next는 플래그된 다음 entry로 점프

```python
def test_next_jumps_to_next_flagged_entry(tmp_path):
    entries = [
        ListEntry("a.wav", "s", "ko", "정상 텍스트입니다"),      # pass
        ListEntry("b.wav", "s", "ko", ""),                      # flag
        ListEntry("c.wav", "s", "ko", "또 다른 정상 텍스트"),    # pass
        ListEntry("d.wav", "s", "ko", "아"),                    # flag
    ]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    # 초기 커서를 첫 플래그(b)로 두고 시작
    ...
    # n을 눌렀을 때 d.wav로 점프하는지 검증
```

### RED 3 — 시작 시 첫 플래그 항목으로 커서 초기화

필터 있을 때 `session.cursor`가 첫 플래그 항목으로 자동 이동.

### RED 4 — 모든 플래그 항목 처리 후 종료 또는 안내

필터 통과하는 entry가 더 없으면 "No more flagged entries" 메시지 + 자동 종료(또는 q 대기).

## 파일 변경

```
src/voxprep/review/
├── loop.py                     ← edit: run_review_loop에 entry_filter 파라미터
└── (run_auto_prune_loop 삭제)

src/voxprep/commands/review.py  ← edit: --auto-prune 분기가 entry_filter 만들기

tests/unit/
├── test_review_loop.py         ← edit: 필터 시나리오 추가
└── test_auto_prune_loop.py     ← 삭제 또는 재작성 (통합 후 의미 바뀜)
```

## 완료 기준

- [ ] 플래그된 항목 사이를 n/b로 이동하면서 Enter로 오디오 재생
- [ ] 플래그된 항목을 e로 편집 가능 (편집 후 필터 재평가 여부는 설계 토론)
- [ ] `voxprep review file.list`(전체) 동작 회귀 없음
- [ ] `voxprep review file.list --auto-prune`(필터) 동작 정상
- [ ] 커밋:
  - `refactor: unify review loop with optional entry_filter`
  - `feat: route --auto-prune through filter`
  - `test: add filter scenarios to review loop`

## 설계 토론 포인트

- **편집 후 필터 재평가**: 사용자가 `" 음..."`을 `"음 그래요"`로 편집하면 `non_korean_noise`가 풀림. 필터를 즉시 재평가해서 다음에 이 entry를 건너뛰게 할지, 현 세션에서는 그대로 순회할지. 1차 권장: **현 세션에서는 그대로 순회** (단순함 우선, 재진입 시 필터가 올바르게 동작).
- **`n`을 눌렀는데 다음 플래그가 없을 때**: 현재 위치 유지 + 안내? 또는 자동 종료? 1차 권장: 안내 + 대기 (q 눌러야 종료).
