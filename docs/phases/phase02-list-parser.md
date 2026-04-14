# Phase 02 — `.list` 파서 (Value Object)

## 학습 목표

- `@dataclass(frozen=True)`로 **Value Object**를 만드는 첫 경험
- 값 동등성(`__eq__`)과 해시 가능성(`__hash__`)이 자동으로 따라오는 이유 이해
- 파싱은 클래스메서드(`from_line`) 또는 자유 함수 어디에 두는 게 자연스러운지 직접 비교
- 잘못된 입력에 대한 예외 정책 설계 — "어디서 검증할 것인가"의 첫 결정
- 파일 IO와 라인 단위 파싱의 분리 (한 단위 테스트가능성을 깨지 않게)

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| `.list` 생성 코드 | `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py:136` | `f"{file_path}|{speaker_name}|{lang.upper()}|{text}"` 출력 형식 확인 |
| `.list` 생성 코드 (FunASR) | `voxprep/GPT-SoVITS/tools/asr/funasr_asr.py:87` | 동일 포맷, 언어 코드만 다름 (zh/yue) |
| `.list` 소비 코드 | `voxprep/GPT-SoVITS/GPT_SoVITS/prepare_datasets/1-get-text.py:129` | `line.split("|")`로 4-field 분해 — 우리도 이 단계와 호환되어야 함 |
| ODP Value Object 규칙 | `~/.claude/skills/object-design-practices/rules/` | 불변성, `__eq__` 값 비교, 식별자 없음 |

## `.list` 포맷 (확정)

```
audio_path|speaker_name|language|text
```

- 구분자: `|` (정확히 3개)
- 인코딩: UTF-8
- 줄 구분: `\n`
- 한 줄 = 한 세그먼트 (오디오 한 chunk의 ASR 결과)
- `audio_path`: 상대/절대 경로 모두 가능 — 파서는 검증하지 않음 (파일 존재 확인은 `slice`/`asr` 단계 책임)
- `speaker_name`: 임의 문자열, 빈 문자열 허용 X (Phase 04에서 디폴트 부여)
- `language`: 대소문자 혼재 가능 (`ZH`/`zh`, `JP`/`ja`, `EN`/`en`, `KO`/`ko`, `YUE`/`yue`). 파서는 **소문자로 정규화**해 저장.
- `text`: 임의 문자열. **`|` 포함 불가** (split이 깨짐) — 발견 시 예외.

## 구현 범위

### 만들 것

1. `src/voxprep/parsing/__init__.py`
2. `src/voxprep/parsing/list_file.py` — 다음 두 가지:
   - `ListEntry` Value Object: `audio_path: str`, `speaker: str`, `language: str`, `text: str` 4 필드, frozen
   - `ListEntry.from_line(line: str) -> ListEntry` — 한 줄 파싱
   - `ListEntry.to_line(self) -> str` — 직렬화 (round-trip 보장)
   - `read_list_file(path: Path) -> list[ListEntry]` — 파일 → 리스트
   - `write_list_file(path: Path, entries: Iterable[ListEntry]) -> None` — 리스트 → 파일
3. `src/voxprep/parsing/errors.py` — `MalformedListLineError(ValueError)` (어느 줄이 어떻게 잘못됐는지 메시지 포함)
4. `tests/unit/test_list_parser.py` — 아래 시나리오들

### 미루는 것

- `.list` 파일을 받아 파일 시스템에서 오디오 존재를 검증하는 로직 → `slice`/`review` 책임
- 정렬, 중복 제거 → 필요해진 Phase에서

## TDD 사이클 시나리오

테스트는 **작은 단위로 한 번에 한 시나리오**씩 추가합니다. 각 테스트마다 RED → GREEN → 다음 테스트.

### 시나리오 A — 한 줄 파싱

```python
from voxprep.parsing.list_file import ListEntry


def test_from_line_parses_four_fields():
    line = "data/wav/01.wav|narrator|ko|안녕하세요"

    entry = ListEntry.from_line(line)

    assert entry.audio_path == "data/wav/01.wav"
    assert entry.speaker == "narrator"
    assert entry.language == "ko"
    assert entry.text == "안녕하세요"
```

GREEN 최소 구현: `split("|", 3)` + `dataclass`.

### 시나리오 B — 언어 정규화

```python
def test_from_line_lowercases_language():
    entry = ListEntry.from_line("a.wav|s|ZH|你好")

    assert entry.language == "zh"
```

GREEN: `language.lower()` 한 줄 추가. 이미 통과하는 시나리오 A를 깨지 않게 주의.

### 시나리오 C — Value Object 동등성

```python
def test_value_equality():
    a = ListEntry("a.wav", "s", "ko", "hi")
    b = ListEntry("a.wav", "s", "ko", "hi")

    assert a == b
    assert hash(a) == hash(b)
```

GREEN: 이미 `@dataclass(frozen=True)`라면 자동 통과. 통과하지 않는다면 `frozen=True` 빠진 것 — 진단 기회.

### 시나리오 D — 잘못된 줄: 필드 부족

```python
import pytest

from voxprep.parsing.errors import MalformedListLineError


def test_from_line_rejects_three_fields():
    with pytest.raises(MalformedListLineError) as excinfo:
        ListEntry.from_line("a.wav|s|ko")

    assert "expected 4 fields" in str(excinfo.value).lower()
```

GREEN: split 결과 길이 검사.

### 시나리오 E — 잘못된 줄: text에 `|` 포함

```python
def test_from_line_rejects_pipe_in_text():
    with pytest.raises(MalformedListLineError):
        ListEntry.from_line("a.wav|s|ko|hello|world")
```

GREEN: 길이 검사가 5필드를 거부함 — 시나리오 D의 메시지는 "expected 4"라는 게 시나리오 E도 의미를 잘 전달하는지 점검 (좋은 학습 포인트).

