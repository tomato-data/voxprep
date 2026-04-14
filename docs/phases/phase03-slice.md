# Phase 03 — `slice` 커맨드 (slicer2 리라이트)

## 학습 목표

- **Service 분류**의 첫 사례 — 의존성을 받고, 상태 없이 동작하는 객체
- 알고리즘(`Slicer`)과 IO(파일 읽기·쓰기)의 **명확한 분리(seam)** — 알고리즘은 numpy array만 받고, IO는 호출자가 책임
- Typer 커맨드 함수에서 인자 검증 / 진행 표시 / 에러 처리 분리
- Rich `Progress`로 파일 단위 진행률 표시 (subprocess 없이 in-process)
- "테스트가 어려우면 설계가 잘못됐다" — 거대한 IO + 알고리즘 덩어리를 쪼개는 경험

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| 원본 알고리즘 | `voxprep/GPT-SoVITS/tools/slicer2.py` | `Slicer` 클래스 전체. 그대로 따라 짜는 게 아니라 **읽고 이해한 다음 새로 작성** |
| CLI 진입 (subprocess 호출) | `voxprep/GPT-SoVITS/tools/slice_audio.py` | 원본은 부분 병렬화(`n_parts`)까지 함 — 우리는 1차로 단일 프로세스로만 |
| WebUI 트리거 | `voxprep/GPT-SoVITS/webui.py` `open_slice()` (라인 ~682) | 어떤 파라미터들이 사용자에게 노출되는지 확인 |
| **사용자 검증 설정** | `voxprep/GPT-SoVITS/docs/ko/SETUP_GUIDE.md` 3-2절 | "나머지 설정 기본값 유지" — WebUI 기본값(아래 표)을 그대로 voxprep 기본값으로 채택. 출력 디렉토리 관례: `output/slicer_opt` |
| 진행률 표시 | `claude-code-study`에는 적합 사례 없음 | Rich 공식 문서: `rich.progress.Progress` |

## `Slicer` 알고리즘 요약 + 업스트림 노브

> 직접 확인할 것: `voxprep/GPT-SoVITS/tools/slicer2.py`(`Slicer.__init__`), `voxprep/GPT-SoVITS/tools/slice_audio.py`(CLI 래퍼), `voxprep/GPT-SoVITS/webui.py:682` (`open_slice` 시그니처). voxprep은 아래 노브들을 **모두** CLI에 노출하는 것이 기본입니다.

- 입력: 1D 또는 2D numpy waveform, sample rate
- **`Slicer` 생성자 파라미터** (slicer2.py):
  - `sr` — sample rate. **GPT-SoVITS는 32000 hardcode** (slice_audio.py L22). voxprep은 `--sample-rate` 플래그로 노출하되 기본값 32000.
  - `threshold` (dB, 기본 GPT-SoVITS는 -34, slicer2 자체 기본 -40) — RMS가 이보다 낮으면 침묵
  - `min_length` (ms, 기본 4000) — 슬라이스 결과의 최소 길이
  - `min_interval` (ms, 기본 300) — 침묵 구간이 이 이상 길어야 자르기 후보
  - `hop_size` (ms, 기본 10) — RMS 계산 윈도우 hop
  - `max_sil_kept` (ms, 기본 500) — 자른 청크 양 끝에 남길 최대 침묵 길이
- **slice_audio.py 추가 노브** (정규화 단계 — `Slicer` 외부에서 적용):
  - `_max` (float, 기본 0.9) — 청크 정규화 시 목표 피크. CLI 플래그명: `--max-amp`
  - `alpha` (float, 기본 0.25) — 정규화 청크와 원본의 믹스 비율 (`normalized * alpha + original * (1 - alpha)`). CLI 플래그명: `--alpha`
- 알고리즘:
  1. waveform을 hop_size 단위 프레임으로 나눠 RMS 곡선 계산
  2. RMS < threshold 인 구간을 침묵으로 마킹
  3. 침묵 구간이 `min_interval` 이상이면 그 가운데에서 자르기
  4. 결과 청크가 `min_length` 미만이면 인접 청크와 병합
  5. 각 청크 양 끝의 침묵을 `max_sil_kept` 이하로 트리밍
  6. (slice_audio.py 단계) 청크별로 `--max-amp` / `--alpha`로 정규화 + 믹스
