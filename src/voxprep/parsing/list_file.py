from voxprep.parsing.errors import MalformedListLineError


class ListEntry:
    def __init__(self, audio_path: str, speaker: str, language: str, text: str) -> None:
        self.audio_path = audio_path
        self.speaker = speaker
        self.language = language.lower()
        self.text = text

    @classmethod
    def from_line(cls, line: str) -> "ListEntry":
        values = line.strip().split("|")
        if len(values) != 4:
            raise MalformedListLineError(
                f"expected 4 fields separated by '|', got {len(values)}: {line!r}"
            )
        return cls(values[0], values[1], values[2], values[3])
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ListEntry):
            return NotImplemented
        return (
            self.audio_path == other.audio_path
            and self.speaker == other.speaker
            and self.language == other.language
            and self.text == other.text
        )
    
    def __hash__(self) -> int:
        return hash((self.audio_path, self.speaker, self.language, self.text))