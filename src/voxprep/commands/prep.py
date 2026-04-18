from pathlib import Path

import typer

from voxprep.pipeline.workspace import Workspace
from voxprep.pipeline.runner import slice_step, asr_step, review_step
from voxprep.slicing.options import SliceOptions
from voxprep.transcription.options import AsrOptions
from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.transcription.model_factory import load_whisper


def _build_transcriber(options: AsrOptions) -> WhisperTranscriber:
    model = load_whisper(
        model_size=options.model_size,
        device=options.device,
        compute_type=options.compute_type,
    )
    return WhisperTranscriber(
        model=model,
        default_language=options.language,
        beam_size=options.beam_size,
        vad_filter=options.vad_filter,
        vad_min_silence_ms=options.vad_min_silence_ms,
    )


def prep_command(
    raw_audio: Path = typer.Argument(..., exists=True, file_okay=False,
help="Directory containing raw audio files"),
    workspace: Path = typer.Option(..., help="Workspace directory for outputs"),
    speaker: str = typer.Option("narrator", help="Speaker label"),
    language: str = typer.Option("ko", help="Language code"),
    skip_review: bool = typer.Option(False, "--skip-review", help="Skip interactive review"),
    sample_rate: int = typer.Option(32000, help="Expected sample rate"),
    threshold: int = typer.Option(-34, help="Silence threshold in dB"),
    min_length: int = typer.Option(4000, help="Minimum chunk length in ms"),
    min_interval: int = typer.Option(300, help="Minimum silence interval in ms"),
    hop_size: int = typer.Option(10, help="RMS hop size in ms"),
    max_sil_kept: int = typer.Option(500, help="Max silence kept at edges in ms"),
    max_amp: float = typer.Option(0.9, help="Normalization target peak"),
    alpha: float = typer.Option(0.25, help="Normalization mix ratio"),
    model_size: str = typer.Option("large-v3-turbo", help="Whisper model size"),
    device: str = typer.Option("auto", help="Device: auto/cuda/cpu"),
    compute_type: str = typer.Option("auto", help="Compute type"),
    beam_size: int = typer.Option(5, help="Beam search size"),
    vad: bool = typer.Option(True, help="Enable VAD filter"),
    vad_min_silence_ms: int = typer.Option(700, help="VAD minimum silence in ms"),
) -> None:
    """Run full preprocessing pipeline: slice -> asr -> review."""
    ws = Workspace(root=workspace)
    ws.ensure_root()

    slice_options = SliceOptions(
        sample_rate=sample_rate,
        threshold=threshold,
        min_length=min_length,
        min_interval=min_interval,
        hop_size=hop_size,
        max_sil_kept=max_sil_kept,
        max_amp=max_amp,
        alpha=alpha,
    )
    slice_step(workspace=ws, raw_dir=raw_audio, options=slice_options)

    asr_options = AsrOptions(
        language=language,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        beam_size=beam_size,
        vad_filter=vad,
        vad_min_silence_ms=vad_min_silence_ms,
    )
    transcriber = _build_transcriber(asr_options)
    asr_step(workspace=ws, transcriber=transcriber, speaker=speaker, options=asr_options)

    review_step(workspace=ws, skip_review=skip_review)

    typer.echo(f"Done. Output: {ws.final_list}")