# voxprep

[![English](https://img.shields.io/badge/lang-English-blue)](README.md)

> GPT-SoVITS 데이터셋 전처리 CLI, **없었던 `review` 단계까지 함께** — `slice → asr → review → prep` 루프를 터미널에서 실제로 쓸 만한 물건으로 만들기 위해 TDD로 다시 짠 프로젝트입니다.

> [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) (MIT) 위에 올라간 프로젝트입니다. 학습·추론은 원본이 맡고, voxprep은 그 앞단의 전처리 루프만 다시 짓습니다.

## Highlights

- **GPT-SoVITS에 없는 `review` 단계** — ASR 결과를 사람이 검수하는 대화형 TUI. 인라인 편집, 삭제/undo, 문제 있는 줄 자동 플래그(빈 텍스트·감탄사·짧은 잡음) 포함
- **제대로 된 CLI 루프** — `slice → asr → review → prep`을 터미널에서 조합 가능. 브라우저 불필요, WebUI 드롭다운 대신 합리적 기본값
- **열 개의 Phase를 하나씩** — 엄격한 Red-Green-Refactor 사이클. 모든 패턴은 구체적인 Force가 요구할 때만 도입됩니다
- **macOS Apple Silicon을 일차 환경으로** — 기본값(`--language ko`, `--model-size large-v3-turbo`, CTranslate2용 CPU)은 WebUI 기본값이 아니라 제가 실제로 쓰는 환경을 반영합니다
- **AI 활용, 사용자 직접 타이핑** — Claude는 튜터, 저는 `src/voxprep/**`와 `tests/**`의 모든 줄을 손으로 타이핑. Q&A와 함정은 [`learnings/`](learnings/)에 실시간으로 누적

> **현재 진행 상황**: Phase 02 진행 중. `version` 커맨드는 동작합니다. `.list` 파서는 시나리오 D/7까지 완료(수동 `__eq__`/`__hash__`로 구현한 Value Object, 커스텀 예외 포함). 나머지 CLI는 아직 계약(contract)입니다 — [로드맵](#로드맵--10-phase)에서 예정된 내용을 확인하세요.

---

## 왜 만들었나

GPT-SoVITS는 음성 합성 모델을 학습시키는 데 필요한 모든 것을 제공합니다 — **반복적인 데이터셋 작업을 견딜 만하게 만들어 주는 전처리 프런트엔드**만 빼고요. 원본은 WebUI와 반(半)독립적인 스크립트들(`slicer2.py`, `fasterwhisper_asr.py`, `1-get-text.py`)로 구성되어 있고, 각자 버튼·드롭다운·가정을 따로 가지고 있습니다.

실제로 쓰면서 반복적으로 부딪힌 마찰 두 가지:

1. **CLI 루프가 깨져 있다.** 파일 한 배치에 대해 `slice → asr → review → prep`을 돌리려고 브라우저를 열 이유가 없습니다. 기존 도구는 탭 전환을 계속 요구하고, 조합이 안 되고, 기본값이 참조 구성에 맞춰져 있어 매번 같은 플래그를 다시 입력해야 합니다.
2. **`review` 단계가 아예 없다.** Whisper의 ASR 결과는 `.list` 파일(`audio_path|speaker|language|text`)로 떨어지고, 이걸 어떻게 편집해야 할까요? `vim`으로 수백 줄을 스크롤하면서 `|` 구분자를 깨뜨리지 않기를 기도하면서? 놓친 ASR 오인식은 학습이 한참 진행된 뒤에야 드러납니다.

그래서 전처리 파이프라인을 제대로 된 CLI로 다시 짓고, **있었어야 할 `review` 단계를 직접 추가**합니다 — 키보드 중심, 인라인 오디오 재생, 인라인 편집, 삭제/undo, 문제 줄 자동 플래그까지.

실용 목적과 나란히, 이 프로젝트는 **TDD Red-Green-Refactor**(Kent Beck)와 **Object Design Practices**(Matthias Noback의 46규칙)를 체화하는 자리이기도 합니다. 모든 줄은 실패하는 테스트를 먼저 거치고, 모든 패턴은 Force로 정당화된 뒤에야 도입되며, 중요한 모든 결정은 [`learnings/DISCOVERIES.md`](learnings/DISCOVERIES.md)에 근거와 함께 기록됩니다.

---

## 어떻게 학습하나

```
1. Phase 가이드 읽기 (docs/phases/phaseNN-*.md) — 범위 + 학습 목표
       ↓
2. 해당 Phase가 리라이트하는 GPT-SoVITS 원본 코드 읽기 (예: tools/slicer2.py)
       ↓
3. Claude가 RED 테스트 스니펫 제공, 저는 tests/에 직접 타이핑
       ↓
4. RED 진화 관찰:
   ModuleNotFoundError → ImportError → AttributeError → AssertionError
       ↓
5. GREEN으로 가는 최소 코드 — 섣부른 추상화 금지, if/else도 괜찮음
       ↓
6. REFACTOR 게이트 — 테스트 품질, 코드 냄새, ODP 분류, 패턴 신호
       ↓
7. learnings/phaseNN-qa.md에 Q&A, learnings/DISCOVERIES.md에 발견 기록
       ↓
8. Tidy First 커밋 분리 — feat: / refactor: / docs: / chore:
```

> **코드는 제 것, Claude는 튜터입니다.** `src/voxprep/`와 `tests/`의 모든 줄을 손으로 타이핑합니다. Claude는 인프라와 문서 파일(`pyproject.toml`, `CLAUDE.md`, `docs/phases/*.md`)만 직접 작성합니다.

---

## 로드맵 — 10 Phase

| # | Phase | 산출물 | 처음 등장하는 ODP 객체 | 상태 |
|---|-------|--------|----------------------|------|
| 01 | 부트스트랩 — Typer + pytest | `voxprep version` | *(아직 없음 — 어댑터만)* | ✅ |
| 02 | `.list` 파서 | `ListEntry` + `read/write_list_file` | **Value Object** | 🔄 |
| 03 | `slice` 커맨드 | `voxprep slice <in> <out>` | **Service** (`Slicer`) | ⏳ |
| 04 | `asr` 커맨드 | `voxprep asr <dir>` | Service + DI + fake 더블 | ⏳ |
| 05 | `review` — 내비게이션 | `voxprep review` (`n`/`b`/`q`) | **Entity** (커서 상태) | ⏳ |
| 06 | `review` — 오디오 재생 | `Enter`로 재생 | subprocess seam | ⏳ |
| 07 | `review` — 인라인 편집 | `e`로 편집 | prompt_toolkit `default=` | ⏳ |
| 08 | `review` — 삭제 + undo | `d` / `u` | **Command** 패턴 도착 | ⏳ |
| 09 | `review` — 자동 플래그 | `--auto-prune` 모드 | 규칙 집합 응집 | ⏳ |
| 10 | `prep` 파이프라인 | `voxprep prep <raw>` | Rich Live 조합 | ⏳ |

범례: ✅ 완료 · 🔄 진행 중 · ⏳ 예정

각 Phase는 [`docs/phases/`](docs/phases/)에 가이드가, [`learnings/phaseNN-qa.md`](learnings/)에 Q&A가, [`learnings/DISCOVERIES.md`](learnings/DISCOVERIES.md)에 Phase를 가로지르는 원칙이 누적됩니다.

---

## `.list` 포맷

리라이트 대상(GPT-SoVITS)과 voxprep이 공유하는 포맷이며, ASR 결과가 학습으로 넘어가는 통로입니다:

```
audio_path|speaker_name|language|text
```

- `|`로 구분된 4 필드 (`text` 안에 파이프 포함 시 양방향 모두 파싱 에러)
- UTF-8, 줄바꿈 구분, **파일 끝 개행 없음** (원본의 `"\n".join(...)`과 일치)
- 언어 코드는 **파서 경계에서 소문자로 정규화** — 근거는 [경계에서 정규화 원칙](learnings/DISCOVERIES.md) 참고

이 파서가 voxprep의 첫 Value Object이자 "데이터는 경계에서 검증한다" 원칙이 처음 강제되는 자리입니다.

---

## 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| **언어** | Python 3.12 | `.python-version`으로 고정 |
| **CLI** | Typer 0.24 | 서브커맨드 그룹, 자동 `--help` |
| **터미널 출력** | Rich 15 | 컬러, 테이블, subprocess 스트리밍용 `rich.progress.Progress` |
| **대화형 입력** | prompt_toolkit 3 | Phase 07에서 `default=` 기반 인라인 편집 |
| **테스트** | pytest 9 + Typer `CliRunner` | 단위 + 통합(`tmp_path` e2e) |
| **패키지 관리** | [uv](https://github.com/astral-sh/uv) | `uv sync` + `uv.lock`, project 모드 |
| **리라이트 원본** | [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | `tools/`와 `GPT_SoVITS/prepare_datasets/`를 직접 읽음 |

**Phase 04 이후 의존성**(`faster-whisper`, `ctranslate2`, `torch`)은 ASR Phase에 들어갈 때 `uv add`로 추가합니다. 그 전까지는 의존성 풋프린트가 의도적으로 작습니다.

---

## 프로젝트 구조

현재 상태 — Phase 01~02 일부 완료. 이후 Phase는 아래 트리에서 Phase 번호가 표시된 디렉토리에 추가됩니다:

```
voxprep/
├── src/voxprep/
│   ├── __init__.py              # __version__ (단일 진실 원천)
│   ├── cli.py                   # Typer 앱 + version 커맨드        Phase 01 ✅
│   ├── parsing/                 # .list 파서                       Phase 02 🔄
│   │   ├── list_file.py         #   ListEntry Value Object
│   │   └── errors.py            #   MalformedListLineError
│   ├── commands/                #   서브커맨드별 얇은 어댑터       Phase 03+
│   ├── slicing/                 #   slicer2 리라이트                Phase 03
│   ├── transcription/           #   faster-whisper 래퍼             Phase 04
│   ├── review/                  #   대화형 TUI                     Phase 05~09
│   └── pipeline/                #   prep 올인원                    Phase 10
│
├── tests/
│   ├── conftest.py
│   ├── unit/                    # 빠른 in-process 테스트
│   │   ├── test_version.py
│   │   └── test_list_parser.py
│   └── integration/             # CliRunner + tmp_path e2e          Phase 03+
│
├── docs/                        # Claude 저작 — 스펙과 가이드
│   ├── README.md                # 10-Phase 로드맵 (상태 포함)
│   └── phases/
│       ├── phase01-bootstrap.md
│       ├── phase02-list-parser.md
│       └── ... (phase03~10)
│
├── learnings/                   # 사용자 저작 — 진짜 산출물
│   ├── README.md                # 학습 맵 (Phase → 2줄 요약)
│   ├── phase01-qa.md            # Phase별 Q&A
│   ├── phase02-qa.md
│   └── DISCOVERIES.md           # 함정 + 설계 원칙 (Phase 경계 초월)
│
├── CLAUDE.md                    # Claude용 튜터 모드 계약
├── .python-version              # 3.12
├── pyproject.toml               # [dependency-groups].dev, [project.scripts]
└── uv.lock                      # 재현성을 위해 추적
```

---

## 실행

**요구 사항:** [uv](https://docs.astral.sh/uv/). 필요하면 uv가 Python 3.12를 자동 설치합니다.

```bash
git clone https://github.com/tomato-data/voxprep.git
cd voxprep
uv sync

# 테스트 실행
uv run pytest tests/ -v

# CLI 실행 (현재는 version 커맨드만 연결됨)
uv run voxprep --help
uv run voxprep version
# → 0.0.1
```

Phase 04 이후로는 `uv add`로 `faster-whisper` 등이 들어옵니다. 그 전까지는 설치가 분 단위가 아니라 초 단위입니다.

---

## 읽는 순서 (학습 목적으로 오셨다면)

이 레포에서 가장 흥미로운 경로는 **아직 코드가 아닙니다** — 코드는 진행 중이거든요. 의미 있는 경로는 **방법론 + 여정**입니다:

1. [`CLAUDE.md`](CLAUDE.md) — 튜터 모드 계약, CLI 일차성 프레이밍, Tidy First 규칙, "설정 노브는 SETUP_GUIDE에" 방침
2. [`docs/README.md`](docs/README.md) — 10-Phase 로드맵
3. [`docs/phases/phase01-bootstrap.md`](docs/phases/phase01-bootstrap.md) — Phase 가이드가 어떻게 생겼는지, RED 진화 시나리오 포함
4. [`learnings/phase01-qa.md`](learnings/phase01-qa.md) — Phase 01에서 실제로 제가 던진 질문들 (`CliRunner` 내부 동작, exit code의 HTTP status 비유, 왜 지금 uv로 갈아타는가)
5. [`learnings/DISCOVERIES.md`](learnings/DISCOVERIES.md) — Phase 경계를 가로지르는 함정과 설계 원칙. Phase 01의 Typer 함정 두 개와 Phase 02의 "경계에서 정규화" 원칙이 모두 여기 있습니다
6. 로드맵이 ✅로 바뀌는 걸 따라오세요

git log도 일부러 읽을 만하게 만들었습니다 — 모든 커밋이 Tidy First 단위입니다 (`feat:` 행동 변경, `refactor:` 구조 변경, `docs:` 회고/원칙, `chore:` 인프라). 혼합 커밋은 없습니다.

---

## 크레딧

voxprep은 [RVC-Boss](https://github.com/RVC-Boss)와 기여자들이 만든 **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)**의 전처리 프런트엔드를 다시 작성한 프로젝트입니다. GPT-SoVITS는 MIT 라이선스(Copyright © 2024 RVC-Boss)로 공개되어 있습니다. voxprep의 파일 포맷·알고리즘·기본값은 모두 GPT-SoVITS에서 가져왔습니다 — 특히 `tools/slicer2.py`의 분할 로직, `tools/asr/fasterwhisper_asr.py`의 ASR 래퍼, `GPT_SoVITS/prepare_datasets/1-get-text.py`의 `.list` 소비 코드를 직접 읽으며 각 Phase를 작성했습니다. GPT-SoVITS의 소스는 이 레포지토리에 포함·배포되지 않으며, 개발 중 참조용으로만 사용합니다.

voxprep이 쓸 만하셨다면 원본 GPT-SoVITS에도 스타 한 번 눌러 주시면 좋겠습니다. 무거운 작업인 학습과 추론은 전부 그쪽이 하고, voxprep은 그 앞에 붙는 전처리 단계를 터미널에서 덜 귀찮게 만든 것뿐입니다.

---

## 참고 자료

- **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** — 리라이트 대상. `tools/slicer2.py`, `tools/asr/fasterwhisper_asr.py`, `GPT_SoVITS/prepare_datasets/1-get-text.py`가 각 Phase 가이드와 함께 읽는 핵심 파일
- **Object Design Style Guide** — Matthias Noback. 서비스·엔티티·Value Object·메서드·아키텍처·테스팅에 대한 46가지 규칙
- **Test Driven Development: By Example** — Kent Beck. Red-Green-Refactor 사이클과 "테스트가 곧 명세"
- **Tidy First?** — Kent Beck. 구조 변경과 행동 변경을 커밋 단위에서 분리
- **[Typer](https://typer.tiangolo.com/)**, **[Rich](https://rich.readthedocs.io/)**, **[prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)** — CLI craft 3종 세트
- **[uv](https://docs.astral.sh/uv/)** — pip + venv + pyenv를 하나로 합친 빠른 패키지/프로젝트 매니저

---
