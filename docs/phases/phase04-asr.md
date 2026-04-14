# Phase 04 — `asr` 커맨드 (faster-whisper 래퍼)

## 학습 목표

- **외부 라이브러리 경계**의 처리 — 무거운 의존성을 어떻게 테스트 가능한 형태로 감쌀 것인가
- **의존성 주입(DI)**으로 fake 모델을 주입하는 첫 경험 — 진짜 GPU/모델 로드 없이 로직 검증
- Service ↔ DTO 구분: 트랜스크립션 1건의 결과(`Transcription`)는 Value Object이지만, 경계 너머 외부 라이브러리에서 받는 raw 결과는 DTO로 보고 즉시 변환
- Phase 02의 `ListEntry`와의 통합 — `Transcription → ListEntry → write_list_file` 흐름
- 진행 상황과 실패에 대한 정책 — 한 파일이 실패하면 전체 중단? 스킵? (학습 결정 포인트)

## 사용자 기본값 (SETUP_GUIDE 3-3절)

`voxprep/GPT-SoVITS/docs/ko/SETUP_GUIDE.md` 3-3절에서 사용자가 직접 검증한 값:

| 항목 | 값 | voxprep 플래그 |
|------|----|---------------|
| ASR 모델 | Faster Whisper | (이번 Phase 1차 범위) |
| ASR 모델 크기 | **large-v3-turbo** | `--model-size` 기본값 |
| ASR 언어 | **ko (한국어)** | `--language` 기본값 |
| 입력 폴더 | `output/slicer_opt` | (Phase 03 출력과 일치) |
| 출력 위치 | `output/asr_opt/{name}.list` | (Phase 10 prep의 workspace 관례에 반영) |

> macOS Apple Silicon: CTranslate2가 MPS를 지원하지 않으므로 `--device auto`는 cuda 없으면 cpu로 resolve. cpu에서는 `--compute-type int8`이 합리적 기본값.

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| Faster-Whisper 래퍼 원본 | `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py` | `execute_asr(input_folder, output_folder, model_path, language, precision)` 시그니처. 모델 로드 → 디렉토리 순회 → segments 결합 → `.list` 출력. 직접 열어볼 것 |
| FunASR 래퍼 (참고만) | `voxprep/GPT-SoVITS/tools/asr/funasr_asr.py:87` | 중국어/광동어 전용. 우리 1차 범위는 faster-whisper만, FunASR auto-fallback은 노트로만 |
| 모델/언어 카탈로그 | `voxprep/GPT-SoVITS/tools/asr/config.py` `asr_dict` | 모델 사이즈, 언어 옵션의 UI 노출 형태. WebUI dropdown은 좁지만 실제 whisper는 99 언어 지원 |
| 99-언어 코드 list | `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py` `language_code_list` (라인 17~38) | voxprep `--language` 검증에 그대로 사용 |
| WebUI 진입 | `voxprep/GPT-SoVITS/webui.py` `open_asr()` (라인 371~415) | UI 단에서 어떤 노브가 노출되는지: model/size/lang/precision |
| `.list` 포맷 | `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py:136` | Phase 02에서 이미 다뤘지만 다시 확인 |
| `faster-whisper` 공식 | https://github.com/SYSTRAN/faster-whisper | `WhisperModel`, `transcribe()` 시그니처 |

## 업스트림 노브 점검 (전부 CLI에 노출)

`fasterwhisper_asr.py`의 `execute_asr` + `model.transcribe` 호출에서 발견되는 노브들:

| 원본 위치 | 노브 | 기본값 (원본) | voxprep 기본 (SETUP_GUIDE 반영) | 플래그 |
|----------|------|---------------|--------------------------------|--------|
| `execute_asr(model_path)` | 모델 식별 | argparse `large-v3` / WebUI dropdown | **`large-v3-turbo`** (사용자 검증) | `--model-size` |
| `execute_asr(language)` | 언어 코드 | argparse `ja` / WebUI `auto` | **`ko`** (사용자 검증) | `--language` |
| `execute_asr(precision)` | 연산 정밀도 | argparse `float16` | `int8` (cpu) / `float16` (cuda) | `--compute-type` |
| `WhisperModel(device=...)` | GPU/CPU | `cuda if available else cpu` | `auto` → 동일 (Apple Silicon은 cpu) | `--device` |
| `model.transcribe(beam_size=5)` | beam search | `5` | `5` | `--beam-size` |
| `model.transcribe(vad_filter=True)` | VAD on/off | `True` | `True` | `--vad / --no-vad` |
| `vad_parameters=dict(min_silence_duration_ms=700)` | VAD 침묵 임계 | `700` ms | `700` | `--vad-min-silence-ms` |
| `info.language` 분기 → FunASR | 중국어 자동 폴백 | (자동) | **1차 범위 외** — 사용자 데이터셋이 한국어라 우선순위 낮음 | (없음) |
| `--speaker` (voxprep 추가) | speaker 라벨 | (output dirname 사용) | `narrator` | `--speaker` |

