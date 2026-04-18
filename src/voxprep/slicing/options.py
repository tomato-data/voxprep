from dataclasses import dataclass


@dataclass(frozen=True)
class SliceOptions:
    sample_rate: int = 32000
    threshold: int = -34
    min_length: int = 4000
    min_interval: int = 300
    hop_size: int = 10
    max_sil_kept: int = 500
    max_amp: float = 0.9
    alpha: float = 0.25
