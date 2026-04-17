from dataclasses import dataclass
from pathlib import Path

from voxprep.parsing.list_file import ListEntry


@dataclass(frozen=True)
class Transcription:
    audio_path: Path
    language: str
    text: str

    def to_list_entry(self, speaker: str) -> ListEntry:
        return ListEntry(str(self.audio_path), speaker, self.language, self.text)