> **언어 코드 화이트리스트**: `language_code_list`(99개 + `auto`)를 그대로 import해서 `--language` 검증에 사용. Typer의 `click.Choice`나 `Enum`으로 묶을 수 있지만, 99개 enum은 help 메시지가 폭발 — `--language-list` 보조 커맨드 또는 `voxprep asr --help` 끝에 "see voxprep asr --list-languages" 안내 권장.

## 구현 범위

### 만들 것

1. `src/voxprep/transcription/__init__.py`
2. `src/voxprep/transcription/types.py` — `Transcription` Value Object (`audio_path: Path`, `language: str`, `text: str`)
3. `src/voxprep/transcription/whisper.py` — `WhisperTranscriber` Service
   - `__init__(self, model: WhisperLike, default_language: str | None = None, beam_size: int = 5, vad_filter: bool = True, vad_min_silence_ms: int = 700)`
   - `transcribe(self, audio_path: Path) -> Transcription`
   - `WhisperLike`는 `typing.Protocol`로 정의 — `transcribe(audio, language=..., beam_size=..., vad_filter=..., vad_parameters=...) -> tuple[Iterable[Segment], Info]`
   - 진짜 `WhisperModel`은 `model_factory.py`에서 한 번만 로드하고 주입. 위 4개 transcribe 옵션은 transcriber 인스턴스 상태로 보유 → call site마다 동일 설정
4. `src/voxprep/transcription/model_factory.py` — `load_whisper(model_size: str, device: str, compute_type: str) -> WhisperModel`
5. `src/voxprep/transcription/languages.py` — `LANGUAGE_CODES`(set), `validate_language(code: str)` — `fasterwhisper_asr.language_code_list` 기반
6. `src/voxprep/commands/asr.py` — Typer 커맨드. **모든 업스트림 노브 노출**, 기본값은 SETUP_GUIDE 반영:
   - `input_dir: Path`, `output_list: Path` (위치 인자)
   - `--model-size` (str, default **`large-v3-turbo`**) — choices: `medium`, `medium.en`, `large-v2`, `large-v3`, `large-v3-turbo`
   - `--language` (str, default **`ko`**) — `LANGUAGE_CODES`로 검증, `auto`도 허용
   - `--device` (str, default `auto`) — `auto`/`cuda`/`cpu`. `auto`는 cuda 있으면 cuda, 없으면 cpu (Apple Silicon은 cpu)
   - `--compute-type` (str, default `auto`) — `auto`/`float16`/`float32`/`int8`. `auto`는 cuda면 `float16`, cpu면 `int8`
   - `--beam-size` (int, default `5`)
   - `--vad / --no-vad` (bool flag, default `True`)
   - `--vad-min-silence-ms` (int, default `700`)
   - `--speaker` (str, default `narrator`)
   - `--list-languages` (eager flag) — 99개 코드 출력 후 종료
   - 동작: input_dir 순회 → 한 파일씩 transcribe → `Transcription`을 `ListEntry`로 변환 → `write_list_file`로 append
6. `tests/unit/test_whisper_transcriber.py` — fake `WhisperLike`로 단위 테스트
7. **`tests/integration/test_asr_pipeline.py`** — fake transcriber를 monkey-patch로 주입해 e2e 테스트 (Phase 03에서 만든 `tests/integration/`에 합류)
8. **`tests/fixtures/audio.py`** — Phase 03에서 인라인으로 두었던 `_build_two_segment_waveform`을 **여기서 처음 추출** (Phase 04 테스트에서도 같은 합성 waveform 필요 → 두 번째 사용처 등장 = 추출 신호)
9. **`tests/fixtures/doubles.py`** — `FakeWhisperModel`(시나리오 C~F), `FakeSegment`, `FakeInfo`. Phase 06+에서 `SpyPlayer`, `FakeEditor`, `FakeConfirmer`도 같은 파일에 누적

