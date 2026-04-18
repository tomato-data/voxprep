"""Audio loading helpers — ported from GPT-SoVITS/tools/my_utils.py."""
import os
from pathlib import Path

import ffmpeg
import numpy as np


def clean_path(path_str: str) -> str:
    if path_str.endswith(("\\", "/")):
        return clean_path(path_str[:-1])
    path_str = path_str.replace("/", os.sep).replace("\\", os.sep)
    return path_str.strip(" '\n\"\u202a")


def load_audio(file: str | Path, sr: int) -> np.ndarray:
    """Decode and resample audio via ffmpeg to float32 mono PCM at target sr."""
    file = clean_path(str(file))
    if not os.path.exists(file):
        raise RuntimeError(f"audio not found: {file}")
    out, _ = (
        ffmpeg.input(file, threads=0)
        .output("-", format="f32le", acodec="pcm_f32le", ac=1, ar=sr)
        .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
    )
    return np.frombuffer(out, np.float32).flatten()
