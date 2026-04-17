from enum import Enum
from pathlib import Path
from typing import Callable

from voxprep.review.player import AudioPlayer

class ReviewOutcome(Enum):
    CONTINUE = "continue"
    QUIT = "quit"

class Dispatcher:
    def __init__(self) -> None:
        self._actions: dict[str, Callable] = {}

    def register(self, key: str, action: Callable) -> None:
        self._actions[key] = action

    def handle(self, key: str, session) -> ReviewOutcome:
        action = self._actions.get(key)
        if action is None:
            return ReviewOutcome.CONTINUE
        return action(session)


def build_default_dispatcher(player: AudioPlayer | None = None) -> Dispatcher:
    d = Dispatcher()
    d.register("n", lambda s: (s.next(), ReviewOutcome.CONTINUE)[1])
    d.register("b", lambda s: (s.prev(), ReviewOutcome.CONTINUE)[1])
    d.register("q", lambda s: ReviewOutcome.QUIT)
    if player is not None:
        d.register("\r", lambda s: (
            player.stop(),
            player.play(Path(s.current().audio_path)),
            ReviewOutcome.CONTINUE,
        )[-1])
    return d