- 출력: `[(chunk_waveform, start_sample, end_sample), ...]`

> **노브 누락 점검**: 위 8개(`sr`, `threshold`, `min_length`, `min_interval`, `hop_size`, `max_sil_kept`, `_max`, `alpha`)가 voxprep `slice` 커맨드에 모두 플래그로 보여야 합니다. 빠진 게 있으면 사용자가 GPT-SoVITS 파이프라인을 voxprep으로 옮길 때 재현 불가능해집니다.

## 구현 범위

### 만들 것

1. `src/voxprep/slicing/__init__.py`
2. `src/voxprep/slicing/slicer.py` — `Slicer` 클래스 (Service)
   - `__init__(sr, threshold=-40.0, min_length=5000, min_interval=300, hop_size=20, max_sil_kept=5000)`
   - `slice(waveform: np.ndarray) -> list[Chunk]` (Chunk는 frozen dataclass: `data: np.ndarray`, `start_sample: int`, `end_sample: int`)
   - 내부 헬퍼 `_rms_curve`, `_find_silence_regions`, `_merge_short` 등은 처음엔 한 메서드 안에 두고, GREEN 후 REFACTOR에서 추출
3. `src/voxprep/slicing/io.py` — IO 헬퍼
   - `load_audio(path: Path) -> tuple[np.ndarray, int]` (librosa 또는 soundfile)
   - `save_chunk(chunk: Chunk, dst: Path) -> None`
4. `src/voxprep/commands/slice.py` — Typer 커맨드 함수
   - 인자: `input_dir: Path`, `output_dir: Path`
   - **모든 업스트림 노브를 플래그로 노출** (기본값은 GPT-SoVITS 기본값 일치):
     - `--sample-rate` (int, default `32000`)
     - `--threshold` (int, default `-34`) — dB
     - `--min-length` (int, default `4000`) — ms
     - `--min-interval` (int, default `300`) — ms
     - `--hop-size` (int, default `10`) — ms
     - `--max-sil-kept` (int, default `500`) — ms
     - `--max-amp` (float, default `0.9`) — 정규화 목표 피크
     - `--alpha` (float, default `0.25`) — 정규화 믹스 비율
   - 동작: input_dir의 wav/flac 파일들을 순회 → `--sample-rate`로 리샘플 load → `Slicer.slice` → `--max-amp`/`--alpha`로 정규화 → `output_dir/{stem}_{start}_{end}.wav`로 저장
   - Rich `Progress`로 파일 단위 진행률
5. `src/voxprep/cli.py`에 `app.add_typer` 또는 `@app.command()`로 `slice` 등록
6. 테스트:
   - `tests/unit/test_slicer.py` — 알고리즘 단위 테스트 (합성 waveform 사용)
   - **`tests/integration/test_slice_command.py`** — Typer `CliRunner` + `tmp_path` e2e. **`tests/integration/` 디렉토리 첫 등장** — `__init__.py` 같이 만들 것
   - 합성 waveform 헬퍼(`_build_two_segment_waveform`)는 일단 `test_slicer.py`/`test_slice_command.py` 내부에 둡니다. **Phase 04에서 같은 헬퍼가 또 필요해지면 그때 `tests/fixtures/audio.py`로 추출** — premature extraction 금지

### 미루는 것

- 병렬화 (`n_parts`)
- 비-wav 포맷 자동 변환
- 진행률을 NDJSON으로 노출 (Phase 10에서 prep 파이프라인이 자식 프로세스로 호출할 때 다시 결정)

## TDD 사이클 시나리오

### 시나리오 A — RMS 곡선이 만들어진다

먼저 알고리즘을 **합성 waveform**으로 단위 테스트할 수 있게 만듭니다. 이게 핵심 학습 — 진짜 오디오 파일 없이도 알고리즘을 검증할 수 있어야 합니다.

