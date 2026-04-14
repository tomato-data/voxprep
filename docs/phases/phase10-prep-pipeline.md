# Phase 10 — `prep` 올인원 파이프라인

## 학습 목표

- 이미 만든 Service들을 **조합(composition)**해서 더 큰 워크플로우 만들기 — 새 도메인 객체 추가 거의 없음
- **단계 간 산출물 폴더 구조** 결정 — 어디에 청크를, 어디에 `.list`를, 어디에 backup을
- **부분 실행 / 재개** 설계 — 이미 slice된 청크가 있으면 건너뛸지
- Rich `Live`로 여러 단계의 진행 상황을 한 화면에 통합하는 경험
- 마지막 단계로 `review` 진입 — interactive와 non-interactive 흐름의 자연스러운 연결
- "통합 테스트는 어디까지 끌어올릴 것인가" — 전체 파이프라인 e2e 테스트의 비용/가치

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| 원본 `prepare_datasets` 흐름 | `voxprep/GPT-SoVITS/GPT_SoVITS/prepare_datasets/1-get-text.py`, `2-...`, `3-...` | 우리 범위 밖이지만, voxprep 산출물(`.list`)이 어떻게 소비되는지 흐름 이해 |
| 원본 WebUI 파이프 | `voxprep/GPT-SoVITS/webui.py` `open_slice()`, `open_asr()` | UI 단에서 단계가 어떻게 묶여 있는지 |
| Rich Live | https://rich.readthedocs.io/en/stable/live.html | 여러 진행률 통합 |
| Phase 03 `Slicer`, `commands/slice.py` | | 그대로 호출 |
| Phase 04 `WhisperTranscriber`, `commands/asr.py` | | 그대로 호출 |
| Phase 05~09 `review` | | 마지막 단계로 진입 |

## 사용자 시점 흐름

```bash
# 가장 짧은 형태 — 모든 옵션이 SETUP_GUIDE 검증 기본값
# 한국어 ASMR + macOS Apple Silicon이 voxprep의 1차 가정이라 거의 인자 없이 동작
voxprep prep ./raw_audio --workspace ./datasets/myvoice --speaker myvoice

# 전체 노브 노출 (Phase 03/04 옵션 그대로 forward, 기본값 모두 SETUP_GUIDE 일치)
voxprep prep ./raw_audio \
  --workspace ./datasets/myvoice \
  --speaker myvoice \
  --language ko \
  --sample-rate 32000 \
  --threshold -34 \
  --min-length 4000 \
  --min-interval 300 \
  --hop-size 10 \
  --max-sil-kept 500 \
  --max-amp 0.9 \
  --alpha 0.25 \
  --model-size large-v3-turbo \
  --device auto \
  --compute-type auto \
  --beam-size 5 \
  --vad \
  --vad-min-silence-ms 700 \
  --skip-review
```

> **기본값 출처**: 모두 `voxprep/GPT-SoVITS/docs/ko/SETUP_GUIDE.md`. 사용자가 한국어 ASMR 데이터셋으로 직접 검증한 값이라 인자 없이 호출해도 그대로 동작해야 합니다.

> **원칙**: prep은 slice 옵션과 asr 옵션을 **모두** 그대로 노출합니다 (Phase 03/04와 같은 기본값). 옵션 폭발이 보이지만 1차 GREEN에서는 그대로 갑니다 — 회고에서 `--config myvoice.toml` 도입 신호 점검.

기대 결과:
```
datasets/myvoice/
├── chunks/                # slice 결과 wav들 (SETUP_GUIDE의 output/slicer_opt 대응)
├── draft.list             # asr 직후 (SETUP_GUIDE의 output/asr_opt/*.list 대응)
├── final.list             # review 후 (즉시 flush로 도중 저장)
└── .voxprep_state.json    # (선택) 단계 완료 상태
```

> **하위 호환 옵션** (선택): `--legacy-layout` 플래그를 두어 SETUP_GUIDE의 디렉토리 이름(`slicer_opt/`, `asr_opt/`)을 그대로 쓰도록. 1차 GREEN에서는 빼고, 사용자가 GPT-SoVITS WebUI와 voxprep을 병행할 때만 회고에서 도입 검토.

