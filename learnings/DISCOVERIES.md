# DISCOVERIES

voxprep 개발 과정에서 **디버깅·에러·시행착오를 통해 "자연스럽게 알게 된 것들"**의 누적 로그입니다. Q&A(`phaseNN-qa.md`)는 내가 **직접 던진 질문**의 기록이고, 이 파일은 **내가 묻지 않았는데 튀어나와 배우게 된 것들**의 기록입니다. 둘 다 학습의 산출물이지만 성격이 달라서 분리합니다.

엔트리 작성 원칙:

- 각 발견은 짧은 제목 + 맥락(어느 Phase의 어느 상황에서 나왔는지) + 본질 + 재현 방법 + 기억 훅
- Phase를 가로질러 계속 누적 — 새로운 발견은 **파일 상단**에 추가(최근이 위)
- "내가 틀렸던 지점"을 숨기지 않기. 허위 GREEN, 잘못 이해한 동작, 놓친 가정 등이 가장 가치 있는 엔트리
- 디버깅 발견뿐 아니라 **개발 중 굳어진 설계 원칙**(예: "경계에서 정규화")도 여기 누적. 원칙은 나중에 프로젝트 곳곳에서 판단 근거로 재사용된다

---

## Phase 04 — "모델 로드"와 "모델 사용"을 분리하면 무거운 외부 의존성 없이 통합 테스트가 가능하다

**맥락**: Phase 04 시나리오 E, `asr` 커맨드의 통합 테스트를 설계하는 자리. faster-whisper 모델(수 GB)을 로드하지 않고 전체 파이프라인(파일 순회 → transcribe → ListEntry 변환 → .list 작성)을 테스트하려면 어떻게 해야 하는가?

### 문제 — Typer 커맨드가 모델 로드를 직접 품고 있으면 테스트 불가능

```python
# ❌ 이 구조의 통합 테스트는 불가능
def asr_command(input_dir, output_list, model_size, ...):
    model = load_whisper(model_size)    # ← 3GB 다운로드, GPU 필요, 수십 초 소요
    transcriber = WhisperTranscriber(model=model)
    for audio_path in ...:
        transcriber.transcribe(audio_path)
        ...
```

`CliRunner.invoke(app, ["asr", ...])`로 이 커맨드를 테스트하면 `load_whisper`가 실제로 실행됨 → 모델 다운로드/로드가 발생. CI 서버에선 항상 실패하고, 로컬에서도 테스트 한 번에 분 단위 소요. **TDD 사이클 불가능.**

### 해법 — 함수를 둘로 쪼갬

```
asr_command (Typer 어댑터)             run_asr_pipeline (비즈니스 로직)
┌────────────────────────┐            ┌─────────────────────────────┐
│ 1. 인자 파싱           │            │                             │
│ 2. validate_language   │            │ transcriber를 파라미터로 받음 │
│ 3. load_whisper() ─────┼─ 무거움    │ → 파일 순회                 │
│ 4. WhisperTranscriber  │            │ → transcriber.transcribe()  │
│ 5. run_asr_pipeline ───┼──────────▶ │ → to_list_entry()           │
│    (transcriber 전달)   │            │ → write_list_file()         │
└────────────────────────┘            └─────────────────────────────┘
```

`run_asr_pipeline`은 **이미 만들어진 `transcriber`를 파라미터로 받는다.** 이 함수는 모델이 어디서 왔는지 전혀 모른다 — `transcriber.transcribe(audio_path)`를 호출할 뿐.

### 프로덕션 경로 vs 테스트 경로

```python
# 프로덕션 (asr_command 안에서)
model = load_whisper("large-v3-turbo", ...)    # 진짜 모델 로드
transcriber = WhisperTranscriber(model=model)
run_asr_pipeline(transcriber=transcriber, ...)  # 진짜 동작

# 테스트 (test_asr_pipeline.py 안에서)
model = FakeWhisperModel(["hello"], language="en")  # 모델 로드 없음, 즉시 생성
transcriber = WhisperTranscriber(model=model)        # 같은 클래스
run_asr_pipeline(transcriber=transcriber, ...)        # 같은 파이프라인 로직
```

**두 경로 모두 `run_asr_pipeline` 안에서는 완전히 동일한 코드를 실행한다.** 차이는 오직 "transcriber 안의 model이 진짜냐 가짜냐" — 그 차이를 만드는 것은 **호출자가 무엇을 주입하느냐**. 이게 의존성 주입(DI)의 실질적 이득.

### 왜 CliRunner 관통 테스트를 안 쓰는가

Phase 03 `slice` 커맨드는 CliRunner로 관통 테스트를 했다. 거기선 가능했던 이유: **Slicer에 외부 의존성이 없었기 때문**. numpy만 쓰고 모델 다운로드 같은 건 없었다.

Phase 04에서 CliRunner로 관통하면 `load_whisper`를 피할 수 없다. 대안 비교:

| 접근 | 장점 | 단점 |
|---|---|---|
| **(A) `run_asr_pipeline`을 직접 호출** | 가장 단순. DI가 자연스러움 | Typer 인자 파싱은 검증 안 됨 |
| (B) `monkeypatch`로 `load_whisper` 교체 | CliRunner 관통 가능 | "어디를 바꿨는지"가 코드에서 안 읽힘 |
| (C) 환경변수로 "테스트 모드" 분기 | 간단 | 프로덕션 코드에 테스트 로직이 섞임 |

**voxprep은 (A)**. 이유: Typer 인자 파싱은 Typer가 이미 검증한 것이고, 우리의 책임은 "파싱된 인자를 받아서 올바르게 transcribe하고 `.list`를 쓰는 것"이기 때문.

### ODP 관점 — 의존성 역전의 가장 작은 사례

```
commands/asr.py (어댑터)
    ↓
run_asr_pipeline (비즈니스 로직)
    ↓
WhisperTranscriber (서비스)
    ↓ Protocol을 통해 의존
WhisperLike (계약 — 추상)
    ↑ 구현
WhisperModel (진짜) 또는 FakeWhisperModel (가짜)
```

`WhisperTranscriber`는 `WhisperLike` Protocol에만 의존한다. `WhisperModel`이라는 구체 클래스에는 의존하지 않는다. **의존성의 방향이 추상화를 향한다** — 이게 의존성 역전 원칙(DIP)의 가장 작은 실용 사례. 그리고 이것의 실용적 결과가 "테스트에서 fake를 끼워 넣을 수 있다"는 것.

Protocol이 빠지면 어떻게 되나: `WhisperTranscriber.__init__`의 타입 힌트가 `model: WhisperModel`로 박혀 있으면, 타입 체커가 `FakeWhisperModel`을 넣을 때 경고한다. Protocol이 있으면 "transcribe 메서드가 있으면 OK"라고 열어주므로 fake도 진짜도 같은 구멍으로 들어온다. Runtime에는 Protocol이 아무것도 하지 않지만(파이썬은 duck typing), **"이 자리에 뭐가 꽂힐 수 있는지"를 코드 읽는 사람과 타입 체커에게 명시**하는 문서 역할을 한다.

### 적용 체크리스트 (이후 외부 의존성 등장 시)

1. 외부 의존성(모델 로드, API 클라이언트, DB 연결)을 **직접 호출하는 함수**와 **그 결과를 사용하는 함수**를 분리할 수 있는가?
2. "사용하는 함수"의 파라미터를 **추상화(Protocol)**로 선언해서 fake를 끼울 수 있는가?
3. Typer 커맨드(어댑터)는 "만드는 것" 담당, 비즈니스 로직 함수는 "쓰는 것" 담당으로 이분?

### 기억 훅

*"테스트 못 하는 건 설계 문제다. 모델을 만드는 코드와 모델을 쓰는 코드를 같은 함수에 넣으면 둘 다 테스트 못 한다. 쪼개면 '쓰는 쪽'은 fake로 언제든 검증 가능."*

---

## Phase 04 — Test Double의 4종류와 "직접 만든 fake/spy"가 mock 프레임워크보다 나은 이유

**맥락**: Phase 04 시나리오 C~D에서 `FakeWhisperModel`을 만들며 — "왜 `unittest.mock.Mock`을 안 쓰고 직접 클래스를 만드는가?"라는 질문이 자연스럽게 등장하는 자리.

### Test Double의 4종류

외부 의존성을 테스트에서 대체하는 객체를 통칭 **Test Double**이라 한다 (Gerard Meszaros, xUnit Test Patterns). 4종류:

| 이름 | 역할 | 특징 | 예시 |
|---|---|---|---|
| **Stub** | 정해진 답만 돌려줌 | 로직 없음. 호출되면 고정값 반환 | `def transcribe(...): return ("hello", info)` |
| **Fake** | 실제 동작을 단순화한 것 | 경량이지만 비즈니스 로직을 가짐 | 인메모리 DB, voxprep의 `FakeWhisperModel`(고정 segments 반환) |
| **Spy** | 호출 기록을 남김 | "뭘 호출했는지, 어떤 인자로"를 사후 확인 | `self.calls.append({"audio": audio, **kwargs})` |
| **Mock** | 기대값을 미리 설정하고 자동 검증 | 프레임워크(`unittest.mock`, `pytest-mock`)가 제공 | `mock.assert_called_with(language="ko")` |

**경계가 칼로 자르듯 나뉘는 건 아니다** — voxprep의 `FakeWhisperModel`은 **Fake + Spy** 결합체다. 고정 segments를 반환(Fake)하면서 호출 기록도 남긴다(Spy). 실전에선 한 객체가 여러 역할을 겸하는 게 일반적.

### 왜 직접 만드는가 — `unittest.mock.Mock`을 쓰지 않는 이유

`unittest.mock`이나 `pytest-mock`은 강력하지만, 학습 프로젝트 관점에서 두 가지 문제가 있다:

**1. "뭘 검증하는지"가 코드에서 바로 안 읽힌다**

