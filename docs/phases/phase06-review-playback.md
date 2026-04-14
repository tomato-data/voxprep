# Phase 06 — `review` 오디오 재생 (Enter)

## 학습 목표

- **subprocess seam** 만들기 — 재생기 호출을 추상화해 테스트에서 실제 `afplay`를 띄우지 않음
- 동기 vs 비동기 재생 결정 (재생 중에 다음 키 입력을 받을 것인가?)
- 크로스플랫폼 분기를 어디에 둘지 — Service 한 군데에 모으기
- 외부 명령 실패(파일 없음, 코덱 미지원)에 대한 friendly handling
- Phase 05의 Dispatcher에 새 키 추가 — 기존 테스트가 깨지지 않는 경험 (회귀 안전망)

## 참조 자료

| 무엇을 | 어디서 | 왜 |
|--------|--------|----|
| Phase 05 Dispatcher | `src/voxprep/review/keybindings.py` | 새 키를 추가하는 자리 |
| `subprocess` 모듈 | https://docs.python.org/3/library/subprocess.html | `Popen` 비동기 vs `run` 동기 |
| `claude-code-study` subprocess 패턴 | (해당 없음 — Ink 렌더만 사용) | 참고할 거 없음. 우리는 단순 Popen으로 충분 |
| afplay (macOS) | `man afplay` | `afplay <file>`만으로 동작. 종료 코드만 확인 |

## 설계 결정 — 동기 vs 비동기 재생

- **동기 (`subprocess.run`)**: 재생이 끝날 때까지 키 입력 못 받음. 단순. 단점: 긴 청크에서 답답.
- **비동기 (`subprocess.Popen`)**: 재생 시작 후 즉시 다음 키 받음. 다음 키가 또 Enter면 이전 재생 중단? 또는 겹쳐 재생? 정책 필요.

**1차 권장: 비동기 + 새 재생 시작 시 이전 재생 중단**. 이유:
- review 워크플로우의 본질은 "들어보고 → 편집/넘어가기"의 빠른 반복. 동기는 흐름 끊김.
- 이전 재생을 중단하지 않으면 실수로 Enter 두 번 누를 때 카오스.

`AudioPlayer` Service가 `play(path)` 호출 시 내부에 `_current: Popen | None`을 유지하고, 새 호출 전에 `terminate()`. → Service에 약간의 상태가 있음 → **사실상 작은 Entity로 봐야 하는가?** 학습 토론 포인트. 1차 분류는 **Service**로 두되, 회고에 "상태가 한 줄 들어가서 경계 지점에 있다"고 적기.

## 구현 범위

### 만들 것

1. `src/voxprep/review/player.py`
   - `AudioPlayer` (Protocol 또는 ABC) — `play(path: Path) -> None`, `stop() -> None`
   - `SubprocessAudioPlayer(AudioPlayer)` — 실제 구현. 플랫폼별 명령 분기:
     - macOS: `["afplay", str(path)]`
     - Linux: `["aplay", str(path)]` (또는 `paplay`)
     - Windows: `["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"]` (또는 미지원)
   - 내부에 `_current: subprocess.Popen | None` 유지
2. `src/voxprep/review/keybindings.py` — Enter 키 액션 등록 추가
3. `src/voxprep/commands/review.py` — `SubprocessAudioPlayer` 인스턴스 생성 후 dispatcher에 액션 와이어
4. 테스트:
   - `tests/unit/test_audio_player.py` — `FakeAudioPlayer`(spy)로 dispatcher → action 호출 검증
   - `tests/unit/test_subprocess_audio_player.py` — `subprocess.Popen`을 monkey-patch한 단위 테스트 (실제 afplay 안 띄움)

### 미루는 것

- 볼륨 조절
- 재생 위치 표시 (어차피 청크가 짧음 — 보통 5~10초)
- 재생 속도 조절

## TDD 사이클 시나리오

### 시나리오 A — Player Protocol과 fake spy

