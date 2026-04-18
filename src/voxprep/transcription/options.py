from dataclasses import dataclass


@dataclass(frozen=True)
class AsrOptions:
    language: str = "ko"
    model_size: str = "large-v3-turbo"
    device: str = "auto"
    compute_type: str = "auto"
    beam_size: int = 5
    vad_filter: bool = True
    vad_min_silence_ms: int = 700
