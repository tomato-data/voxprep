# Phase 07 — `review` 인라인 편집 (e)

## 학습 목표

- `prompt_toolkit.shortcuts.prompt(default=..., key_bindings=...)` 활용 — Textarea보다 단순한 한 줄 편집
- **불변성 유지** — `ListEntry`는 frozen이므로 편집은 "교체"로 표현. `dataclasses.replace`의 첫 사용
- **dirty 플래그 도입** — `ReviewSession`이 처음으로 "수정됨" 상태를 가짐. Entity의 의미가 짙어지는 순간
- **즉시 flush 정책** — 매 수정마다 `.list` 파일 다시 쓰기. 크래시 안전성과 학습 단순함의 trade-off
- **취소 처리** — Escape 또는 빈 입력 시 변경 없음. enter vs escape 분기

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| 편집 가능 입력 | `claude-code-study/components/BaseTextInput.tsx` | inputState + 커서 + enter/escape 분기. 우리는 prompt_toolkit이 대신 해줌 |
| `prompt_toolkit` 예제 | https://python-prompt-toolkit.readthedocs.io/en/master/pages/asking_for_input.html | `prompt(default=..., key_bindings=...)` |
| `dataclasses.replace` | https://docs.python.org/3/library/dataclasses.html#dataclasses.replace | frozen dataclass의 부분 교체 |
| Phase 02 `ListEntry` | `src/voxprep/parsing/list_file.py` | frozen 보장 확인 |

## 구현 범위

### 만들 것

1. `src/voxprep/review/editor.py`
   - `TextEditor` Protocol — `edit(initial: str) -> str | None` (None = 취소)
   - `PromptToolkitTextEditor(TextEditor)` — `prompt(default=initial)` 호출. KeyboardInterrupt/EOFError → None 반환
2. `src/voxprep/review/session.py` — 메서드 추가
   - `update_current_text(self, new_text: str) -> None` — 현재 entry를 `replace(text=new_text)`로 교체. `dirty = True`로 마킹
   - `dirty: bool` 필드 (`__init__`에서 False 초기화)
   - `save(self) -> None` — `write_list_file(list_path, entries)` 호출 후 `dirty = False`
3. `src/voxprep/review/keybindings.py`
   - `e` 키 액션 추가: editor.edit(current.text) → None이면 무동작, 아니면 `session.update_current_text(...)` + `session.save()`
   - `build_default_dispatcher` 시그니처에 `editor: TextEditor` 추가
4. `src/voxprep/commands/review.py` — `PromptToolkitTextEditor` 인스턴스 주입
5. 테스트:
   - `tests/unit/test_review_session.py` — `update_current_text`, `dirty`, `save` 시나리오 추가
   - `tests/unit/test_review_editor.py` — fake editor로 `e` 키 동작 검증

### 미루는 것

- 다른 필드(speaker, language) 편집 — 이번 Phase는 text 한정
- 멀티라인 편집 — `.list`는 한 줄 = 한 entry라 무의미
- Undo (Phase 08)
- "변경 사항이 있습니다" 종료 확인 — Phase 08에서 dirty가 더 풍부해질 때 함께

## 즉시 flush 정책

매 편집마다 `.list` 전체를 다시 씁니다. 이유:
- 크래시/Ctrl-C 안전성
- 학습 단계에서 "트랜잭션 / 저널" 같은 개념 도입 미루기
- `.list`는 보통 수천 줄 — 다시 쓰는 비용이 사용자 체감 불가

REFACTOR 거리 — atomic write (`tmp + rename`)로 가는 것이 자연스러운 다음 단계. 이번 Phase 4-1에서 도착할 수 있음.

## TDD 사이클 시나리오

### 시나리오 A — `update_current_text`가 dirty를 켠다

```python
from dataclasses import replace
from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession


def _entries():
    return [
        ListEntry("a.wav", "narrator", "ko", "안녕"),
        ListEntry("b.wav", "narrator", "ko", "hi"),
    ]


def test_update_current_text_replaces_entry_and_marks_dirty(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=_entries())

    session.update_current_text("새 텍스트")

    assert session.current() == ListEntry("a.wav", "narrator", "ko", "새 텍스트")
    assert session.dirty
```

