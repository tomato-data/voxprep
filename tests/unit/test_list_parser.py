import pytest
from pathlib import Path

from voxprep.parsing.errors import MalformedListLineError
from voxprep.parsing.list_file import ListEntry, read_list_file, write_list_file


def test_from_line_parses_four_fields():
    line = "data/wav/01.wav|narrator|ko|안녕하세요"

    entry = ListEntry.from_line(line)

    assert entry.audio_path == "data/wav/01.wav"
    assert entry.speaker == "narrator"
    assert entry.language == "ko"
    assert entry.text == "안녕하세요"


def test_from_line_lowercases_language():
    line = "a.wav|s|ZH|你好"

    entry = ListEntry.from_line(line)

    assert entry.language == "zh"


def test_value_equality():
    a = ListEntry("a.wav", "s", "ko", "hi")
    b = ListEntry("a.wav", "s", "ko", "hi")

    assert a == b
    assert hash(a) == hash(b)


def test_from_line_rejects_three_fields():
    with pytest.raises(MalformedListLineError) as excinfo:
        ListEntry.from_line("a.wav|s|ko")

    assert "expected 4 fields" in str(excinfo.value).lower()


def test_from_line_rejects_pipe_in_text():
    with pytest.raises(MalformedListLineError):
        ListEntry.from_line("a.wav|s|ko|hello|world")


def test_to_line_round_trips():
    entry = ListEntry("a.wav", "narrator", "ko", "안녕")

    assert ListEntry.from_line(entry.to_line()) == entry


def test_write_then_read(tmp_path: Path):
    entries = [
        ListEntry("a.wav", "s1", "ko", "hi"),
        ListEntry("b.wav", "s2", "en", "hello"),
    ]
    target = tmp_path / "test.list"

    write_list_file(target, entries)
    loaded = read_list_file(target)

    assert loaded == entries