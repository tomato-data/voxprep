from typing import Iterator

from rich.console import Console

from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import Dispatcher, ReviewOutcome
from voxprep.review.render import render_session
from voxprep.review.issues import inspect
from voxprep.review.confirmer import Confirmer


def run_review_loop(
        session: ReviewSession,
        dispatcher: Dispatcher,
        key_source: Iterator[str],
        console: Console,
) -> None:
    while True:
        console.clear()
        console.print(render_session(session))
        try:
            key = next(key_source)
        except StopIteration:
            break
        outcome = dispatcher.handle(key, session)
        if outcome == ReviewOutcome.QUIT:
            break

def run_auto_prune_loop(
        session,
        confirmer: Confirmer,
        on_visit=None,
) -> None:
    i = 0
    while i < len(session.entries):
        entry = session.entries[i]
        issues = inspect(entry)
        if not issues:
            i += 1
            continue
        if on_visit is not None:
            on_visit(entry)
        if confirmer.confirm(f"Delete '{entry.text}'?"):
            session.cursor = i
            session.delete_current()
            session.save()
        else:
            i += 1