```python
# mock 방식
mock_model.transcribe.assert_called_once_with(
    str(audio), language="ko", beam_size=3, vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500}
)

# 직접 만든 spy 방식
call = model.calls[0]
assert call["language"] == "ko"
assert call["beam_size"] == 3
```

후자가 **읽으면 바로 보인다** — 각 assert가 한 가지 속성만 검증하고, 실패 시 pytest가 "어떤 값이 달랐는지"를 바로 보여준다. 전자는 `assert_called_once_with`가 실패하면 거대한 diff가 나오고, 어느 인자가 문제인지 찾기 어렵다.

**2. Mock은 "존재하지 않는 메서드도 성공"시킨다**

```python
mock = Mock()
mock.trancribe(audio)  # 오타 — 하지만 Mock은 모른다. 속성 접근 자체가 성공.
mock.trancribe.assert_called_once()  # 통과! 오타를 못 잡음
```

직접 만든 fake는 `transcribe` 메서드가 명시적으로 정의되어 있어, `trancribe`로 오타를 치면 **`AttributeError`로 즉시 터진다**. Protocol과 결합하면 타입 체커도 잡아준다.

**3. 언제 Mock이 나은가**

- 외부 API 호출을 가로채야 할 때 (`requests.get` patch 등) — 호출 지점이 테스트 코드 밖에 있어 직접 주입이 어려운 경우
- 이미 잘 격리된 대규모 코드베이스에서 수십 개 의존성을 빠르게 대체할 때
- voxprep 규모에서는 **아직 필요 없다** — 의존성이 1~2개라 직접 만드는 게 더 명확

### voxprep의 방침

- **기본은 직접 만든 Fake/Spy** — Protocol로 계약을 정의하고, fake 클래스로 구현
- `unittest.mock`은 "직접 만든 fake로 대체하기 어려운 자리"가 생길 때까지 도입하지 않음
- fake/spy 클래스가 2+ 테스트 파일에서 재사용되면 `tests/fixtures/doubles.py`로 추출 (premature extraction 금지 — 두 번째 사용처 등장이 추출 신호)

### 기억 훅

*"Mock은 강력한 도구지만, 읽는 사람에게 '뭘 검증하는지'를 숨기기 쉽다. 직접 만든 fake/spy는 덜 편리하지만 의도가 코드에 그대로 드러난다. 편의보다 명확성이 먼저."*

---

## Phase 02 — `@dataclass(frozen=True)` 이관이 불러오는 5가지 변화와 2가지 강제 결정

**맥락**: Phase 02 REFACTOR 라운드. 수동으로 구현한 `ListEntry`(`__init__`/`__eq__`/`__hash__`를 직접 정의)를 `@dataclass(frozen=True)`로 이관하는 과정에서, 겉보기에 "보일러플레이트 축소"인 이 리팩터가 실제로 어떤 파급을 불러오는지 기록.

### 변화 1 — `__init__` 자동 생성: 기존 수동 `__init__`이 사라짐

**Before**: `__init__`에서 `self.language = language.lower()`로 정규화를 강제하고 있었음.

**After**: dataclass는 `__init__`을 **자동 생성**한다. 필드 선언(`language: str`)을 보고 `self.language = language`로 단순 대입하는 코드를 내부적으로 만듦. **사용자 정의 로직(`lower()`)이 끼어들 자리가 없다.**

**파급**: DISCOVERIES에 박아 둔 **"정규화는 `__init__`에서"** 원칙이 그대로는 적용 불가. 해법이 필요 (아래 "강제 결정 1" 참고).

### 변화 2 — `__eq__` 자동 생성: 수동 `__eq__` 15줄이 사라짐

**Before**: `isinstance` 체크 + 4필드 비교를 직접 구현. `NotImplemented` 반환까지 처리.

**After**: dataclass가 **모든 필드를 순서대로 비교**하는 `__eq__`를 자동 생성. 내부적으로 `other.__class__ is self.__class__`를 체크(수동 버전의 `isinstance`보다 **엄격** — 서브클래스도 다른 것으로 취급).

**파급**: 수동 `__eq__`에서 `isinstance`를 쓴 것과 미묘하게 다르다. voxprep에서 `ListEntry`를 상속할 계획이 없으므로 실질 영향은 없지만, **"자동 생성된 `__eq__`가 수동 구현과 100% 동등하지는 않다"**는 사실을 인지할 것. (참고: Phase 02 Q&A에서 `isinstance` vs `type ... is`의 차이를 이미 다룸.)

### 변화 3 — `__hash__` 자동 생성: `frozen=True`일 때만 활성화

**Before**: `hash((self.audio_path, self.speaker, self.language, self.text))`를 직접 구현.

**After**: `frozen=True`이면 dataclass가 **동일한 전략**(모든 필드의 튜플 해시)으로 `__hash__`를 자동 생성. `frozen=False`이면 `__hash__`를 **생성하지 않음** (mutable 객체의 해시는 위험하므로 파이썬이 의도적으로 차단).

**파급**: `frozen=True`가 **필수**. 빼면 `__hash__`가 사라지고 시나리오 C(`hash(a) == hash(b)`)가 깨짐. 즉 `frozen`은 "불변성의 미학"이 아니라 **`__hash__` 확보를 위한 기술적 필수 조건**이다.

