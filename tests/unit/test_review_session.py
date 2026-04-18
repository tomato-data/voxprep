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


def test_update_current_text_replaces_entry_and_marks_dirty(tmp_path):
    entries = [_entry("a"), _entry("b")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)

    session.update_current_text("새 텍스트")

    assert session.current().text == "새 텍스트"
    assert session.dirty


def test_save_writes_to_disk_and_clears_dirty(tmp_path):
    entries = [_entry("a"), _entry("b")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    session.update_current_text("새 텍스트")

    session.save()

    assert not session.dirty
    content = (tmp_path / "x.list").read_text(encoding="utf-8")
    assert "새 텍스트" in content


def test_delete_middle_entry_keeps_cursor(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a"), _entry("b"), _entry("c")])
    session.next()

    session.delete_current()

    assert [e.audio_path for e in session.entries] == ["a.wav", "c.wav"]
    assert session.cursor == 1
    assert session.current().audio_path == "c.wav"
    assert session.dirty


def test_delete_last_entry_moves_cursor_back(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a"), _entry("b"), _entry("c")])
    session.next()
    session.next()

    session.delete_current()

    assert session.cursor == 1
    assert session.current().audio_path == "b.wav"


def test_delete_only_entry_makes_session_empty(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a")])
    
    session.delete_current()

    assert session.entries == []
    assert session.is_empty()


def test_undo_restores_deleted_entry(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a"), _entry("b"), _entry("c")])
    session.next()
    session.delete_current()

    restored = session.undo()

    assert restored is True
    assert [e.audio_path for e in session.entries] == ["a.wav", "b.wav", "c.wav"]
    assert session.cursor == 1


def test_undo_only_one_step(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a"), _entry("b")])
    session.delete_current()
    session.undo()

    assert session.undo() is False


def test_undo_after_edit(tmp_path):
    session = ReviewSession(list_path=tmp_path / "x.list", entries=[_entry("a")])
    session.update_current_text("changed")

    session.undo()

    assert session.current().text == "a"