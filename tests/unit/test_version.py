from typer.testing import CliRunner

from voxprep.cli import app

runner = CliRunner()

def test_version_command_prints_package_version():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.0.1" in result.stdout