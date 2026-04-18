import json
from pathlib import Path

import pytest
import yaml

from voxprep.gptsovits.paths import GptSovitsPaths
from voxprep.gptsovits.config_builder import (
    SovitsTrainConfig,
    GptTrainConfig,
    build_sovits_config,
    build_gpt_config,
    write_sovits_temp_config,
    write_gpt_temp_config,
)


@pytest.fixture
def fake_gsv_root(tmp_path):
    root = tmp_path / "GPT-SoVITS"
    configs = root / "GPT_SoVITS" / "configs"
    configs.mkdir(parents=True)

    s2_template = {
        "train": {"batch_size": 32, "epochs": 100},
        "model": {"version": "v2Pro"},
        "data": {"exp_dir": ""},
    }
    (configs / "s2v2Pro.json").write_text(json.dumps(s2_template), encoding="utf-8")

    s1_template = {
        "train": {"batch_size": 8, "epochs": 20, "precision": "16-mixed"},
        "output_dir": "",
        "pretrained_s1": "",
    }
    (configs / "s1longer-v2.yaml").write_text(yaml.safe_dump(s1_template), encoding="utf-8")

    return root


def test_build_sovits_config_injects_user_options(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = SovitsTrainConfig(exp_name="myvoice", batch_size=2, epochs=10, save_every=4)

    data = build_sovits_config(paths, options)

    assert data["train"]["epochs"] == 10
    assert data["train"]["save_every_epoch"] == 4
    assert data["name"] == "myvoice"
    assert data["version"] == "v2Pro"
    assert data["save_weight_dir"].endswith("SoVITS_weights_v2Pro")


def test_build_sovits_config_halves_batch_when_not_half(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = SovitsTrainConfig(exp_name="e", batch_size=4, is_half=False)

    data = build_sovits_config(paths, options)

    assert data["train"]["batch_size"] == 2
    assert data["train"]["fp16_run"] is False


def test_build_sovits_config_keeps_batch_when_half(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = SovitsTrainConfig(exp_name="e", batch_size=4, is_half=True)

    data = build_sovits_config(paths, options)

    assert data["train"]["batch_size"] == 4


def test_build_gpt_config_injects_paths(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = GptTrainConfig(exp_name="myvoice", epochs=20, save_every=4)

    data = build_gpt_config(paths, options)

    assert data["train"]["epochs"] == 20
    assert data["train"]["exp_name"] == "myvoice"
    assert data["train_semantic_path"].endswith("logs/myvoice/6-name2semantic.tsv")
    assert data["train_phoneme_path"].endswith("logs/myvoice/2-name2text.txt")
    assert data["pretrained_s1"].endswith("s1v3.ckpt")


def test_build_gpt_config_sets_precision_32_when_not_half(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = GptTrainConfig(exp_name="e", is_half=False)

    data = build_gpt_config(paths, options)

    assert data["train"]["precision"] == "32"


def test_write_sovits_temp_config_writes_to_temp(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = SovitsTrainConfig(exp_name="e")
    data = build_sovits_config(paths, options)

    out = write_sovits_temp_config(paths, data)

    assert out == fake_gsv_root / "TEMP" / "tmp_s2.json"
    assert json.loads(out.read_text())["name"] == "e"


def test_write_gpt_temp_config_writes_to_temp(fake_gsv_root):
    paths = GptSovitsPaths(root=fake_gsv_root, version="v2Pro")
    options = GptTrainConfig(exp_name="e")
    data = build_gpt_config(paths, options)

    out = write_gpt_temp_config(paths, data)

    assert out == fake_gsv_root / "TEMP" / "tmp_s1.yaml"
    assert yaml.safe_load(out.read_text())["train"]["exp_name"] == "e"
