# voxprep — GPT-SoVITS 전처리 CLI를 만들며 Typer + TDD + ODP 체화

이 파일은 Claude Code가 이 리포지토리에서 작업할 때 따르는 지침입니다. **학습 목적 프로젝트**로, 실제로 돌아가는 CLI를 만드는 것이 목표이지만 코드만큼이나 **체화 과정** 자체가 산출물입니다.

## 프로젝트 목적

GPT-SoVITS의 학습/추론은 기존 코드를 그대로 쓰되, 그 앞단의 **데이터셋 전처리 파이프라인**(`slice` → `asr` → `review` → `prep`)을 처음부터 다시 작성합니다. 원본은 WebUI 중심이라 CLI 루프가 불편했고, 특히 ASR 결과를 사람이 검수하는 `review` 단계가 없어 직접 만들어야 했습니다.

이 과정에서 체화할 것:

- **Typer + Rich + prompt_toolkit**을 활용한 대화형 CLI 설계
- **TDD Red-Green-Refactor** — 테스트가 코드를 이끌게 하기
- **ODP(Object Design Practices) 46규칙** — Service / Entity / Value Object / DTO 분류 체득
- 기존 코드(`voxprep/GPT-SoVITS/`)를 **참조 자료**로 읽으며 새로 짜는 리라이트 경험

---

## 협업 방식

> ⚠️ **학습 모드 — 사용자가 직접 코드와 테스트를 타이핑합니다. Claude는 튜터입니다.**

- **Claude는 학습 대상 파일에 Write/Edit하지 않습니다.** 코드 스니펫은 메시지에 보여주고, 사용자가 보고 직접 입력합니다.
- **예외 — 인프라/메타 파일**: `.gitignore`, `pyproject.toml`, `CLAUDE.md`, `docs/**/*.md` 같이 학습 대상이 아닌 파일은 Claude가 직접 작성해도 OK.
- **매 스텝마다 학습 맥락 설명**:
  1. 지금 TDD 사이클의 어느 단계인지 (RED / GREEN / REFACTOR)
  2. 이 코드가 어떤 ODP 규칙과 연결되는지
  3. 왜 이 순서로 하는지
- **테스트 의도 설명 필수** — 각 테스트가 무엇을 왜 검증하는지, 핵심 assertion이 무엇을 보는지
- **코드 예시는 영어**로 작성 (한영 전환 부담 방지). 설명은 한국어 OK.
- **에러/버그는 학습 기회** — 정답만 주지 말고 원인 메커니즘을 설명

---

## 핵심 원칙

### 1. "일단 직설적으로 만들자"

이 프로젝트는 패턴 체화보다 **돌아가는 CLI를 끝까지 가져가는 것**이 먼저입니다. 패턴 이름을 먼저 꺼내지 말고, `if/else`로 시작하세요. 고통이 생기면 그때 추출합니다. 각 Phase 문서에 "언제 리팩터로 넘어갈지" 기준을 적어둡니다.

### 2. TDD Red-Green-Refactor

실패 메시지가 다음 할 일의 명세서입니다. Phase마다 GREEN 커밋과 REFACTOR 커밋을 분리합니다 (Tidy First).

**RED 에러 진화**:
```
ModuleNotFoundError  → 모듈 파일 생성
ImportError          → 클래스/함수 껍데기
AttributeError       → 메서드 껍데기 (pass)
TypeError (missing)  → 파라미터 추가
AssertionError       → ✅ 진짜 RED. GREEN으로
```

**허위 GREEN 주의** — 테스트가 통과해도 "올바른 이유"로 통과했는지 확인.

### 3. ODP 객체 분류 — 4분류 판단

| 분류 | 특성 | 불변성 |
|------|------|--------|
| **Service** | 상태 없음, 의존성 주입 | 절대 불변 |
| **Entity** | ID로 식별, 상태 변경 | 규칙 하 가변 |
| **Value Object** | 값으로 식별, 불변 | 절대 불변 |
| **DTO** | 경계 전송용 | 제약 없음 |

