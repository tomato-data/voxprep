import numpy as np


def build_two_segment_waveform(sr: int) -> np.ndarray:
    waveform = np.zeros(sr * 5, dtype=np.float32)
    t = np.arange(sr) / sr
    waveform[:sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    waveform[3 * sr : 4 * sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    return waveform
