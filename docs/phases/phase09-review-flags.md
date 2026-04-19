# Phase 09 — `review` 자동 플래그 시각 경고 (+ `--auto-prune`)

## 학습 목표

- **규칙 집합의 응집** — 여러 검사 함수가 모일 때 어떻게 묶을 것인가. 평탄한 list로 둘지 클래스로 묶을지
- **순수 함수 vs Service** 비교 — 검사 규칙들은 입력만으로 결과 — 자유 함수가 자연스러움
- **정책과 표현의 분리** — 검사 결과(`Issue`)는 데이터, 표시(`⚠`)는 렌더링 책임
- `--auto-prune` 모드 — 같은 규칙을 반대 방향(필터)으로 사용하는 경험
- (선택) Strategy 패턴 도착 신호 점검 — 검사기가 5개를 넘을 때

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| Phase 05 `render_session` | `src/voxprep/review/render.py` | 경고 표시 자리 |
| Phase 02 `ListEntry` | `src/voxprep/parsing/list_file.py` | 검사 대상 |
| Rich `Text` 스타일 | https://rich.readthedocs.io/en/stable/text.html | 색상/굵기로 경고 표시 |

## 자동 플래그 규칙 (사용자 정의)

> **출처**: `voxprep/GPT-SoVITS/docs/ko/SETUP_GUIDE.md` 3-4절 "ASR 결과 정리". 사용자가 Korean voice 데이터셋을 직접 처리하면서 정의한 제거 대상 목록입니다. voxprep `--auto-prune`은 이 규칙을 자동화한 것입니다.

| 규칙 키 | 설명 | 예시 | SETUP_GUIDE 출처 |
|---------|------|------|------------------|
| `empty_text` | text가 빈 문자열 또는 공백만 | `""`, `"   "` | "텍스트가 비어있는 항목" |
| `too_short` | text 길이 ≤ 3 글자 (사용자 명시 임계값) | `"아"`, `"안녕"` | "3글자 이하의 너무 짧은 항목" |
| `interjection_only` | 단순 반복 감탄사 (`음`, `응`, `어`, `아` 등) | `"음"`, `"어어어"`, `"응응"` | "음, 응, 어, 아 등 단순 반복만 있는 항목" |
| `non_korean_noise` | 한국어 데이터셋인데 한국어 외 글자만 (한자/일본어/라틴) | `language=ko` entry에 `"こんにちは"` | "비한국어 (일본어, 영어 잡음)" — **사용자가 직접 강조** |
| `too_long` | text 길이 ≥ 60 글자 — slice가 잘못됐을 가능성 | 한 청크에 두 문장 | (voxprep 추가, 사용자 명시 X) |
| `punctuation_only` | 구두점/숫자만 | `"???"`, `"123"` | "ASR 오인식" 일부 |

> **3글자 임계값은 사용자 명시값**. CJK 2글자/라틴 3글자 같은 언어별 분기는 1차 범위 외 — 사용자 데이터셋이 한국어 단일이라 단순한 글자 수 임계값으로 충분.

> **`non_korean_noise`는 1차 GREEN에 포함**. 단순 구현으로 가능: `language == "ko"`일 때 텍스트의 한글(가-힣) 비율이 일정 % 이하이면 플래그. 한국어 데이터셋이 voxprep의 기본 가정이라 이 규칙은 우선순위가 높습니다.

## 구현 범위

### 만들 것

1. `src/voxprep/review/issues.py`
   - `Severity` Enum: `INFO`, `WARN`, `SUSPICIOUS_DELETE_CANDIDATE`
   - `Issue` Value Object: `code: str`, `severity: Severity`, `message: str`
   - 검사 함수들 (모두 `(entry: ListEntry) -> Issue | None` 시그니처):
     - `check_empty_text`
     - `check_too_short` — 임계값 **3** (사용자 명시)
     - `check_too_long`
     - `check_interjection_only` — `INTERJECTIONS = {"아", "어", "오", "음", "응", "에이"}` (사용자 명시 4개 + 일반 보강)
     - `check_punctuation_only`
     - `check_non_korean_noise` — `language == "ko"`일 때 한글 비율 검사
   - `ALL_CHECKS: list[Callable[[ListEntry], Issue | None]]`
   - `inspect(entry: ListEntry, checks=ALL_CHECKS) -> list[Issue]`
