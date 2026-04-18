from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def chunks_dir(self) -> Path:
        return self.root / "chunks"
    
    @property
    def draft_list(self) -> Path:
        return self.root / "draft.list"
    
    @property
    def final_list(self) -> Path:
        return self.root / "final.list"
    
    def ensure_root(self) -> None:
        self.chunks_dir.mkdir(parents=True, exist_ok=True)