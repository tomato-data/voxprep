"""Generate s2/s1 training configs from templates + user options."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from voxprep.extract.models_path import ModelsPaths


_S2_TEMPLATES = {
    "v1": "s2.json",
    "v2": "s2.json",
    "v2Pro": "s2v2Pro.json",
    "v2ProPlus": "s2v2ProPlus.json",
    "v3": "s2.json",
    "v4": "s2.json",
}

_S1_TEMPLATES = {
    "v1": "s1longer.yaml",
    "v2": "s1longer-v2.yaml",
    "v2Pro": "s1longer-v2.yaml",
    "v2ProPlus": "s1longer-v2.yaml",
    "v3": "s1longer-v2.yaml",
    "v4": "s1longer-v2.yaml",
}

_SOVITS_WEIGHTS_DIR = {
    "v1": "SoVITS_weights",
    "v2": "SoVITS_weights_v2",
    "v2Pro": "SoVITS_weights_v2Pro",
    "v2ProPlus": "SoVITS_weights_v2ProPlus",
    "v3": "SoVITS_weights_v3",
    "v4": "SoVITS_weights_v4",
}

_GPT_WEIGHTS_DIR = {
    "v1": "GPT_weights",
    "v2": "GPT_weights_v2",
    "v2Pro": "GPT_weights_v2Pro",
    "v2ProPlus": "GPT_weights_v2ProPlus",
    "v3": "GPT_weights_v3",
    "v4": "GPT_weights_v4",
}


@dataclass(frozen=True)
class SovitsTrainOptions:
    exp_name: str
    exp_dir: Path
    weights_dir: Path
    version: str = "v2Pro"
    batch_size: int = 1
    epochs: int = 10
    save_every: int = 4
    save_every_weights: bool = True
    save_latest: bool = True
    text_low_lr_rate: float = 0.4
    grad_ckpt: bool = False
    lora_rank: int = 32
    is_half: bool = False
    gpus: str = "0"


@dataclass(frozen=True)
class GptTrainOptions:
    exp_name: str
    exp_dir: Path
    weights_dir: Path
    version: str = "v2Pro"
    batch_size: int = 1
    epochs: int = 20
    save_every: int = 4
    save_every_weights: bool = True
    save_latest: bool = True
    if_dpo: bool = False
    is_half: bool = False
    gpus: str = "0"


def _s2_template_path(version: str) -> Path:
    return Path(__file__).resolve().parents[1] / "extract" / "configs" / _S2_TEMPLATES[version]


def _s1_template_path(version: str) -> Path:
    return Path(__file__).resolve().parents[1] / "extract" / "configs" / _S1_TEMPLATES[version]


def build_sovits_config(opts: SovitsTrainOptions, models: ModelsPaths) -> dict:
    with open(_s2_template_path(opts.version), "r", encoding="utf-8") as f:
        data = json.load(f)

    batch = opts.batch_size if opts.is_half else max(opts.batch_size // 2, 1)
    data["train"]["batch_size"] = batch
    data["train"]["epochs"] = opts.epochs
    data["train"]["text_low_lr_rate"] = opts.text_low_lr_rate
    data["train"]["pretrained_s2G"] = str(models.sovits_pretrained(opts.version))
    # s2D path (discriminator) — mirror s2G naming
    s2d_map = {
        "v1": models.root / "pretrained/s2D488k.pth",
        "v2": models.root / "pretrained/gsv-v2final-pretrained/s2D2333k.pth",
        "v2Pro": models.root / "pretrained/v2Pro/s2Dv2Pro.pth",
        "v2ProPlus": models.root / "pretrained/v2Pro/s2Dv2ProPlus.pth",
        "v3": models.root / "pretrained/s2D488k.pth",
        "v4": models.root / "pretrained/s2D488k.pth",
    }
    data["train"]["pretrained_s2D"] = str(s2d_map[opts.version])
    data["train"]["if_save_latest"] = opts.save_latest
    data["train"]["if_save_every_weights"] = opts.save_every_weights
    data["train"]["save_every_epoch"] = opts.save_every
    data["train"]["gpu_numbers"] = opts.gpus
    data["train"]["grad_ckpt"] = opts.grad_ckpt
    data["train"]["lora_rank"] = opts.lora_rank
    if not opts.is_half:
        data["train"]["fp16_run"] = False

    if "model" not in data:
        data["model"] = {}
    data["model"]["version"] = opts.version

    if "data" not in data:
        data["data"] = {}
    data["data"]["exp_dir"] = str(opts.exp_dir)

    data["s2_ckpt_dir"] = str(opts.exp_dir)
    data["save_weight_dir"] = str(opts.weights_dir)
    data["name"] = opts.exp_name
    data["version"] = opts.version
    return data


def build_gpt_config(opts: GptTrainOptions, models: ModelsPaths) -> dict:
    with open(_s1_template_path(opts.version), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    batch = opts.batch_size if opts.is_half else max(opts.batch_size // 2, 1)
    data.setdefault("train", {})
    data["train"]["batch_size"] = batch
    data["train"]["epochs"] = opts.epochs
    data["train"]["save_every_n_epoch"] = opts.save_every
    data["train"]["if_save_every_weights"] = opts.save_every_weights
    data["train"]["if_save_latest"] = opts.save_latest
    data["train"]["if_dpo"] = opts.if_dpo
    data["train"]["half_weights_save_dir"] = str(opts.weights_dir)
    data["train"]["exp_name"] = opts.exp_name
    if not opts.is_half:
        data["train"]["precision"] = "32"

    data["train_semantic_path"] = str(opts.exp_dir / "6-name2semantic.tsv")
    data["train_phoneme_path"] = str(opts.exp_dir / "2-name2text.txt")
    data["output_dir"] = str(opts.exp_dir / f"logs_s1_{opts.version}")
    data["pretrained_s1"] = str(models.gpt_pretrained(opts.version))
    return data


def write_sovits_config(data: dict, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return target


def write_gpt_config(data: dict, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return target


def sovits_weights_dir(models: ModelsPaths, version: str) -> Path:
    return models.root / "trained" / _SOVITS_WEIGHTS_DIR[version]


def gpt_weights_dir(models: ModelsPaths, version: str) -> Path:
    return models.root / "trained" / _GPT_WEIGHTS_DIR[version]