### 미루는 것

- 광동어/중국어 FunASR 폴백
- VAD 필터 옵션
- 진행률을 외부 프로세스로 노출 (Phase 10에서 결정)
- GPU 감지 자동화 — 일단 사용자가 명시

## TDD 사이클 시나리오

### 시나리오 A — Transcription Value Object

먼저 도메인 객체부터:

```python
from pathlib import Path

from voxprep.transcription.types import Transcription


def test_transcription_value_equality():
    a = Transcription(Path("a.wav"), "ko", "안녕")
    b = Transcription(Path("a.wav"), "ko", "안녕")

    assert a == b
```

GREEN: `@dataclass(frozen=True)`.

### 시나리오 B — Transcription → ListEntry 변환

```python
from voxprep.parsing.list_file import ListEntry
from voxprep.transcription.types import Transcription


def test_to_list_entry_with_speaker():
    t = Transcription(Path("data/01.wav"), "ko", "hi")

    entry = t.to_list_entry(speaker="narrator")

    assert entry == ListEntry("data/01.wav", "narrator", "ko", "hi")
```

GREEN: `to_list_entry` 메서드 추가. 경로는 `str(self.audio_path)`로 변환.

### 시나리오 C — WhisperTranscriber가 fake model을 부른다

```python
from typing import Iterable

from voxprep.transcription.whisper import WhisperTranscriber


class FakeSegment:
    def __init__(self, text: str):
        self.text = text


class FakeInfo:
    def __init__(self, language: str):
        self.language = language


class FakeWhisperModel:
    def __init__(self, segments: list[str], language: str):
        self._segments = segments
        self._language = language
        self.calls: list[tuple] = []

    def transcribe(self, audio, language=None, **kwargs):
        self.calls.append((audio, language))
        return (
            (FakeSegment(s) for s in self._segments),
            FakeInfo(self._language),
        )


def test_transcribe_concatenates_segments(tmp_path):
    audio = tmp_path / "x.wav"
    audio.touch()
    model = FakeWhisperModel(["Hello", " world"], language="en")
    transcriber = WhisperTranscriber(model=model)

    result = transcriber.transcribe(audio)

    assert result.text == "Hello world"
    assert result.language == "en"
    assert result.audio_path == audio
```

GREEN: `WhisperTranscriber.transcribe` → `model.transcribe(str(audio_path), language=self.default_language)` → segment 텍스트 join → `Transcription`.

핵심 학습: **fake가 진짜 라이브러리의 인터페이스 모양을 닮기만 하면 된다.** 상속 안 함, Protocol 덕분.

### 시나리오 D — transcribe 옵션이 모델로 전달된다

```python
def test_transcribe_passes_language_beam_and_vad_params(tmp_path):
    audio = tmp_path / "x.wav"
    audio.touch()
    model = FakeWhisperModel([""], language="ko")
    transcriber = WhisperTranscriber(
        model=model,
        default_language="ko",
        beam_size=3,
        vad_filter=True,
        vad_min_silence_ms=500,
    )

    transcriber.transcribe(audio)

    call = model.calls[0]  # (audio, kwargs)
    assert call.kwargs["language"] == "ko"
    assert call.kwargs["beam_size"] == 3
    assert call.kwargs["vad_filter"] is True
    assert call.kwargs["vad_parameters"] == {"min_silence_duration_ms": 500}


def test_auto_language_passed_as_none(tmp_path):
    audio = tmp_path / "x.wav"
    audio.touch()
    model = FakeWhisperModel([""], language="en")
    transcriber = WhisperTranscriber(model=model, default_language="auto")

    transcriber.transcribe(audio)

    # 'auto'는 whisper에 None으로 넘겨야 자동 감지
    assert model.calls[0].kwargs["language"] is None
```

`FakeWhisperModel`은 `kwargs`까지 캡처하도록 살짝 보강. 학습 토론 포인트: `auto` → `None` 정규화는 어디서? **transcriber 내부**가 자연스럽다 (CLI는 사용자 표현 그대로 전달, 도메인 객체에서 라이브러리 표현으로 번역).

### 시나리오 E — Typer 커맨드 통합 (transcriber 주입)

ASR 커맨드는 부트할 때 transcriber를 만드는데, 테스트에서는 모델 로드를 피해야 합니다. 두 가지 접근:

1. `commands.asr` 모듈 레벨에 `_transcriber_factory` 함수를 두고, 테스트에서 monkey-patch
2. Typer 커맨드가 의존성 객체를 인자로 받는 게 아니라 모듈 함수에 위임 — 모듈 함수가 transcriber를 받음

권장: **(2)** — 비즈니스 로직(`run_asr_pipeline(transcriber, input_dir, output_list, speaker)`) 함수를 따로 두고 Typer 커맨드는 얇은 어댑터.

```python
def test_run_asr_pipeline_writes_list(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.wav").touch()
    (src / "b.wav").touch()
    out_list = tmp_path / "out.list"

    fake_model = FakeWhisperModel(["hello"], language="en")
    transcriber = WhisperTranscriber(model=fake_model)

    from voxprep.commands.asr import run_asr_pipeline
    run_asr_pipeline(
        transcriber=transcriber,
        input_dir=src,
        output_list=out_list,
        speaker="narrator",
    )

    lines = out_list.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert all(l.split("|")[1] == "narrator" for l in lines)
```

GREEN: `run_asr_pipeline` 구현 — input_dir의 wav/flac 순회 → `transcriber.transcribe` → `to_list_entry` → `write_list_file` 또는 append.

### 시나리오 F (선택) — 한 파일 실패 시 다음 파일 계속

```python
class FlakyModel:
    def __init__(self):
        self.count = 0
    def transcribe(self, audio, language=None, **kwargs):
        self.count += 1
        if self.count == 1:
            raise RuntimeError("decode failed")
        return ((FakeSegment("ok"),), FakeInfo("en"))


def test_pipeline_skips_failed_files(tmp_path):
    ...
    # 첫 파일 실패해도 두 번째는 .list에 들어가야 함
```

GREEN: try/except로 감싸고 stderr로 경고. **결정 포인트**: 실패 정책은 학습 토론 가치 — "기본은 fail-fast, `--skip-on-error`로 옵트인"이 권장 답이지만 사용자가 다른 답을 내도 OK.

## REFACTOR 게이트

- **4-0**: fake 모델이 너무 똑똑하지 않은가? — 위 fake는 단순한 데이터만 보유 ✅
- **4-1**: `run_asr_pipeline` 함수가 너무 길면 `_iter_audio_files`, `_transcribe_one`, `_append_entry` 등으로 추출
- **4-2 (ODP 게이트)**:
  - `WhisperTranscriber`는 Service ✅ (의존성 주입, 상태 없음)
  - `Transcription`은 Value Object ✅
  - `WhisperLike`는 Protocol — 상속 강제 없는 의존성 계약, ODP에서 권장하는 형태
  - `commands/asr.py`의 Typer 함수는 어댑터일 뿐, 비즈니스 로직 X
- **4-3**: 패턴 신호 없음. 단일 모델만 다루므로 Strategy 도입 X.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `Transcription` | **Value Object** | 불변, 값 비교 |
| `WhisperTranscriber` | **Service** | 모델 의존성 주입, 메서드 호출당 동일 입력→동일 출력 |
| `WhisperLike` (Protocol) | (계약) | 분류 외 — 의존성 추상화 |
| Faster-Whisper의 raw `Segment`, `Info` | **DTO (외부 경계)** | 즉시 우리 도메인 객체로 변환 후 버려짐 |
| `run_asr_pipeline` | 자유 함수 | Typer 어댑터와 비즈니스 로직 사이의 한 층 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── types.py                    ← user types (Transcription)
│   │   ├── whisper.py                  ← user types (WhisperTranscriber, WhisperLike)
│   │   ├── languages.py                ← user types (LANGUAGE_CODES)
│   │   └── model_factory.py            ← user types (load_whisper)
│   ├── commands/
│   │   └── asr.py                      ← user types (얇은 어댑터 + run_asr_pipeline)
│   └── cli.py                          ← edit: register asr command
└── tests/
    ├── fixtures/                       ← ★ 첫 등장
    │   ├── __init__.py                 ← user types
    │   ├── audio.py                    ← user types (Phase 03에서 추출)
    │   └── doubles.py                  ← user types (FakeWhisperModel)
    ├── unit/
    │   └── test_whisper_transcriber.py ← user types
    └── integration/
        └── test_asr_pipeline.py        ← user types
