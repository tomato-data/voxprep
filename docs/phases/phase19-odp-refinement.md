# Phase 19 — ODP 46 규칙 기반 리팩터

> **범위**: voxprep-native 코드(`parsing/`, `slicing/`, `transcription/`, `review/`, `pipeline/`, `extract/models_path.py`, `training/config_builder.py`, `inference/session.py`, `inference/ref_picker.py`, `inference/sv.py`, `commands/`)
>
> **제외**: 이식된 코드(`extract/module/`, `extract/text/`, `extract/eres2net/`, `training/AR/`, `training/s{1,2}_train.py`, `training/utils.py`, `training/process_ckpt.py`, `inference/tts_pack/`) — 업스트림 호환 유지가 ODP 준수보다 우선
>
> **방식**: Matthias Noback "Object Design Style Guide" 46 규칙 전수 검토. 규칙 파일 경로: `~/.claude/skills/object-design-practices/rules/`

---

## 0. 점검 요약 (trend initial)

| Impact | Count | 파일/클래스 개수 |
|--------|-------|------------------|
| CRITICAL | 12 | 8 |
| HIGH | 18 | 11 |
| MEDIUM | 9 | 7 |

가장 많이 반복되는 규칙 위반:
- `svc-all-args-required` (6회) — 서비스 생성자에 기본값 산재
- `method-information-hiding` (5회) — 공개 속성 과다
- `obj-require-minimum-data` / `obj-require-meaningful-data` (합산 8회) — VO 검증 부재
- `svc-explicit-deps` (4회) — 함수 내부 import, `sys.platform` 등 숨은 의존성

(이 숫자는 `.odp-history.json` 에 저장되며, 다음 검토 시 트렌드 비교에 사용)

---

## 1. CRITICAL 위반 — 즉시 수정

### 1-1. `svc-immutable-after-creation` — `Dispatcher`
**위치**: `review/keybindings.py:13–24`

**문제**: `Dispatcher.register()`가 생성 후 `_actions` dict 를 변경. 서비스는 생성 직후 완전 구성되어야 한다는 강제 원칙 위배.

**수정안**:
```python
@dataclass(frozen=True)
class Dispatcher:
    _actions: Mapping[str, Callable]   # frozen map, 외부에서 주입

    def handle(self, key: str, session) -> ReviewOutcome:
        action = self._actions.get(key)
        if action is None:
            return ReviewOutcome.CONTINUE
        return action(session)

def build_default_dispatcher(
    player: AudioPlayer,
    editor: TextEditor,
    confirmer: Confirmer,
) -> Dispatcher:
    actions: dict[str, Callable] = {
        "n": lambda s: (s.next(), ReviewOutcome.CONTINUE)[1],
        "b": lambda s: (s.prev(), ReviewOutcome.CONTINUE)[1],
        "q": lambda s: ReviewOutcome.QUIT,
        # ... 모든 등록을 빌더 안에서 완료
    }
    return Dispatcher(_actions=types.MappingProxyType(actions))
```
테스트에서 `register()`를 쓰고 있으면 `build_test_dispatcher(actions)` 헬퍼로 교체.

**연관 규칙**: `svc-constructor-inject`, `obj-no-di-in-values` (역으로 Dispatcher도 VO처럼 불변)

---

### 1-2. `obj-require-minimum-data` + `obj-require-meaningful-data` — Options VO 전반
**위치**:
- `slicing/options.py:4–13` (SliceOptions, 8개 전부 기본값)
- `transcription/options.py:4–12` (AsrOptions, 7개 전부 기본값)
- `inference/session.py:20–31` (InferenceInputs, `text`만 필수)

**문제**: "최소 데이터" 원칙 — VO는 **필수 정보 없이 존재할 수 없어야** 한다. 현재는 `SliceOptions()` 빈 호출로 생성 가능. 또한 도메인 불변속성 검증 전무:
- `sample_rate > 0`? `threshold < 0` (dB)?
- `min_length < max_sil_kept`?
- `InferenceInputs.text` 공백?
- `ref_audio=None`이 허용되지만 실제로는 필수

