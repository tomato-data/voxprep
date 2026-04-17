from pathlib import Path
from typing import Protocol, Iterable, Any

from voxprep.transcription.types import Transcription


class WhisperLike(Protocol):
    def transcribe(self, audio: Any, **kwargs: Any) -> tuple[Iterable[Any], Any]: ...


class WhisperTranscriber:
    def __init__(
            self,
            model: WhisperLike,
            default_language: str | None = None,
            beam_size: int = 5,
            vad_filter: bool = True,
            vad_min_silence_ms: int = 700,
    ) -> None:
        self.model = model
        self.default_language = default_language
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.vad_min_silence_ms = vad_min_silence_ms

    def transcribe(self, audio_path: Path) -> Transcription:
        language = None if self.default_language == "auto" else self.default_language
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            vad_parameters={"min_silence_duration_ms": self.vad_min_silence_ms},
        )
        text = "".join(seg.text for seg in segments)
        return Transcription(
            audio_path=audio_path,
            language=info.language,
            text=text,
        )