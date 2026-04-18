from pathlib import Path
from dataclasses import replace

from voxprep.parsing.list_file import ListEntry, write_list_file


class ReviewSession:
    def __init__(self, list_path: Path, entries: list[ListEntry]) -> None:
        self.list_path = list_path
        self.entries = entries
        self.cursor = 0
        self.dirty = False
        self._undo_snapshot = None

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
        
    def save(self) -> None:
        write_list_file(self.list_path, self.entries)
        self.dirty = False

    def _save_snapshot(self) -> None:
        self._undo_snapshot = (list(self.entries), self.cursor)

    def delete_current(self) -> None:
        self._save_snapshot()
        del self.entries[self.cursor]
        if self.cursor >= len(self.entries) and self.cursor > 0:
            self.cursor -= 1
        self.dirty = True

    def update_current_text(self, new_text: str) -> None:
        self._save_snapshot()
        self.entries[self.cursor] = replace(self.entries[self.cursor], text=new_text)
        self.dirty = True

    def undo(self) -> bool:
        if self._undo_snapshot is None:
            return False
        self.entries, self.cursor = self._undo_snapshot
        self._undo_snapshot = None
        self.dirty = True
        return True
    
    def can_undo(self) -> bool:
        return self._undo_snapshot is not None
    
    def is_empty(self) -> bool:
        return len(self.entries) == 0