**수정안**:
```python
# Named constructors로 "유의미한 기본값 조합" 분리
@dataclass(frozen=True)
class SliceOptions:
    sample_rate: int
    threshold: int
    min_length: int
    min_interval: int
    hop_size: int
    max_sil_kept: int
    max_amp: float
    alpha: float

    def __post_init__(self) -> None:
        assert self.sample_rate > 0, f"sample_rate must be positive, got {self.sample_rate}"
        assert self.threshold < 0, f"threshold dB must be negative, got {self.threshold}"
        assert 0 < self.alpha < 1, f"alpha must be in (0,1), got {self.alpha}"
        assert self.min_length >= self.min_interval, \
            f"min_length ({self.min_length}) must be >= min_interval ({self.min_interval})"

    @classmethod
    def setup_guide_defaults(cls) -> "SliceOptions":
        """사용자가 SETUP_GUIDE 에서 검증한 macOS/한국어 기본값."""
        return cls(
            sample_rate=32000, threshold=-34, min_length=4000,
            min_interval=300, hop_size=10, max_sil_kept=500,
            max_amp=0.9, alpha=0.25,
        )
```
`InferenceInputs`: `ref_audio` 필수로 승격, `text` 공백 검증.

**연관 규칙**: `obj-use-assertions`, `obj-named-constructors`

---

### 1-3. `method-information-hiding` — 공개 속성 전반
**위치**:
- `review/session.py:9–12` (list_path, entries, cursor, _undo_snapshot)
- `slicing/slicer.py:20–25` (sr, threshold, hop_size 등)
- `transcription/whisper.py:20–24` (model, default_language 등)
- `inference/session.py:67–68` (tts, version)

**문제**: 내부 상태가 공개 속성으로 노출. 외부 코드가 이를 직접 읽거나 변경 가능 → 캡슐화 위반.

**수정안** (ReviewSession 예시):
```python
class ReviewSession:
    def __init__(self, list_path: Path, entries: list[ListEntry]) -> None:
        self._list_path = list_path
        self._entries = list(entries)  # defensive copy
        self._cursor = 0
        self._undo_snapshot: UndoSnapshot | None = None

    # 질의 메서드만 공개
    def current(self) -> ListEntry: ...
    def position(self) -> Position: ...   # (cursor+1, total) 반환 VO
    def is_at_start(self) -> bool: ...
    def is_at_end(self) -> bool: ...
    def is_empty(self) -> bool: ...
    # 커맨드
    def next(self) -> None: ...
    # ...
```

`render.py` 가 `session.cursor`, `session.entries` 를 직접 읽고 있는데 `session.position()` 같은 도메인 질의로 대체.

**연관 규칙**: `arch-final-private-default`

---

### 1-4. `method-cqs-separation` + `method-single-return-type` — ReviewSession.undo
**위치**: `review/session.py:47–55`

**문제**:
```python
def undo(self) -> bool:
    if self._undo_snapshot is None:
        return False      # query (상태 질의)
    self.entries, self.cursor = self._undo_snapshot   # command (mutation)
    self._undo_snapshot = None
    return True           # query (성공 여부)
```
한 메서드가 **상태를 질의** + **상태 변경** + **결과 반환** 을 섞음.

**수정안 — 분리**:
```python
def can_undo(self) -> bool:       # 순수 query
    return self._undo_snapshot is not None

def undo(self) -> None:           # 순수 command
    if self._undo_snapshot is None:
        raise CouldNotUndo.no_snapshot_available()
    self._entries, self._cursor = self._undo_snapshot
    self._undo_snapshot = None
```
호출부는:
```python
if session.can_undo():
    session.undo()
    session.save()
```

**연관 규칙**: `method-exception-naming` (CouldNotUndo)

---

### 1-5. `method-exception-naming` — 도메인 예외 부재
**위치**: 프로젝트 전체. 유일한 도메인 예외: `MalformedListLineError` (`parsing/errors.py`).

