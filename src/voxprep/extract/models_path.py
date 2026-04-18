import os
from pathlib import Path


def resolve_models_root(cli_override: Path | None = None) -> Path:
    if cli_override is not None:
        return cli_override.resolve()
    env = os.environ.get("VOXPREP_MODELS_ROOT")
    if env:
        return Path(env).resolve()
    project_models = Path(__file__).resolve().parents[3] / "models"
    if project_models.exists():
        return project_models
    return Path.home() / ".voxprep" / "models"


class ModelsPaths:
    def __init__(self, root: Path | None = None) -> None:
        self.root = resolve_models_root(root)

    @property
    def bert_dir(self) -> Path:
        return self.root / "pretrained" / "chinese-roberta-wwm-ext-large"

    @property
    def cnhubert_dir(self) -> Path:
        return self.root / "pretrained" / "chinese-hubert-base"

    @property
    def sv_ckpt(self) -> Path:
        return self.root / "pretrained" / "sv" / "pretrained_eres2netv2w24s4ep4.ckpt"

    @property
    def g2pw_model_dir(self) -> Path:
        return self.root / "g2pw" / "G2PWModel"

    def sovits_pretrained(self, version: str) -> Path:
        mapping = {
            "v1": "s2G488k.pth",
            "v2": "gsv-v2final-pretrained/s2G2333k.pth",
            "v2Pro": "v2Pro/s2Gv2Pro.pth",
            "v2ProPlus": "v2Pro/s2Gv2ProPlus.pth",
            "v3": "s2Gv3.pth",
            "v4": "gsv-v4-pretrained/s2Gv4.pth",
        }
        return self.root / "pretrained" / mapping[version]

    def gpt_pretrained(self, version: str) -> Path:
        mapping = {
            "v1": "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
            "v2": "gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
            "v2Pro": "s1v3.ckpt",
            "v2ProPlus": "s1v3.ckpt",
            "v3": "s1v3.ckpt",
            "v4": "s1v3.ckpt",
        }
        return self.root / "pretrained" / mapping[version]

    def require(self, path: Path, what: str) -> Path:
        if not path.exists():
            raise FileNotFoundError(
                f"{what} not found at {path}. "
                "Download pretrained models (see SETUP_GUIDE.md) and place under "
                f"{self.root} — or override with VOXPREP_MODELS_ROOT / --models-root."
            )
        return path


def select_device(prefer_half: bool = False) -> tuple[str, bool]:
    import torch

    if torch.cuda.is_available():
        return "cuda:0", prefer_half
    return "cpu", False
