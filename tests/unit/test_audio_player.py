from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import build_default_dispatcher


class SpyPlayer:
    def __init__(self):
        self.played: list[Path] = []
        self.stop_count = 0

    def play(self, path: Path) -> None:
        self.stop()
        self.played.append(path)

    def stop(self) -> None:
        self.stop_count += 1


def _make_session() -> ReviewSession:
    entries = [
        ListEntry("a.wav", "s", "ko", "hi"),
        ListEntry("b.wav", "s", "ko", "bye"),
    ]
    return ReviewSession(list_path=Path("x.list"), entries=entries)


def test_enter_plays_current_entry_audio():
    session = _make_session()
    player = SpyPlayer()
    dispatcher = build_default_dispatcher(player=player)

    dispatcher.handle("\r", session)

    assert player.played == [Path("a.wav")]


def test_consecutive_enter_stops_previous_playback():
    session = _make_session()
    player = SpyPlayer()
    dispatcher = build_default_dispatcher(player=player)

    dispatcher.handle("\r", session)
    session.next()
    dispatcher.handle("\r", session)

    assert player.stop_count >= 2
    assert player.played == [Path("a.wav"), Path("b.wav")]
    