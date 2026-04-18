from pathlib import Path
import shutil

from voxprep.pipeline.workspace import Workspace
from voxprep.slicing.slicer import Slicer
from voxprep.slicing.io import load_audio, normalize_chunk, save_chunk
from voxprep.slicing.slicer import Chunk
from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.parsing.list_file import write_list_file


def slice_step(
        workspace: Workspace,
        raw_dir: Path,
        slicer: Slicer,
        max_amp: float = 0.9,
        alpha: float = 0.25,
        skip_if_exists: bool = False,
) -> None:
    if skip_if_exists and any(workspace.chunks_dir.iterdir()):
        return
    
    wav_files = sorted(raw_dir.glob("*.wav"))
    for wav_path in wav_files:
        audio = load_audio(wav_path, slicer.sr)
        chunks = slicer.slice(audio)
        for chunk in chunks:
            name = f"{wav_path.stem}_{chunk.start_sample:010d}_{chunk.end_sample:010d}.wav"
            normalized = normalize_chunk(chunk.data, max_amp, alpha)
            save_chunk(
                Chunk(data=normalized, start_sample=chunk.start_sample, end_sample=chunk.end_sample),
                workspace.chunks_dir / name,
                slicer.sr,
            )


def asr_step(
        workspace: Workspace,
        transcriber: WhisperTranscriber,
        speaker: str,
        skip_if_exists: bool = False,
) -> None:
    if skip_if_exists and workspace.draft_list.exists():
        return
    
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