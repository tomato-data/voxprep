from io import StringIO
from pathlib import Path

from rich.console import Console

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import build_default_dispatcher
from voxprep.review.loop import run_review_loop


def _entry(name: str) -> ListEntry:
    return ListEntry(f"{name}.wav", "narrator", "ko", name)


def _make_session(n: int) -> ReviewSession:
    entries = [_entry(str(i)) for i in range(n)]
    return ReviewSession(list_path=Path("x.list"), entries=entries)


def test_loop_quit_on_q():
    session = _make_session(3)
    dispatcher = build_default_dispatcher()
    keys = iter(["n", "n", "q"])
    console = Console(file=StringIO(), force_terminal=False)

    run_review_loop(session, dispatcher, key_source=keys, console=console)

    assert session.cursor == 2
