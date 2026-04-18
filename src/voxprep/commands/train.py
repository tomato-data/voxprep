import argparse
from pathlib import Path

import typer
from rich.console import Console

from voxprep.extract.models_path import ModelsPaths
from voxprep.training import s1_train, s2_train
from voxprep.training.config_builder import (
    GptTrainOptions,
    SovitsTrainOptions,
    build_gpt_config,
    build_sovits_config,
    gpt_weights_dir,
    sovits_weights_dir,
    write_gpt_config,
    write_sovits_config,
)


train_app = typer.Typer(help="Train SoVITS and/or GPT models.")


def _resolve_exp_dir(exp_root: Path | None, exp_name: str) -> Path:
    root = exp_root or (Path.cwd() / "logs")
    return (root / exp_name).resolve()


def _run_sovits(
    opts: SovitsTrainOptions,
    models: ModelsPaths,
    console: Console,
) -> None:
    # Ensure the checkpoint subdir exists: {exp_dir}/logs_s2_{version}/
    (opts.exp_dir / f"logs_s2_{opts.version}").mkdir(parents=True, exist_ok=True)
    (opts.exp_dir / f"logs_s2_{opts.version}" / "eval").mkdir(parents=True, exist_ok=True)

    data = build_sovits_config(opts, models)
    temp_dir = models.root / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_path = write_sovits_config(data, temp_dir / "tmp_s2.json")
    console.print(f"[dim]SoVITS config: {config_path}[/dim]")
    console.print(f"[bold cyan]Training SoVITS ({opts.version})[/bold cyan]")
    s2_train.main(str(config_path))


def _run_gpt(
    opts: GptTrainOptions,
    models: ModelsPaths,
    console: Console,
) -> None:
    # Ensure GPT output directory exists
    (opts.exp_dir / f"logs_s1_{opts.version}").mkdir(parents=True, exist_ok=True)

    data = build_gpt_config(opts, models)
    temp_dir = models.root / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config_path = write_gpt_config(data, temp_dir / "tmp_s1.yaml")
    console.print(f"[dim]GPT config: {config_path}[/dim]")
    console.print(f"[bold cyan]Training GPT ({opts.version})[/bold cyan]")
    args = argparse.Namespace(config_file=str(config_path))
    s1_train.main(args)


@train_app.command("sovits")
def train_sovits(
    exp_name: str = typer.Option(..., "--exp-name"),
    version: str = typer.Option("v2Pro"),
    models_root: Path = typer.Option(None, "--models-root"),
    exp_root: Path = typer.Option(None, "--exp-root", help="Root for logs/{exp_name} (default ./logs)"),
    epochs: int = typer.Option(10),
    batch_size: int = typer.Option(1),
    save_every: int = typer.Option(4),
    is_half: bool = typer.Option(False, "--half/--no-half"),
    gpus: str = typer.Option("0"),
) -> None:
    """Train SoVITS (s2) model."""
    models = ModelsPaths(root=models_root)
    exp_dir = _resolve_exp_dir(exp_root, exp_name)
    weights = sovits_weights_dir(models, version)
    weights.mkdir(parents=True, exist_ok=True)

    opts = SovitsTrainOptions(
        exp_name=exp_name,
        exp_dir=exp_dir,
        weights_dir=weights,
        version=version,
        batch_size=batch_size,
        epochs=epochs,
        save_every=save_every,
        is_half=is_half,
        gpus=gpus,
    )
    _run_sovits(opts, models, Console())
    typer.echo(f"Done. SoVITS weights: {weights}")


@train_app.command("gpt")
def train_gpt(
    exp_name: str = typer.Option(..., "--exp-name"),
    version: str = typer.Option("v2Pro"),
    models_root: Path = typer.Option(None, "--models-root"),
    exp_root: Path = typer.Option(None, "--exp-root"),
    epochs: int = typer.Option(20),
    batch_size: int = typer.Option(1),
    save_every: int = typer.Option(4),
    is_half: bool = typer.Option(False, "--half/--no-half"),
    gpus: str = typer.Option("0"),
    dpo: bool = typer.Option(False, "--dpo/--no-dpo"),
) -> None:
    """Train GPT (s1) model."""
    models = ModelsPaths(root=models_root)
    exp_dir = _resolve_exp_dir(exp_root, exp_name)
    weights = gpt_weights_dir(models, version)
    weights.mkdir(parents=True, exist_ok=True)

    opts = GptTrainOptions(
        exp_name=exp_name,
        exp_dir=exp_dir,
        weights_dir=weights,
        version=version,
        batch_size=batch_size,
        epochs=epochs,
        save_every=save_every,
        is_half=is_half,
        gpus=gpus,
        if_dpo=dpo,
    )
    _run_gpt(opts, models, Console())
    typer.echo(f"Done. GPT weights: {weights}")


@train_app.command("all")
def train_all(
    exp_name: str = typer.Option(..., "--exp-name"),
    version: str = typer.Option("v2Pro"),
    models_root: Path = typer.Option(None, "--models-root"),
    exp_root: Path = typer.Option(None, "--exp-root"),
    sovits_epochs: int = typer.Option(10),
    gpt_epochs: int = typer.Option(20),
    batch_size: int = typer.Option(1),
    save_every: int = typer.Option(4),
    is_half: bool = typer.Option(False, "--half/--no-half"),
    gpus: str = typer.Option("0"),
    dpo: bool = typer.Option(False, "--dpo/--no-dpo"),
) -> None:
    """Train SoVITS first, then GPT."""
    models = ModelsPaths(root=models_root)
    exp_dir = _resolve_exp_dir(exp_root, exp_name)
    console = Console()

    s_weights = sovits_weights_dir(models, version)
    g_weights = gpt_weights_dir(models, version)
    s_weights.mkdir(parents=True, exist_ok=True)
    g_weights.mkdir(parents=True, exist_ok=True)

    _run_sovits(
        SovitsTrainOptions(
            exp_name=exp_name, exp_dir=exp_dir, weights_dir=s_weights, version=version,
            batch_size=batch_size, epochs=sovits_epochs, save_every=save_every,
            is_half=is_half, gpus=gpus,
        ),
        models, console,
    )
    _run_gpt(
        GptTrainOptions(
            exp_name=exp_name, exp_dir=exp_dir, weights_dir=g_weights, version=version,
            batch_size=batch_size, epochs=gpt_epochs, save_every=save_every,
            is_half=is_half, gpus=gpus, if_dpo=dpo,
        ),
        models, console,
    )
    typer.echo("Done.")
    typer.echo(f"  SoVITS: {s_weights}")
    typer.echo(f"  GPT:    {g_weights}")
