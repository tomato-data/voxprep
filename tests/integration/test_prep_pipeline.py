import numpy as np
import soundfile as sf
from pathlib import Path

from voxprep.pipeline.workspace import Workspace
from voxprep.pipeline.runner import slice_step, asr_step, review_step
from voxprep.slicing.slicer import Slicer
from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.cli import app

from typer.testing import CliRunner
from tests.fixtures.doubles import FakeWhisperModel


def _build_two_segment_waveform(sr: int) -> np.ndarray:
    silence = np.zeros(int(sr * 0.5))
    loud = np.random.uniform(-0.5, 0.5, int(sr * 0.8)).astype(np.float32)
    return np.concatenate([loud, silence, loud])


def test_slice_step_runs_when_chunks_dir_empty(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    sf.write(raw / "x.wav", _build_two_segment_waveform(sr=16000), 16000)

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()

    slice_step(workspace=ws, raw_dir=raw, slicer=Slicer(sr=16000, min_length=500))

    chunks = sorted(ws.chunks_dir.glob("x_*.wav"))
    assert len(chunks) >= 2


def test_slice_step_skips_when_chunks_exist(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()
    (ws.chunks_dir / "existing.wav").touch()

    raw = tmp_path / "raw"
    raw.mkdir()

    slice_step(workspace=ws, raw_dir=raw, slicer=Slicer(sr=16000), skip_if_exists=True)

    assert (ws.chunks_dir / "existing.wav").exists()


def test_asr_step_writes_draft_list(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()
    (ws.chunks_dir / "a.wav").touch()
    (ws.chunks_dir / "b.wav").touch()

    fake_model = FakeWhisperModel(["hello"], language="en")
    transcriber = WhisperTranscriber(model=fake_model)

    asr_step(workspace=ws, transcriber=transcriber, speaker="myvoice")

    assert ws.draft_list.exists()
    lines = ws.draft_list.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert all("myvoice" in l for l in lines)


def test_review_step_creates_final_from_draft_when_missing(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure_root()
    ws.draft_list.write_text("a.wav|s|ko|hi\n", encoding="utf-8")

    review_step(workspace=ws, skip_review=True)

    assert ws.final_list.exists()
    assert ws.final_list.read_text(encoding="utf-8") == ws.draft_list.read_text(encoding="utf-8")



def test_prep_command_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "voxprep.commands.prep._build_transcriber",
        lambda **kwargs: WhisperTranscriber(model=FakeWhisperModel(["test"], "en")),
    )

    raw = tmp_path / "raw"
    raw.mkdir()
    sf.write(raw / "x.wav", _build_two_segment_waveform(16000), 16000)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "prep", str(raw),
            "--workspace", str(tmp_path / "ws"),
            "--speaker", "myvoice",
            "--language", "en",
            "--sample-rate", "16000",
            "--min-length", "500",
            "--skip-review",
        ]
    )

    assert result.exit_code == 0, result.output
    ws_root = tmp_path / "ws"
    assert (ws_root / "chunks").exists()
    assert (ws_root / "draft.list").exists()
    assert (ws_root / "final.list").exists()