from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession
from voxprep.review.loop import run_auto_prune_loop


class ScriptedConfirmer:
    def __init__(self, responses: list[bool]):
        self._responses = iter(responses)

    def confirm(self, message: str) -> bool:
        return next(self._responses)


def test_auto_prune_iterates_only_flagged_entries(tmp_path):
    entries = [
        ListEntry("a.wav", "s", "ko", "정상 텍스트입니다"),
        ListEntry("b.wav", "s", "ko", ""),
        ListEntry("c.wav", "s", "ko", "이것도 정상입니다"),
        ListEntry("d.wav", "s", "ko", "아"),
    ]
    list_path = tmp_path / "x.list"
    list_path.write_text("dummy", encoding="utf-8")
    session = ReviewSession(list_path=list_path, entries=entries)

    visited = []
    confirmer = ScriptedConfirmer([False, False])

    run_auto_prune_loop(
        session,
        confirmer=confirmer,
        on_visit=lambda e: visited.append(e.audio_path),
    )

    assert visited == ["b.wav", "d.wav"]


def test_auto_prune_deletes_confirmed_entries(tmp_path):
    entries = [
        ListEntry("a.wav", "s", "ko", "정상 텍스트입니다"),
        ListEntry("b.wav", "s", "ko", ""),
        ListEntry("c.wav", "s", "ko", "아"),
    ]
    list_path = tmp_path / "x.list"
    list_path.write_text("dummy", encoding="utf-8")
    session = ReviewSession(list_path=list_path, entries=entries)

    confirmer = ScriptedConfirmer([True, True])

    run_auto_prune_loop(session, confirmer=confirmer)

    assert len(session.entries) == 1
    assert session.entries[0].audio_path == "a.wav"