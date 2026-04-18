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


class FakeEditor:
    def __init__(self, return_value: str | None):
        self.return_value = return_value
        self.received: list[str] = []
    def edit(self, initial: str) -> str | None:
        self.received.append(initial)
        return self.return_value
    

def _entry(name: str) -> ListEntry:
    return ListEntry(f"{name}.wav", "narrator", "ko", name)


def test_e_key_updates_current_entry(tmp_path):
    entries = [_entry("a"), _entry("b")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    editor = FakeEditor(return_value="고친 텍스트")
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=editor)

    dispatcher.handle("e", session)

    assert editor.received == ["a"]
    assert session.current().text == "고친 텍스트"
    assert (tmp_path / "x.list").exists()
    assert "고친 텍스트" in (tmp_path / "x.list").read_text(encoding="utf-8")


def test_e_key_calncel_keeps_entry_intact(tmp_path):
    entries = [_entry("a"), _entry("b")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    editor = FakeEditor(return_value=None)
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=editor)

    dispatcher.handle("e", session)

    assert session.current().text == "a"


def test_e_key_empty_string_is_valid_edit(tmp_path):
    entries = [_entry("a"), _entry("b")]
    session = ReviewSession(list_path=tmp_path / "x.list", entries=entries)
    editor = FakeEditor(return_value="")
    dispatcher = build_default_dispatcher(player=SpyPlayer(), editor=editor)

    dispatcher.handle("e", session)

    assert session.current().text == ""