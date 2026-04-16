import numpy as np
import soundfile as sf
from pathlib import Path

from voxprep.slicing.slicer import Chunk


def load_audio(path: Path, sr: int) -> np.ndarray:
    data, file_sr = sf.read(path, dtype="float32", always_2d=False)
    if file_sr != sr:
        raise ValueError(
            f"expected sample rate {sr}, got {file_sr}: {path}"
        )
    return data


def normalize_chunk(chunk: np.ndarray, max_amp: float, alpha: float) -> np.ndarray:
    peak = np.abs(chunk).max()
    if peak < 1e-8:
        return chunk
    if peak > 1:
        chunk = chunk / peak
    return (chunk / peak * (max_amp * alpha)) + (1 - alpha) * chunk


def save_chunk(chunk: Chunk, dst: Path, sr: int) -> None:
    sf.write(str(dst), chunk.data, sr)