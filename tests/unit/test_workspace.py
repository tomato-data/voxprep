from pathlib import Path

from voxprep.pipeline.workspace import Workspace


def test_workspace_paths(tmp_path):
    ws = Workspace(root=tmp_path / "myvoice")

    assert ws.chunks_dir == tmp_path / "myvoice" / "chunks"
    assert ws.draft_list == tmp_path / "myvoice" / "draft.list"
    assert ws.final_list == tmp_path / "myvoice" / "final.list"


def test_ensure_root_creates_directories(tmp_path):
    ws = Workspace(root=tmp_path / "myvoice")

    ws.ensure_root()

    assert ws.root.exists()
    assert ws.chunks_dir.exists()