GREEN: `entries[cursor] = replace(entries[cursor], text=new_text)` + `self.dirty = True`. 이 시점에서 `entries`가 list라 mutation 가능 — frozen dataclass와의 대비를 학습 토론 포인트로.

### 시나리오 B — `save`가 파일을 쓰고 dirty를 끈다

```python
def test_save_writes_to_disk_and_clears_dirty(tmp_path):
    list_path = tmp_path / "x.list"
    list_path.write_text("a.wav|narrator|ko|old\n", encoding="utf-8")
    session = ReviewSession(list_path=list_path, entries=_entries())
    session.update_current_text("새 텍스트")

    session.save()

    assert not session.dirty
    content = list_path.read_text(encoding="utf-8")
    assert "새 텍스트" in content
    assert content.startswith("a.wav|narrator|ko|새 텍스트")
```

GREEN: `write_list_file(self.list_path, self.entries); self.dirty = False`.

### 시나리오 C — Editor Protocol과 fake

```python
class FakeEditor:
    def __init__(self, return_value: str | None):
        self.return_value = return_value
        self.received: list[str] = []
    def edit(self, initial: str) -> str | None:
        self.received.append(initial)
        return self.return_value
```

### 시나리오 D — `e` 키가 editor를 호출하고 결과를 반영한다

```python
def test_e_key_updates_current_entry(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=_entries())
    editor = FakeEditor(return_value="고친 텍스트")
    player = SpyPlayer()
    dispatcher = build_default_dispatcher(player=player, editor=editor)

    dispatcher.handle("e", session)

    assert editor.received == ["안녕"]
    assert session.current().text == "고친 텍스트"
    assert session.dirty
    # 즉시 flush
    assert (tmp_path / "x.list").exists()
    assert "고친 텍스트" in (tmp_path / "x.list").read_text(encoding="utf-8")
```

GREEN: `e` 액션에서 `new = editor.edit(s.current().text); if new is not None: s.update_current_text(new); s.save()`.

### 시나리오 E — 취소 시 변경 없음

```python
def test_e_key_cancel_keeps_entry_intact(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=_entries())
    editor = FakeEditor(return_value=None)  # 취소
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=editor)

    dispatcher.handle("e", session)

    assert session.current().text == "안녕"
    assert not session.dirty
```

### 시나리오 F — 빈 문자열 입력은 정책 결정 포인트

```python
def test_e_key_empty_string_input(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=_entries())
    editor = FakeEditor(return_value="")  # 빈 텍스트
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=editor)

    dispatcher.handle("e", session)

    # 결정: 빈 텍스트도 유효한 편집으로 받는다 (자동 플래그는 Phase 09에서)
    assert session.current().text == ""
    assert session.dirty
```

학습 토론: 빈 텍스트는 거부할까? **1차 권장: 받는다.** 사용자가 의도적으로 비울 수 있고, Phase 09에서 자동 플래그로 경고만 표시.

## REFACTOR 게이트

- **4-0**: `FakeEditor`가 호출 횟수를 안 세고 입력을 list로 모음 — spy 패턴. OK.
- **4-1**:
  - `save()`가 atomic write로 가는가? — 1차 GREEN은 그냥 `write_text`. 4-1에서 `tmp + rename` 추출 권장.
  - `update_current_text` + `save` 2단계 호출이 항상 같이 일어나면 묶어서 `commit_text(new)`로? — 묶지 말 것. 명령(update)과 영속(save)의 책임 분리가 학습 가치.
- **4-2 (ODP 게이트)**:
  - `ReviewSession`은 이제 명백히 Entity ✅ (`dirty` 상태 + 식별자 `list_path`)
  - `TextEditor` Protocol — 의존성 계약 ✅
  - `PromptToolkitTextEditor`는 Service ✅ — 무상태
  - `dataclasses.replace`로 Value Object 불변성 유지 ✅
