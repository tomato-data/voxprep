from rich.panel import Panel
from rich.text import Text

from voxprep.review.session import ReviewSession
from voxprep.review.issues import inspect


def render_session(session: ReviewSession) -> Panel:
    entry = session.current()
    position = f"{session.cursor + 1}/{len(session.entries)}"

    body = Text()
    body.append(f"  Path:     {entry.audio_path}\n")
    body.append(f"  Speaker:  {entry.speaker}\n")
    body.append(f"  Language: {entry.language}\n")
    body.append(f"  Text:     {entry.text}\n\n")

    issues = inspect(entry)
    if issues:
        body.append("\n")
        for issue in issues:
            body.append(f"  ⚠ {issue.code}: {issue.message}\n", style="bold yellow")

    body.append("\n")
    body.append("  [n] next  [b] back  [q] quit", style="dim")

    return Panel(body, title=f"Review [{position}]", border_style="blue")
