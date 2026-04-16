import numpy as np

from voxprep.slicing.slicer import Slicer

def test_silence_only_audio_return_no_chunks():
    sr = 16000
    waveform = np.zeros(sr * 3, dtype=np.float32)
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=1000)

    chunks = slicer.slice(waveform)

    assert chunks == []


def test_single_loud_segment_returns_one_chunk():
    sr = 16000
    waveform = np.zeros(sr * 3, dtype=np.float32)
    t = np.arange(sr) / sr
    waveform[sr : 2 * sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=500, min_interval=200)

    chunks = slicer.slice(waveform)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.end_sample - chunk.start_sample >= int(sr * 0.5)


def test_two_segments_separated_by_silence_returns_two_chunks():
    sr = 16000
    waveform = np.zeros(sr * 5, dtype=np.float32)
    t = np.arange(sr) / sr
    waveform[:sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    waveform[3 * sr : 4 * sr] = 0.5 * np.sin(2 * np.pi * 440 * t)
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=500, min_interval=300)

    chunks = slicer.slice(waveform)

    assert len(chunks) == 2


def test_short_segment_returned_as_single_chunk():
    sr = 16000
    waveform = np.zeros(sr * 2, dtype=np.float32)
    t = np.arange(int(sr * 0.1)) / sr
    waveform[sr : sr + int(sr * 0.1)] = 0.5 * np.sin(2 * np.pi * 440 * t)
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=500, min_interval=200)

    chunks = slicer.slice(waveform)

    assert len(chunks) == 1


def test_short_chunks_are_merged_with_neighbor():
    sr = 16000
    waveform = np.zeros(sr * 4, dtype=np.float32)
    t_short = np.arange(int(sr * 0.2)) / sr
    # 두 개의 짧은 음성 구간 (각 0.2초), 사이에 0.5초 침묵
    waveform[int(sr * 0.5) : int(sr * 0.7)] = 0.5 * np.sin(2 * np.pi * 440 * t_short)
    waveform[int(sr * 1.2) : int(sr * 1.4)] = 0.5 * np.sin(2 * np.pi * 440 * t_short)
    slicer = Slicer(sr=sr, threshold=-40.0, min_length=500, min_interval=200)

    chunks = slicer.slice(waveform)

    assert len(chunks) == 1
    assert chunks[0].end_sample - chunks[0].start_sample >= sr * 0.5