from pathlib import Path

import pytest

from voxprep.gptsovits.paths import GptSovitsPaths, validate_version, resolve_root


def test_v2pro_pretrained_paths():
    paths = GptSovitsPaths(root=Path("/tmp/gsv"), version="v2Pro")

    assert paths.pretrained_s2g == Path("/tmp/gsv/GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth")
    assert paths.pretrained_s1 == Path("/tmp/gsv/GPT_SoVITS/pretrained_models/s1v3.ckpt")
    assert paths.sovits_weights_dir == Path("/tmp/gsv/SoVITS_weights_v2Pro")
    assert paths.gpt_weights_dir == Path("/tmp/gsv/GPT_weights_v2Pro")


def test_exp_log_dir():
    paths = GptSovitsPaths(root=Path("/tmp/gsv"), version="v2Pro")

    assert paths.exp_log_dir("myvoice") == Path("/tmp/gsv/logs/myvoice")


def test_validate_version_rejects_unknown():
    with pytest.raises(ValueError, match="unsupported version"):
        validate_version("v99")


def test_validate_version_accepts_known():
    validate_version("v2Pro")


def test_resolve_root_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("VOXPREP_GPT_SOVITS_ROOT", str(tmp_path))

    assert resolve_root() == tmp_path.resolve()


def test_resolve_root_cli_wins_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("VOXPREP_GPT_SOVITS_ROOT", "/nonexistent")
    override = tmp_path / "custom"
    override.mkdir()

    assert resolve_root(override) == override.resolve()