**문제**: 다음 상황들이 전부 `typer.Exit`, `FileNotFoundError`, `ValueError`, `RuntimeError` 로 처리됨:
- `commands/infer.py`: `typer.Exit("no weights found")`
- `inference/session.py`: `FileNotFoundError(f"reference audio required")`
- `inference/session.py`: `RuntimeError("no audio produced")`
- `extract/models_path.py`: `FileNotFoundError(f"{what} not found at {path}")`
- `review/session.py`: IndexError (암묵적, 가드 없음)

**수정안**:
```python
# src/voxprep/errors.py (신규)
class InvalidReferenceAudio(ValueError):
    @classmethod
    def not_found(cls, path: Path) -> "InvalidReferenceAudio":
        return cls(f"reference audio not found: {path}")

    @classmethod
    def missing(cls) -> "InvalidReferenceAudio":
        return cls("reference audio is required for synthesis")

class CouldNotFindWeights(FileNotFoundError):
    @classmethod
    def for_version(cls, version: str, kind: str) -> "CouldNotFindWeights":
        return cls(f"no {kind} weights found for version {version}")

class CouldNotUndo(RuntimeError):
    @classmethod
    def no_snapshot_available(cls) -> "CouldNotUndo":
        return cls("no undo snapshot available")

class InvalidModelsRoot(FileNotFoundError):
    @classmethod
    def missing_file(cls, what: str, path: Path) -> "InvalidModelsRoot":
        return cls(
            f"{what} not found at {path}. "
            "Download pretrained models and place under the models root."
        )
```

CLI 어댑터층에서 이 예외들을 잡아 `typer.Exit`으로 번역.

**연관 규칙**: `method-named-exception-ctor`, `test-exception-message`

---

### 1-6. `obj-require-meaningful-data` — 검증 없는 VO 전반
**위치**:
- `parsing/list_file.py:6–27` (ListEntry — 빈 audio_path/text 허용)
- `slicing/slicer.py:4–8` (Chunk — start > end 허용)
- `pipeline/workspace.py:6–7` (Workspace — 아무 Path OK)
- `inference/ref_picker.py` (RefCandidate — duration<0, score 음수 OK)

**수정안** (ListEntry):
```python
@dataclass(frozen=True)
class ListEntry:
    audio_path: str
    speaker: str
    language: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", self.language.lower())
        assert self.audio_path, "audio_path must not be empty"
        assert self.speaker, "speaker must not be empty"
        assert self.language, "language must not be empty"
        # text 는 의도적으로 빈 값 허용 (ASR 무음 결과)
```

(Chunk):
```python
def __post_init__(self) -> None:
    assert self.start_sample >= 0, f"start_sample must be >= 0, got {self.start_sample}"
    assert self.end_sample > self.start_sample, \
        f"end_sample ({self.end_sample}) must exceed start_sample ({self.start_sample})"
    assert self.data.ndim >= 1 and len(self.data) > 0, "chunk data must be non-empty"
```

**연관 규칙**: `obj-use-assertions`, `mut-valid-after-mutation`

---

## 2. HIGH 위반 — 강력 권장

### 2-1. `svc-all-args-required` — 서비스 기본값
**위치**:
- `transcription/whisper.py:12–19` — `default_language=None`, `beam_size=5`, `vad_filter=True`, `vad_min_silence_ms=700`
- `slicing/slicer.py:12–19` — 5개 파라미터 전부 기본값
- `extract/models_path.py:18–19` — `root=None`
- `inference/session.py:35–43` — `version="v2Pro"`, `models=None`, `device="cpu"`, `is_half=False`

**수정안**: 기본값 제거 + 명명 생성자 제공
```python
class WhisperTranscriber:
    def __init__(
        self,
        model: WhisperLike,
        default_language: str,   # 기본값 제거
        beam_size: int,
        vad_filter: bool,
        vad_min_silence_ms: int,
    ) -> None: ...

    @classmethod
    def with_setup_guide_defaults(cls, model: WhisperLike) -> "WhisperTranscriber":
        return cls(
            model=model, default_language="ko", beam_size=5,
            vad_filter=True, vad_min_silence_ms=700,
        )
```

