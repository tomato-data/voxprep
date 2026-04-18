from pathlib import Path
import shutil

from voxprep.pipeline.workspace import Workspace
from voxprep.slicing.slicer import Slicer
from voxprep.slicing.io import load_audio, normalize_chunk, save_chunk
from voxprep.slicing.slicer import Chunk
from voxprep.slicing.options import SliceOptions
from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.transcription.options import AsrOptions
from voxprep.parsing.list_file import write_list_file



def slice_step(
        workspace: Workspace,
        raw_dir: Path,
        options: SliceOptions | None = None,
        skip_if_exists: bool = False,
) -> None:
    if skip_if_exists and any(workspace.chunks_dir.iterdir()):
        return
    
    if options is None:
        options = SliceOptions()

    slicer = Slicer(
        sr=options.sample_rate,
        threshold=options.threshold,
        min_length=options.min_length,
        min_interval=options.min_interval,
        hop_size=options.hop_size,
        max_sil_kept=options.max_sil_kept,
    )
    
    wav_files = sorted(raw_dir.glob("*.wav"))
    for wav_path in wav_files:
        audio = load_audio(wav_path, options.sample_rate)
        chunks = slicer.slice(audio)
        for chunk in chunks:
            name = f"{wav_path.stem}_{chunk.start_sample:010d}_{chunk.end_sample:010d}.wav"
            normalized = normalize_chunk(chunk.data, options.max_amp, options.alpha)
            save_chunk(
                Chunk(data=normalized, start_sample=chunk.start_sample, end_sample=chunk.end_sample),
                workspace.chunks_dir / name,
                options.sample_rate,
            )


def asr_step(
        workspace: Workspace,
        transcriber: WhisperTranscriber,
        speaker: str,
        options: AsrOptions | None = None,
        skip_if_exists: bool = False,
) -> None:
    if skip_if_exists and workspace.draft_list.exists():
        return

    if options is None:
        options = AsrOptions()

    wav_files = sorted(
        p for p in workspace.chunks_dir.iterdir()
        if p.suffix.lower() in {".wav", ".flac"}
    )
    entries = []
    for audio_path in wav_files:
        result = transcriber.transcribe(audio_path)
        entries.append(result.to_list_entry(speaker=speaker))

    write_list_file(workspace.draft_list, entries)


def review_step(
        workspace: Workspace,
        skip_review: bool = False,
) -> None:
    if not workspace.final_list.exists():
        shutil.copy2(workspace.draft_list, workspace.final_list)

    if skip_review:
        return