흐름:
1. `chunks/`가 존재하면 "이미 slice됨, 재실행할까요?" 프롬프트. 아니면 slice 수행.
2. `draft.list`가 존재하면 "이미 ASR됨, 재실행할까요?" 프롬프트. 아니면 ASR 수행.
3. `final.list` 없으면 `draft.list`를 복사해 `final.list` 생성 → review 진입.
4. review 종료 시 `final.list`가 사용자 손에 남음.

## 구현 범위

### 만들 것

1. `src/voxprep/commands/prep.py` — Typer 커맨드
   - 위치 인자: `raw_audio: Path`
   - workspace/공통: `--workspace`, `--speaker`, `--skip-review`, `--no-confirm-rerun`
   - **slice 옵션 forward** (Phase 03과 동일 기본값): `--sample-rate`, `--threshold`, `--min-length`, `--min-interval`, `--hop-size`, `--max-sil-kept`, `--max-amp`, `--alpha`
   - **asr 옵션 forward** (Phase 04와 동일 기본값): `--language`, `--model-size`, `--device`, `--compute-type`, `--beam-size`, `--vad / --no-vad`, `--vad-min-silence-ms`
   - 동작: 위 흐름. 단계별 `_step_slice`, `_step_asr`, `_step_review` 자유 함수에 옵션을 묶어 전달

> **옵션을 dataclass로 묶기 — 이 Phase에서 도착**: prep 커맨드의 인자 개수가 16개를 넘는 순간이 옵션 dataclass의 도착 신호입니다. 1차 GREEN은 그냥 평탄한 인자로 가고, REFACTOR 단계(아래 시나리오 G)에서 `SliceOptions` / `AsrOptions` 도입. **중요**: dataclass는 Phase 03/04 함수의 시그니처도 역으로 단순화하므로 그쪽도 같은 커밋에서 함께 변경.
2. `src/voxprep/pipeline/__init__.py`
3. `src/voxprep/pipeline/workspace.py` — `Workspace` Value Object 또는 작은 Entity
   - `root: Path`
   - 프로퍼티: `chunks_dir: Path`, `draft_list: Path`, `final_list: Path`, `state_file: Path`
   - `ensure_root() -> None` (mkdir)
4. `src/voxprep/pipeline/runner.py` — 단계별 함수 모음 (Service)
   - `slice_step(workspace, raw_dir, slicer_options) -> None`
   - `asr_step(workspace, transcriber, speaker) -> None`
   - `review_step(workspace, ...) -> None`
   - 각 함수가 시작 전에 `Workspace`의 해당 산출물 존재 여부를 보고 skip/rerun 결정 (또는 호출자가)
5. `src/voxprep/pipeline/progress.py` (선택) — Rich Live로 단계 진행 표시. 1차로는 단순 console.print로도 OK
6. 테스트:
   - `tests/unit/test_workspace.py` — 경로 계산
   - `tests/unit/test_prep_pipeline.py` — fake transcriber + 합성 wav 1~2개로 전체 흐름 e2e
   - 단, **review 단계는 `--skip-review`로 건너뛴 통합 테스트**가 자동화 가치 — 실제 키 입력은 사람만

### 미루는 것

- Resume from arbitrary checkpoint (단계별 skip만 있어도 충분)
- Parallel slice (Phase 03에서 미룬 것)
- Train pipeline 연결 — 범위 밖

## TDD 사이클 시나리오

### 시나리오 A — Workspace 경로 계산

```python
from pathlib import Path

from voxprep.pipeline.workspace import Workspace


def test_workspace_paths(tmp_path):
    ws = Workspace(root=tmp_path / "myvoice")

    assert ws.chunks_dir == tmp_path / "myvoice" / "chunks"
    assert ws.draft_list == tmp_path / "myvoice" / "draft.list"
    assert ws.final_list == tmp_path / "myvoice" / "final.list"


def test_ensure_root_creates_directories(tmp_path):
    ws = Workspace(root=tmp_path / "myvoice")

    ws.ensure_root()

    assert ws.root.exists()
    assert ws.chunks_dir.exists()
```

