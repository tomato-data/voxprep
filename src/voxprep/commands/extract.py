from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from voxprep.extract.models_path import ModelsPaths
from voxprep.extract.text_features import extract_text_features
from voxprep.extract.hubert_features import extract_hubert_features
from voxprep.extract.speaker_vectors import extract_speaker_vectors
from voxprep.extract.semantic_tokens import extract_semantic_tokens


def extract_command(
    list_file: Path = typer.Option(..., "--list-file", exists=True, dir_okay=False,
                                   help="Reviewed .list file"),
    wav_dir: Path = typer.Option(..., "--wav-dir", exists=True, file_okay=False,
                                 help="Directory of sliced audio chunks"),
    exp_name: str = typer.Option(..., "--exp-name",
                                 help="Experiment identifier (used for logs/ subdir and weight filenames)"),
    version: str = typer.Option("v2Pro", help="Model version: v1/v2/v2Pro/v2ProPlus/v3/v4"),
    models_root: Path = typer.Option(None, "--models-root",
                                     help="Root of pretrained models (overrides VOXPREP_MODELS_ROOT)"),
    is_half: bool = typer.Option(False, "--half/--no-half", help="Use fp16 (requires CUDA)"),
    skip_sv: bool = typer.Option(False, "--skip-sv",
                                 help="Skip speaker vector extraction (v2Pro/v2ProPlus only)"),
    exp_root: Path = typer.Option(None, "--exp-root",
                                  help="Where to write logs/{exp_name}/ (default: ./logs)"),
) -> None:
    """Extract BERT + HuBERT + (speaker vectors) + semantic tokens for training."""
    models = ModelsPaths(root=models_root)
    root = exp_root or Path.cwd() / "logs"
    opt_dir = (root / exp_name).resolve()
    opt_dir.mkdir(parents=True, exist_ok=True)

    console = Console()
    console.print(f"[bold]Output:[/bold] {opt_dir}")
    console.print(f"[bold]Models root:[/bold] {models.root}")
    console.print(f"[bold]Version:[/bold] {version}")
    console.print()

    def _progress(label: str):
        progress = Progress()
        task = progress.add_task(label, total=None)
        return progress, task

    # 1. Text + BERT
    console.print("[bold cyan][1/4][/bold cyan] Text + BERT features")
    prog, task = _progress("Text")
    with prog:
        def cb(i, n, name):
            prog.update(task, completed=i, total=n, description=f"Text [{i}/{n}] {name[:40]}")
        extract_text_features(
            list_file=list_file,
            opt_dir=opt_dir,
            models=models,
            version="v2" if version in {"v2", "v2Pro", "v2ProPlus"} else version,
            is_half=is_half,
            progress_cb=cb,
        )

    # 2. HuBERT
    console.print("[bold cyan][2/4][/bold cyan] HuBERT + 32kHz resample")
    prog, task = _progress("HuBERT")
    with prog:
        def cb(i, n, name):
            prog.update(task, completed=i, total=n, description=f"HuBERT [{i}/{n}] {name[:40]}")
        extract_hubert_features(
            list_file=list_file,
            wav_dir=wav_dir,
            opt_dir=opt_dir,
            models=models,
            is_half=is_half,
            progress_cb=cb,
        )

    # 3. Speaker vectors (v2Pro/v2ProPlus only)
    if version in {"v2Pro", "v2ProPlus"} and not skip_sv:
        console.print("[bold cyan][3/4][/bold cyan] Speaker vectors")
        prog, task = _progress("SV")
        with prog:
            def cb(i, n, name):
                prog.update(task, completed=i, total=n, description=f"SV [{i}/{n}] {name[:40]}")
            extract_speaker_vectors(
                list_file=list_file,
                opt_dir=opt_dir,
                models=models,
                is_half=is_half,
                progress_cb=cb,
            )
    else:
        console.print("[dim][3/4] Speaker vectors skipped (not v2Pro/v2ProPlus)[/dim]")

    # 4. Semantic tokens
    console.print("[bold cyan][4/4][/bold cyan] Semantic tokens")
    prog, task = _progress("Semantic")
    with prog:
        def cb(i, n, name):
            prog.update(task, completed=i, total=n, description=f"Semantic [{i}/{n}] {name[:40]}")
        extract_semantic_tokens(
            list_file=list_file,
            opt_dir=opt_dir,
            models=models,
            version=version,
            is_half=is_half,
            progress_cb=cb,
        )

    console.print(f"\n[bold green]Done.[/bold green] Output: {opt_dir}")