CLI 어댑터와 테스트는 모두 명시 인자 또는 named ctor 호출.

---

### 2-2. `svc-explicit-deps` — 숨은 의존성
**위치**:
- `extract/models_path.py:69–74` `select_device()` — `import torch` 함수 안
- `review/player.py:33–39` `_command()` — `sys.platform` 정적 조회
- `review/editor.py:9–14` — `from prompt_toolkit import prompt` 함수 안
- `commands/review.py:16` — prompt_toolkit 임포트 함수 내
- `review/session.py:31–32` `save()` — `write_list_file` 직접 호출 (하드 의존)

**수정안**:
```python
# Platform 추상화
class PlatformPlayback(Protocol):
    def command(self, path: Path) -> list[str]: ...

class MacPlayback:
    def command(self, path: Path) -> list[str]:
        return ["afplay", str(path)]

class LinuxPlayback:
    def command(self, path: Path) -> list[str]:
        return ["aplay", str(path)]

def detect_platform_playback() -> PlatformPlayback:
    if sys.platform == "darwin": return MacPlayback()
    if sys.platform == "linux": return LinuxPlayback()
    raise RuntimeError(f"unsupported platform: {sys.platform}")

class SubprocessAudioPlayer:
    def __init__(self, platform: PlatformPlayback) -> None:
        self._platform = platform
        self._current: subprocess.Popen | None = None
```

Device 선택:
```python
class DeviceSelector(Protocol):
    def select(self, prefer_half: bool) -> tuple[str, bool]: ...

class TorchDeviceSelector:
    def select(self, prefer_half: bool) -> tuple[str, bool]:
        import torch
        if torch.cuda.is_available():
            return "cuda:0", prefer_half
        return "cpu", False
```

`ReviewSession.save()` 가 직접 `write_list_file` 부르는 부분은 Repository 주입으로 해결 (2-6 참조).

---

### 2-3. `svc-constructor-assign-only` — ModelsPaths 부수효과
**위치**: `extract/models_path.py:17–19`

**문제**: `__init__` 이 `resolve_models_root()` 호출 → env var 읽음 + filesystem exists() 호출 → 부수효과.

**수정안**:
```python
@dataclass(frozen=True)
class ModelsPaths:
    root: Path   # 완전히 해석된 경로만 받음

    # 모든 경로는 @property 로 계산만 (필요 시)
    @property
    def bert_dir(self) -> Path: ...

    @classmethod
    def from_environment(
        cls,
        cli_override: Path | None = None,
        project_root: Path = None,
    ) -> "ModelsPaths":
        """env / CLI / 프로젝트 루트 에서 해석해 생성."""
        if cli_override is not None:
            return cls(root=cli_override.resolve())
        if env := os.environ.get("VOXPREP_MODELS_ROOT"):
            return cls(root=Path(env).resolve())
        # ...
```
`ModelsPaths()` 빈 호출을 금지하고 `ModelsPaths.from_environment()` 를 경유하도록 전환.

---

### 2-4. `svc-constructor-assign-only` — Workspace.ensure_root 부수효과
**위치**: `pipeline/workspace.py:21–22`

**문제**: `frozen=True` VO 가 mkdir 부수효과 가진 메서드 보유 — VO 순수성 위반.

**수정안**:
```python
# pipeline/workspace.py
@dataclass(frozen=True)
class Workspace:
    root: Path
    @property def chunks_dir(self): ...
    # 부수효과 메서드 제거

# pipeline/workspace_setup.py (신규, 자유 함수)
def ensure_workspace(ws: Workspace) -> None:
    ws.chunks_dir.mkdir(parents=True, exist_ok=True)
```

호출부 `commands/prep.py` 는 `ensure_workspace(ws)` 로 전환.

---