GREEN: `@dataclass(frozen=True)` + properties + `ensure_root()`.

### 시나리오 B — slice_step이 chunks_dir이 비어있을 때 슬라이스한다

```python
import soundfile as sf

from voxprep.pipeline.runner import slice_step
from voxprep.slicing.slicer import Slicer


def test_slice_step_runs_when_chunks_dir_empty(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    waveform = _build_two_segment_waveform(sr=16000)
    sf.write(raw / "x.wav", waveform, 16000)

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()

    slice_step(workspace=ws, raw_dir=raw, slicer=Slicer(sr=16000, min_length=500))

    chunks = sorted(ws.chunks_dir.glob("x_*.wav"))
    assert len(chunks) >= 2
```

### 시나리오 C — slice_step skip 동작

```python
def test_slice_step_skips_when_chunks_exist(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()
    (ws.chunks_dir / "existing.wav").touch()

    raw = tmp_path / "raw"
    raw.mkdir()

    slice_step(workspace=ws, raw_dir=raw, slicer=Slicer(sr=16000), skip_if_exists=True)

    # raw에는 파일이 없지만 슬라이스 시도 안 했으므로 에러 없음
    assert (ws.chunks_dir / "existing.wav").exists()
```

GREEN: `if skip_if_exists and any(workspace.chunks_dir.iterdir()): return`.

### 시나리오 D — asr_step이 chunks_dir의 청크들을 transcribe해 draft.list 생성

```python
def test_asr_step_writes_draft_list(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()
    (ws.chunks_dir / "a.wav").touch()
    (ws.chunks_dir / "b.wav").touch()

    fake_model = FakeWhisperModel(["hello"], language="en")
    transcriber = WhisperTranscriber(model=fake_model)

    asr_step(workspace=ws, transcriber=transcriber, speaker="myvoice")

    assert ws.draft_list.exists()
    lines = ws.draft_list.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert all("myvoice" in l for l in lines)
```

### 시나리오 E — review_step이 draft.list → final.list 부트스트랩

```python
def test_review_step_creates_final_from_draft_when_missing(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()
    ws.draft_list.write_text("a.wav|s|ko|hi\n", encoding="utf-8")

    review_step(workspace=ws, skip_review=True)  # interactive 건너뜀

    assert ws.final_list.exists()
    assert ws.final_list.read_text(encoding="utf-8") == ws.draft_list.read_text(encoding="utf-8")
```

GREEN: `if not ws.final_list.exists(): copy(draft, final)`. `skip_review` True면 거기서 종료.

### 시나리오 F — 전체 prep 명령 e2e (skip-review)

```python
from typer.testing import CliRunner

from voxprep.cli import app


def test_prep_command_end_to_end(tmp_path, monkeypatch):
    # FakeWhisperModel 주입 — Phase 04에서 한 monkeypatch 트릭 재사용
    monkeypatch.setattr(
        "voxprep.commands.prep._build_transcriber",
        lambda **kwargs: WhisperTranscriber(model=FakeWhisperModel(["test"], "en")),
    )

    raw = tmp_path / "raw"
    raw.mkdir()
    sf.write(raw / "x.wav", _build_two_segment_waveform(16000), 16000)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "prep", str(raw),
            "--workspace", str(tmp_path / "ws"),
            "--speaker", "myvoice",
            "--language", "en",
            "--min-length", "500",
            "--skip-review",
        ],
    )

    assert result.exit_code == 0
    ws_root = tmp_path / "ws"
    assert (ws_root / "chunks").exists()
    assert (ws_root / "draft.list").exists()
    assert (ws_root / "final.list").exists()
```

GREEN: `commands/prep.py`에서 단계 함수 호출. transcriber 빌드는 모듈 함수로 분리해 monkey-patch가 가능하게.

## 시나리오 G — 옵션 dataclass 추출 (REFACTOR)

GREEN으로 시나리오 A~F가 통과한 뒤, prep 커맨드의 16개 인자가 단계 함수로 forward되는 코드가 손에 잡힙니다 (각 step 호출이 한 줄에 안 들어옴). 이 고통이 옵션 dataclass의 도착 신호.