```python
from pathlib import Path
from typing import Protocol


class AudioPlayer(Protocol):
    def play(self, path: Path) -> None: ...
    def stop(self) -> None: ...


class SpyPlayer:
    def __init__(self):
        self.played: list[Path] = []
        self.stop_count = 0
    def play(self, path: Path) -> None:
        self.played.append(path)
    def stop(self) -> None:
        self.stop_count += 1
```

이 시나리오 자체는 테스트가 아니라 **테스트 인프라**. 실제 테스트는 시나리오 B부터.

### 시나리오 B — Enter 키가 현재 entry의 오디오를 재생한다

```python
from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import Dispatcher, build_default_dispatcher
from voxprep.parsing.list_file import ListEntry


def test_enter_plays_current_entry_audio():
    entries = [ListEntry("a.wav", "s", "ko", "hi"), ListEntry("b.wav", "s", "ko", "bye")]
    session = ReviewSession(list_path=Path("x.list"), entries=entries)
    player = SpyPlayer()
    dispatcher = build_default_dispatcher(player=player)

    dispatcher.handle("\r", session)  # Enter

    assert player.played == [Path("a.wav")]
```

GREEN: `build_default_dispatcher`가 `player` 의존성을 받게 시그니처 변경. Enter 키 액션은 `lambda s: (player.play(Path(s.current().audio_path)), ReviewOutcome.CONTINUE)[1]`.

여기서 **dispatcher 빌더 함수**가 등장하는 게 중요한 학습 포인트 — Phase 05에서는 직접 `register`했지만, 의존성이 늘어나니 빌더로 응집.

### 시나리오 C — 새 재생이 이전 재생을 중단

```python
def test_consecutive_enter_stops_previous_playback():
    entries = [ListEntry("a.wav", "s", "ko", "hi"), ListEntry("b.wav", "s", "ko", "bye")]
    session = ReviewSession(list_path=Path("x.list"), entries=entries)
    player = SpyPlayer()
    dispatcher = build_default_dispatcher(player=player)

    dispatcher.handle("\r", session)
    session.next()
    dispatcher.handle("\r", session)

    assert player.stop_count >= 1  # 두 번째 play 전에 stop
    assert player.played == [Path("a.wav"), Path("b.wav")]
```

GREEN: `play()` 내부에서 진입 시 `self.stop()`을 먼저 호출하도록 — 단, 이 동작은 `SpyPlayer`에는 없으니, **Enter 액션 함수 안에서 명시적으로** `player.stop(); player.play(...)`로 짤지, **Player 구현에서** 알아서 처리할지 결정. 1차 권장: **Player 책임** (호출자는 모름). SpyPlayer도 같은 동작을 흉내 내도록 손봐야 함:

```python
class SpyPlayer:
    def play(self, path: Path) -> None:
        self.stop()  # 새 play 전에 stop
        self.played.append(path)
```

### 시나리오 D — `SubprocessAudioPlayer`의 명령 결정 (monkey-patch)

```python
import subprocess
import sys

import pytest

from voxprep.review.player import SubprocessAudioPlayer


def test_subprocess_player_uses_afplay_on_darwin(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            calls.append(args)
            self.args = args
        def terminate(self):
            pass
        def poll(self):
            return None

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(sys, "platform", "darwin")

    player = SubprocessAudioPlayer()
    player.play(Path("a.wav"))

    assert calls == [["afplay", "a.wav"]]
```

GREEN: `_command_for_platform()` 헬퍼 + `Popen` 호출.

### 시나리오 E — 파일 없음 시 friendly 메시지

```python
def test_play_missing_file_logs_warning(capsys, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")

    player = SubprocessAudioPlayer()
    player.play(Path("nonexistent.wav"))

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()
```

GREEN: `path.exists()` 체크 + stderr 출력 또는 logging. **Popen 호출은 안 함**.

## REFACTOR 게이트

