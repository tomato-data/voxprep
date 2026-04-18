import sys
from pathlib import Path

import typer
from rich.console import Console

from voxprep.parsing.list_file import read_list_file
from voxprep.review.session import ReviewSession
from voxprep.review.keybindings import build_default_dispatcher
from voxprep.review.loop import run_review_loop
from voxprep.review.player import SubprocessAudioPlayer
from voxprep.review.editor import PromptToolkitTextEditor


def _stdin_key_source():
    try:
        from prompt_toolkit.input import create_input
        inp = create_input()
        with inp.raw_mode():
            while True:
                for key_press in inp.read_keys():
                    yield key_press.key
    except ImportError:
        while True:
            ch = sys.stdin.read(1)
            if not ch:
                return
            yield ch


def review_command(
    list_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to .list file"),
) -> None:
    """Interactively review ASR transcription results."""
    if not sys.stdin.isatty():
        typer.echo("Error: review requires an interactive terminal")
        raise typer.Exit(1)

    entries = read_list_file(list_file)
    if not entries:
        typer.echo(f"No entries found in {list_file}")
        raise typer.Exit(1)

    session = ReviewSession(list_path=list_file, entries=entries)
    player = SubprocessAudioPlayer()
    editor = PromptToolkitTextEditor()
    dispatcher = build_default_dispatcher(player=player, editor=editor)
    console = Console()

    try:
        run_review_loop(session, dispatcher, key_source=_stdin_key_source(), console=console)
    finally:
        player.stop()