판단 질문:
1. 생성 후 내부 상태가 바뀌는가? → **Entity**
2. `__eq__`가 값 비교인가? → **Value Object**
3. 생성자에 의존성을 받는가? → **Service**
4. 외부 경계에서만 쓰이는가? → **DTO**

46규칙 상세: `~/.claude/skills/object-design-practices/`

### 4. Tidy First — 구조/행동 분리 커밋

- `feat:` = 행동 변경 (기능 추가/수정)
- `refactor:` = 구조 변경 (동작 불변)
- `test:` = 테스트 추가/수정
- 한 커밋에 두 종류를 섞지 않습니다. GREEN 직후 REFACTOR는 별도 커밋.

### 5. 설정 노출 원칙 — "업스트림 노브는 모두 CLI에, 기본값은 SETUP_GUIDE에"

GPT-SoVITS는 단계별로 의미 있는 설정값들을 노출합니다 (slice의 `threshold/min_length/max/alpha`, asr의 `language/model_size/precision/vad`, 등). voxprep은 이 노브들을 **숨기지 않습니다**.

- 각 단계 커맨드(`slice`, `asr`)는 업스트림에 존재하는 모든 의미 있는 옵션을 Typer 플래그로 노출합니다.
- **기본값의 진실 원천**: `voxprep/GPT-SoVITS/docs/ko/SETUP_GUIDE.md`. 사용자가 직접 ASMR 한국어 데이터셋으로 검증한 macOS(Apple Silicon) 설정. WebUI 기본값과 동일한 항목은 "기본값 유지", 사용자가 명시 변경한 항목(`--language ko`, `--model-size large-v3-turbo` 등)은 그 값을 voxprep 기본으로.
- **언어(language)는 특히 중요** — `asr`/`prep`의 `--language` 기본값은 **`ko`**. 다른 언어 데이터셋은 명시 전달.
- **macOS 가정** — 1차 사용 환경. `--device auto`는 cuda 없으면 cpu, MPS는 CTranslate2 미지원이라 cpu로. 훈련 단계는 voxprep 범위 외지만 SETUP_GUIDE 5절은 CPU 권장.
- 옵션이 폭발하면 (10+) `--config <toml>` 도입을 검토하지만, 1차 GREEN에서는 그냥 플래그로 갑니다. 패턴 도착은 고통이 발생한 뒤에.
- 새로운 단계/도구를 voxprep에 가져올 때는 **먼저 SETUP_GUIDE.md와 원본의 argparse/UI dropdown을 직접 읽어** 어떤 노브가 노출되어 있고 사용자가 어떤 값을 썼는지 확인한 뒤, 그 목록 그대로 가져오는 것이 기본입니다.

---

## 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| 언어 | Python 3.10+ | |
| CLI | Typer | 서브커맨드, 자동 help |
| 터미널 출력 | Rich | 컬러, 테이블, progress |
| 대화형 입력 | prompt_toolkit | Phase 07 인라인 편집 |
| 테스트 | pytest + Typer `CliRunner` | |
| 패키지 관리 | pip (editable) | `pip install -e .` |
| 가상환경 | `GPT-SoVITS/.venv` 공유 | 새로 만들지 않음 |

---

## 명령어

```bash
# 가상환경 활성화 (GPT-SoVITS와 공유)
source GPT-SoVITS/.venv/bin/activate

# editable 설치 (Phase 01에서 최초)
pip install -e .

# 테스트
pytest tests/ -v
pytest tests/unit/test_list_parser.py::test_parses_single_line -v

# CLI
voxprep --help
voxprep version
voxprep slice <input_dir> <output_dir>
voxprep asr <output_dir>
voxprep review <list_file>
voxprep prep <raw_dir>
```

---

## 프로젝트 구조

claude-code-study(TypeScript CLI 바이블)를 전체 탐색해 추출한 패턴을 Python/Typer에 맞게 단순화했습니다. 핵심 원칙:

- **`commands/`는 얇은 어댑터** — 인자 파싱 + 도메인 객체 조립 + `run_*_pipeline()` 호출만. 비즈니스 로직 X (claude-code-study `cli/handlers/*.ts` 패턴)
- **도메인별 패키지** — `parsing/`, `slicing/`, `transcription/`, `review/`, `pipeline/`. claude-code-study `services/`의 Python 등가
- **단위 vs 통합 분리** — `tests/unit/`(in-process, 빠름), `tests/integration/`(`CliRunner` + `tmp_path` e2e)
- **공유 더블/팩토리** — `tests/fixtures/`. 같은 헬퍼가 2+ 테스트 파일에 등장하면 그때 추출 (premature 금지)
- **만들지 않을 디렉토리** — `state/`, `types/`, `utils/`, `keybindings/`(풀 시스템), `screens/`. 모두 React/대규모 모놀리스 산물. Python에서는 import가 가까운 게 자연스러움

```
voxprep/
├── pyproject.toml
├── .gitignore
├── CLAUDE.md
├── src/voxprep/
│   ├── __init__.py              # __version__
│   ├── cli.py                   # Typer app + version 커맨드 (fast-path)
│   ├── commands/                # 얇은 어댑터 — 커맨드당 파일 1개
│   │   ├── __init__.py
│   │   ├── slice.py
│   │   ├── asr.py
│   │   ├── review.py
│   │   └── prep.py
│   ├── parsing/                 # Phase 02 — .list 파서 (Value Object)
│   │   ├── __init__.py
│   │   ├── list_file.py
│   │   └── errors.py
│   ├── slicing/                 # Phase 03 — slicer2 리라이트
│   │   ├── __init__.py
│   │   ├── slicer.py            # Slicer (Service)
│   │   ├── io.py                # load_audio / save_chunk
│   │   └── options.py           # SliceOptions dataclass (Phase 10 refactor 도착)
│   ├── transcription/           # Phase 04 — faster-whisper 래퍼
│   │   ├── __init__.py
│   │   ├── types.py             # Transcription VO
│   │   ├── whisper.py           # WhisperTranscriber (Service) + WhisperLike Protocol
│   │   ├── languages.py         # 99-code list, validate_language
│   │   ├── model_factory.py     # load_whisper
│   │   └── options.py           # AsrOptions dataclass (Phase 10 refactor 도착)
│   ├── review/                  # Phase 05~09 — interactive TUI
│   │   ├── __init__.py
│   │   ├── session.py           # ReviewSession (Entity)
│   │   ├── keybindings.py       # 단순 dict dispatcher (풀 시스템 X)
│   │   ├── render.py            # Rich 출력
│   │   ├── loop.py              # run_review_loop / run_auto_prune_loop
│   │   ├── player.py            # AudioPlayer Service (Phase 06)
│   │   ├── editor.py            # TextEditor Service (Phase 07)
│   │   ├── confirmer.py         # Confirmer Service (Phase 08)
│   │   └── issues.py            # 자동 플래그 검사 (Phase 09)
│   └── pipeline/                # Phase 10 — prep 올인원
│       ├── __init__.py
│       ├── workspace.py         # Workspace VO
│       └── runner.py            # slice_step / asr_step / review_step
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures (Phase 01부터 빈 파일로 준비)
│   ├── fixtures/                # 공유 더블/팩토리 (Phase 04부터 채워짐)
│   │   ├── __init__.py
│   │   ├── audio.py             # _build_two_segment_waveform 등
│   │   └── doubles.py           # FakeWhisperModel, SpyPlayer, FakeEditor, ...
│   ├── unit/                    # in-process 빠른 단위 테스트
│   │   ├── __init__.py
│   │   ├── test_version.py
│   │   ├── test_list_parser.py
│   │   ├── test_slicer.py
│   │   ├── test_whisper_transcriber.py
│   │   ├── test_review_session.py
│   │   ├── test_review_dispatcher.py
│   │   ├── test_review_editor.py
│   │   ├── test_audio_player.py
│   │   └── test_issues.py
│   └── integration/             # CliRunner + tmp_path e2e
│       ├── __init__.py
│       ├── test_slice_command.py    # Phase 03
│       ├── test_asr_pipeline.py     # Phase 04
│       ├── test_review_loop.py      # Phase 05+
│       └── test_prep_pipeline.py    # Phase 10
├── docs/                        # Claude 저작 — "지시서"
│   ├── README.md                # Phase 인덱스
│   └── phases/
│       ├── phase01-bootstrap.md
│       └── ...
├── learnings/                   # 📚 사용자 저작 — 진짜 산출물
│   ├── README.md
│   ├── phase01-qa.md
│   └── phase01-bootstrap.md
└── GPT-SoVITS/                  # 참조용 원본 (.gitignore됨. 리라이트 끝난 부분은 삭제해 나감)
```

