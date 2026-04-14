# Phase 01 — 부트스트랩 (Typer + pytest)

## 학습 목표

- `pyproject.toml` 기반 editable 설치(`pip install -e .`)로 패키지 + CLI 엔트리포인트가 만들어지는 흐름 체득
- Typer `CliRunner`를 이용한 CLI 테스트의 첫 사이클 (RED → GREEN → REFACTOR) 한 번 완주
- "테스트가 코드를 끌어낸다"의 첫 체험: `ModuleNotFoundError → ImportError → AttributeError → AssertionError` 진화 보기
- 학습 대상 코드 / 인프라 파일의 작성 책임 분리 감각 (사용자가 직접 타이핑 vs Claude 직접 Write)

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| Typer 앱 진입점 패턴 | `claude-code-study/entrypoints/cli.tsx` (TypeScript) | 빠른 경로(`--version`)와 일반 경로의 분기 구조 참고 |
| 커맨드당 파일 1개 | `claude-code-study/cli/handlers/agents.ts` | 가장 단순한 handler — voxprep `commands/version.py`(가상)의 모델 |
| Typer 공식 튜토리얼 | https://typer.tiangolo.com/tutorial/ | 데코레이터, `CliRunner` 사용법 |

## 구현 범위

### 만들 것

1. `pyproject.toml` — 패키지 메타 + Typer/Rich/pytest 의존성 + `[project.scripts]`로 `voxprep` 엔트리포인트
2. `src/voxprep/__init__.py` — `__version__ = "0.0.1"` (단일 진실 원천)
3. `src/voxprep/cli.py` — Typer `app` 인스턴스 + `version` 커맨드 1개
4. `tests/__init__.py`, `tests/unit/__init__.py`
5. `tests/unit/test_version.py` — Typer `CliRunner`로 `voxprep version` 호출 → stdout에 버전 문자열 포함 검증

### 미루는 것 (다음 Phase로)

- `slice` / `asr` / `review` / `prep` 커맨드 함수 자체 (Phase 03~10)
- 서브패키지 (`commands/`, `parsing/`, `review/`) 생성 — 아직 빌 거라 만들 필요 없음
- 타입체커 / 린터 설정 — 학습 흐름 끊기지 않게 나중에

## TDD 사이클 시나리오

> Claude는 각 단계에서 **스니펫만 보여주고** 사용자에게 타이핑을 요청합니다. `pyproject.toml`은 Claude가 직접 Write OK.

### Step 0 — 인프라 (Claude 직접 Write OK)

`pyproject.toml` 작성. 핵심 키:
- `[project] name = "voxprep"`, `version = "0.0.1"`, `requires-python = ">=3.10"`
- `dependencies = ["typer>=0.12", "rich>=13", "prompt_toolkit>=3"]`
- `[project.optional-dependencies] dev = ["pytest>=8"]`
- `[project.scripts] voxprep = "voxprep.cli:app"`
- `[tool.setuptools.packages.find] where = ["src"]`

작성 후 `pip install -e ".[dev]"` 실행을 사용자에게 요청.

### Step 1 — RED 시작 전: 빈 디렉토리 만들기

사용자에게 요청:
```bash
mkdir -p src/voxprep tests/unit
```

### Step 2 — RED: 첫 테스트 작성

`tests/unit/test_version.py` — 사용자에게 다음 스니펫을 보여주고 타이핑하게 함:

```python
from typer.testing import CliRunner

from voxprep.cli import app

runner = CliRunner()


def test_version_command_prints_package_version():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.0.1" in result.stdout
```

설명할 것:
- `CliRunner.invoke(app, [...])`는 Typer 앱을 in-process로 호출 — subprocess 안 띄움
- `result.exit_code == 0`은 "정상 종료" 검증, `result.stdout`에 출력 검증
- 이 테스트가 실패할 이유 4가지(`voxprep` 모듈 없음 → `app` 없음 → `version` 커맨드 없음 → 출력 문자열 불일치)를 RED 진화로 보게 됨

`pytest tests/ -v` 실행 → `ModuleNotFoundError: No module named 'voxprep'` 확인.

### Step 3 — RED 진화 1: 패키지 껍데기

사용자에게 요청:
```python
# src/voxprep/__init__.py
__version__ = "0.0.1"
```

다시 `pytest` → 이번엔 `ImportError: cannot import name 'app' from 'voxprep.cli'` 또는 `ModuleNotFoundError: voxprep.cli`.

### Step 4 — RED 진화 2: cli.py 껍데기

`src/voxprep/cli.py`:

```python
import typer

app = typer.Typer(help="voxprep — GPT-SoVITS preprocessing CLI")
```

다시 `pytest` → `version` 커맨드가 없어서 exit_code != 0 (Typer가 "No such command" 출력) → AssertionError. 진짜 RED 도착.

### Step 5 — GREEN: 최소 구현

`src/voxprep/cli.py`에 추가:

```python
from voxprep import __version__


@app.command()
def version() -> None:
    """Print voxprep version."""
    typer.echo(__version__)
```

`pytest` → ✅ 통과.

**커밋 분리**:
- `feat: add version command and CLI bootstrap` (cli.py + test)
- 단, pyproject.toml과 패키지 init은 같은 커밋에 묶어도 됨 — 부트스트랩이라 분리 가치 낮음

### Step 6 — REFACTOR (있다면)

이 Phase의 GREEN 코드는 너무 작아서 거의 리팩터링할 게 없음. 단, 다음을 점검:

- **4-0 (테스트 품질)**: 테스트가 화이트박스가 아닌가? — `result.stdout`만 보고 있음 ✅
- **4-1 (코드 냄새)**: 매직 문자열? `__version__` 단일 진실 원천 사용 ✅
- **4-2 (ODP 게이트)**: `app`은 Typer가 제공하는 객체, `version()`은 함수형 — 아직 사용자 정의 객체가 없으니 분류 적용 대상 없음
- **4-3 (패턴 신호)**: 없음

> **이 Phase의 ODP 메모**: 아직 도메인 객체가 없습니다. Phase 02부터 Value Object가 등장합니다.

## 파일 구조 (Phase 종료 시)

```
voxprep/
├── pyproject.toml              ← Claude write
├── src/voxprep/
│   ├── __init__.py             ← user types
│   └── cli.py                  ← user types
└── tests/
    ├── __init__.py             ← user types (빈 파일)
    ├── conftest.py             ← user types (빈 파일, Phase 04에서 채워짐)
    └── unit/
        ├── __init__.py         ← user types (빈 파일)
        └── test_version.py     ← user types
```

> `conftest.py`는 Phase 01에서는 빈 파일로만 만들어 둡니다. pytest가 자동 인식하는 자리이고, 공유 fixture가 등장할 때(Phase 04 이후) 채워집니다. `tests/integration/`과 `tests/fixtures/`는 Phase 03/04에서 처음 등장하므로 지금 만들지 않습니다 — 필요해질 때 생성.

## 완료 기준

- [ ] `pip install -e ".[dev]"` 성공
- [ ] `tests/conftest.py`(빈 파일) 생성 — Phase 04 fixtures 도입의 자리 확보
- [ ] `pytest tests/ -v` 1 passed
- [ ] `voxprep version` 실행 시 `0.0.1` 출력
- [ ] `voxprep --help` 실행 시 `version` 커맨드 표시
- [ ] `learnings/phase01-qa.md`에 본 Phase에서 나온 질문/답변 기록
- [ ] `learnings/phase01-bootstrap.md` 회고 작성 (감상 + 가장 인상적이었던 한 가지)
- [ ] 커밋: `feat: bootstrap voxprep cli with version command`

## 주의사항 / 엣지케이스

- **`src/` 레이아웃 함정**: editable 설치 없이 `pytest`를 돌리면 `import voxprep` 실패. `pip install -e .`이 선행되어야 함.
- **`typer.echo` vs `print`**: `CliRunner`는 `typer.echo`/`print` 둘 다 캡처 가능하지만, Typer 컨벤션은 `typer.echo`. 일관성 위해 `typer.echo` 사용.
- **`__version__` 두 곳에 적지 말기**: `pyproject.toml`의 `version`과 `src/voxprep/__init__.py`의 `__version__` 둘 다 `"0.0.1"`로 적고 있다는 게 신경 쓰일 수 있음. 학습 흐름 우선 — `importlib.metadata.version` 같은 동기화 트릭은 Phase 외 주제로 미루기.
- **`tests/__init__.py`를 만드는 이유**: pytest는 없어도 동작하지만, `__init__.py` 있는 쪽이 `from tests.helpers import ...` 같은 미래 import에 자유롭다. 학습용으론 만들고 가는 게 안전.

## 다음 Phase 준비

Phase 02에서 `.list` 파일 포맷을 Value Object로 모델링합니다. Phase 01 종료 시점에 `voxprep/GPT-SoVITS/tools/asr/fasterwhisper_asr.py`의 `.list` 출력 라인(약 136번째 줄)을 한 번 훑어두면 Phase 02 시작이 매끄럽습니다.
