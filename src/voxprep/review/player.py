import subprocess
import sys
from pathlib import Path
from typing import Protocol


class AudioPlayer(Protocol):
    def play(self, path: Path) -> None: ...
    def stop(self) -> None: ...


class SubprocessAudioPlayer:
    def __init__(self) -> None:
        self._current: subprocess.Popen | None = None

    def play(self, path: Path) -> None:
        self.stop()
        if not path.exists():
            print(f"Warning: audio file not found: {path}", file=sys.stderr)
            return
        cmd = self._command(path)
        self._current = subprocess.Popen(cmd)

    def stop(self) -> None:
        if self._current is not None:
            self._current.terminate()
            try:
                self._current.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self._current.kill()
            self._current = None

    def _command(self, path: Path) -> list[str]:
        if sys.platform == "darwin":
            return ["afplay", str(path)]
        elif sys.platform == "linux":
            return ["aplay", str(path)]
        else:
            raise RuntimeError(f"unsupported platform for audio playback: {sys.platform}")
