from typing import Iterator

from rich.console import Console

from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import Dispatcher, ReviewOutcome
from voxprep.review.render import render_session


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