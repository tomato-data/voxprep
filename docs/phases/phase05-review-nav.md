# Phase 05 — `review` 내비게이션 (n/b/q)

## 학습 목표

- **Entity의 첫 사례** — `ReviewSession`은 ID(파일 경로)로 식별되고, 시간이 흐르며 상태(현재 인덱스, dirty 플래그)가 바뀜. Value Object와의 차이를 몸으로 느끼기
- **키바인딩 dispatcher** 설계 — 키 입력 → 액션 함수 매핑을 어떻게 분리할 것인가
- 터미널 입력 처리의 두 갈래 (`prompt_toolkit.Application` vs 단순 `input()`/`getch`)
- "사용자 입력"을 의존성으로 만들어 테스트 가능하게 만들기 (input source seam)
- Phase 02의 `read_list_file`/`write_list_file` 재사용

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| 키 파싱 | `claude-code-study/keybindings/parser.ts` | `parseKeystroke("ctrl+k")` 같은 정규화 — 우리는 단일 문자 위주라 단순화 OK |
| Context-aware dispatch | `claude-code-study/keybindings/resolver.ts`, `KeybindingContext.tsx` | "이 화면에서만 유효한 키"의 분기 구조. 우리는 review 모드 단일 context라 단순화 |
| prompt_toolkit Application | https://python-prompt-toolkit.readthedocs.io/en/master/pages/full_screen_apps.html | 풀스크린 앱 만들 때 — 우리는 1차로 안 쓰고 더 단순한 길로 |
| `prompt_toolkit.input.create_input` | 공식 문서 | 한 키씩 읽기 위한 저수준 인터페이스 (의존성 주입에 적합) |

## 설계 결정 — 입력 처리 방식

두 가지 후보:

1. **`prompt_toolkit.Application`** (풀스크린): 화면 전체를 다시 그리며 키 이벤트를 비동기로 받음. 리치 UI 가능하지만 학습 곡선 큼.
2. **stdin 기반 단일 키 읽기 + Rich 출력**: Rich로 한 화면 그리고, `getch` 또는 `prompt_toolkit.input.create_input().read_keys()`로 한 키씩 받음. 단순.

**1차 권장: (2)**. 이유 — Phase 05~09 동안 점진적으로 기능을 더할 때, 풀스크린 앱은 매번 전체 레이아웃을 다시 짜야 함. 단순 read-loop는 한 단계씩 키 추가가 자연스러움. 풀스크린 전환은 Phase 09 회고 시점에 다시 결정.

## 구현 범위

### 만들 것

1. `src/voxprep/review/__init__.py`
2. `src/voxprep/review/session.py` — `ReviewSession` Entity
   - `__init__(self, list_path: Path, entries: list[ListEntry])`
   - 상태: `cursor: int`, `dirty: bool`
   - 메서드: `current() -> ListEntry`, `next() -> None`, `prev() -> None`, `is_at_start() -> bool`, `is_at_end() -> bool`
   - 보존: `len(entries)`, `cursor`는 `0..len-1` 범위 강제
3. `src/voxprep/review/keybindings.py` — Dispatcher
   - `KeyAction = Callable[[ReviewSession], ReviewOutcome]`
   - `ReviewOutcome` Enum: `CONTINUE`, `QUIT`
   - `Dispatcher` 클래스: `register(key: str, action: KeyAction)`, `handle(key: str, session) -> ReviewOutcome`
   - 미등록 키는 `CONTINUE` 반환 (무시)
4. `src/voxprep/review/render.py` — `render_session(session: ReviewSession) -> RenderableType` (Rich panel/table)
   - 현재 인덱스/총 개수, 현재 entry의 4개 필드, 키 도움말 한 줄 표시
5. `src/voxprep/review/loop.py` — `run_review_loop(session, dispatcher, key_source, console)` 자유 함수
   - `key_source: Iterator[str]` — 의존성 주입으로 테스트 시 list로 대체
   - `console: rich.console.Console`
   - 흐름: while True → render → 다음 키 read → dispatch → outcome == QUIT면 break