2. `src/voxprep/review/render.py` — `render_session`이 현재 entry의 `inspect()` 결과를 받아 경고 라인 추가
3. `src/voxprep/commands/review.py`
   - `--auto-prune` 플래그 추가
   - 활성 시: review 시작 전에 모든 entry inspect → `SUSPICIOUS_DELETE_CANDIDATE` severity가 있는 entry만 순회하며 사용자에게 d/skip 확인
4. `src/voxprep/review/loop.py` — `--auto-prune` 모드일 때 loop의 다음 entry 선택 로직이 다름. 두 가지 접근:
   - (a) `run_review_loop`에 `entry_filter: Callable[[ListEntry], bool]` 추가
   - (b) 별도 `run_auto_prune_loop` 함수
   1차 권장: **(b)** — `if/else`로 분기하지 말고 응집된 두 함수.
5. 테스트:
   - `tests/unit/test_issues.py` — 각 검사 함수 + `inspect`
   - `tests/unit/test_render_with_issues.py` — 경고가 렌더 출력에 나타나는지
   - `tests/unit/test_auto_prune_loop.py` — fake key_source로 통합 테스트

### 미루는 것

- `mismatched_language`
- 사용자 정의 규칙 (외부 설정 파일)
- 규칙 일괄 disable 옵션

## TDD 사이클 시나리오

### 시나리오 A — `check_empty_text`

```python
from voxprep.parsing.list_file import ListEntry
from voxprep.review.issues import check_empty_text, Severity


def test_empty_text_returns_warn():
    entry = ListEntry("a.wav", "s", "ko", "")

    issue = check_empty_text(entry)

    assert issue is not None
    assert issue.code == "empty_text"
    assert issue.severity == Severity.WARN


def test_whitespace_only_text_returns_warn():
    entry = ListEntry("a.wav", "s", "ko", "   ")

    assert check_empty_text(entry) is not None


def test_non_empty_text_returns_none():
    entry = ListEntry("a.wav", "s", "ko", "hi")

    assert check_empty_text(entry) is None
```

GREEN: `if not entry.text.strip(): return Issue("empty_text", Severity.WARN, "Text is empty")`

### 시나리오 B — `check_too_short` (사용자 임계값 3글자)

```python
def test_too_short_three_chars_or_less():
    for text in ["", "아", "안녕"]:  # 0, 1, 2 글자
        entry = ListEntry("a.wav", "s", "ko", text)
        assert check_too_short(entry) is not None, f"{text!r} should flag"


def test_three_chars_exactly_is_boundary():
    entry = ListEntry("a.wav", "s", "ko", "안녕요")  # 3글자

    # SETUP_GUIDE "3글자 이하" → 3글자 포함
    assert check_too_short(entry) is not None


def test_four_chars_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세")  # 4글자

    assert check_too_short(entry) is None
```

GREEN: `MIN_TEXT_LEN = 3`(상수) + `if len(entry.text.strip()) <= MIN_TEXT_LEN: ...`. 언어별 분기 X — 사용자 데이터셋이 한국어라 글자 수 단순 임계값으로 충분.

> "이하"의 경계 해석: SETUP_GUIDE는 "3글자 이하"라고 했으므로 3글자도 포함해서 플래그. 시나리오 자체에 명시.

### 시나리오 C — `check_interjection_only`

```python
def test_interjection_only():
    # SETUP_GUIDE: "음, 응, 어, 아 등 단순 반복만"
    for text in ["아", "어어어", "음", "에이", "오", "응", "응응응"]:
        entry = ListEntry("a.wav", "s", "ko", text)
        assert check_interjection_only(entry) is not None, f"{text!r} should flag"


def test_non_interjection_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세요")

    assert check_interjection_only(entry) is None
```

GREEN: `INTERJECTIONS = {"아", "어", "오", "음", "응", "에이"}` — 사용자 명시 4개(`아`,`어`,`오`,`음`,`응`) + `에이`. 반복 글자(`어어어`, `응응응`)는 `re.sub(r"(.)\1+", r"\1", text)`로 압축 후 비교. **학습 토론 포인트**: 정규화 책임을 어디 둘 것인가, `에이` 같은 2글자는 어떻게 다룰지.

