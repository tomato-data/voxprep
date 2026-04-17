import soundfile as sf
from pathlib import Path
from typer.testing import CliRunner

from voxprep.cli import app

from tests.fixtures.audio import build_two_segment_waveform

runner = CliRunner()


def test_slice_command_writes_chunks(tmp_path: Path):
    sr = 16000
    src_dir = tmp_path / "in"
    dst_dir = tmp_path / "out"
    src_dir.mkdir()

    waveform = build_two_segment_waveform(sr)
    sf.write(str(src_dir / "sample.wav"), waveform, sr)

    result = runner.invoke(
        app,
        [
            "slice", str(src_dir), str(dst_dir),
            "--sample-rate", "16000",
            "--min-length", "500",
            "--threshold", "-40"
        ],
    )

    assert result.exit_code == 0, result.output
    out_files = sorted(dst_dir.glob("sample_*.wav"))
    assert len(out_files) >= 2