6. `src/voxprep/commands/review.py` — Typer 커맨드
   - 인자: `list_file: Path`
   - 부트: `read_list_file` → `ReviewSession` 생성 → 기본 `Dispatcher` 구성 (n/b/q만) → `run_review_loop` 호출
   - real `key_source`는 `prompt_toolkit.input.create_input()` 기반
7. 테스트:
   - `tests/unit/test_review_session.py` — Entity 상태 전이
   - `tests/unit/test_review_dispatcher.py` — 키 → 액션 매핑
   - `tests/unit/test_review_loop.py` — 가짜 key_source로 전체 루프 통합

### 미루는 것 (다음 Phase로)

- Enter 키로 오디오 재생 → Phase 06
- e 키로 인라인 편집 → Phase 07
- d/u 키로 삭제/undo → Phase 08
- 자동 플래그 시각 경고 → Phase 09
- 진행상황 저장(`.review_progress.json`) → Phase 08 즈음 (dirty 처리와 함께)

## TDD 사이클 시나리오

### 시나리오 A — Session 생성과 cursor 초기값

```python
from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession


def _entry(name: str) -> ListEntry:
    return ListEntry(f"{name}.wav", "narrator", "ko", name)


def test_session_starts_at_first_entry():
    entries = [_entry("a"), _entry("b"), _entry("c")]
    session = ReviewSession(list_path=Path("x.list"), entries=entries)

    assert session.cursor == 0
    assert session.current() == entries[0]
    assert session.is_at_start()
    assert not session.is_at_end()
```

### 시나리오 B — next/prev 경계

```python
def test_next_advances_cursor():
    session = _make_session(3)

    session.next()

    assert session.cursor == 1


def test_next_at_end_does_not_overflow():
    session = _make_session(3)
    session.next()
    session.next()  # cursor=2 (마지막)

    session.next()  # 무동작 또는 동일 위치 유지

    assert session.cursor == 2
    assert session.is_at_end()


def test_prev_at_start_does_not_underflow():
    session = _make_session(3)

    session.prev()

    assert session.cursor == 0
```

**결정 포인트**: 끝에서 next는 무동작? 또는 회귀(첫 entry로 wrap)? 학습 토론 — 1차 권장은 **clamp (무동작)**.

### 시나리오 C — Dispatcher 등록과 호출

```python
from voxprep.review.keybindings import Dispatcher, ReviewOutcome


def test_dispatcher_invokes_registered_action():
    calls = []
    dispatcher = Dispatcher()
    dispatcher.register("n", lambda s: (calls.append("n"), ReviewOutcome.CONTINUE)[1])

    outcome = dispatcher.handle("n", session=None)

    assert calls == ["n"]
    assert outcome == ReviewOutcome.CONTINUE


def test_dispatcher_ignores_unknown_key():
    dispatcher = Dispatcher()

    assert dispatcher.handle("z", session=None) == ReviewOutcome.CONTINUE


def test_quit_action_returns_quit_outcome():
    dispatcher = Dispatcher()
    dispatcher.register("q", lambda s: ReviewOutcome.QUIT)

    assert dispatcher.handle("q", session=None) == ReviewOutcome.QUIT
```

### 시나리오 D — Loop 통합 (key_source 주입)

```python
from io import StringIO

from rich.console import Console

from voxprep.review.loop import run_review_loop


def test_loop_quits_on_q():
    session = _make_session(3)
    dispatcher = _build_default_dispatcher()  # n, b, q 등록

    keys = iter(["n", "n", "q"])
    console = Console(file=StringIO(), force_terminal=False)

    run_review_loop(session, dispatcher, key_source=keys, console=console)

    assert session.cursor == 2  # n n 으로 2번 전진
```

GREEN: `run_review_loop`은 단순한 while 루프. `next(key_source)`로 한 키씩.

### 시나리오 E — Render 출력 안정성 (스냅샷 같은 거 X, 핵심 정보만)

```python
def test_render_includes_position_and_text():
    session = _make_session(3)

    rendered = render_session(session)

    text = _to_plain_text(rendered)  # Rich → str 헬퍼
    assert "1/3" in text
    assert session.current().text in text
```

GREEN: Rich `Panel` 또는 `Table`로 단순 렌더.

## REFACTOR 게이트

