# Phase 08 — `review` 삭제 + 1회 undo (d/u)

## 학습 목표

- **하드 삭제** 정책의 의미 — `.list`에서 줄이 사라지고, 인덱스 재계산이 필요
- **1회 undo**를 어떻게 메모리에서 표현할 것인가 — 직전 상태 스냅샷? Command 객체?
- **Command 패턴이 자연스럽게 도착하는지** 관찰 — 두 종류의 변경(편집/삭제)이 같은 undo 인터페이스로 묶일 때
- 확인 프롬프트 (`Are you sure?`) 디자인 — 또 다른 입력 seam
- 인덱스 재계산: 마지막 entry를 지웠을 때 cursor가 어디로?

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| Phase 07 `update_current_text` + `dirty` | `src/voxprep/review/session.py` | 같은 패턴 확장 |
| Phase 02 `write_list_file` | `src/voxprep/parsing/list_file.py` | 삭제 후 다시 쓰기 |
| Command 패턴 (참고만, 미리 적용 X) | 일반 GoF 자료 | 1단계 undo는 Command 없이도 가능 |

## 설계 결정 — undo의 표현

세 가지 후보:

1. **단일 스냅샷**: 삭제 직전의 `(entries 복사, cursor)`를 메모리에 저장. undo는 이 스냅샷으로 복구. 단순.
2. **Command 객체**: `DeleteCommand(index, removed_entry)` 같은 객체를 stack에 푸시. undo는 pop 후 inverse 적용. 미래에 다단계 undo로 확장 자연스러움.
3. **이벤트 로그**: 모든 변경을 append-only 로그로. 가장 풍부하지만 과한 학습.

**1차 권장: (1) 단일 스냅샷**. 이유:
- "1회 undo"라는 요구사항에 정확히 맞음
- 패턴은 고통이 있을 때 도착해야 함 — 지금은 고통 없음
- Phase 09 회고에서 "다단계 undo가 필요하다"는 신호가 오면 그때 Command로 리팩터

단, 시나리오 D~F를 거치면서 "편집도 undo되어야 하지 않나?" 학습 토론이 자연스러움 → 그때 패턴 도착 신호 점검.

## 구현 범위

### 만들 것

1. `src/voxprep/review/session.py` — 메서드 추가
   - `delete_current(self) -> None`
     - 현재 entry 제거, cursor 재계산 (지운 위치가 마지막이면 한 칸 앞으로, 아니면 같은 인덱스의 새 entry로)
     - 직전 상태 스냅샷 저장 (`_undo_snapshot`)
     - `dirty = True`
   - `update_current_text` 도 스냅샷을 저장하도록 확장 (선택적 통합)
   - `undo(self) -> bool` — 스냅샷이 있으면 복구 후 스냅샷 비움, True 반환. 없으면 False.
   - `can_undo(self) -> bool`
2. `src/voxprep/review/keybindings.py`
   - `d` 키 액션: 확인 프롬프트 → 확인 시 `delete_current()` + `save()`
   - `u` 키 액션: `if session.can_undo(): session.undo(); session.save()`
   - `Confirmer` Protocol — `confirm(message: str) -> bool`. `PromptToolkitConfirmer` 구현
   - `build_default_dispatcher` 시그니처에 `confirmer` 추가
3. 테스트:
   - `tests/unit/test_review_session.py` — delete/undo 시나리오 추가
   - `tests/unit/test_review_dispatcher.py` — d 키 + 확인, u 키 시나리오

### 미루는 것

- 다단계 undo (스냅샷이 단일이라 자연스럽게 1회로 한정됨)
- 자동 플래그 → Phase 09
- `.review_progress.json` (커서 위치 보존) — Phase 09 또는 Phase 10에서 다시 결정

## TDD 사이클 시나리오

### 시나리오 A — 중간 entry 삭제 후 cursor 동일 위치 유지

```python
def test_delete_middle_entry_keeps_cursor_position(tmp_path):
    entries = [_e("a"), _e("b"), _e("c")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    session.next()  # cursor=1 (b)

    session.delete_current()

    assert [e.audio_path for e in session.entries] == ["a.wav", "c.wav"]
    assert session.cursor == 1  # 같은 인덱스의 새 entry (c)
    assert session.current().audio_path == "c.wav"
    assert session.dirty
```

### 시나리오 B — 마지막 entry 삭제 시 cursor 한 칸 앞으로