- **4-3**: 패턴 신호 없음. Command 패턴은 Phase 08에서 undo와 함께 도착 가능성.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `ReviewSession` | **Entity (강화)** | dirty 상태 추가, save 책임 |
| `TextEditor` (Protocol) | (계약) | DI 추상화 |
| `PromptToolkitTextEditor` | Service | prompt_toolkit 호출 래핑, 무상태 |
| `FakeEditor` | (테스트 더블) | spy |
| `dataclasses.replace` 결과 | **Value Object** | 새 인스턴스 — 기존 frozen이라 가능 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   └── review/
│       ├── editor.py           ← user types
│       ├── session.py          ← edit: update_current_text, dirty, save
│       └── keybindings.py      ← edit: e 키 등록, build_default_dispatcher 시그니처 변경
└── tests/unit/
    ├── test_review_session.py  ← edit: 시나리오 A, B 추가
    └── test_review_editor.py   ← user types (D, E, F)
```

## 완료 기준

- [ ] 시나리오 A~F 모두 통과
- [ ] `voxprep review some.list` → e 키로 텍스트 편집 → Enter로 확정 → 파일 즉시 반영 확인
- [ ] e → Escape 시 변경 없음 확인
- [ ] Phase 05/06 테스트가 여전히 통과 (`build_default_dispatcher` 시그니처 변경 전파 OK)
- [ ] `learnings/phase07-qa.md` (불변성 + replace, dirty 도입, 즉시 flush 정책)
- [ ] 커밋:
  - `feat: add TextEditor protocol and prompt_toolkit implementation`
  - `feat: add update_current_text and dirty save on ReviewSession`
  - `feat: wire e key to inline edit current entry text`
  - (선택) `refactor: write list file atomically via tmp + rename`

## 주의사항 / 엣지케이스

- **`prompt_toolkit.prompt()`의 화면 충돌**: review 루프가 Rich로 화면을 그리고 있는 상태에서 `prompt()`를 호출하면 출력이 뒤섞일 수 있음. 호출 전후에 `console.clear()` 또는 줄바꿈 출력으로 정리.
- **유니코드 입력**: 한국어 IME 편집 중 Escape 등이 IME 컨텍스트로 가는 경우. macOS Terminal에서는 보통 OK. 문제 발생 시 학습 메모로.
- **취소의 표현**: `prompt_toolkit`은 Ctrl-C → `KeyboardInterrupt`, Ctrl-D → `EOFError`. 두 경우 모두 None 반환. Escape는 기본적으로 입력 종료가 아니므로 별도 key_binding 등록 필요할 수 있음 — 1차로는 Ctrl-C/Ctrl-D만 취소로 정의해도 충분.
- **편집 중 재생 멈춤?**: e로 편집 들어가는 순간 이전 재생을 멈출지. 1차 권장: **멈추지 않음** (사용자가 들으면서 편집 가능). Phase 06의 `player.stop()`을 호출하지 않음.
- **`save()` 실패**: 디스크 풀, 권한 에러 등. 1차로는 예외를 그대로 올리고 review 루프가 friendly 메시지로 잡아주는 형태. 데이터 보존이 최우선이므로 예외 삼키지 말 것.
- **`dirty`가 켜졌는데 q로 종료할 때**: 이번 Phase에선 즉시 flush이므로 `dirty`가 켜진 채 종료될 일이 거의 없음. Phase 08에서 undo 후 dirty를 끄는 케이스가 생기면 다시 점검.

## 다음 Phase 준비

Phase 08은 삭제(d) + 1회 undo(u)입니다. 시작 전:

1. **하드 삭제** vs 소프트 삭제(deleted 플래그) 정책 결정 — 1차 권장은 하드 삭제 + 1단계 undo 메모리
2. Command 패턴이 자연스럽게 도착할 가능성 — 미리 이름을 꺼내지 말고, 두 작업(update_current_text, delete_current)의 undo를 같은 구조로 다룰 때 발견
3. `.review_progress.json` 도입 시점도 함께 결정 (cursor 위치 보존)