### 시나리오 C-2 — `check_non_korean_noise` (사용자 핵심 규칙)

```python
def test_non_korean_text_in_korean_entry_flags():
    entry = ListEntry("a.wav", "s", "ko", "こんにちは")  # 일본어

    issue = check_non_korean_noise(entry)

    assert issue is not None
    assert issue.code == "non_korean_noise"


def test_korean_text_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세요")

    assert check_non_korean_noise(entry) is None


def test_mixed_with_majority_korean_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕 hello")  # 대부분 한국어

    assert check_non_korean_noise(entry) is None


def test_non_ko_language_entry_skipped():
    entry = ListEntry("a.wav", "s", "en", "hello world")

    # language가 ko가 아니면 이 검사는 무시
    assert check_non_korean_noise(entry) is None
```

GREEN: `if entry.language != "ko": return None` → 한글(`\uAC00-\uD7A3`) + 호환 자모 비율 계산 → 50% 미만이면 플래그. 임계값 50%는 학습 토론 포인트(엄격한 80%? 너그러운 30%?), 회고에 결정 근거 적기.

### 시나리오 D — `inspect`가 모든 검사를 모은다

```python
from voxprep.review.issues import inspect


def test_inspect_runs_all_checks():
    entry = ListEntry("a.wav", "s", "ko", "")  # empty + too_short 둘 다 잡힘

    issues = inspect(entry)

    codes = {i.code for i in issues}
    assert "empty_text" in codes
    assert "too_short" in codes  # 빈 문자열은 길이 0이라 too_short도 발화
```

GREEN: `[c(entry) for c in checks if c(entry) is not None]`.

### 시나리오 E — Render에 경고 표시

```python
def test_render_includes_warning_for_flagged_entry():
    session = ReviewSession(
        list_path=Path("x.list"),
        entries=[ListEntry("a.wav", "s", "ko", "")],
    )

    rendered = render_session(session)
    text = _to_plain_text(rendered)

    assert "⚠" in text or "warning" in text.lower()
    assert "empty_text" in text or "empty" in text.lower()
```

GREEN: `render_session` 안에서 `inspect(session.current())` 호출 → issues가 있으면 경고 줄 추가.

### 시나리오 F — `--auto-prune` 모드: 의심 entry만 순회

```python
def test_auto_prune_iterates_only_flagged_entries(tmp_path):
    entries = [
        ListEntry("a.wav", "s", "ko", "정상 텍스트입니다"),  # 통과
        ListEntry("b.wav", "s", "ko", ""),                  # 플래그
        ListEntry("c.wav", "s", "ko", "이것도 정상입니다"),  # 통과
        ListEntry("d.wav", "s", "ko", "아"),                # 플래그
    ]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)

    visited: list[str] = []
    confirmer = ScriptedConfirmer(["n", "n"])  # 둘 다 skip
    keys = iter([])  # auto_prune은 키 없이 confirmer만으로 진행

    run_auto_prune_loop(
        session,
        confirmer=confirmer,
        on_visit=lambda e: visited.append(e.audio_path),
    )

    assert visited == ["b.wav", "d.wav"]
```

GREEN: 별도 함수 `run_auto_prune_loop`. 자동으로 의심 entry로 점프 → confirmer.confirm("Delete?") → True면 delete, False면 다음.

`ScriptedConfirmer`는 시나리오마다 응답 시퀀스를 받는 더블.

## REFACTOR 게이트

- **4-0**: 시나리오들이 단일 검사를 검증, OK
- **4-1**:
  - 임계값 상수 추출 (`MAX_LONG_TEXT_LEN = 60` 등)
  - INTERJECTIONS 셋의 정규화 로직이 두 곳 이상에 나타나면 헬퍼 추출
- **4-2 (ODP 게이트)**:
  - `Issue`는 Value Object ✅
  - 검사 함수들은 자유 함수 ✅ — 클래스화 X
  - `Severity`는 Enum
  - `inspect`는 자유 함수 ✅