### 변화 4 — `__repr__` 자동 생성 (신규)

**Before**: 기본 `<ListEntry object at 0x...>`. 디버깅 시 필드 값이 보이지 않았음. pytest 에러 메시지에서 **메모리 주소만** 찍혀서 혼란 유발 (Phase 02 Q&A에서 다룬 "세 메커니즘" 중 ②③).

**After**: `ListEntry(audio_path='a.wav', speaker='s', language='ko', text='hi')` 형태. 필드 값이 전부 보임.

**파급**: 이건 순수 개선. 기존 테스트에 영향 없음. 하지만 이후 디버깅 경험이 극적으로 좋아짐. 에러 메시지에서 "어떤 값이 다른지"를 바로 읽을 수 있음.

### 변화 5 — 속성 재할당 금지 (신규 강제)

**Before**: `entry.speaker = "other"`가 **조용히 성공**했음. VO인데 수정 가능 = 약한 불변성.

**After**: `entry.speaker = "other"` → **`FrozenInstanceError`**. 파이썬이 불변성을 강제.

**파급**: 지금 테스트나 코드 중에 **ListEntry의 속성을 재할당하는 곳이 없으므로** 바로 터지진 않음. 하지만 이후 Phase 05~09(`review` 단계)에서 "편집" 기능을 만들 때, **기존 entry를 수정하는 대신 새 entry를 생성**해야 하는 제약이 됨. 이건 **Entity가 아니라 Value Object**라서 올바른 행동이지만, 처음 만나면 "불편한 제약"으로 느껴질 수 있음. 그때가 "왜 VO는 불변이어야 하는가"를 체감하는 두 번째 순간이 될 것.

---

### 강제 결정 1 — `__init__`에서의 정규화를 어떻게 유지하는가

**문제**: dataclass가 `__init__`을 자동 생성하므로, `self.language = language.lower()` 같은 커스텀 로직을 `__init__`에 **직접 끼워 넣을 수 없다**.

**선택지 세 가지**:

| 선택 | 구현 | 기존 원칙 유지 | 코드 복잡도 |
|---|---|---|---|
| **(A) `__post_init__` + `object.__setattr__` 우회** | dataclass가 제공하는 `__post_init__` 훅에서 `object.__setattr__(self, 'language', self.language.lower())` 호출. `frozen=True`는 `self.language = ...`를 금지하므로 `object.__setattr__`로 우회해야 함 | **유지** — 모든 생성 경로가 `__init__` → `__post_init__`을 거치므로 불변식 구멍 없음 | 약간 마법적인 한 줄이 추가됨. "frozen인데 왜 setattr로 고칠 수 있지?"라는 의문이 남는 자리 |
| **(B) 정규화를 `from_line`으로 이동** | `from_line` 안에서 `values[2].lower()`를 호출하고, `__init__`은 단순 대입 | **깨짐** — `ListEntry("a", "s", "ZH", "x")` 직접 생성 시 대문자 그대로 저장. DISCOVERIES의 "모든 생성 경로를 한 지점에 수렴" 원칙 위반 | 가장 단순, 코드 한 줄 이동 |
| **(C) dataclass 포기** | 수동 `__init__`/`__eq__`/`__hash__` 유지 | **유지** | 보일러플레이트 20줄 존속 |

**voxprep의 결정 (Phase 02 REFACTOR)**: **(A)**. 근거:
1. DISCOVERIES에 박은 **"정규화는 생성자에서, 모든 생성 경로가 한 지점으로 수렴"** 원칙을 깨지 않음
2. `object.__setattr__` 우회는 파이썬 dataclass 공식 문서에서 **frozen 불변성 내부 초기화의 관용 패턴**으로 안내하는 방법이므로, "해킹"이 아니라 "설계된 탈출구"
3. voxprep 전체에서 `__post_init__`이 필요한 VO는 `ListEntry`뿐일 가능성이 높아 (다른 VO는 정규화가 불필요할 수 있음) 패턴 남용 위험이 낮음

### 강제 결정 2 — `from_line`의 `cls(...)` 호출이 여전히 동작하는가

**문제**: 현재 `from_line`은 `return cls(values[0], values[1], values[2], values[3])`로 위치 인자를 전달함. dataclass의 자동 생성 `__init__`은 **필드 선언 순서대로 위치 인자를 받으므로** 동일하게 동작. **변경 불필요.**

단, dataclass 필드 순서를 나중에 바꾸면 `from_line`이 조용히 깨질 수 있음. 키워드 인자로 명시하면 더 안전:

```python
return cls(audio_path=values[0], speaker=values[1], language=values[2], text=values[3])
```

이건 선택 사항. 필드가 4개뿐이고 순서가 직관적이라 위치 인자로 두는 것도 합리적. 다만 Phase 10까지 가면서 필드가 추가될 가능성(예: `line_number: int`)이 있다면 키워드가 안전함. **voxprep에서는 `.list` 포맷이 4필드 확정이므로 위치 인자 유지.**

