import typer

from voxprep import __version__

app = typer.Typer(help="voxprep — GPT-SoVITS preprocessing CLI")

@app.callback()
def main() -> None:
    """voxprep — GPT-SoVITS dataset preprocessing CLI."""

@app.command()
def version() -> None:
    """Print voxprep version."""
    typer.echo(__version__)