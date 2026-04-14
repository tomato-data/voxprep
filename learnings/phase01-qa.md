# Phase 01 — Q&A

Phase 01(부트스트랩 — Typer + pytest) 진행 중 주고받은 질문과 답변.

---

## Typer / CLI

### Q: `CliRunner`는 메인 앱을 실행할 때 쓰는 게 아니라 테스트용으로 가볍게 띄우는 목적인가요? 캡처해서 보여주는 가벼운 친구?

맞습니다. 다만 정확히 이해하려면 **"같은 `app` 객체를 양쪽이 다르게 부른다"**는 구조를 잡는 게 좋습니다.

```
사용자가 쉘에서 `voxprep version`
  → setuptools가 만든 bin/voxprep 래퍼
  → voxprep.cli:app 에 sys.argv 전달
  → Typer가 argv 파싱 → version() 실행 → stdout 출력 → 프로세스 exit

CliRunner.invoke(app, ["version"])
  → 같은 app에 ["version"] 을 넘김
  → Typer가 동일하게 파싱 → version() 실행
  → 다만 stdout/stderr 를 가로채 result 객체로 반환, 프로세스는 안 죽임
```

`CliRunner`는 "다른 실행기"가 아니라 **"같은 파이프라인의 마지막 한 마디만 캡처로 바꾼 것"**. subprocess를 띄우지 않으므로:

- 빠름 (프로세스 fork 없음)
- 디버거 붙일 수 있음
- OS 의존성 없음
- 테스트 간 격리가 runner 인스턴스 수준에서 끝남

실전 팁:

- `CliRunner(mix_stderr=False)` — stderr/stdout 분리 캡처. 에러 메시지만 따로 볼 때 유용
- `runner.invoke(app, [...], catch_exceptions=False)` — 내부 예외가 그대로 올라와 traceback 확인 가능. RED 진화 디버깅용
- `result.exception` — 마지막 예외 객체. `isinstance(result.exception, MyError)` 같은 단언 가능

---

### Q: exit code는 웹 개발로 비유하자면 exception 같은 건가요? HTTP 500 같은? + 커스텀도 할 수 있는?

**HTTP status code에 더 가깝습니다**, exception이 아니라. 이유를 정리해 두면 앞으로 헷갈릴 일이 줄어듭니다.

- **exception = 언어 내부 메커니즘.** 호출 스택을 따라 올라가고 try/except로 잡을 수 있음. 프로세스 경계를 못 넘음
- **exit code = 프로세스 경계의 통신 수단.** 정수 하나로 부모 프로세스에게 "나 어떻게 죽었어"를 알리는 것. 쉘이 `$?`로 읽고, Makefile이 빌드 실패를 감지하고, CI가 step fail을 판정하는 바로 그 값

HTTP 대응:

| HTTP | exit code |
|---|---|
| `200 OK` | `0` (success) |
| `4xx` (client error) | `2` (Typer/click 기본값 — 사용자 입력 잘못) |
| `5xx` (server error) | `1` (일반 실패) 또는 custom |
| custom status | custom code — 관례상 0~127, 128~255는 시그널용 예약 |

**exception과 exit code의 연결고리** — Typer는 중간에서 전자를 후자로 번역해 주는 어댑터입니다:

```python
raise typer.Exit(code=2)                        # 우아한 종료, exit_code=2
raise typer.BadParameter("--foo must be positive")  # Typer가 잡아 exit_code=2 + 메시지
raise RuntimeError("oops")                      # 잡히지 않음 → traceback + exit_code=1
```

FastAPI의 `HTTPException`이 파이썬 예외를 HTTP status로 번역해 내보내는 것과 **구조가 동형**입니다.

**voxprep에서 경계 잡는 법**: `raise typer.Exit(code=N)`는 `commands/*.py`(어댑터)에서만 쓴다. 도메인 객체(Value Object, Service)는 `ValueError`/`RuntimeError`/커스텀 예외를 던지고, `commands/*.py`가 그걸 잡아서 Typer exit로 번역한다. 도메인이 `typer.Exit`을 던지면 Typer에 커플링되어 테스트가 어려워진다. 이게 CLAUDE.md의 "`commands/`는 얇은 어댑터"의 실제 의미.

---

## 툴링 / 인프라

### Q: 버전 관리 uv로 하는 게 어떤가요?

**좋은 판단이고 바로 전환했습니다.** uv는 Ruff를 만든 Astral의 파이썬 패키지/프로젝트 매니저로, `pip` + `venv` + `pip-tools` + `pyenv` + `pipx`를 하나로 묶고 Rust로 다시 쓴 것.

| 기능 | pip 방식 | uv 방식 |
|---|---|---|
| 설치 속도 | 느림 | 10~100배 빠름 |
| venv 생성 | `python -m venv .venv` | `uv venv` |
| editable 설치 | `pip install -e ".[dev]"` | `uv sync` (project 모드) |
| 명령 실행 | `source .venv/bin/activate` 먼저 | `uv run pytest` — 자동 |
| 락파일 | 없음 (수동 `pip freeze`) | `uv.lock` 자동 생성, 크로스플랫폼 |
| Python 버전 | 시스템/brew/pyenv 의존 | `.python-version` 파일로 고정, uv가 직접 관리 |
| 의존성 추가 | `pip install X` + pyproject 수동 편집 | `uv add X` — 자동 반영 + lock |

voxprep에 적용한 구체 설정:

- **pyproject.toml 구조 변경**: `[project.optional-dependencies].dev` → `[dependency-groups].dev` (uv 선호 관례)
- **`.python-version` 파일**: 내용 `3.12` — uv가 이 파일을 읽어 Python 3.12.13으로 고정. 만약 빠뜨리면 시스템에 설치된 가장 새 파이썬(내 환경에선 3.14)을 집어가서 GPT-SoVITS 스택 호환이 깨질 수 있음
- **`uv.lock` 커밋**: `.gitignore`에서 제외. 재현성 보장. 재생성은 `rm -rf .venv uv.lock && uv sync`
- **워크플로우**: `source .venv/bin/activate` 없이 `uv run pytest` / `uv run voxprep version`

Phase 04에서 faster-whisper 추가할 땐 `uv add faster-whisper` 한 줄로 pyproject.toml + uv.lock 모두 갱신됩니다.

**왜 지금이 전환 시점으로 적절했나**: 설치된 패키지가 4개뿐이라 되돌릴 비용이 거의 없음. 그리고 uv는 2024년 중반 이후 파이썬 생태계의 사실상 새 표준이라 이번 프로젝트에서 한 번 굴려 두면 이후 모든 파이썬 작업의 기본기가 된다.

---