```python
def test_delete_last_entry_moves_cursor_back(tmp_path):
    entries = [_e("a"), _e("b"), _e("c")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    session.next(); session.next()  # cursor=2

    session.delete_current()

    assert session.cursor == 1
    assert session.current().audio_path == "b.wav"
```

### 시나리오 C — 마지막 한 entry 삭제 시 빈 세션이 되는가?

```python
def test_delete_only_remaining_entry(tmp_path):
    entries = [_e("a")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)

    session.delete_current()

    assert session.entries == []
    assert session.cursor == 0  # 또는 -1, 결정 필요
    assert session.is_empty()  # 새 헬퍼
```

GREEN: `is_empty()` 메서드 추가. cursor는 0으로 두되 `current()`는 `is_empty()`일 때 예외 또는 None 반환 결정. 1차 권장: 예외 — 호출 전에 `is_empty()` 체크 강제.

### 시나리오 D — undo가 직전 삭제를 복구한다

```python
def test_undo_restores_deleted_entry(tmp_path):
    entries = [_e("a"), _e("b"), _e("c")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    session.next()  # cursor=1
    session.delete_current()
    assert session.current().audio_path == "c.wav"

    restored = session.undo()

    assert restored is True
    assert [e.audio_path for e in session.entries] == ["a.wav", "b.wav", "c.wav"]
    assert session.cursor == 1
    assert session.current().audio_path == "b.wav"
```

GREEN: `_undo_snapshot = (list(self.entries), self.cursor)` 저장 후 복구. **얕은 복사면 충분** — entries는 `ListEntry` 불변.

### 시나리오 E — undo는 1회만 가능

```python
def test_undo_only_one_step(tmp_path):
    entries = [_e("a"), _e("b"), _e("c")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    session.delete_current()  # a 지움
    session.undo()  # 복구

    assert session.undo() is False  # 두 번째 undo는 무동작
```

GREEN: undo 후 `_undo_snapshot = None`.

### 시나리오 F — 편집도 undo 가능한가? (학습 결정)

```python
def test_undo_after_edit(tmp_path):
    entries = [_e("a")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    session.update_current_text("changed")

    session.undo()

    assert session.current().text == "a"
```

**결정 포인트**: 편집도 스냅샷에 포함시킬지. 1차 권장: **YES**. 같은 메커니즘으로 일관. 이게 Command 패턴이 도착하지 않아도 되는 이유 — 단일 스냅샷이면 충분.

GREEN: `update_current_text`도 호출 전에 스냅샷 저장.

### 시나리오 G — d 키 + 확인 프롬프트

```python
class FakeConfirmer:
    def __init__(self, response: bool):
        self.response = response
        self.received: list[str] = []
    def confirm(self, message: str) -> bool:
        self.received.append(message)
        return self.response


def test_d_key_with_confirmation_deletes(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_e("a"), _e("b")])
    confirmer = FakeConfirmer(response=True)
    dispatcher = build_default_dispatcher(
        player=SpyPlayer(), editor=FakeEditor(None), confirmer=confirmer
    )

    dispatcher.handle("d", session)

    assert len(session.entries) == 1
    assert session.entries[0].audio_path == "b.wav"
    assert confirmer.received  # 메시지가 호출됨


def test_d_key_cancelled_keeps_entry(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_e("a")])
    confirmer = FakeConfirmer(response=False)
    dispatcher = build_default_dispatcher(
        player=SpyPlayer(), editor=FakeEditor(None), confirmer=confirmer
    )

    dispatcher.handle("d", session)

    assert len(session.entries) == 1  # 그대로
```

### 시나리오 H — u 키가 가장 최근 변경을 되돌린다

```python
def test_u_key_undoes_last_delete(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_e("a"), _e("b")])
    confirmer = FakeConfirmer(response=True)
    dispatcher = build_default_dispatcher(
        player=SpyPlayer(), editor=FakeEditor(None), confirmer=confirmer
    )
    dispatcher.handle("d", session)

    dispatcher.handle("u", session)

    assert len(session.entries) == 2
    assert session.entries[0].audio_path == "a.wav"
```

## REFACTOR 게이트

- **4-0**: 시나리오들이 한 가지씩 검증 ✅
- **4-1**:
  - `_undo_snapshot`을 명확한 named tuple 또는 dataclass로 — 가독성 향상
  - delete/update에서 스냅샷 저장 코드가 중복 → `_save_snapshot()` 헬퍼로 추출
