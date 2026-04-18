from pathlib import Path

from voxprep.parsing.list_file import ListEntry
from voxprep.review.session import ReviewSession
from voxprep.review.render import render_session


def _to_plain_text(panel) -> str:
    from rich.console import Console
    console = Console(width=120, no_color=True)
    with console.capture() as capture:
        console.print(panel)
    return capture.get()


def test_render_includes_warning_for_flagged_entry():
    session = ReviewSession(
        list_path=Path("x.list"),
        entries=[ListEntry("a.wav", "s", "ko", "")],
    )

    rendered = render_session(session)
    text = _to_plain_text(rendered)

    assert "empty_text" in text.lower() or "empty" in text.lower()


def test_render_no_warning_for_clean_entry():
    session = ReviewSession(
        list_path=Path("x.list"),
        entries=[ListEntry("a.wav", "s", "ko", "정상 텍스트입니다")],
    )

    rendered = render_session(session)
    text = _to_plain_text(rendered)

    assert "⚠" not in text