- **4-3 (패턴 신호)**:
  - **Strategy 도착했나?** — 검사가 5개. "검사를 plug-in처럼 추가/제거하고 싶다"는 욕구가 있으면 도착. 1차 GREEN에서는 `ALL_CHECKS` list로 충분 — Strategy의 절반 (인터페이스 통일). 명시적 `Check` 클래스로 만들 필요는 없음. 회고에 "함수 시그니처 자체가 strategy 인터페이스 역할"이라고 정리.
  - dirty 플래그의 운명: 즉시 flush 정책으로 사실상 의미 없음 → REFACTOR로 제거 검토 (별도 커밋).

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `Issue` | **Value Object** | code/severity/message 값 비교 |
| `Severity` | Enum | |
| 검사 함수들 | 자유 함수 | 순수 함수 — 입력 → 출력 |
| `inspect` | 자유 함수 | 함수들의 합성 |
| `run_auto_prune_loop` | 자유 함수 | 또 하나의 어댑터 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   ├── review/
│   │   ├── issues.py           ← user types
│   │   ├── render.py           ← edit: 경고 라인 추가
│   │   └── loop.py             ← edit: run_auto_prune_loop 추가
│   └── commands/
│       └── review.py           ← edit: --auto-prune 플래그
└── tests/unit/
    ├── test_issues.py              ← user types
    ├── test_render_with_issues.py  ← user types
    └── test_auto_prune_loop.py     ← user types
```

## 완료 기준

- [ ] 시나리오 A~F 모두 통과
- [ ] `voxprep review some.list` → 빈 텍스트 entry에서 ⚠ 경고 표시 확인
- [ ] `voxprep review some.list --auto-prune` → 의심 entry만 순회 확인
- [ ] Phase 05~08 테스트가 여전히 통과
- [ ] (선택) `dirty` 플래그 제거 리팩터 + 커밋
- [ ] `learnings/phase09-qa.md` (Strategy 도착 관찰, 함수 vs 클래스, dirty 운명)
- [ ] 커밋:
  - `feat: add issue checks for review entries`
  - `feat: render warnings for flagged entries`
  - `feat: add --auto-prune review mode`
  - (선택) `refactor: drop unused dirty flag from ReviewSession`

## 주의사항 / 엣지케이스

- **언어별 길이 기준**: 사용자 데이터셋이 한국어라 단순 글자 수(임계값 3) 사용. 다국어 데이터셋이 들어오면 회고에서 분기 검토.
- **`non_korean_noise`의 임계값**: 한글 비율 50% 기준은 임의값. 사용자 데이터셋에 한자/영문이 섞여 있을 가능성 — 처음 돌릴 때 false positive가 많으면 회고에 임계값 조정 기록.
- **반복 감탄사**: `어어어`, `아아아아`. 단순화 정규화는 `re.sub(r"(.)\1+", r"\1", text)` 같은 식으로 연속 문자 압축. 욕심내면 함정 — 문장 안에 들어간 의도된 강조까지 잡힘. 1차 한정: **단일 토큰일 때만 정규화**.
- **`punctuation_only` 함정**: 한국어 문장 부호와 영어 문장 부호 모두 커버해야 함. `unicodedata.category(c).startswith("P")` 활용.
- **`--auto-prune`이 단 하나의 의심도 못 찾았을 때**: 즉시 종료 + "No suspicious entries found." 메시지.
- **`--auto-prune`에서 d/skip 외 명령이 필요할까?** — 1차로는 d(delete)/n(skip)/q(quit) 세 개만. e(edit)는 일반 review 모드에서 하라고 안내. 회고에서 학습 토론.
- **검사 비용**: 모든 entry를 시작 시 한 번 검사. `.list`가 수만 줄이면 약간 느림. 1차로는 그대로, 회고에 "lazy iter 검토".

## 다음 Phase 준비

Phase 10은 `prep` 올인원 파이프라인입니다. 시작 전:

1. `voxprep slice → asr → review` 흐름이 연결될 때 사용자 시점에서 어떤 인자가 자연스러운지 손그림으로 그려보기
2. `subprocess.Popen`으로 자식 voxprep 호출 vs 함수 직접 호출 — 1차 권장은 **함수 직접 호출** (in-process). 의존성 객체 재사용이 자연스러움.
3. Rich `Live`로 여러 단계 진행률을 한 화면에 합치는 예제 한 번 보기