> `learnings/`는 루트에 둡니다 (`docs/learnings/`로 중첩하지 않음). `docs/`(Claude 저작)와 `learnings/`(사용자 저작)는 소유권·목적이 다르므로 나란히.

> **차용하지 않은 패턴** (claude-code-study에서 가져오지 않음): React/Ink, `state/` + observer store(Entity 한 개로 충분), `types/` 중앙 디렉토리(Python은 import 가까이), `utils/` 전역 폴더(실제 cross-cutting 고통이 오면 그때), `keybindings/` 풀 시스템(parser/resolver/context/chord/hot-reload — `review/keybindings.py` dict 1개로 대체), `screens/` vs `components/` 분리(`review/render.py` 한 파일).

---

## Phase 로드맵

상세는 `docs/phases/phaseNN-*.md` 참조. `docs/README.md`에 인덱스.

| Phase | 제목 | 핵심 학습 포인트 |
|-------|------|-----------------|
| 01 | 부트스트랩 | TDD 최초 사이클, Typer `CliRunner`, editable install |
| 02 | `.list` 파서 | Value Object, `@dataclass(frozen=True)`, `__eq__` |
| 03 | `slice` 커맨드 | Service 분류, 파일 IO seam, subprocess 진행 표시 |
| 04 | `asr` 커맨드 | 외부 라이브러리 경계, DI, 느린 의존성 fake |
| 05 | `review` — 내비게이션 | Entity (커서 상태), 키바인딩 dispatcher |
| 06 | `review` — 오디오 재생 | subprocess seam (afplay), 크로스플랫폼 가드 |
| 07 | `review` — 인라인 편집 | prompt_toolkit `default=` 패턴, 취소/확정 분기 |
| 08 | `review` — 삭제 + undo | Command 도착 관찰, 파일 즉시 flush |
| 09 | `review` — 자동 플래그 | 규칙 집합 응집, `--auto-prune` 모드 |
| 10 | `prep` 파이프라인 | 파이프라인 조합, Rich Live로 전체 진행 표시 |

---

## 참조 코드

> ⚠️ **직접 들여다볼 것.** 각 Phase 문서에 정리된 경로/시그니처 요약은 시작점일 뿐입니다. 의문이 생기거나 디테일이 필요하면 **반드시 아래 두 디렉토리를 직접 Read/Grep으로 열어보세요.** 요약본만 믿고 추측하지 말 것 — 학습 프로젝트의 핵심은 "원본을 읽고 새로 짜는 경험"입니다.
>
> - **`voxprep/GPT-SoVITS/`** — 리라이트 대상. 알고리즘/포맷/엣지케이스의 진실 원천. Phase 02~04, 10에서 해당 파일을 직접 읽고 사용자에게 "여기 이렇게 되어 있는데 우리는 어떻게 가져갈까요?"를 묻는 것이 정상적인 흐름입니다.
> - **`/Users/eboshi/Desktop/Code/claude-code-study/`** — CLI 패턴 바이블 (TypeScript). Phase 01, 05~09에서 dispatcher/입력/렌더링 패턴이 막힐 때 직접 Read해서 구조를 보고 Python으로 이식. **이 경로는 voxprep 외부**라 default search 범위 밖이지만 절대경로로 열면 됩니다.
>
> 사용자에게 스니펫을 제시하기 전에 관련 원본을 한 번이라도 직접 확인하는 것이 권장 워크플로우입니다.

### `voxprep/GPT-SoVITS/` — 리라이트 대상 원본

각 Phase에서 해당 부분을 읽어가며 새로 작성. **재작성이 끝난 파일은 `voxprep/GPT-SoVITS/`에서 삭제**해 나가 최종적으로 훈련/추론 관련 파일만 남깁니다.