### 2-5. `method-information-hiding` — Slicer/WhisperTranscriber 공개 속성
**위치**: 1-3에 포함됐지만 별도 적용 필요.

**수정안**: 모든 속성을 `_name` 으로 마킹, 외부에서 읽으려면 메서드 추가.

특히 `slice_step`/`asr_step`이 `options.sample_rate` 등을 읽는 부분 — 이미 Options VO 를 통해 읽으므로 Slicer 내부까지 노출할 필요 없음.

---

### 2-6. `method-domain-abstraction` — Repository 부재
**위치**: `parsing/list_file.py:30–36` (`write_list_file`, `read_list_file`)

**문제**: 자유 함수로 직접 파일 I/O. 테스트마다 `tmp_path` 써야 함. 경계 추상화 없음.

**수정안** (점진적):
```python
# parsing/list_file.py 에 추가
class ListFileRepository(Protocol):
    def read(self, path: Path) -> list[ListEntry]: ...
    def write(self, path: Path, entries: list[ListEntry]) -> None: ...

class FilesystemListFileRepository:
    def read(self, path: Path) -> list[ListEntry]:
        content = path.read_text(encoding="utf-8")
        return [ListEntry.from_line(s) for s in content.splitlines() if s.strip()]
    def write(self, path: Path, entries: list[ListEntry]) -> None:
        path.write_text("\n".join(e.to_line() for e in entries), encoding="utf-8")

class InMemoryListFileRepository:
    def __init__(self) -> None:
        self._store: dict[Path, list[ListEntry]] = {}
    def read(self, path: Path) -> list[ListEntry]: return list(self._store[path])
    def write(self, path: Path, entries: list[ListEntry]) -> None: self._store[path] = list(entries)
```

`ReviewSession` 이 Repository 주입받게 변경 → `save()` 가 I/O 없이 테스트 가능.

**주의**: 이 리팩터는 **테스트 72개 이상 영향**. Phase 내에서 마지막 단계로 실행.

---

### 2-7. `mut-valid-state-transition` — ReviewSession 가드 부재
**위치**: `review/session.py` 전반

**문제**: 다음 상황에서 IndexError:
- `is_empty()` 상태에서 `current()`, `delete_current()`, `update_current_text()`
- `can_undo() == False` 인데 `undo()` 호출

**수정안**:
```python
def current(self) -> ListEntry:
    if self.is_empty():
        raise InvalidSessionState.no_entries()
    return self._entries[self._cursor]

def delete_current(self) -> None:
    if self.is_empty():
        raise InvalidSessionState.cannot_delete_from_empty()
    # ...

def update_current_text(self, new_text: str) -> None:
    if self.is_empty():
        raise InvalidSessionState.cannot_update_empty()
    # ...
```

Dispatcher 에서 이미 `is_empty()` 체크하고 있어 실사용에서는 안전하지만, Entity 자체의 불변식 가드는 있어야 함.

---

### 2-8. `obj-named-constructors` — 명명 생성자 확산
**위치**: 여러 VO/Service 에서 underused

**수정안**:
```python
# Workspace
@classmethod
def for_experiment(cls, base_dir: Path, exp_name: str) -> "Workspace":
    return cls(root=base_dir / exp_name)

# ListEntry — 이미 from_line 있음, 추가:
@classmethod
def from_transcription(cls, t: Transcription, speaker: str) -> "ListEntry":
    # Transcription.to_list_entry 대신 역방향 이동 검토 (Mover)
    ...

# InferenceInputs
@classmethod
def quick(cls, text: str, ref_audio: Path, prompt_text: str, lang: str = "ko") -> "InferenceInputs":
    return cls(text=text, text_lang=lang, ref_audio=ref_audio,
               prompt_text=prompt_text, prompt_lang=lang)

# Slicer
@classmethod
def for_slice_options(cls, opts: SliceOptions) -> "Slicer":
    return cls(sr=opts.sample_rate, threshold=opts.threshold, ...)
```