---

### REFACTOR 전후 비교 — 코드 줄 수

| 요소 | Before (수동) | After (dataclass) | 변화 |
|---|---|---|---|
| `__init__` | 5줄 | 0줄 (자동) + `__post_init__` 2줄 | -3줄 |
| `__eq__` | 8줄 | 0줄 (자동) | -8줄 |
| `__hash__` | 2줄 | 0줄 (자동) | -2줄 |
| `__repr__` | 0줄 (없었음) | 0줄 (자동, 공짜 획득) | 0줄 (기능 추가) |
| decorator + fields | 0줄 | 6줄 (`@dataclass` + 4필드 선언 + import) | +6줄 |
| **합계** | 15줄 | 8줄 | **-7줄 + `__repr__` 공짜 + 불변성 강제** |

7줄 감소보다 **"앞으로 필드를 추가할 때 `__eq__`/`__hash__`를 수동 동기화할 필요가 사라진다"**는 유지보수 이득이 더 큼.

---

### 관련 DISCOVERIES
- **Phase 02 — 데이터는 경계에서 정규화한다** (본 파일 아래 엔트리): `__init__`에서 정규화 결정의 근거
- **Phase 02 Q&A — `__eq__`/`__hash__`/`__repr__`은 독립된 세 메서드**: 수동 구현의 의미를 이해한 뒤 자동 생성으로 넘어가는 순서가 왜 중요한가
- **Phase 02 — `object.__setattr__`은 frozen dataclass의 설계된 탈출구** (바로 아래 엔트리)

---

## Phase 02 — `object.__setattr__`은 frozen dataclass의 "설계된 탈출구"

**맥락**: Phase 02 REFACTOR 라운드에서 `@dataclass(frozen=True)`로 이관할 때, `__post_init__`에서 `self.language = self.language.lower()`를 쓰면 `FrozenInstanceError`가 나는 현상에서 비롯.

### 문제 상황

`frozen=True`는 **`self.X = ...` 형태의 모든 대입을 차단**한다. 이건 `__init__` 이후만이 아니라 **`__post_init__` 안에서도 마찬가지**다. 즉:

```python
@dataclass(frozen=True)
class ListEntry:
    language: str

    def __post_init__(self) -> None:
        self.language = self.language.lower()  # ← FrozenInstanceError!
```

직관적으로 "초기화 도중인데 왜 막지?"라고 느낄 수 있지만, `frozen=True`의 구현은 `__setattr__`을 오버라이드해서 **모든 시점의 대입을 무조건 차단**하는 방식이다. `__post_init__`이 "초기화의 연장"이라는 의미론적 지위를 파이썬 런타임은 구분하지 못한다.

### 해법 — `object.__setattr__`

```python
def __post_init__(self) -> None:
    object.__setattr__(self, "language", self.language.lower())
```

`object.__setattr__`은 **파이썬 객체 시스템의 가장 낮은 레벨 속성 대입**이다. dataclass가 `__setattr__`을 오버라이드해서 `FrozenInstanceError`를 던지는 방어막을 **아래로 우회**해서, 원본 `object`의 `__setattr__`을 직접 호출한다.

### 이게 "해킹"이 아닌 이유

- 파이썬 **공식 문서(dataclasses 모듈 — Frozen instances)**가 이 정확한 패턴을 안내한다
- `__post_init__`은 dataclass 인프라가 `__init__` 실행 직후에 **자동으로 호출**하는 훅이라, 이 안에서의 `object.__setattr__`은 "**생성 완료 전의 마지막 초기화**"로 읽힌다
- 객체가 외부에 노출된 이후(= 생성자 반환 이후)에는 `object.__setattr__`을 외부에서 호출하는 것은 **정상 경로가 아님**. 기술적으로 가능하지만 "방화문을 밀고 들어간 것"이지 의도된 API가 아니다
- 정상 경로(`entry.language = "JP"`)는 **여전히 `FrozenInstanceError`로 차단**됨

### 보호 모델 요약

```
생성 시점 (__init__ → __post_init__):
  object.__setattr__으로 값 변환 가능 (설계된 탈출구)
       ↓
생성 완료 후 (외부 코드):
  self.X = ... → FrozenInstanceError (frozen 보호 활성)
  object.__setattr__(entry, ...) → 기술적으로 성공하지만 비정상 경로
```

즉 "**생성 완료 전에는 열려 있고, 생성 완료 후에는 닫혀 있다**"는 반제품(half-baked) 보호 모델이다.

### 왜 이 지식이 중요한가

- `frozen=True` dataclass에서 **초기화 시점 값 변환**(정규화, 파생 필드 계산 등)이 필요할 때 **유일한 공식 방법**. 대안은 frozen을 포기하거나 정규화 위치를 외부로 옮기는 것뿐이고, 둘 다 더 큰 트레이드오프를 수반
- voxprep의 "정규화는 생성자에서" 원칙(DISCOVERIES 별도 엔트리)과 `frozen=True`의 조합에서 **이 패턴이 없으면 두 원칙이 양립 불가**
- 파이썬 dataclass를 쓰는 모든 프로젝트에서 frozen VO를 만들 때 거의 반드시 한 번은 마주치는 패턴이므로, 한 번 체득하면 계속 쓰게 됨

