# DISCOVERIES

voxprep 개발 과정에서 **디버깅·에러·시행착오를 통해 "자연스럽게 알게 된 것들"**의 누적 로그입니다. Q&A(`phaseNN-qa.md`)는 내가 **직접 던진 질문**의 기록이고, 이 파일은 **내가 묻지 않았는데 튀어나와 배우게 된 것들**의 기록입니다. 둘 다 학습의 산출물이지만 성격이 달라서 분리합니다.

엔트리 작성 원칙:

- 각 발견은 짧은 제목 + 맥락(어느 Phase의 어느 상황에서 나왔는지) + 본질 + 재현 방법 + 기억 훅
- Phase를 가로질러 계속 누적 — 새로운 발견은 **파일 상단**에 추가(최근이 위)
- "내가 틀렸던 지점"을 숨기지 않기. 허위 GREEN, 잘못 이해한 동작, 놓친 가정 등이 가장 가치 있는 엔트리
- 디버깅 발견뿐 아니라 **개발 중 굳어진 설계 원칙**(예: "경계에서 정규화")도 여기 누적. 원칙은 나중에 프로젝트 곳곳에서 판단 근거로 재사용된다

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
