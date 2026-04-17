from io import StringIO
from rich.console import Console
from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.render import render_session
from voxprep.review.session import ReviewSession


def _entry(name: str) -> ListEntry:
    return ListEntry(f"{name}.wav", "narrator", "ko", name)


def test_session_starts_at_first_entry():
    entries = [_entry("a"), _entry("b"), _entry("c")]
    session = ReviewSession(list_path=Path("x.list"), entries=entries)

    assert session.cursor == 0
    assert session.current() == entries[0]
    assert session.is_at_start()
    assert not session.is_at_end()


def _make_session(n: int) -> ReviewSession:
    entries = [_entry(str(i)) for i in range(n)]
    return ReviewSession(list_path=Path("x.list"), entries=entries)


def test_next_advances_cursor():
    session = _make_session(3)

    session.next()

    assert session.cursor == 1


def test_next_at_end_does_not_overflow():
    session = _make_session(3)
    session.next()
    session.next()

    session.next()

    assert session.cursor == 2
    assert session.is_at_end()


def test_prev_at_start_does_not_underflow():
    session = _make_session(3)

    session.prev()

    assert session.cursor == 0


def test_render_includes_position_and_text():
    session = _make_session(3)

    rendered = render_session(session)

    output = StringIO()
    console = Console(file=output, force_terminal=False)
    console.print(rendered)
    text = output.getvalue()
    assert "1/3" in text
    assert session.current().text in text