### 기억 훅

*"frozen은 문을 잠그지만, `__post_init__` + `object.__setattr__`은 잠그기 직전에 마지막 손질을 허용하는 설계된 틈이다."*

---

## Phase 02 — 데이터는 경계에서 정규화한다 (Value Object가 유효성을 자체 책임)

**맥락**: Phase 02 시나리오 B, `.list` 파일의 언어 코드 대소문자 혼재를 어떻게 다룰지 결정하는 자리에서 나온 원칙. 시나리오 B 자체는 "`ZH`를 `zh`로 바꾸는 `.lower()` 한 줄"이지만, 그 뒤에 깔린 방침은 프로젝트 전체를 관통한다.

**원본 코드베이스의 불일치** (직접 확인):

- 쓰는 쪽 — `GPT-SoVITS/tools/asr/fasterwhisper_asr.py:136`:
  ```python
  output.append(f"{file_path}|{output_file_name}|{info.language.upper()}|{text}")
  ```
  `.upper()` — **대문자**로 쓴다.

- 읽는 쪽 — `GPT-SoVITS/GPT_SoVITS/prepare_datasets/1-get-text.py:113~125`:
  ```python
  language_v1_to_language_v2 = {
      "KO": "ko", "Ko": "ko", "ko": "ko",
      "YUE": "yue", "Yue": "yue", "yue": "yue",
      "JA": "ja", "ja": "ja",
      "EN": "en", "en": "en", "En": "en",
      ...
  }
  ```
  **대소문자 변형 흡수 딕셔너리**. 모든 케이스 조합을 받아 소문자로 다시 내려보낸다.

상류가 대문자로 쓰는데 하류가 대소문자 변형 사전으로 흡수하고 있다 = 누가 언제 어떤 케이스로 주는지 신뢰할 수 없다 = **경계마다 방어가 필요하다**. 원본 프로젝트 안에서도 "이 필드의 정규 형태는 무엇인가"가 합의되지 않았다는 증거.

**voxprep의 방침**: **파서 경계에서 소문자로 못박는다.** `ListEntry.from_line` 또는 `ListEntry.__init__` 중 한 곳에서 `.lower()`를 적용하여, 한 번 정규화되면 이후 voxprep 내부의 모든 코드가 **"언어 코드는 항상 소문자"**라는 불변식을 전제로 동작할 수 있게 한다. 이 불변식이 깨지지 않는 한, 나중에 `if entry.language == "ko":` 같은 체크가 안전하다.

**정규화를 안 하면 어떻게 되나**: voxprep 내부 곳곳에서 `if entry.language.lower() == "ko":` 같은 방어 코드가 반복되거나, 어느 한 곳에서 실수로 `== "ko"`만 써서 대문자 입력에 **조용히 실패**한다. "경계에서 정규화"의 반대는 **"사용처마다 정규화"**이고, 후자는 언젠가 반드시 하나를 빠뜨린다. 원본이 소비자 쪽에 거대한 흡수 딕셔너리를 두게 된 것이 바로 이 "사용처마다 정규화"의 결과다.

**ODP 용어로**: **Value Object가 데이터의 유효성/정규 형태를 자체 책임진다.** `ListEntry`는 자신이 유효한 상태(`language`는 소문자)로만 존재하도록 생성 경로에서 보장하고, 생성된 이후로는 내부 필드가 규칙을 지킨다고 믿을 수 있어야 한다. 이 책임을 외부로 미루는 순간 VO가 **"그냥 데이터 묶음"**으로 전락한다. 유효성을 자체 책임지지 않는 VO는 dict와 본질적으로 같다.

**구현 선택지 (Phase 02 현장에서 맞닥뜨리는 분기)**:

| 선택 | 장단 |
|---|---|
| `from_line` 안에서 `values[2].lower()` | 파싱 경로만 정규화됨. `ListEntry("a", "s", "ZH", "x")` 직접 생성 시 구멍 |
| `__init__` 안에서 `self.language = language.lower()` | 모든 생성 경로가 통과. 더 강한 불변식. **권장** |

**voxprep의 결정 (2026-04-14, Phase 02 시나리오 B)**: **`__init__`에서 정규화**. 근거 두 가지:
1. 과거 읽은 책 — **"VO의 최소한의 검증/정규화는 `__init__`에서 해도 좋다"** (출처 미상, 기억에 의존). 생성자에 단순 대입만 두어야 한다는 금욕적 원칙보다, VO 자체의 유효성 책임을 강하게 본 입장이 voxprep의 ODP 방침(VO는 스스로 유효함)과 일치
2. 위 표의 비교에서 `__init__` 쪽이 모든 생성 경로(`from_line`, 직접 생성자 호출, 미래에 추가될 다른 팩토리 메서드)를 한 지점으로 수렴시키기 때문에 **불변식 구멍이 원리적으로 안 생긴다**