`slice_step` 의 수동 `Slicer(sr=options.sample_rate, ...)` 가 `Slicer.for_slice_options(options)` 한 줄로 단순화.

---

### 2-9. `obj-extract-composite` — 복합 값 후보
**위치**: `review/session.py:12,34–35`

**문제**: `_undo_snapshot: tuple[list[ListEntry], int]` — 짝 지은 값이 튜플.

**수정안**:
```python
@dataclass(frozen=True)
class UndoSnapshot:
    entries: tuple[ListEntry, ...]   # 불변 튜플
    cursor: int
```

---

### 2-10. `test-exception-message` — 메시지 검증 부재
**위치**: 여러 테스트

**수정안**:
```python
# 지금
with pytest.raises(MalformedListLineError):
    ListEntry.from_line("a|b|c")

# 개선
with pytest.raises(MalformedListLineError, match="got 3"):
    ListEntry.from_line("a|b|c")
```

도메인 예외 네임드 ctor 가 생기면 자연스럽게 메시지 내용이 안정화되므로 메시지 매칭이 안전해짐.

---

## 3. MEDIUM 위반 — 참고 사항

### 3-1. `method-single-return-type` — `Optional[T]` 반환
**위치**:
- `review/issues.py` 모든 `check_*` 함수 — `Issue | None`
- `review/editor.py` `TextEditor.edit` — `str | None`

**ODP 입장**: Optional 은 "두 타입" 반환. 순수한 적용이라면 Null Object (NoIssue), empty list, 또는 sentinel 반환.

**현실적 판단**: 현재 방식이 Python 관례상 자연스러움. Phase 문서에 근거도 남아있음. **waiver 로 처리**. 만약 리팩터 한다면:
```python
# Issue 체크
class NoIssue(Issue):  # Null Object
    ...
# 또는
def check_empty_text(entry) -> list[Issue]:   # 0 or 1개 반환
    if not entry.text.strip():
        return [Issue("empty_text", ...)]
    return []
```

### 3-2. `obj-dto-exception` — 실제 DTO 없음
Typer 가 CLI 인자를 받아주므로 별도 DTO 불필요. Pass.

### 3-3. `arch-separate-read-write` — Read/Write 모델 분리
현재 voxprep 은 소규모 CLI — 분리 불필요. N/A.

### 3-4. `arch-decorate-to-extend` — Decorator 미사용
`LoggingAudioPlayer`, `TimingInferenceSession` 등 데코레이터 패턴 적용 여지 있지만 현재 필요 없음. 실제 고통이 오면 도입.

### 3-5. `arch-final-private-default` — final/private 기본값
Python 은 final 강제 불가. 철학 반영 차원에서:
- 도메인 클래스에 `@final` (from typing) 적용
- 모든 내부 속성 `_name` 프리픽스
- 부분 적용 가능

### 3-6. `mut-record-domain-events` — 이벤트 기록 없음
ReviewSession 에 `EntryDeleted`, `TextUpdated` 이벤트 기록하면 테스트가 "동작" 대신 "결과 이벤트"로 검증 가능. Phase 16(GUI) 또는 Phase 17(MCP 서버)로 확장 시 자연스럽게 필요.

### 3-7. `test-constructor-failure-only` — 생성자 성공 테스트 다수
현재 `test_list_parser.py` 등 여러 테스트가 생성자 성공 케이스 검증. ODP 는 "성공은 다른 테스트에서 간접 증명, 실패만 직접 테스트" 권장. 기존 테스트 유지하되, VO validation 추가 시 실패 케이스 중심으로 작성.

### 3-8. `test-events-for-mutation`
`ReviewSession` 에 이벤트 없으니 현재 적용 불가. 3-6 도입 시 함께.

### 3-9. `svc-method-arg-for-task`
`WhisperTranscriber.default_language` — 생성자에 있지만 "현재 이 호출의 언어"가 필요하면 메서드 인자가 맞음. 현재는 설정값 역할이라 OK. waiver.

---

## 4. 적용 불가 / Waiver

아래 규칙은 voxprep 맥락상 적용 X:

