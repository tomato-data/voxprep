import typer

from voxprep import __version__
from voxprep.commands.slice import slice_command

app = typer.Typer(help="voxprep — GPT-SoVITS preprocessing CLI")
app.command(name="slice")(slice_command)

@app.callback()
def main() -> None:
    """voxprep — GPT-SoVITS dataset preprocessing CLI."""

@app.command()
def version() -> None:
    """Print voxprep version."""
    typer.echo(__version__)