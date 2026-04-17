from pathlib import Path

import typer
from rich.progress import Progress

from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.transcription.model_factory import load_whisper
from voxprep.transcription.languages import validate_language, LANGUAGE_CODES
from voxprep.parsing.list_file import write_list_file


def run_asr_pipeline(
    transcriber: WhisperTranscriber,
    input_dir: Path,
    output_list: Path,
    speaker: str,
) -> None:
    wav_files = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() in {".wav", ".flac"}
    )
    if not wav_files:
        raise FileNotFoundError(f"No audio files found in {input_dir}")

    entries = []
    with Progress() as progress:
        task = progress.add_task("Transcribing...", total=len(wav_files))
        for audio_path in wav_files:
            result = transcriber.transcribe(audio_path)
            entries.append(result.to_list_entry(speaker=speaker))
            progress.advance(task)

    output_list.parent.mkdir(parents=True, exist_ok=True)
    write_list_file(output_list, entries)


def asr_command(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="Directory containing sliced audio"),
    output_list: Path = typer.Argument(..., help="Output .list file path"),
    model_size: str = typer.Option("large-v3-turbo", help="Whisper model size"),
    language: str = typer.Option("ko", help="Language code (use --list-languages to see all)"),
    device: str = typer.Option("auto", help="Device: auto/cuda/cpu"),
    compute_type: str = typer.Option("auto", help="Compute type: auto/float16/float32/int8"),
    beam_size: int = typer.Option(5, help="Beam search size"),
    vad: bool = typer.Option(True, help="Enable VAD filter"),
    vad_min_silence_ms: int = typer.Option(700, help="VAD minimum silence duration in ms"),
    speaker: str = typer.Option("narrator", help="Speaker label for .list entries"),
    list_languages: bool = typer.Option(False, "--list-languages", help="Print supported languages and exit"),
) -> None:
    """Transcribe sliced audio files to a .list file."""
    if list_languages:
        for code in sorted(LANGUAGE_CODES - {"auto"}):
            typer.echo(code)
        raise typer.Exit()

    validate_language(language)

    model = load_whisper(model_size=model_size, device=device, compute_type=compute_type)
    transcriber = WhisperTranscriber(
        model=model,
        default_language=language,
        beam_size=beam_size,
        vad_filter=vad,
        vad_min_silence_ms=vad_min_silence_ms,
    )

    run_asr_pipeline(
        transcriber=transcriber,
        input_dir=input_dir,
        output_list=output_list,
        speaker=speaker,
    )