| 규칙 | 사유 |
|------|------|
| `arch-usecase-read-model` / `arch-direct-from-source` / `arch-event-driven-read` | CQRS 분리 수준의 복잡성 없음 |
| `arch-compose-not-inherit` | 이미 준수 (상속 없음) |
| `obj-dto-exception` | 실제 DTO 없음 (Typer가 경계 처리) |
| `method-information-hiding` — `ref_picker.RefCandidate.audio_path/text` property | 의도적 도메인 질의, 내부 노출 아님 |
| `method-single-return-type` — Optional 반환 | Python 관례상 허용, 별도 waiver |

---

## 5. 단계별 실행 계획

### Phase 19a — 경계 정리 (1~2일)
**우선순위**: CRITICAL 1-1, 1-5, 1-6

1. `src/voxprep/errors.py` 신설 — 도메인 예외 모듈
2. `MalformedListLineError` → 여기로 이동
3. `InvalidReferenceAudio`, `CouldNotFindWeights`, `CouldNotUndo`, `InvalidSessionState`, `InvalidModelsRoot` 추가 (모두 named ctor)
4. `Dispatcher` frozen dataclass 전환 + `register()` 제거 + `build_default_dispatcher` 만 남김
5. 모든 VO 에 `__post_init__` assert 추가 (ListEntry, Chunk, Workspace, SliceOptions, AsrOptions, InferenceInputs)
6. 테스트: 각 VO 실패 케이스 1~2개씩, 예외 메시지 매칭

**커밋**:
- `feat: add domain exception module with named constructors`
- `refactor: make Dispatcher immutable with mapping proxy`
- `feat: add meaningful data assertions to value objects`
- `test: cover VO validation failures with exception message asserts`

### Phase 19b — 서비스 생성자 정리 (1일)
**우선순위**: CRITICAL 1-3, HIGH 2-1, 2-3

7. `WhisperTranscriber`, `Slicer`, `InferenceSession` 에서 기본값 전부 제거
8. `WhisperTranscriber.with_setup_guide_defaults()`, `Slicer.for_slice_options(opts)` 등 named ctor 추가
9. `ModelsPaths` → `frozen=True` dataclass + `from_environment()` classmethod
10. 공개 속성 전부 `_name` 프리픽스 (ReviewSession, Slicer, WhisperTranscriber)
11. `render.py` 가 session 내부 직접 참조하는 부분 → `session.position()`, `session.current()` 등 도메인 질의로

**커밋**:
- `refactor: require all service constructor args; add named defaults`
- `refactor: hide internal state behind domain queries`

### Phase 19c — CQS 분리 (0.5일)
**우선순위**: CRITICAL 1-4

12. `ReviewSession.undo() -> None` (raise on empty) + `can_undo() -> bool`
13. 호출부 (keybindings.py의 'u' action) 업데이트

### Phase 19d — 부수효과 외부화 (0.5일)
**우선순위**: HIGH 2-4

14. `Workspace.ensure_root()` 제거 → 자유 함수 `ensure_workspace(ws)` in `pipeline/runner.py` 또는 신규 `pipeline/setup.py`

### Phase 19e — 숨은 의존성 노출 (1일)
**우선순위**: HIGH 2-2

15. `PlatformPlayback` Protocol + `MacPlayback`/`LinuxPlayback` 추상화
16. `DeviceSelector` Protocol + `TorchDeviceSelector`
17. `SubprocessAudioPlayer(platform=...)` DI
18. `select_device()` 자유 함수는 TorchDeviceSelector 로 대체

### Phase 19f — Repository 도입 (1~2일, 신중)
**우선순위**: HIGH 2-6

19. `ListFileRepository` Protocol + `FilesystemListFileRepository` + `InMemoryListFileRepository`
20. `ReviewSession(list_path, entries, repo: ListFileRepository)` 로 시그니처 변경
21. 기존 `read_list_file`/`write_list_file` 자유 함수는 유지 (deprecation 주석) + 위 Repository로 위임
22. 테스트 더블 추가 + 기존 tmp_path 기반 테스트 일부를 InMemoryRepository 로 전환

