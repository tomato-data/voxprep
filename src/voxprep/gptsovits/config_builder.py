import json
from dataclasses import dataclass
from pathlib import Path

from voxprep.gptsovits.paths import GptSovitsPaths


@dataclass(frozen=True)
class SovitsTrainConfig:
    exp_name: str
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
class GptTrainConfig:
    exp_name: str
    batch_size: int = 1
    epochs: int = 20
    save_every: int = 4
    save_every_weights: bool = True
    save_latest: bool = True
    if_dpo: bool = False
    is_half: bool = False
    gpus: str = "0"


def build_sovits_config(paths: GptSovitsPaths, options: SovitsTrainConfig) -> dict:
    with open(paths.s2_config_template, "r", encoding="utf-8") as f:
        data = json.load(f)

    batch = options.batch_size if options.is_half else max(options.batch_size // 2, 1)
    data["train"]["batch_size"] = batch
    data["train"]["epochs"] = options.epochs
    data["train"]["text_low_lr_rate"] = options.text_low_lr_rate
    data["train"]["pretrained_s2G"] = str(paths.pretrained_s2g)
    data["train"]["pretrained_s2D"] = str(paths.pretrained_s2d)
    data["train"]["if_save_latest"] = options.save_latest
    data["train"]["if_save_every_weights"] = options.save_every_weights
    data["train"]["save_every_epoch"] = options.save_every
    data["train"]["gpu_numbers"] = options.gpus
    data["train"]["grad_ckpt"] = options.grad_ckpt
    data["train"]["lora_rank"] = options.lora_rank
    if not options.is_half:
        data["train"]["fp16_run"] = False
    data["model"]["version"] = paths.version
    data["data"]["exp_dir"] = str(paths.exp_log_dir(options.exp_name))
    data["s2_ckpt_dir"] = str(paths.exp_log_dir(options.exp_name))
    data["save_weight_dir"] = str(paths.sovits_weights_dir)
    data["name"] = options.exp_name
    data["version"] = paths.version
    return data


def build_gpt_config(paths: GptSovitsPaths, options: GptTrainConfig) -> dict:
    import yaml

    with open(paths.s1_config_template, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    batch = options.batch_size if options.is_half else max(options.batch_size // 2, 1)
    data["train"]["batch_size"] = batch
    data["train"]["epochs"] = options.epochs
    data["train"]["save_every_n_epoch"] = options.save_every
    data["train"]["if_save_every_weights"] = options.save_every_weights
    data["train"]["if_save_latest"] = options.save_latest
    data["train"]["if_dpo"] = options.if_dpo
    data["train"]["half_weights_save_dir"] = str(paths.gpt_weights_dir)
    data["train"]["exp_name"] = options.exp_name
    if not options.is_half:
        data["train"]["precision"] = "32"
    exp_log = paths.exp_log_dir(options.exp_name)
    data["train_semantic_path"] = str(exp_log / "6-name2semantic.tsv")
    data["train_phoneme_path"] = str(exp_log / "2-name2text.txt")
    data["output_dir"] = str(exp_log / f"logs_s1_{paths.version}")
    data["pretrained_s1"] = str(paths.pretrained_s1)
    return data


def write_sovits_temp_config(paths: GptSovitsPaths, data: dict) -> Path:
    temp = paths.temp_dir()
    temp.mkdir(parents=True, exist_ok=True)
    out = temp / "tmp_s2.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out


def write_gpt_temp_config(paths: GptSovitsPaths, data: dict) -> Path:
    import yaml

    temp = paths.temp_dir()
    temp.mkdir(parents=True, exist_ok=True)
    out = temp / "tmp_s1.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return out