- **4-0**: `_make_session` 헬퍼는 테스트 conftest나 파일 상단에. 픽스처화 가능.
- **4-1**: `ReviewSession`이 너무 부풀지 않게. `dirty` 플래그는 Phase 07부터 등장하므로 지금은 추가 X.
- **4-2 (ODP 게이트)**:
  - `ReviewSession`은 Entity ✅ — `list_path`로 식별, `cursor`/`dirty` 상태 변화, 메서드가 부수효과 가짐
  - `Dispatcher`는 Service ✅ — registry를 보유하지만 "처리 자체"는 무상태. 또는 "registry"가 상태라 작은 Entity로 볼 수도 있음 → 학습 토론 포인트
  - `ReviewOutcome`은 Enum (Value Object의 한 형태)
  - `run_review_loop`는 자유 함수 (어댑터 한 층)
- **4-3**: 패턴 신호 없음.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `ReviewSession` | **Entity** | 상태 변화 + 식별성 |
| `Dispatcher` | Service | registry는 의존성으로 보면 Service, registry를 Entity로 보면 작은 Entity. 학습 토론 |
| `ReviewOutcome` | Enum / Value Object | 분기 결과 표현 |
| `run_review_loop` | 자유 함수 | 어댑터 |
| `key_source: Iterator[str]` | (의존성) | 입력 seam — 테스트에서 list로 대체 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   ├── review/
│   │   ├── __init__.py
│   │   ├── session.py          ← user types (Entity)
│   │   ├── keybindings.py      ← user types (Dispatcher, ReviewOutcome)
│   │   ├── render.py           ← user types (Rich render)
│   │   └── loop.py             ← user types (run_review_loop)
│   └── commands/
│       └── review.py           ← user types (Typer command)
└── tests/unit/
    ├── test_review_session.py     ← user types
    ├── test_review_dispatcher.py  ← user types
    └── test_review_loop.py        ← user types
```

## 완료 기준

- [ ] 시나리오 A~E 모두 통과
- [ ] `voxprep review some.list` 실행 시 화면이 그려지고 n/b/q가 동작
- [ ] q로 종료 시 변경 없으면 파일 그대로 (dirty=False)
- [ ] `key_source`가 의존성으로 주입되어 테스트가 100% in-process
- [ ] `learnings/phase05-qa.md` 작성 (특히 Entity vs Service 첫 토론)
- [ ] 커밋:
  - `feat: add ReviewSession entity with cursor navigation`
  - `feat: add review key dispatcher and loop`
  - `feat: add review command wired to navigation only`

## 주의사항 / 엣지케이스

- **빈 `.list` 파일**: entries가 0개이면 `current()` 호출 불가. 부트 시점에 검증해서 friendly 에러 메시지로 종료.
- **`prompt_toolkit.input.create_input()` 사용 주의**: 컨텍스트 매니저 패턴, raw mode 진입 필요. 진짜 사용은 `commands/review.py`에서만 하고 `loop.py`는 추상 iterator만 받기.
- **터미널이 redirect되어 있을 때**: pipe로 들어온 입력은 raw mode 못 잡음. `sys.stdin.isatty()` 체크해서 friendly 에러.
- **Rich 출력 정리**: 매 키 입력마다 화면을 다시 그릴지(`console.clear()`), 단순히 새 패널을 아래에 출력할지 결정. 1차 권장은 **`console.clear()` + 새 render** — 단순.
- **Windows 호환**: `getch`는 Windows에서 다르게 동작. `prompt_toolkit`은 cross-platform이라 권장 — 학습 단계에서는 macOS만 지원해도 OK라고 결정해도 됨.
- **`q`로 종료할 때 저장?**: 이번 Phase는 dirty가 없으므로 무관. Phase 07~08에서 dirty가 True일 때의 정책 (자동 저장 vs 확인 프롬프트)을 다시 결정.

## 다음 Phase 준비

Phase 06에서 Enter 키로 현재 entry의 오디오를 재생합니다. 시작 전:

1. `afplay` 명령 확인 (`which afplay` — macOS 기본)
2. `subprocess.Popen` vs `subprocess.run` 의 차이 — 비동기 재생을 원하는지 학습 토론
3. Linux/Windows 호환은 어떻게 할지 (afplay → aplay → start) 미리 생각
