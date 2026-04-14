# DISCOVERIES

voxprep 개발 과정에서 **디버깅·에러·시행착오를 통해 "자연스럽게 알게 된 것들"**의 누적 로그입니다. Q&A(`phaseNN-qa.md`)는 내가 **직접 던진 질문**의 기록이고, 이 파일은 **내가 묻지 않았는데 튀어나와 배우게 된 것들**의 기록입니다. 둘 다 학습의 산출물이지만 성격이 달라서 분리합니다.

엔트리 작성 원칙:

- 각 발견은 짧은 제목 + 맥락(어느 Phase의 어느 상황에서 나왔는지) + 본질 + 재현 방법 + 기억 훅
- Phase를 가로질러 계속 누적 — 새로운 발견은 **파일 상단**에 추가(최근이 위)
- "내가 틀렸던 지점"을 숨기지 않기. 허위 GREEN, 잘못 이해한 동작, 놓친 가정 등이 가장 가치 있는 엔트리

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