추출 순서:

1. **`src/voxprep/slicing/options.py`** 신설 — frozen dataclass (Value Object):
   ```python
   @dataclass(frozen=True)
   class SliceOptions:
       sample_rate: int = 32000
       threshold: int = -34
       min_length: int = 4000
       min_interval: int = 300
       hop_size: int = 10
       max_sil_kept: int = 500
       max_amp: float = 0.9
       alpha: float = 0.25
   ```
2. **`src/voxprep/transcription/options.py`** 신설:
   ```python
   @dataclass(frozen=True)
   class AsrOptions:
       language: str = "ko"
       model_size: str = "large-v3-turbo"
       device: str = "auto"
       compute_type: str = "auto"
       beam_size: int = 5
       vad_filter: bool = True
       vad_min_silence_ms: int = 700
       speaker: str = "narrator"
   ```
3. **Phase 03 `commands/slice.py`** 시그니처 변경 — 평탄한 8개 인자를 `SliceOptions`로 묶어 받음. Typer가 dataclass를 직접 받지는 못하므로 어댑터에서 `SliceOptions(**locals())` 패턴 또는 `typer.Argument`/`typer.Option`을 그대로 두고 함수 안에서 묶기.
4. **Phase 04 `commands/asr.py`** 동일하게 `AsrOptions`로 묶기.
5. **`pipeline/runner.py`의 `slice_step` / `asr_step` 시그니처** 도 dataclass로 받게 변경.
6. **`commands/prep.py`** — Typer 평탄 인자를 받아 `SliceOptions(...)`, `AsrOptions(...)` 생성 후 step 함수에 전달.

테스트 회귀 확인: Phase 03/04 단위·통합 테스트가 모두 통과해야 함. 시나리오 시그니처도 dataclass 기반으로 손봄.

**커밋 분리 (Tidy First)**:
- `refactor: introduce SliceOptions and AsrOptions value objects`
- `feat: prep command forwards full slice and asr options`

## REFACTOR 게이트

- **4-0**: e2e 테스트 한 개로 충분. 단계별 단위 테스트(B~E)와 중복되지만, 통합 가치 있음. `--skip-review` 덕에 자동화 가능.
- **4-1**:
  - 단계 함수가 길어지면 `_should_skip(...)` 같은 헬퍼 추출
  - 옵션 dataclass로 시그니처는 이미 단순화됨 (시나리오 G)
- **4-2 (ODP 게이트)**:
  - `Workspace`는 Value Object(경로 묶음) ✅
  - `slice_step`/`asr_step`/`review_step`은 자유 함수, Service-한 줄
  - 새 Entity 없음 — 기존 객체 조합
- **4-3 (패턴 신호)**:
  - **Pipeline 패턴 도착했나?** — 3단계가 명시적 순서로 호출되고 각 단계가 skip 가능. 추상 `Step` 인터페이스로 만들고 list로 등록하는 게 더 유연하지만, 3개라 if/else가 더 읽기 좋음. **도착 안 함.**
  - 만약 단계가 5개를 넘거나 사용자가 단계를 골라 끄고 싶다고 할 때 도착.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `Workspace` | **Value Object** | 경로 묶음, 불변 |
| `SliceOptions` / `AsrOptions` | **Value Object** (REFACTOR 도착) | frozen dataclass, 옵션 묶음 — Phase 03/04 시그니처도 역으로 단순화 |
| `slice_step`/`asr_step`/`review_step` | 자유 함수 | 기존 Service 호출 어댑터, Options dataclass를 인자로 받음 |
| `prep` Typer 커맨드 | 자유 함수 (entry) | CLI 어댑터 — 평탄 인자 → Options 생성 → step 호출 |
| Phase 03~09의 모든 객체 | (재사용) | 새로 만들 것 거의 없음 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   ├── slicing/
│   │   └── options.py              ← user types (★ 신규, REFACTOR 단계)
│   ├── transcription/
│   │   └── options.py              ← user types (★ 신규, REFACTOR 단계)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── workspace.py            ← user types
│   │   ├── runner.py               ← user types
│   │   └── progress.py             ← (선택) user types
│   └── commands/
│       ├── slice.py                ← edit: SliceOptions 사용으로 시그니처 단순화
│       ├── asr.py                  ← edit: AsrOptions 사용으로 시그니처 단순화
│       └── prep.py                 ← user types (얇은 어댑터)
└── tests/
    ├── unit/
    │   └── test_workspace.py       ← user types
    └── integration/
        └── test_prep_pipeline.py   ← user types (B~F)
