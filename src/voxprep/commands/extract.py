from pathlib import Path

import typer
from rich.console import Console

from voxprep.gptsovits.paths import GptSovitsPaths, resolve_root, validate_version
from voxprep.gptsovits.runner import run_script


def _base_env(
    paths: GptSovitsPaths,
    list_file: Path,
    wav_dir: Path,
    exp_name: str,
    is_half: bool,
    gpu: str,
) -> dict[str, str]:
    return {
        "inp_text": str(list_file.resolve()),
        "inp_wav_dir": str(wav_dir.resolve()),
        "exp_name": exp_name,
        "opt_dir": str(paths.exp_log_dir(exp_name)),
        "i_part": "0",
        "all_parts": "1",
        "_CUDA_VISIBLE_DEVICES": gpu,
        "is_half": "True" if is_half else "False",
        "version": paths.version,
    }


def extract_command(
    list_file: Path = typer.Option(..., "--list-file", exists=True, dir_okay=False, help="Reviewed .list file"),
    wav_dir: Path = typer.Option(..., "--wav-dir", exists=True, file_okay=False, help="Directory of sliced audio chunks"),
    exp_name: str = typer.Option(..., "--exp-name", help="Experiment name (used for logs/ subdir)"),
    gpt_sovits_root: Path = typer.Option(None, "--gpt-sovits-root", help="Path to GPT-SoVITS repo"),
    version: str = typer.Option("v2Pro", help="Model version: v1/v2/v2Pro/v2ProPlus/v3/v4"),
    is_half: bool = typer.Option(False, "--half/--no-half", help="Use fp16 (requires CUDA)"),
    gpu: str = typer.Option("0", help="CUDA device index; ignored on CPU"),
    skip_sv: bool = typer.Option(False, "--skip-sv", help="Skip speaker vector extraction (v2Pro only)"),
) -> None:
    """Run GPT-SoVITS feature extraction pipeline (text → HuBERT → semantic)."""
    validate_version(version)
    root = resolve_root(gpt_sovits_root)
    paths = GptSovitsPaths(root=root, version=version)

    console = Console()
    log_dir = paths.exp_log_dir(exp_name)
    log_dir.mkdir(parents=True, exist_ok=True)

    base = _base_env(paths, list_file, wav_dir, exp_name, is_half, gpu)

    console.print(f"[bold cyan][1/3][/bold cyan] Text + BERT features")
    run_script(
        script="GPT_SoVITS/prepare_datasets/1-get-text.py",
        cwd=root,
        env_overrides={
            **base,
            "bert_pretrained_dir": str(paths.bert_dir),
        },
        console=console,
    )

    console.print(f"[bold cyan][2/3][/bold cyan] HuBERT + 32kHz resampling")
    run_script(
        script="GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
        cwd=root,
        env_overrides={
            **base,
            "cnhubert_base_dir": str(paths.cnhubert_dir),
            "sv_path": str(paths.sv_ckpt),
        },
        console=console,
    )

    if version in {"v2Pro", "v2ProPlus"} and not skip_sv:
        console.print(f"[bold cyan][2b/3][/bold cyan] Speaker vectors (v2Pro)")
        run_script(
            script="GPT_SoVITS/prepare_datasets/2-get-sv.py",
            cwd=root,
            env_overrides={
                **base,
                "cnhubert_base_dir": str(paths.cnhubert_dir),
                "sv_path": str(paths.sv_ckpt),
            },
            console=console,
        )

    console.print(f"[bold cyan][3/3][/bold cyan] Semantic tokens")
    run_script(
        script="GPT_SoVITS/prepare_datasets/3-get-semantic.py",
        cwd=root,
        env_overrides={
            **base,
            "pretrained_s2G": str(paths.pretrained_s2g),
            "s2config_path": str(paths.s2_config_template),
        },
        console=console,
    )

    typer.echo(f"Done. Output: {log_dir}")
