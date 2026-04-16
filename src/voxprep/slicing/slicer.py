import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class Chunk:
    data: np.ndarray
    start_sample: int
    end_sample: int


class Slicer:
    def __init__(
            self, 
            sr: int, 
            threshold: float = -40.0, 
            min_length: int = 5000, 
            min_interval: int = 300, 
            hop_size: int = 20,
            max_sil_kept: int = 5000,):
        self.sr = sr
        self.threshold = 10 ** (threshold / 20)
        self.hop_size = round(sr * hop_size / 1000)
        self.min_length = round(sr * min_length / 1000)
        self.min_interval = round(sr * min_interval / 1000)
        self.max_sil_kept = round(sr * max_sil_kept / 1000)

    def _rms_curve(self, waveform: np.ndarray) -> np.ndarray:
        n_frames = len(waveform) // self.hop_size
        rms = np.zeros(n_frames)
        for i in range(n_frames):
            start = i * self.hop_size
            end = start + self.hop_size
            frame = waveform[start:end]
            rms[i] = np.sqrt(np.mean(frame ** 2))
        return rms

    def _merge_short_chunks(self, chunks: list[Chunk], waveform: np.ndarray) -> list[Chunk]:
        if len(chunks) <= 1:
            return chunks
        
        merged = [chunks[0]]
        for chunk in chunks[1:]:
            prev = merged[-1]
            if (prev.end_sample - prev.start_sample) < self.min_length:
                merged[-1] = Chunk(
                    data=waveform[prev.start_sample:chunk.end_sample],
                    start_sample=prev.start_sample,
                    end_sample=chunk.end_sample,
                )
            else:
                merged.append(chunk)

        # 마지막 chunk가 짧으면 직전과 병합
        if len(merged) >= 2:
            last = merged[-1]
            if (last.end_sample - last.start_sample) < self.min_length:
                prev = merged[-2]
                merged[-2] = Chunk(
                    data=waveform[prev.start_sample:last.end_sample],
                    start_sample=prev.start_sample,
                    end_sample=last.end_sample,
                )
                merged.pop()

        return merged

    def slice(self, waveform: np.ndarray) -> list:
        if len(waveform.shape) > 1:
            samples = waveform.mean(axis=0)
        else:
            samples = waveform
        
        rms = self._rms_curve(samples)

        if np.all(rms <= self.threshold):
            return []
        
        is_voice = rms > self.threshold
        chunks = []
        in_voice = False
        voice_start = 0

        for i, v in enumerate(is_voice):
            if v and not in_voice:
                voice_start = i
                in_voice = True
            elif not v and in_voice:
                start_sample = voice_start * self.hop_size
                end_sample = i * self.hop_size
                chunks.append(Chunk(
                    data=waveform[start_sample:end_sample],
                    start_sample=start_sample,
                    end_sample=end_sample,
                ))
                in_voice = False

        if in_voice:
            start_sample = voice_start * self.hop_size
            end_sample = len(waveform)
            chunks.append(Chunk(
                data=waveform[start_sample:end_sample],
                start_sample=start_sample,
                end_sample=end_sample,
            ))

        chunks = self._merge_short_chunks(chunks, waveform)
        return chunks