```

## 완료 기준

- [ ] 시나리오 A~F 모두 통과
- [ ] `voxprep prep ./raw --workspace ./out --speaker myvoice --language ko` 실제 데이터로 한 번 e2e 동작
- [ ] 두 번째 실행 시 chunks/draft.list가 있으면 skip 또는 rerun 프롬프트
- [ ] `--skip-review`로 review 단계 건너뛰기 동작
- [ ] Phase 03/04의 single-command(`voxprep slice`, `voxprep asr`)도 여전히 동작 (회귀 없음)
- [ ] `learnings/phase10-qa.md` (조합 vs 새 객체, e2e 테스트 가치, dirty 운명 결론)
- [ ] `learnings/phase10-{topic}.md` 회고 — 전체 프로젝트 회고도 같이 작성하면 좋음
- [ ] 커밋:
  - `feat: add Workspace value object for prep pipeline`
  - `feat: add slice/asr/review step functions`
  - `feat: add prep command chaining slice asr review`

## 주의사항 / 엣지케이스

- **단계 의존성**: ASR 단계는 chunks_dir이 비어있으면 의미 없음 → `asr_step`이 빈 디렉토리를 만나면 friendly 에러.
- **`final.list` 덮어쓰기 정책**: 사용자가 prep을 두 번째로 실행할 때 final.list가 이미 있으면? 1차 권장: 그대로 둠 (review 재진입). 명시적 `--reset`으로만 삭제.
- **state 파일은 1차 옵션**: `.voxprep_state.json`은 있으면 좋지만 1차 GREEN에서는 파일 시스템 존재 검사로 충분. 회고에 "단계 partial 완료(crash 중)에 대비하려면 state 파일 도입 필요"라고 메모.
- **transcriber 빌드 시점**: 진짜 모델은 무거움. `commands/prep.py` 모듈 import 시점에 만들지 말고 커맨드 함수 안에서 lazy로. 테스트 monkey-patch와 호환되게 `_build_transcriber()` 함수로 분리.
- **slicer 옵션 노출 범위**: 본 Phase 정책은 **전부 노출** (CLAUDE.md "설정 노출 원칙" 준수). 인자 폭발의 고통이 실제로 와닿으면 회고에 기록 후 `--config <toml>` 도입 또는 옵션 dataclass 묶기로 리팩터.
- **review 진입 시 화면**: prep 흐름 안에서 review가 시작되면 사용자가 갑자기 다른 모드에 들어간 느낌. 진입 직전 짧은 안내("Starting review mode. Press ? for help.") 출력.
- **GPU 실패**: prep을 새 머신에서 처음 돌릴 때 가장 흔한 실패. CUDA/CTranslate2 에러를 잡아 "CPU로 다시 시도하려면 `--device cpu` 추가" 안내 권장.

## 프로젝트 종료 후

- **회고**: 전체 10 Phase의 가장 인상적인 학습 한 가지씩 추출 → `learnings/README.md`에 한 줄씩.
- **GPT-SoVITS 정리**: `voxprep/GPT-SoVITS/` 하위에서 리라이트 끝난 파일들을 모두 삭제. 남는 것은 학습/추론 코드 + 사전훈련 모델만 — `voxprep`이 import 또는 subprocess로 호출하는 형태.
- **승격**: 학습 자산을 `200 Dev KB`로 분산 승격할지 결정 — `CLAUDE.md`의 "참조" 섹션 참고.
- **다음 학습 주제**: voxprep을 GPT-SoVITS의 학습 단계와도 연결할지(Phase 11+), 아니면 다른 도메인의 새 학습 프로젝트를 시작할지 결정.
