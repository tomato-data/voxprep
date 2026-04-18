from dataclasses import dataclass
from pathlib import Path
import os


SUPPORTED_VERSIONS = {"v1", "v2", "v2Pro", "v2ProPlus", "v3", "v4"}


_PRETRAINED_S2G = {
    "v1": "GPT_SoVITS/pretrained_models/s2G488k.pth",
    "v2": "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth",
    "v2Pro": "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth",
    "v2ProPlus": "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth",
    "v3": "GPT_SoVITS/pretrained_models/s2Gv3.pth",
    "v4": "GPT_SoVITS/pretrained_models/gsv-v4-pretrained/s2Gv4.pth",
}

_PRETRAINED_S2D = {
    "v1": "GPT_SoVITS/pretrained_models/s2D488k.pth",
    "v2": "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2D2333k.pth",
    "v2Pro": "GPT_SoVITS/pretrained_models/v2Pro/s2Dv2Pro.pth",
    "v2ProPlus": "GPT_SoVITS/pretrained_models/v2Pro/s2Dv2ProPlus.pth",
}

_PRETRAINED_S1 = {
    "v1": "GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
    "v2": "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
    "v2Pro": "GPT_SoVITS/pretrained_models/s1v3.ckpt",
    "v2ProPlus": "GPT_SoVITS/pretrained_models/s1v3.ckpt",
    "v3": "GPT_SoVITS/pretrained_models/s1v3.ckpt",
    "v4": "GPT_SoVITS/pretrained_models/s1v3.ckpt",
}

_SOVITS_WEIGHTS_ROOT = {
    "v1": "SoVITS_weights",
    "v2": "SoVITS_weights_v2",
    "v2Pro": "SoVITS_weights_v2Pro",
    "v2ProPlus": "SoVITS_weights_v2ProPlus",
    "v3": "SoVITS_weights_v3",
    "v4": "SoVITS_weights_v4",
}

_GPT_WEIGHTS_ROOT = {
    "v1": "GPT_weights",
    "v2": "GPT_weights_v2",
    "v2Pro": "GPT_weights_v2Pro",
    "v2ProPlus": "GPT_weights_v2ProPlus",
    "v3": "GPT_weights_v3",
    "v4": "GPT_weights_v4",
}

_S2_CONFIG_TEMPLATE = {
    "v1": "GPT_SoVITS/configs/s2.json",
    "v2": "GPT_SoVITS/configs/s2.json",
    "v2Pro": "GPT_SoVITS/configs/s2v2Pro.json",
    "v2ProPlus": "GPT_SoVITS/configs/s2v2ProPlus.json",
    "v3": "GPT_SoVITS/configs/s2.json",
    "v4": "GPT_SoVITS/configs/s2.json",
}

_S1_CONFIG_TEMPLATE = {
    "v1": "GPT_SoVITS/configs/s1longer.yaml",
    "v2": "GPT_SoVITS/configs/s1longer-v2.yaml",
    "v2Pro": "GPT_SoVITS/configs/s1longer-v2.yaml",
    "v2ProPlus": "GPT_SoVITS/configs/s1longer-v2.yaml",
    "v3": "GPT_SoVITS/configs/s1longer-v2.yaml",
    "v4": "GPT_SoVITS/configs/s1longer-v2.yaml",
}


@dataclass(frozen=True)
class GptSovitsPaths:
    root: Path
    version: str

    @property
    def bert_dir(self) -> Path:
        return self.root / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"

    @property
    def cnhubert_dir(self) -> Path:
        return self.root / "GPT_SoVITS/pretrained_models/chinese-hubert-base"

    @property
    def sv_ckpt(self) -> Path:
        return self.root / "GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt"

    @property
    def pretrained_s2g(self) -> Path:
        return self.root / _PRETRAINED_S2G[self.version]

    @property
    def pretrained_s2d(self) -> Path:
        return self.root / _PRETRAINED_S2D.get(self.version, _PRETRAINED_S2D["v2"])

    @property
    def pretrained_s1(self) -> Path:
        return self.root / _PRETRAINED_S1[self.version]

    @property
    def sovits_weights_dir(self) -> Path:
        return self.root / _SOVITS_WEIGHTS_ROOT[self.version]

    @property
    def gpt_weights_dir(self) -> Path:
        return self.root / _GPT_WEIGHTS_ROOT[self.version]

    @property
    def s2_config_template(self) -> Path:
        return self.root / _S2_CONFIG_TEMPLATE[self.version]

    @property
    def s1_config_template(self) -> Path:
        return self.root / _S1_CONFIG_TEMPLATE[self.version]

    def exp_log_dir(self, exp_name: str) -> Path:
        return self.root / "logs" / exp_name

    def temp_dir(self) -> Path:
        return self.root / "TEMP"


def resolve_root(cli_override: Path | None = None) -> Path:
    if cli_override is not None:
        return cli_override.resolve()
    env = os.environ.get("VOXPREP_GPT_SOVITS_ROOT") or os.environ.get("GPT_SOVITS_ROOT")
    if env:
        return Path(env).resolve()
    bundled = Path(__file__).resolve().parents[3] / "GPT-SoVITS"
    if bundled.exists():
        return bundled
    raise FileNotFoundError(
        "GPT-SoVITS root not found. Pass --gpt-sovits-root or set "
        "VOXPREP_GPT_SOVITS_ROOT env var."
    )


def validate_version(version: str) -> None:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"unsupported version {version!r}. Choose from: {sorted(SUPPORTED_VERSIONS)}"
        )
