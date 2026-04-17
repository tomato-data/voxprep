from pathlib import Path

from voxprep.parsing.list_file import ListEntry


class ReviewSession:
    def __init__(self, list_path: Path, entries: list[ListEntry]) -> None:
        self.list_path = list_path
        self.entries = entries
        self.cursor = 0

    def current(self) -> ListEntry:
        return self.entries[self.cursor]

    def is_at_start(self) -> bool:
        return self.cursor == 0
        
    def is_at_end(self) -> bool:
        return self.cursor == len(self.entries) - 1
    
    def next(self) -> None:
        if not self.is_at_end():
            self.cursor += 1

    def prev(self) -> None:
        if not self.is_at_start():
            self.cursor -= 1