from pathlib import Path

import typer
from rich.console import Console

from voxprep.gptsovits.paths import GptSovitsPaths, resolve_root, validate_version
from voxprep.gptsovits.runner import run_script
from voxprep.gptsovits.config_builder import (
    SovitsTrainConfig,
    GptTrainConfig,
    build_sovits_config,
    build_gpt_config,
    write_sovits_temp_config,
    write_gpt_temp_config,
)


train_app = typer.Typer(help="Train SoVITS and/or GPT models.")


def _run_sovits(
    paths: GptSovitsPaths,
    options: SovitsTrainConfig,
    console: Console,
) -> None:
    data = build_sovits_config(paths, options)
    config_path = write_sovits_temp_config(paths, data)
    console.print(f"[dim]Config written: {config_path}[/dim]")

    script = (
        "GPT_SoVITS/s2_train_v3_lora.py"
        if paths.version in {"v3", "v4"}
        else "GPT_SoVITS/s2_train.py"
    )
    console.print(f"[bold cyan]Training SoVITS ({paths.version})[/bold cyan]")
    run_script(
        script=script,
        cwd=paths.root,
        env_overrides={
            "_CUDA_VISIBLE_DEVICES": options.gpus,
            "is_half": "True" if options.is_half else "False",
            "version": paths.version,
        },
        args=["--config", str(config_path)],
        console=console,
    )


def _run_gpt(
    paths: GptSovitsPaths,
    options: GptTrainConfig,
    console: Console,
) -> None:
    data = build_gpt_config(paths, options)
    config_path = write_gpt_temp_config(paths, data)
    console.print(f"[dim]Config written: {config_path}[/dim]")

    console.print(f"[bold cyan]Training GPT ({paths.version})[/bold cyan]")
    run_script(
        script="GPT_SoVITS/s1_train.py",
        cwd=paths.root,
        env_overrides={
            "_CUDA_VISIBLE_DEVICES": options.gpus,
            "hz": "25hz",
            "is_half": "True" if options.is_half else "False",
            "version": paths.version,
        },
        args=["--config_file", str(config_path)],
        console=console,
    )


@train_app.command("sovits")
def train_sovits(
    exp_name: str = typer.Option(..., "--exp-name"),
    gpt_sovits_root: Path = typer.Option(None, "--gpt-sovits-root"),
    version: str = typer.Option("v2Pro"),
    epochs: int = typer.Option(10, help="Total training epochs"),
    batch_size: int = typer.Option(1),
    save_every: int = typer.Option(4, help="Save weight every N epochs"),
    is_half: bool = typer.Option(False, "--half/--no-half"),
    gpus: str = typer.Option("0", help="Comma-separated GPU indices"),
) -> None:
    """Train the SoVITS (s2) model."""
    validate_version(version)
    root = resolve_root(gpt_sovits_root)
    paths = GptSovitsPaths(root=root, version=version)
    console = Console()
    options = SovitsTrainConfig(
        exp_name=exp_name,
        batch_size=batch_size,
        epochs=epochs,
        save_every=save_every,
        is_half=is_half,
        gpus=gpus,
    )
    _run_sovits(paths, options, console)
    typer.echo(f"Done. Weights in: {paths.sovits_weights_dir}")


@train_app.command("gpt")
def train_gpt(
    exp_name: str = typer.Option(..., "--exp-name"),
    gpt_sovits_root: Path = typer.Option(None, "--gpt-sovits-root"),
    version: str = typer.Option("v2Pro"),
    epochs: int = typer.Option(20),
    batch_size: int = typer.Option(1),
    save_every: int = typer.Option(4),
    is_half: bool = typer.Option(False, "--half/--no-half"),
    gpus: str = typer.Option("0"),
    dpo: bool = typer.Option(False, "--dpo/--no-dpo", help="Enable DPO training"),
) -> None:
    """Train the GPT (s1) model."""
    validate_version(version)
    root = resolve_root(gpt_sovits_root)
    paths = GptSovitsPaths(root=root, version=version)
    console = Console()
    options = GptTrainConfig(
        exp_name=exp_name,
        batch_size=batch_size,
        epochs=epochs,
        save_every=save_every,
        is_half=is_half,
        gpus=gpus,
        if_dpo=dpo,
    )
    _run_gpt(paths, options, console)
    typer.echo(f"Done. Weights in: {paths.gpt_weights_dir}")


@train_app.command("all")
def train_all(
    exp_name: str = typer.Option(..., "--exp-name"),
    gpt_sovits_root: Path = typer.Option(None, "--gpt-sovits-root"),
    version: str = typer.Option("v2Pro"),
    sovits_epochs: int = typer.Option(10),
    gpt_epochs: int = typer.Option(20),
    batch_size: int = typer.Option(1),
    save_every: int = typer.Option(4),
    is_half: bool = typer.Option(False, "--half/--no-half"),
    gpus: str = typer.Option("0"),
    dpo: bool = typer.Option(False, "--dpo/--no-dpo"),
) -> None:
    """Train SoVITS first, then GPT."""
    validate_version(version)
    root = resolve_root(gpt_sovits_root)
    paths = GptSovitsPaths(root=root, version=version)
    console = Console()
    _run_sovits(
        paths,
        SovitsTrainConfig(
            exp_name=exp_name,
            batch_size=batch_size,
            epochs=sovits_epochs,
            save_every=save_every,
            is_half=is_half,
            gpus=gpus,
        ),
        console,
    )
    _run_gpt(
        paths,
        GptTrainConfig(
            exp_name=exp_name,
            batch_size=batch_size,
            epochs=gpt_epochs,
            save_every=save_every,
            is_half=is_half,
            gpus=gpus,
            if_dpo=dpo,
        ),
        console,
    )
    typer.echo("Done.")
    typer.echo(f"  SoVITS weights: {paths.sovits_weights_dir}")
    typer.echo(f"  GPT weights:    {paths.gpt_weights_dir}")
