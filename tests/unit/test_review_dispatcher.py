from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import Dispatcher, ReviewOutcome, build_default_dispatcher


def test_dispatcher_invokes_registered_actions():
    calls = []
    dispatcher = Dispatcher()
    dispatcher.register("n", lambda s: (calls.append("n"), ReviewOutcome.CONTINUE)[1])

    outcome = dispatcher.handle("n", session=None)

    assert calls == ["n"]
    assert outcome == ReviewOutcome.CONTINUE


def test_dipatcher_ignores_unknown_key():
    dispatcher = Dispatcher()

    assert dispatcher.handle("z", session=None) == ReviewOutcome.CONTINUE


def test_quit_action_returns_quit_outcome():
    dispatcher = Dispatcher()
    dispatcher.register("q", lambda s: ReviewOutcome.QUIT)

    assert dispatcher.handle("q", session=None) == ReviewOutcome.QUIT


class SpyPlayer:
    def __init__(self):
        self.played: list[Path] = []
        self.stop_count = 0
    def play(self, path: Path) -> None:
        self.stop()
        self.played.append(path)
    def stop(self) -> None:
        self.stop_count += 1


class FakeEditor:
    def __init__(self, return_value):
        self.return_value = return_value
    def edit(self, initial):
        return self.return_value


class FakeConfirmer:
    def __init__(self, response: bool):
        self.response = response
        self.received: list[str] = []
    def confirm(self, message: str) -> bool:
        self.received.append(message)
        return self.response
    

def _entry(name: str) -> ListEntry:
    return ListEntry(f"{name}.wav", "narrator", "ko", name)


def test_d_key_with_confirmation_deletes(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a"), _entry("b")])
    confirmer = FakeConfirmer(response=True)
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=FakeEditor(None), confirmer=confirmer)

    dispatcher.handle("d", session)


    assert len(session.entries) == 1
    assert session.entries[0].audio_path == "b.wav"


def test_d_key_cancelled_keeps_entry(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a")])
    confirmer = FakeConfirmer(response=False)
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=FakeEditor(None), confirmer=confirmer)

    dispatcher.handle("d", session)

    assert len(session.entries) == 1


def test_u_key_undoes_last_delete(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a"), _entry("b")])
    confirmer = FakeConfirmer(response=True)
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=FakeEditor(None), confirmer=confirmer)

    dispatcher.handle("d", session)

    dispatcher.handle("u", session)

    assert len(session.entries) == 2
    assert session.entries[0].audio_path == "a.wav"