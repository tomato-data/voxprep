from pathlib import Path

from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.commands.asr import run_asr_pipeline

from tests.fixtures.doubles import FakeWhisperModel


def test_run_asr_pipeline_writes_list(tmp_path: Path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.wav").touch()
    (src / "b.wav").touch()
    out_list = tmp_path / "out.list"

    model = FakeWhisperModel(["hello"], language="en")
    transcriber = WhisperTranscriber(model=model)

    run_asr_pipeline(
        transcriber=transcriber,
        input_dir=src,
        output_list=out_list,
        speaker="narrator",
    )

    lines = out_list.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert all(line.split("|")[1] == "narrator" for line in lines)
    assert all(line.split("|")[3] == "hello" for line in lines)
