import typer

from voxprep import __version__
from voxprep.commands.slice import slice_command
from voxprep.commands.asr import asr_command
from voxprep.commands.review import review_command
from voxprep.commands.prep import prep_command
from voxprep.commands.extract import extract_command

app = typer.Typer(help="voxprep — GPT-SoVITS preprocessing CLI")
app.command(name="slice")(slice_command)
app.command(name="asr")(asr_command)
app.command(name="review")(review_command)
app.command(name="prep")(prep_command)
app.command(name="extract")(extract_command)

@app.callback()
def main() -> None:
    """voxprep — GPT-SoVITS dataset preprocessing CLI."""

@app.command()
def version() -> None:
    """Print voxprep version."""
    typer.echo(__version__)