**이후 voxprep 내 VO 추가 시 일관성 규칙**: 정규화 로직은 **생성자에 집중**. 이 결정을 깨려면 DISCOVERIES에 새 엔트리로 "이 VO는 왜 예외인가"를 기록해야 함.

**기억 훅**: *"경계에서 한 번, 믿음으로 나머지."* VO는 생성자에서 유효성을 보장하고, 이후 사용자는 그 VO를 신뢰한다. 이 원칙을 어기면 프로젝트 전체가 방어 코드로 도배된다.

**적용 체크리스트 (이후 VO 추가 시 매번)**:
- 이 VO는 어떤 불변식을 자체 책임지는가?
- 그 불변식은 `__init__`에서 강제되는가, 아니면 외부 호출자에게 맡겨지는가?
- 후자라면 정말 그게 맞는 결정인가? (거의 항상 전자가 맞다)

**관련**: 이 원칙은 Phase 03 이후 `SliceOptions`, `Transcription` 같은 VO가 새로 등장할 때마다 다시 묻게 될 기준이다. "이 값은 생성 시점에 어떤 정규 형태로 못박혀야 하는가?"

---

## Phase 01 — Typer 앱에 등록된 커맨드가 0개면 `_get_command`가 RuntimeError

**맥락**: Phase 01 Step 4, `src/voxprep/cli.py`에 `import typer; app = typer.Typer(...)`만 써놓은 상태에서 `CliRunner.invoke(app, ["version"])`를 호출.

**에러**:
```
RuntimeError: Could not get a command for this Typer instance
  at typer/main.py:1204 (get_command)
```

**본질**: Typer의 `get_command(typer_instance)`는 내부 분기를 통해 click 오브젝트를 만든다:

```python
# typer/main.py (요약)
if (
    typer_instance.registered_callback
    or typer_instance.info.callback
    or typer_instance.registered_groups
    or len(typer_instance.registered_commands) > 1
):
    return get_group(typer_instance)        # 그룹 앱
elif len(typer_instance.registered_commands) == 1:
    return single_command                    # 단일 명령 앱
raise RuntimeError(...)                      # ← 커맨드 0개면 여기로
```

| 상태 | 결과 |
|---|---|
| 커맨드 0개 + callback 없음 | **RuntimeError** (이 발견의 지점) |
| 커맨드 1개 + callback 없음 | 단일 명령 앱 (서브커맨드 없는 `voxprep` 하나) |
| 커맨드 2개+ 또는 callback 존재 | 그룹 앱 (`voxprep <subcmd>` 형태) |

커맨드가 0개인 Typer 앱은 Typer 입장에서 "이게 뭐 하는 앱인지 자체를 판단할 수 없는 상태"라 빌드를 포기한다. `CliRunner.invoke`의 내부 `_get_command(app)` 호출이 앱 실행 이전에 이미 터져서, CliRunner의 `catch_exceptions`가 가로채 `result.exception`에 넣지 못하고 테스트 본문까지 RuntimeError가 올라온다(pytest는 이걸 FAILED로 출력).

**기억 훅**: "테스트 입력을 주기 전에 Typer가 먼저 '뭘 할 수 있는 앱인지 모르겠다'고 포기할 수 있다." Typer 앱을 만드는 가장 이른 단계에서 마주치는 RED 중 하나로, `AssertionError`보다 더 구조적이어서 오히려 친절한 에러.

**재현**:
```python
# cli.py
import typer
app = typer.Typer()

# test_x.py
from typer.testing import CliRunner
from voxprep.cli import app
CliRunner().invoke(app, ["anything"])  # → RuntimeError
```

---

## Phase 01 — `@app.command()` 1개만 있는 Typer 앱은 "단일 명령 앱"이라 `voxprep version`이 먹히지 않는다

**맥락**: 위 RuntimeError를 고치려고 `@app.command() def version()`만 추가하면 다음 함정이 바로 이어짐. 서브커맨드 구조를 원하는데 Typer는 이걸 단일 명령 앱으로 해석.

**본질**: Typer는 등록된 커맨드가 **정확히 1개**이고 callback이 없으면, 그 함수를 **루트 커맨드**로 취급한다. 즉 `voxprep`을 치면 `version()`이 바로 실행되고, `voxprep version`은 "version이라는 위치 인자를 version 함수에 전달"로 해석되어 `Got unexpected extra argument (version)` 류 에러.

| 호출 | 단일 명령 앱 해석 | 원하는 그룹 앱 해석 |
|---|---|---|
| `voxprep` | version() 실행 | `--help` 표시 |
| `voxprep version` | 오류 (예상 인자 없음) | version() 실행 |

**해결**: `@app.callback()`을 빈 콜백으로라도 달아주면 Typer는 무조건 **그룹 앱**으로 취급한다(`registered_callback` 조건이 참이 되므로).

```python
@app.callback()
def main() -> None:
    """voxprep — GPT-SoVITS dataset preprocessing CLI."""

@app.command()
def version() -> None:
    typer.echo(__version__)
```