- **4-2 (ODP 게이트)**:
  - `ReviewSession`: Entity 강화 — undo state 추가
  - `Confirmer` Protocol: 의존성 계약
  - `_undo_snapshot` 자체는 Value Object (불변, 값 비교 가능)
- **4-3 (패턴 신호)**:
  - **Command 패턴 도착했나?** — 단일 스냅샷이면 도착 신호 약함. 다단계 undo, redo, 또는 변경 종류별 undo 메시지("Restored deletion", "Restored edit") 등이 필요해질 때 도착. **이번 Phase에서는 도착하지 않음.** 회고에 "관찰만 하고 도입 안 함"이라고 명시.
  - 만약 사용자가 "메시지가 다른 게 자연스러운데?" 하면 → 그게 첫 신호. 다음 Phase 회고로 끌어올림.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `ReviewSession` | Entity (강화) | undo snapshot 보유 |
| `_undo_snapshot` | Value Object (내부) | namedtuple/dataclass(frozen) |
| `Confirmer` (Protocol) | (계약) | DI |
| `PromptToolkitConfirmer` | Service | 무상태 |
| `FakeConfirmer` | (테스트 더블) | spy + stub |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   └── review/
│       ├── session.py          ← edit: delete_current, undo, can_undo, is_empty
│       ├── keybindings.py      ← edit: d/u 키 등록, build_default_dispatcher 시그니처 변경
│       └── confirmer.py        ← user types (Confirmer Protocol + PromptToolkitConfirmer)
└── tests/unit/
    ├── test_review_session.py  ← edit: 시나리오 A~F 추가
    └── test_review_dispatcher.py ← edit: 시나리오 G, H 추가
```

## 완료 기준

- [ ] 시나리오 A~H 모두 통과
- [ ] `voxprep review some.list` → d로 삭제(확인 후) → u로 복구 동작
- [ ] e로 편집 후 u로 되돌리기 동작
- [ ] 빈 세션 진입 시 friendly 메시지 (current() 호출 안 함)
- [ ] Phase 05~07 테스트가 여전히 통과
- [ ] `learnings/phase08-qa.md` (단일 스냅샷 vs Command, 패턴 도착 관찰)
- [ ] 커밋:
  - `feat: add delete_current and single-step undo to ReviewSession`
  - `feat: add Confirmer protocol and prompt_toolkit implementation`
  - `feat: wire d and u keys with confirmation flow`
  - (선택) `refactor: extract undo snapshot helper`

## 주의사항 / 엣지케이스

- **확인 프롬프트의 키 처리**: 단순 `(y/N)` Yes/No prompt. `prompt_toolkit.shortcuts.confirm()`이 있음 — 그대로 활용 가능.
- **삭제 후 빈 세션의 렌더링**: `render_session`이 `is_empty()`일 때 어떻게 그릴지 분기 추가 필요. "No entries left. Press q to exit."
- **`current()` 호출 안전성**: Phase 05/06에서 만든 액션들이 `current()`를 호출하기 전에 `is_empty()` 체크가 필요해짐. 액션 함수 내부에서 분기.
- **undo의 직관성**: 사용자가 d로 지우고 화면을 보고 "어 잘못 지웠다" → u. 한 번만 가능하다는 사실을 화면 도움말에 명시 (`u: undo (1 step only)`).
- **dirty 플래그와 즉시 flush의 관계**: 즉시 flush이므로 `dirty`는 거의 항상 False로 돌아옴. `dirty`의 존재 의미는 점점 약해짐 — Phase 09 회고에서 제거 검토 가치.
- **편집 undo의 한계**: 시나리오 F에서 편집도 undo 가능하게 했지만, 사용자가 "편집 → 다음 entry 이동 → undo" 했을 때는? 직전 변경의 cursor도 복구되니 자동으로 이전 entry로 이동. 자연스러움.

## 다음 Phase 준비

Phase 09는 자동 플래그입니다. 시작 전:

1. 어떤 규칙들이 의미 있을지 미리 생각: 빈 텍스트, 3글자 이하, 감탄사만(`아`, `오`, `음`), 길이 비정상(60자 초과)
2. `--auto-prune` 모드의 UX 결정 — 시작할 때 한꺼번에 보여줄지, review 흐름에 끼워 넣을지
3. dirty의 의미 약화 → 제거할지 유지할지 회고로 결정
