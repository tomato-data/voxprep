from enum import Enum
from typing import Callable

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