| Phase | 참조 경로 |
|-------|----------|
| 전체 | `docs/ko/SETUP_GUIDE.md` — 사용자가 직접 검증한 macOS Apple Silicon + 한국어 ASMR 워크플로우. **기본값의 진실 원천** |
| 02 | `tools/asr/funasr_asr.py:87`, `tools/asr/fasterwhisper_asr.py:136` (`.list` 생성), `GPT_SoVITS/prepare_datasets/1-get-text.py:129` (`.list` 소비) |
| 03 | `tools/slicer2.py` (`Slicer` 클래스), `tools/slice_audio.py` (CLI 진입), `webui.py` `open_slice()`, SETUP_GUIDE 3-2 (WebUI 기본값 유지) |
| 04 | `tools/asr/fasterwhisper_asr.py` (`execute_asr`), `tools/asr/config.py` (`asr_dict`), `webui.py` `open_asr()`, SETUP_GUIDE 3-3 (`large-v3-turbo` + `ko`) |
| 09 | SETUP_GUIDE 3-4 (자동 플래그 규칙의 사용자 정의 — 빈 텍스트, 감탄사, 비한국어 잡음, 3글자 이하) |
| 10 | `GPT_SoVITS/prepare_datasets/1-get-text.py`, `2-get-hubert-wav32k.py`, `3-get-semantic.py` (범위 밖이지만 흐름 이해용), SETUP_GUIDE 4절 |

**`.list` 포맷 (확정)**: `audio_path|speaker_name|language|text` — UTF-8, 줄바꿈 구분, 필드당 `|` 하나. 언어 코드는 소문자/대문자 혼재(ZH, JP, EN, KO, YUE / zh, ja, en, ko, yue).

### `/Users/eboshi/Desktop/Code/claude-code-study` — CLI 패턴 바이블 (TypeScript)

TypeScript → Python 이식. 구조와 의도만 차용:

| 참조 파일 | 의도 | voxprep 대응 |
|----------|------|-------------|
| `cli/handlers/*.ts` | 커맨드당 파일 1개, 비동기 handler | `src/voxprep/commands/*.py` + `@app.command()` |
| `entrypoints/cli.tsx` | args 라우팅, version 빠른 경로 | `src/voxprep/cli.py` Typer 앱 |
| `components/BaseTextInput.tsx` | inputState + default value + enter/escape 분기 | `prompt_toolkit.prompt(default=...)` wrapping |
| `keybindings/parser.ts`, `resolver.ts`, `KeybindingContext.tsx` | keystroke 파싱 → context-aware resolve → chord 상태 머신 | `src/voxprep/review/keybindings.py` dispatcher |
| `cli/structuredIO.ts` (참고) | 구조화된 프로세스 간 메시지 | Phase 03/04 subprocess 스트리밍은 `subprocess.Popen` + `rich.progress.Progress` 로 대체 |

---

## learnings/ 구조 (≤10 Phase — 플랫)

```
learnings/
├── README.md                  # Phase → 배운 것 매핑
├── phase01-qa.md              # Phase01 Q&A
├── phase01-bootstrap.md       # Phase01 회고
├── phase02-qa.md
└── ...
```

### Q&A 기록 형식

```markdown
### Q: 질문 내용

답변. 코드 예시가 필요하면 포함.
```

섹션은 의미 단위로: `## TDD 개념`, `## ODP`, `## Python`, `## Typer/CLI`, `## 리라이트 전략`.

### 회고 (Phase 완료 시)

`phaseNN-{topic}.md` 형식. 감상 + 가장 인상적이었던 점 + 다음 Phase로 가져갈 것.

---

## 참조

- **TDD 스킬**: `~/.claude/skills/tdd/` — `/tdd-plan`, `/go`
- **ODP 스킬**: `~/.claude/skills/object-design-practices/` — 46규칙
- **Guided Learning 스킬**: `~/.claude/skills/guided-learning/`
- **GPT-SoVITS 원본**: https://github.com/RVC-Boss/GPT-SoVITS
- **Typer 문서**: https://typer.tiangolo.com/
- **prompt_toolkit**: https://python-prompt-toolkit.readthedocs.io/
- **Rich**: https://rich.readthedocs.io/