```

> **Phase 03에서 인라인이던 `_build_two_segment_waveform`을 `tests/fixtures/audio.py`로 옮기고**, Phase 03 테스트(`test_slicer.py`, `test_slice_command.py`)도 같이 import를 바꾸는 작은 리팩터가 이 Phase에 포함됩니다. 별도 커밋(`refactor: extract synthetic audio helpers to tests/fixtures`)으로 분리.

## 완료 기준

- [ ] 시나리오 A~E 모두 통과 (F는 선택)
- [ ] `voxprep asr <real_dir> draft.list --model-size tiny --language en` 실제 모델로 한 번 동작 확인 (작은 모델로)
- [ ] 모델 로드는 `model_factory.load_whisper`에서만 일어남 (테스트에서 호출되지 않음)
- [ ] `Transcription`이 외부 라이브러리 타입을 expose하지 않음 (purity 유지)
- [ ] `learnings/phase04-qa.md` 작성 (특히 fake vs mock vs Protocol에 대한 정리)
- [ ] 커밋:
  - `refactor: extract synthetic audio helpers to tests/fixtures` (Phase 03에서 인라인이던 헬퍼)
  - `feat: add Transcription value object and to_list_entry conversion`
  - `feat: add WhisperTranscriber service with injected model`
  - `feat: add asr command with file-by-file transcription pipeline`
- [ ] **`voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py` 삭제** (리라이트 완료)
- [ ] FunASR/Paraformer 파일은 **남겨둠** (1차 범위 밖, 후속 학습 여지)

## 주의사항 / 엣지케이스

- **`faster-whisper` 의존성**: `pyproject.toml`에 추가 + `pip install -e .` 재실행. CTranslate2/cuDNN 등 시스템 의존성 트러블슈팅이 있을 수 있음 — 시간이 걸리면 학습 흐름이 끊기니, 처음에는 `--device cpu --compute-type int8`로 시작 권장.
- **Segment iterator는 한 번만 소비**: faster-whisper의 segments는 generator. 두 번 순회 불가. Fake도 동일하게 만들기.
- **`info.language`의 자동 감지**: `language=None`으로 호출하면 모델이 자동 감지 → `info.language`를 결과의 language로 사용. 명시 전달 시에도 `info.language`를 신뢰하는 게 일관적.
- **언어 코드 매핑**: faster-whisper는 `en`, `ko`, `ja`, `zh` 같은 ISO 639-1을 사용. 우리 `.list`도 그대로 → Phase 02 정규화와 충돌 없음. `--language auto`는 transcriber 안에서 `None`으로 변환해 라이브러리에 전달.
- **`info.language` 신뢰**: `--language en`을 명시해도 whisper는 결과에 `info.language`를 다시 채워줌. `Transcription.language`는 항상 `info.language`를 사용 — 사용자 명시는 transcribe **요청**일 뿐, 결과는 모델이 결정.
- **FunASR auto-fallback (1차 범위 외)**: 원본은 `info.language in ["zh", "yue"]`이면 funasr로 재처리. voxprep 1차에서는 **이 분기 구현 안 함**. 회고에 "중국어 데이터 처리 시 fasterwhisper 결과만 사용 — 정확도 떨어지면 fallback 도입"으로 명시. `--language zh`로 사용자가 명시할 수는 있음.
- **빈 텍스트**: 어떤 청크는 ASR 결과가 빈 문자열일 수 있음. 그대로 `.list`에 들어가게 두고, Phase 09 자동 플래그에서 시각 경고.
- **파일 정렬**: `Path.iterdir()`는 OS 순서. 사용자 경험을 위해 `sorted(input_dir.glob("*.wav"))` 같이 정렬 권장.
- **append vs write-once**: 한 줄씩 append하면 도중 중단 시에도 부분 결과 보존. write-once는 단순. 학습 토론 포인트 — 권장은 **append + 임시 파일에 쓰고 마지막에 rename**.

## 다음 Phase 준비

Phase 05~09는 `review` 모드입니다. Phase 05 시작 전에:

1. `claude-code-study/keybindings/parser.ts`, `resolver.ts`, `KeybindingContext.tsx`를 한 번 훑어보기 (구조만)
2. `prompt_toolkit.shortcuts.prompt` 의 `default=` 인자와 `key_bindings=` 인자를 문서에서 확인
3. `Transcription`/`ListEntry` 흐름이 머릿속에 있는 상태로 진입