- **4-0**: Spy가 너무 똑똑해지면 가짜가 진짜를 따라잡는 함정. `played: list[Path]`만 유지하는 게 깔끔.
- **4-1**: 플랫폼 분기를 if/elif가 아니라 dict로 둘지 결정 — 3개라 if/else도 OK.
- **4-2 (ODP 게이트)**:
  - `AudioPlayer` Protocol — 의존성 계약 ✅
  - `SubprocessAudioPlayer`는 Service인가, Entity인가? — `_current` 상태가 있어 경계. **결정**: Service로 분류하되 회고에 "상태가 한 줄 있어 작은 Entity로 봐도 무방"이라고 적기. 학습 가치 있는 회색지대.
  - `build_default_dispatcher`는 자유 함수 ✅
- **4-3**: 패턴 신호 — 3개 플랫폼 분기는 아직 Strategy 도착 신호 아님. 5개 넘으면 그때.

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `AudioPlayer` (Protocol) | (계약) | DI 추상화 |
| `SubprocessAudioPlayer` | Service (경계) | `_current` 상태 한 줄 — 학습 토론 거리 |
| `SpyPlayer` | (테스트 더블) | Service 인터페이스 모방 |
| `build_default_dispatcher` | 자유 함수 | dispatcher 조립 |

## 파일 구조

```
voxprep/
├── src/voxprep/
│   └── review/
│       ├── player.py           ← user types
│       └── keybindings.py      ← edit: Enter 키 등록 (또는 build_default_dispatcher 시그니처 변경)
└── tests/unit/
    ├── test_audio_player.py            ← user types
    └── test_subprocess_audio_player.py ← user types
```

## 완료 기준

- [ ] 시나리오 A~E 모두 통과
- [ ] `voxprep review some.list` → Enter 누르면 실제 afplay로 재생됨 (macOS)
- [ ] 두 번 연속 Enter 시 이전 재생이 중단됨
- [ ] Phase 05 테스트 (`test_review_*`)가 여전히 통과 (시그니처 변경 전파 확인)
- [ ] `learnings/phase06-qa.md` (subprocess seam, Service vs Entity 토론)
- [ ] 커밋:
  - `feat: add AudioPlayer protocol and SubprocessAudioPlayer`
  - `feat: wire enter key to play current entry audio`

## 주의사항 / 엣지케이스

- **Enter 키의 표현**: `prompt_toolkit`의 `KeyPress`로 받으면 `'\r'` 또는 `'\n'`. 둘 다 같은 액션에 등록하거나, `keybindings.py`에서 정규화.
- **`Popen.terminate()` vs `kill()`**: `terminate`는 SIGTERM, `kill`은 SIGKILL. afplay는 SIGTERM에 잘 반응 — terminate로 충분.
- **Zombie 프로세스**: `Popen` 객체를 버리면 자식이 좀비가 될 수 있음. `stop()` 호출 시 `terminate()` + `wait(timeout=0.1)` 권장.
- **상대 경로**: `.list`의 `audio_path`가 상대 경로면 `.list` 파일 위치 기준으로 resolve해야 할 수도 있음. 결정 필요 — 1차 권장: **CWD 기준**. `.list` 기준은 `slice` 단계가 절대 경로를 쓰면 자연스럽게 해결.
- **소리 안 나는 경우**: 시스템 볼륨/출력 디바이스 문제. friendly 에러 안내는 어려움. "들리지 않으면 시스템 사운드 설정 확인" 정도의 도움말.
- **`afplay`가 없는 환경**: 테스트 환경(CI 등)을 위해 `SubprocessAudioPlayer`는 lazy하게 (호출 시점에야 명령 결정). import 시점에 `which afplay` 같은 부수효과 X.

## 다음 Phase 준비

Phase 07에서 `e` 키로 인라인 텍스트 편집을 합니다. 시작 전:

1. `claude-code-study/components/BaseTextInput.tsx` 한 번 더 훑기 — default value, enter/escape 분기
2. `prompt_toolkit.shortcuts.prompt(default=..., key_bindings=...)` 공식 예제 확인
3. dirty 플래그를 `ReviewSession`에 추가할 시점이 됨 — 어떻게 도입할지 미리 생각