```python
import numpy as np

from voxprep.slicing.slicer import Slicer


def test_silence_only_audio_returns_no_chunks():
    sr = 16000
    waveform = np.zeros(sr * 3, dtype=np.float32)  # 3초 완전 침묵
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=1000)

    chunks = slicer.slice(waveform)

    assert chunks == []
```

GREEN: 침묵만 있는 입력은 아무 청크도 안 나오는 게 자연스러움. 가장 단순한 케이스부터.

### 시나리오 B — 단일 음성 구간

```python
def test_single_loud_segment_returns_one_chunk():
    sr = 16000
    waveform = np.zeros(sr * 3, dtype=np.float32)
    # 1.0~2.0초 구간에 톤 신호
    t = np.arange(sr) / sr
    waveform[sr : 2 * sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=500, min_interval=200)

    chunks = slicer.slice(waveform)

    assert len(chunks) == 1
    chunk = chunks[0]
    # 청크가 1초 음성 구간을 포함해야 함 (앞뒤 침묵 일부 trim 후)
    assert chunk.end_sample - chunk.start_sample >= int(sr * 0.5)
```

### 시나리오 C — 두 음성 구간 사이에 충분한 침묵

```python
def test_two_segments_separated_by_silence_returns_two_chunks():
    sr = 16000
    waveform = np.zeros(sr * 5, dtype=np.float32)
    t = np.arange(sr) / sr
    waveform[: sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    waveform[3 * sr : 4 * sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    # 두 청크 사이 2초 침묵 → min_interval=300ms로 충분히 분리
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=500, min_interval=300)

    chunks = slicer.slice(waveform)

    assert len(chunks) == 2
```

### 시나리오 D — `min_length` 미달 청크는 병합/제거

```python
def test_short_segment_merged_or_dropped():
    # 너무 짧은 음성 한 조각만 있을 때 청크 0개 또는 1개로 스무딩되는지
    ...
```

이 시나리오는 알고리즘 결정에 따라 0 vs 1이 갈림. 원본 `slicer2.py`를 보고 결정한 뒤 어느 쪽인지 코멘트로 남길 것.

### 시나리오 E — Typer 커맨드 통합 테스트

```python
import soundfile as sf
from typer.testing import CliRunner

from voxprep.cli import app

runner = CliRunner()


def test_slice_command_writes_chunks(tmp_path):
    sr = 16000
    src_dir = tmp_path / "in"
    dst_dir = tmp_path / "out"
    src_dir.mkdir()

    waveform = _build_two_segment_waveform(sr)  # 헬퍼
    sf.write(src_dir / "sample.wav", waveform, sr)

    result = runner.invoke(
        app,
        [
            "slice", str(src_dir), str(dst_dir),
            "--sample-rate", "16000",
            "--min-length", "500",
            "--threshold", "-40",
        ],
    )

    assert result.exit_code == 0
    out_files = sorted(dst_dir.glob("sample_*.wav"))
    assert len(out_files) >= 2
```

GREEN: `commands/slice.py`에서 input_dir 순회 → `load_audio` → `Slicer().slice` → `save_chunk`.

## REFACTOR 게이트

- **4-0**: `Slicer.slice`가 전체를 한 큰 함수로 GREEN됐을 것. 4-1에서 추출.
- **4-1**: `_rms_curve`, `_find_silence_regions`, `_merge_short_chunks` 추출. 매직 넘버(20, 300, 5000) → 모두 `__init__` 파라미터로 이미 끌어올림 ✅
- **4-2 (ODP 게이트)**:
  - `Slicer`는 Service인가? — 의존성(`sr` 등 설정값)을 받고, 상태 없이 메서드 호출 ✅. 단 "설정값"을 의존성으로 봐도 되는지 토론 가치 있음.
  - `Chunk`는 Value Object인가? — `np.ndarray`는 mutable이라 frozen이어도 깊은 불변성은 깨짐. 학습 포인트로 명시.
  - IO는 클래스로 묶지 않음 → 자유 함수 ✅
