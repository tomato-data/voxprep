import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

from voxprep.extract.models_path import ModelsPaths
from voxprep.inference.ref_picker import RefCandidate, rank_candidates
from voxprep.inference.session import InferenceInputs, InferenceSession
from voxprep.training.config_builder import gpt_weights_dir, sovits_weights_dir


def _list_weights(directory: Path, suffix: str) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob(f"*{suffix}"))


def _pick(console: Console, prompt_label: str, items: list[Path]) -> Path:
    if not items:
        raise typer.Exit(f"no weights found for {prompt_label}")
    console.print(f"\n[bold]{prompt_label}:[/bold]")
    for i, p in enumerate(items, 1):
        console.print(f"  [{i}] {p.name}")
    while True:
        choice = typer.prompt(f"Select [1-{len(items)}]", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        console.print("[red]invalid[/red]")


def _play(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["afplay", str(path)])
    elif sys.platform == "linux":
        subprocess.Popen(["aplay", str(path)])


def _pick_candidate(console: Console, items: list[RefCandidate]) -> RefCandidate:
    if not items:
        raise typer.Exit("no reference candidates found in list (need 4-8s duration, 15-50 char text)")
    console.print("\n[bold]Reference audio candidates:[/bold]")
    for i, c in enumerate(items, 1):
        console.print(f"  [{i}] [{c.duration:4.1f}s] {c.text!r}")
    while True:
        choice = typer.prompt(f"Select [1-{len(items)}]", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        console.print("[red]invalid[/red]")


def infer_command(
    sovits_weights: Path = typer.Option(None, "--sovits", help="SoVITS .pth (overrides picker)"),
    gpt_weights: Path = typer.Option(None, "--gpt", help="GPT .ckpt (overrides picker)"),
    version: str = typer.Option("v2Pro"),
    models_root: Path = typer.Option(None, "--models-root"),
    ref_audio: Path = typer.Option(None, "--ref-audio", help="Explicit reference audio path"),
    ref_text: str = typer.Option("", "--ref-text", help="Transcript of --ref-audio"),
    ref_list: Path = typer.Option(None, "--ref-list", exists=True, dir_okay=False,
                                  help=".list file to auto-pick reference from"),
    autoselect: bool = typer.Option(False, "--autoselect",
                                    help="Auto-pick best candidate from --ref-list (no prompt)"),
    ref_lang: str = typer.Option(None, "--ref-lang",
                                 help="Reference audio language; auto-inferred from --ref-list entry"),
    text_lang: str = typer.Option(None, "--text-lang",
                                  help="Target text language; defaults to --ref-lang"),
    output_dir: Path = typer.Option(None, "--output-dir", help="Where to save synthesized wavs (default: ./infer_out)"),
    no_play: bool = typer.Option(False, "--no-play", help="Disable auto-playback"),
) -> None:
    """Interactive inference session: type text, hear voice.

    Reference audio selection — three modes:
      (1) --ref-audio X.wav --ref-text "..."   explicit
      (2) --ref-list foo.list --autoselect     best candidate auto-picked
      (3) --ref-list foo.list                  top 8 candidates shown, you pick
    """
    console = Console()
    models = ModelsPaths(root=models_root)

    if sovits_weights is None:
        s_list = _list_weights(sovits_weights_dir(models, version), ".pth")
        sovits_weights = _pick(console, f"SoVITS {version} weights", s_list)
    if gpt_weights is None:
        g_list = _list_weights(gpt_weights_dir(models, version), ".ckpt")
        if not g_list:
            pretrained = models.gpt_pretrained(version)
            if pretrained.exists():
                console.print(f"[yellow]no trained GPT found — using pretrained {pretrained.name}[/yellow]")
                gpt_weights = pretrained
            else:
                raise typer.Exit("no GPT weights available")
        else:
            gpt_weights = _pick(console, f"GPT {version} weights", g_list)

    if ref_audio is None and ref_list is None:
        raise typer.Exit("either --ref-audio + --ref-text, or --ref-list [--autoselect] is required")

    if ref_audio is None:
        candidates = rank_candidates(ref_list, limit=8)
        if autoselect:
            if not candidates:
                raise typer.Exit("no suitable reference candidates in list")
            chosen = candidates[0]
            console.print(f"[green]Auto-selected:[/green] [{chosen.duration:.1f}s] {chosen.text!r}")
        else:
            chosen = _pick_candidate(console, candidates)
        ref_audio = chosen.audio_path
        if not ref_text:
            ref_text = chosen.text
        if ref_lang is None:
            ref_lang = chosen.entry.language

    if not ref_text:
        ref_text = typer.prompt("Reference text")
    if ref_lang is None:
        ref_lang = typer.prompt("Reference language (zh/en/ja/ko/yue)", default="ko")
    if text_lang is None:
        text_lang = ref_lang

    out_dir = output_dir or Path.cwd() / "infer_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[dim]Loading models...[/dim]")
    session = InferenceSession(
        sovits_weights=sovits_weights,
        gpt_weights=gpt_weights,
        version=version,
        models=models,
    )
    console.print("[bold green]Ready.[/bold green] Type text (Ctrl+C to exit).\n")

    counter = 1
    while True:
        try:
            text = typer.prompt(f"[{counter}]")
        except (KeyboardInterrupt, EOFError):
            console.print("\nBye.")
            break
        if not text.strip():
            continue
        console.print("[dim]Synthesizing...[/dim]")
        try:
            sr, audio = session.synthesize(
                InferenceInputs(
                    text=text,
                    text_lang=text_lang,
                    ref_audio=ref_audio,
                    prompt_text=ref_text,
                    prompt_lang=ref_lang,
                )
            )
        except Exception as exc:
            console.print(f"[red]error: {exc}[/red]")
            continue
        out_path = out_dir / f"infer_{counter:03d}.wav"
        InferenceSession.save_wav(out_path, sr, audio)
        console.print(f"[green]Saved:[/green] {out_path}")
        if not no_play:
            _play(out_path)
        counter += 1