**영향 범위 큼** — 별도 Phase로 분리할지 재검토.

### Phase 19g — Named Constructor 보강 (0.5일)
**우선순위**: HIGH 2-8, 2-9

23. `Workspace.for_experiment(base, name)`
24. `InferenceInputs.quick(text, ref, prompt)`
25. `Slicer.for_slice_options(opts)`
26. `UndoSnapshot` 복합 VO 추출

### Phase 19h — 테스트 품질 (0.5일)
**우선순위**: HIGH 2-10

27. 모든 `pytest.raises(ExcType)` → `pytest.raises(ExcType, match="...")` 로 업그레이드
28. 새 도메인 예외들이 정확한 메시지 포함하는지 검증

---

## 6. 예상 영향

### 테스트 수
- 현재 73개 → 예상 증가분:
  - VO validation 실패 케이스: +15~20 개
  - 새 도메인 예외: +5~8 개
  - Repository 인메모리 구현 검증: +5 개
- 예상 최종: **100~110 개**

### 코드 변경
- 신규 파일:
  - `src/voxprep/errors.py`
  - `src/voxprep/pipeline/setup.py` (선택)
- 주요 수정:
  - `review/session.py` (Entity 강화)
  - `review/keybindings.py` (Dispatcher immutable)
  - `extract/models_path.py` (VO 화)
  - `parsing/list_file.py` (Repository 분리)
  - `slicing/options.py`, `transcription/options.py`, `inference/session.py` (VO 검증)
  - 다수 VO 파일들 (`__post_init__` assert 추가)

### 예상 LOC 증감
- `+400~600 lines` (named ctors, assertions, exceptions, protocols)
- `-50~100 lines` (register 제거, 중복 제거)
- **순증 ~350~500 lines**

### 위반 감소 목표
| | Before | After |
|---|--------|-------|
| CRITICAL | 12 | 0 |
| HIGH | 18 | 3~5 (waiver) |
| MEDIUM | 9 | 5~6 (waiver) |

---

## 7. 우선순위 순서 (TL;DR)

```
19a: 도메인 예외 + VO 검증 + Dispatcher 불변       (CRITICAL)
19b: 서비스 생성자 정리 + 정보 은닉                (CRITICAL + HIGH)
19c: ReviewSession.undo CQS 분리                  (CRITICAL)
19d: Workspace.ensure_root 외부화                 (HIGH)
19e: PlatformPlayback / DeviceSelector 추상화      (HIGH)
19f: ListFileRepository 도입                      (HIGH, 영향 크므로 마지막)
19g: Named constructor 보강                       (HIGH)
19h: 테스트 메시지 매칭                           (HIGH)
```

각 서브 Phase 끝에는 `uv run pytest tests/ -v` 73+ 전부 통과해야 다음으로.

---

## 8. 메모

- **waiver 기록이 중요**: `method-single-return-type` Optional 반환, `obj-dto-exception` 등은 의도적 예외. 각 waiver 는 코드 주석 또는 이 문서에서 근거 명시.
- **이식 코드는 대상 외**: `extract/module/`, `training/AR/`, `inference/tts_pack/` 등은 업스트림과의 호환성이 ODP 준수보다 우선. 이식본에 ODP 규칙을 강제하지 말 것.
- **Tidy First 유지**: `feat:` / `refactor:` / `test:` 분리 커밋. Phase 19 내에서도 마찬가지.
- **트렌드 추적**: `.odp-history.json` 에 이번 검토 + 각 서브 Phase 완료 후 결과 갱신.

---

## 참고

- ODP 46 규칙: `~/.claude/skills/object-design-practices/rules/`
- Object Design Style Guide (Matthias Noback) — 장별 참조가 각 규칙 파일에 명시
- Phase 01~10 구현 당시 ODP 판단 근거: 각 phase 문서의 "ODP 관점" 섹션