- **4-3**: 아직 패턴 신호 없음. 강제로 Strategy 같은 거 도입하지 말 것.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `Slicer` | **Service** | 설정 의존성 주입, 상태 없음, 메서드 호출당 동일 입력→동일 출력 |
| `Chunk` | **Value Object (얕은)** | numpy 배열 때문에 깊은 불변성은 없음 — 회고에 명시 |
| `load_audio` / `save_chunk` | 자유 함수 | seam 명확. 테스트에서 직접 합성 waveform 만들면 호출 안 해도 됨 |
| `normalize_chunk(chunk, max_amp, alpha)` | 자유 함수 | 정규화는 알고리즘 외부 단계. `Slicer`에 욱여넣지 않고 별도 함수 — 단위 테스트도 별도 |
| `slice` Typer 커맨드 함수 | 자유 함수 (entry) | 위 객체들을 조합. 비즈니스 로직 들어가지 않게 주의 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   ├── slicing/
│   │   ├── __init__.py
│   │   ├── slicer.py               ← user types
│   │   └── io.py                   ← user types
│   ├── commands/
│   │   ├── __init__.py
│   │   └── slice.py                ← user types (얇은 어댑터: 인자 파싱 + slicing.* 호출)
│   └── cli.py                      ← edit: register slice command
└── tests/
    ├── unit/
    │   └── test_slicer.py          ← user types
    └── integration/                ← ★ 첫 등장
        ├── __init__.py             ← user types (빈 파일)
        └── test_slice_command.py   ← user types
```

## 완료 기준

- [ ] 시나리오 A~E 모두 통과
- [ ] `voxprep slice <real_dir> <out_dir>` 실제 오디오로 한 번 동작 확인
- [ ] Rich Progress가 파일 단위로 카운트 표시
- [ ] `Slicer.slice`가 numpy array만 받고 파일을 만지지 않음 (seam 검증)
- [ ] `learnings/phase03-qa.md` + `learnings/phase03-{topic}.md` 회고
- [ ] 커밋:
  - `feat: add Slicer service for silence-based audio chunking`
  - `feat: add slice command with rich progress`
  - (필요 시) `refactor: split Slicer.slice into rms / silence / merge helpers`
- [ ] **`voxprep/GPT-SoVITS/tools/slicer2.py`와 `tools/slice_audio.py` 삭제** (리라이트 완료)

## 주의사항 / 엣지케이스

- **librosa 의존성**: `pyproject.toml`에 추가해야 함 — Phase 03 진입 시 `pip install -e .` 재실행. soundfile만으로 가능하다면 그쪽이 가벼움.
- **부동소수 일치 비교 금지**: 합성 waveform 테스트에서 `start_sample`을 정확한 정수값과 비교하면 hop_size 양자화 때문에 깨짐. `>=` 또는 허용 오차 사용.
- **`np.ndarray` dtype**: float32로 통일. int16 입력 들어오면 첫 단계에서 변환.
- **모노/스테레오**: 스테레오 입력은 어떻게 처리할지 결정. 원본 `slicer2.py`는 양쪽 채널 평균을 RMS 입력으로 씀. 우리도 같이 가는 게 호환.
- **출력 파일명 충돌**: `{stem}_{start}_{end}.wav`로 시작 샘플을 포함하면 한 파일 내 충돌 없음. 다른 입력 파일이 같은 stem이면 충돌 가능 — input_dir 평면 순회만 한다고 명시.
- **Typer Path 타입**: `typer.Argument(..., exists=True, file_okay=False, dir_okay=True)` 같은 옵션을 활용하면 입력 검증이 공짜로 따라옴 — 학습 포인트.
- **GPT-SoVITS 삭제 시점**: 테스트 통과 + 회고 작성 후. 절대 그 전에 지우지 말 것 (참조 잃음).

## 다음 Phase 준비

Phase 04는 ASR(faster-whisper) 래퍼를 만듭니다. 시작 전 읽어둘 것:

1. `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py` 전체
2. `voxprep/GPT-SoVITS/tools/asr/config.py` (`asr_dict`)
3. `faster-whisper` 라이브러리의 `WhisperModel.transcribe()` 시그니처
4. 우리 `ListEntry.from_line` (Phase 02)이 ASR 출력의 round-trip을 보장해야 함을 다시 확인
