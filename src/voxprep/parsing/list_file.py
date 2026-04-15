from dataclasses import dataclass
from pathlib import Path

from voxprep.parsing.errors import MalformedListLineError

@dataclass(frozen=True)
class ListEntry:
    audio_path: str
    speaker: str
    language: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", self.language.lower())

    @classmethod
    def from_line(cls, line: str) -> "ListEntry":
        values = line.strip().split("|")
        if len(values) != 4:
            raise MalformedListLineError(
                f"expected 4 fields separated by '|', got {len(values)} "
                f"(pipe characters are not allowed in any field): {line!r}"
            )
        return cls(values[0], values[1], values[2], values[3])

    def to_line(self) -> str:
        return f"{self.audio_path}|{self.speaker}|{self.language}|{self.text}"


def write_list_file(path: Path, entries: list[ListEntry]):
    content = "\n".join(entry.to_line() for entry in entries)
    path.write_text(content, encoding="utf-8")

def read_list_file(path: Path) -> list[ListEntry]:
    content = path.read_text(encoding="utf-8")
    return [ListEntry.from_line(s) for s in content.splitlines() if s.strip()]