**YAGNI 관점**: 이 callback은 "아직 필요 없는 구조를 선제적으로 만든 것"이 아니다. voxprep는 처음부터 `slice / asr / review / prep / version` 다중 서브커맨드를 가질 CLI라, "단일 명령 앱"은 중간 단계의 착시일 뿐이고 **진짜 최종 구조는 그룹**. callback을 지금 넣는 게 YAGNI 위반이 아니라 최종 구조의 최소 형태.

**기억 훅**: "Typer는 커맨드 개수에 따라 앱 성격을 바꾼다. 커맨드 1개 = 루트 명령, 2개+ = 그룹. callback 한 줄로 '나는 항상 그룹이다'를 선언할 수 있다."

**부가 발견**: Phase 01의 최초 `RuntimeError`는 "0개 커맨드"였고 이 두 번째 함정은 "1개 커맨드"에서 나온다. 즉 Typer 앱의 수명 초기(0→1→2개 커맨드)에서 분기점이 세 번 바뀐다는 것. voxprep처럼 여러 커맨드가 예정된 앱은 **처음부터 callback을 박아서 이 분기 자체를 밟지 않는 것**이 방어적.

---

## Phase 01 — `CliRunner`는 앱 내부 예외를 `result.exception`에 숨긴다 (기본값 `catch_exceptions=True`)

**맥락**: Phase 01 Step 5, `version()`이 `typer.echo(__version__)`을 호출하는데 `cli.py`에 `from voxprep import __version__` import가 빠져 `NameError`가 남.

**관측**:
```
E  assert 1 == 0
E   +  where 1 = <Result NameError("name '__version__' is not defined")>.exit_code
```

**본질**: `CliRunner()`는 기본으로 `catch_exceptions=True`로 생성된다. 테스트 대상 코드에서 예외가 발생하면:

1. CliRunner가 잡아서 `result.exception`에 저장
2. `result.exit_code`는 `1`로 세팅
3. 테스트 본문에서는 `NameError` traceback이 보이지 않고, `assert result.exit_code == 0`에서만 실패

실전 디버깅 팁:

- `result.exception` / `result.output` / `result.exc_info`를 먼저 확인할 것
- 일시적으로 `runner.invoke(app, [...], catch_exceptions=False)`로 호출하면 내부 예외가 그대로 올라와 traceback 전체가 보인다
- pytest의 `where X = ...` 분해 출력을 꼼꼼히 읽자 — `<Result NameError(...)>` 같은 repr에 진짜 원인이 들어있다

**기억 훅**: "CliRunner는 방패다. 테스트는 프로세스가 깔끔하게 죽었는지만 확인하고 진짜 사고는 방패 뒤에 숨긴다. 방패를 내리려면 `catch_exceptions=False`."

---

## Phase 01 — `voxprep` 패키지는 `__init__.py` 없이도 PEP 420 namespace package로 잡힌다 (modern setuptools editable install)

**맥락**: Phase 01 Step 2. `src/voxprep/` 디렉토리만 만들고 `__init__.py`를 아직 안 쓴 상태에서 `uv run pytest`를 돌렸더니, 기대했던 `ModuleNotFoundError: No module named 'voxprep'` 대신 **`ModuleNotFoundError: No module named 'voxprep.cli'`**가 나왔다.

**본질**: PEP 420 이후 파이썬은 **namespace package**를 지원한다 — 디렉토리에 `__init__.py`가 없어도 그 디렉토리가 sys.path에 걸려 있으면 모듈 탐색 시 "implicit namespace package"로 발견된다. `uv sync`로 editable install되면 setuptools가 `src/`를 `.pth` 파일로 sys.path에 등록하고, 이 순간부터 `src/voxprep/` 디렉토리는 `__init__.py`가 없어도 `import voxprep`에 응답한다. 다만 **서브모듈은 실제 파일이 있어야** 하므로 `import voxprep.cli`는 `cli.py`가 없으면 실패.

**Phase 01 문서와의 차이**: CLAUDE.md의 Phase 01 시나리오는 "RED 진화 1단계"로 `ModuleNotFoundError: No module named 'voxprep'`를 기대했지만, 현대 setuptools 동작 때문에 실제로는 **한 단계 건너뛰고** 바로 `voxprep.cli`에서 터진다. 문서를 쓸 당시의 setuptools는 namespace package에 덜 관대했거나, 시나리오 저자가 이 세부를 인지하지 못했을 수 있음.

**기억 훅**: "namespace package 덕분에 빈 디렉토리만 있어도 import가 반쯤 성공한다. 파이썬이 '없다'고 거짓말하는 건 아니고, 네가 예상한 만큼 철저하게 거부하지 않을 뿐."

**재현**:
```bash
mkdir -p src/voxprep
# __init__.py 없음
uv sync            # editable install
uv run python -c "import voxprep; print(voxprep.__path__)"
# → _NamespacePath(['/.../src/voxprep'])  ← 성공
uv run python -c "import voxprep.cli"
# → ModuleNotFoundError: No module named 'voxprep.cli'
```

---
