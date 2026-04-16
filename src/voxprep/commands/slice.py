from pathlib import Path

import typer
from rich.progress import Progress

from voxprep.slicing.slicer import Slicer, Chunk
from voxprep.slicing.io import load_audio, normalize_chunk, save_chunk

def slice_command(
        input_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="Directory containing audio files"),
        output_dir: Path = typer.Argument(..., help="Directory for sliced chunks"),
        sample_rate: int = typer.Option(32000, help="Expected sample rate"),
        threshold: int = typer.Option(-34, help="Silence threshold in dB"),
        min_length: int = typer.Option(4000, help="Minimum chunk length in ms"),
        min_interval: int = typer.Option(300, help="Minimum silence interval in ms"),
        hop_size: int = typer.Option(10, help="RMS hop size in ms"),
        max_sil_kept: int = typer.Option(500, help="Max silence kept at chunk edges in ms"),
        max_amp: float = typer.Option(0.9, help="Normalization target peak"),
        alpha: float = typer.Option(0.25, help="Normalization mix ratio"),
    ) -> None:
    """Slice audio files by silence."""
    wave_files = sorted(input_dir.glob("*.wav"))
    if not wave_files:
        typer.echo(f"No .wav files found in {input_dir}")
        raise typer.Exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    slicer = Slicer(
        sr=sample_rate,
        threshold=threshold,
        min_length=min_length,
        min_interval=min_interval,
        hop_size=hop_size,
        max_sil_kept=max_sil_kept,
    )

    with Progress() as progress:
        task = progress.add_task("Slicing...", total=len(wave_files))
        for wav_path in wave_files:
            audio = load_audio(wav_path, sample_rate)
            chunks = slicer.slice(audio)
            for chunk in chunks:
                name = f"{wav_path.stem}_{chunk.start_sample:010d}_{chunk.end_sample:010d}.wav"
                normalized = normalize_chunk(chunk.data, max_amp, alpha)
                save_chunk(
                    Chunk(data=normalized,
                          start_sample=chunk.start_sample,
                          end_sample=chunk.end_sample),
                          output_dir / name,
                          sample_rate,
                    )
            progress.advance(task)