### 시나리오 F — round-trip

```python
def test_to_line_round_trips():
    entry = ListEntry("a.wav", "narrator", "ko", "안녕")

    assert ListEntry.from_line(entry.to_line()) == entry
```

GREEN: `to_line`을 `f"{audio_path}|{speaker}|{language}|{text}"`로 구현. 단, **language 정규화 후 round-trip이 안전한지** 의식해야 함 — `from_line("a|s|ZH|x").to_line() == "a|s|zh|x"`로 변형됨. 이게 의도인가? **그렇다** (정규화는 명시적 정책이라고 회고에 적기).

### 시나리오 G — 파일 read/write

`tmp_path` 픽스처 사용:

```python
from pathlib import Path

from voxplep.parsing.list_file import read_list_file, write_list_file  # 의도적 typo? 아니, voxprep


def test_write_then_read(tmp_path: Path):
    entries = [
        ListEntry("a.wav", "s1", "ko", "hi"),
        ListEntry("b.wav", "s2", "en", "hello"),
    ]
    target = tmp_path / "test.list"

    write_list_file(target, entries)
    loaded = read_list_file(target)

    assert loaded == entries
```

GREEN: `Path.write_text("\n".join(e.to_line() for e in entries), encoding="utf-8")` + 마지막 개행 정책 결정 (붙일까 말까 — 학습 포인트로 유저에게 물어볼 것).

## REFACTOR 게이트

- **4-0 (테스트 품질)**: 각 테스트가 한 가지만 검증하는가? 위 시나리오들은 OK.
- **4-1 (코드 냄새)**: `from_line`이 분기 많은가? — 빈 문자열 처리/필드 길이 검사 정도면 OK. 길어지면 `_validate_fields` 추출.
- **4-2 (ODP 게이트)**:
  - `ListEntry`가 정말 Value Object인가? → 식별자 없음, frozen, `__eq__` 값 비교 ✅
  - 의존성을 받는가? → 받지 않음 (Service 아님) ✅
  - `read_list_file`/`write_list_file`은 함수형 — 모듈 수준 함수로 두는 게 자연스러움 (Service로 클래스화 X)
- **4-3 (패턴 신호)**: 아직 없음.

## ODP 관점

| 객체 | 분류 | 근거 |
|------|------|------|
| `ListEntry` | **Value Object** | 4개 필드 값으로 식별, 불변, 식별자 없음 |
| `MalformedListLineError` | (예외) | 분류 외 |
| `read_list_file` / `write_list_file` | 자유 함수 | 상태/의존성 없음. 굳이 클래스로 묶을 이유 없음 |

이 Phase의 가장 큰 ODP 학습: **모든 것을 클래스로 만들 필요가 없다.** Service-가짜를 피하기.

## 파일 구조 (Phase 종료 시 추가/변경)

```
voxprep/
├── src/voxprep/
│   └── parsing/
│       ├── __init__.py
│       ├── list_file.py        ← user types
│       └── errors.py           ← user types
└── tests/unit/
    └── test_list_parser.py     ← user types
```

## 완료 기준

- [ ] 시나리오 A~G 모두 통과
- [ ] `MalformedListLineError`가 어느 줄·어느 필드가 잘못됐는지 메시지에 포함
- [ ] round-trip 정책(언어 정규화 적용 후 동일성 깨짐) 회고에 명시
- [ ] `learnings/phase02-qa.md` 작성
- [ ] 커밋 분리:
  - `feat: parse list file lines into ListEntry value objects`
  - (필요 시) `refactor: extract list-line field validation`
- [ ] `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py:136` 근처를 한 번 더 보고 우리 포맷이 호환되는지 확인

## 주의사항 / 엣지케이스

- **개행 정책**: 마지막 줄에 `\n`을 붙일지 말지 — 일관성만 있으면 됨. GPT-SoVITS의 기존 `.list` 파일을 한 개 열어보고 거기 컨벤션을 따르는 게 안전.
- **빈 줄 처리**: `read_list_file`은 파일 끝의 빈 줄을 무시할까, 예외를 던질까? 학습 흐름엔 "무시" 쪽이 무난. 회고에 결정 근거 적기.
- **Path vs str**: `audio_path`는 일단 `str`로 둠. `Path`로 강타입화하면 round-trip 검증이 복잡해지고, 파싱 단계에서 파일 시스템 의존이 들어옴 → 다음 Phase로 미룸.
- **유니코드 정규화**: 한국어 `안녕` 같은 텍스트의 NFC/NFD 차이는 이 Phase에서 다루지 않음. `from_line`은 입력을 그대로 보존.
- **언어 코드 화이트리스트?**: `zh`/`ja`/`en`/`ko`/`yue` 외 값을 거부할지 여부는 학습 포인트 — 일단 거부하지 않고 **소문자로만 정규화**. 화이트리스트 검증은 `asr` 출력 검증 단계에서 다시 결정.
- **`tests/unit/test_list_parser.py` 안의 import 오타 주의**: 위 시나리오 G 스니펫에 일부러 `voxplep`이라고 적어둔 부분은 사용자가 RED로 한 번 만나보게 하려는 의도 — 직접 발견하면 좋은 학습 순간.

## 다음 Phase 준비

Phase 03에서 `slice` 커맨드를 만듭니다. 시작 전에:

1. `voxprep/GPT-SoVITS/tools/slicer2.py` 전체를 한 번 읽어보기 (200줄 안팎)
2. `voxprep/GPT-SoVITS/tools/slice_audio.py` (CLI 진입점) 한 번 읽어보기
3. `Slicer.__init__` 파라미터 6개의 의미를 한국어로 메모해두면 Phase 03 시작이 빠릅니다
