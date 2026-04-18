"""Semantic token extraction — ported from GPT-SoVITS/prepare_datasets/3-get-semantic.py."""
from __future__ import annotations

import os
import traceback
from pathlib import Path

import torch

from voxprep.extract.hparams import get_hparams_from_file
from voxprep.extract.models_path import ModelsPaths, select_device


def _detect_version(s2g_path: Path) -> str:
    size = s2g_path.stat().st_size
    if size < 82978 * 1024:
        return "v1"
    if size < 100 * 1024 * 1024:
        return "v2"
    if size < 103520 * 1024:
        return "v1"
    if size < 700 * 1024 * 1024:
        return "v2"
    return "v3"


def _clean_path(p: str) -> str:
    return p.strip().strip('"').strip("'").strip()


def _config_template_for(version: str, repo_root: Path) -> Path:
    mapping = {
        "v1": "s2.json",
        "v2": "s2.json",
        "v2Pro": "s2v2Pro.json",
        "v2ProPlus": "s2v2ProPlus.json",
        "v3": "s2.json",
        "v4": "s2.json",
    }
    return repo_root / "src" / "voxprep" / "extract" / "configs" / mapping[version]


def extract_semantic_tokens(
    list_file: Path,
    opt_dir: Path,
    models: ModelsPaths,
    version: str = "v2Pro",
    s2config_path: Path | None = None,
    is_half: bool = False,
    progress_cb=None,
) -> Path:
    """Quantize HuBERT features to semantic tokens for every chunk.

    Inputs:
      - {opt_dir}/4-cnhubert/*.pt  (from hubert_features step)
    Output:
      - {opt_dir}/6-name2semantic.tsv
    """
    s2g = models.require(models.sovits_pretrained(version), f"SoVITS {version} s2G")
    device, is_half = select_device(prefer_half=is_half)
    detected_version = _detect_version(s2g) if version == "auto" else version

    if s2config_path is None:
        # look for bundled config inside voxprep
        project_root = Path(__file__).resolve().parents[3]
        s2config_path = _config_template_for(detected_version, project_root)
    if not s2config_path.exists():
        raise FileNotFoundError(f"s2 config template not found: {s2config_path}")

    hps = get_hparams_from_file(s2config_path)

    if detected_version == "v3":
        from voxprep.extract.module.models import SynthesizerTrnV3 as Synth
    else:
        from voxprep.extract.module.models import SynthesizerTrn as Synth

    vq_model = Synth(
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        n_speakers=hps.data.n_speakers,
        version=detected_version,
        **hps.model,
    )
    vq_model = vq_model.half().to(device) if is_half else vq_model.to(device)
    vq_model.eval()

    state = torch.load(s2g, map_location="cpu", weights_only=False)["weight"]
    missing, unexpected = vq_model.load_state_dict(state, strict=False)
    if missing:
        print(f"[semantic] missing keys: {len(missing)} (e.g. {missing[:3]})")
    if unexpected:
        print(f"[semantic] unexpected keys: {len(unexpected)}")

    hubert_dir = opt_dir / "4-cnhubert"
    out_path = opt_dir / "6-name2semantic.tsv"
    opt_dir.mkdir(parents=True, exist_ok=True)

    with open(list_file, "r", encoding="utf-8") as f:
        lines = [ln for ln in f.read().strip("\n").split("\n") if ln.strip()]

    results: list[str] = ["item_name\tsemantic_audio"]
    for idx, line in enumerate(lines, 1):
        try:
            wav_name, _spk, _lang, _text = line.split("|")
            wav_name = os.path.basename(_clean_path(wav_name))
            hubert_path = hubert_dir / f"{wav_name}.pt"
            if not hubert_path.exists():
                continue
            ssl = torch.load(hubert_path, map_location="cpu", weights_only=False)
            ssl = ssl.half().to(device) if is_half else ssl.to(device)
            codes = vq_model.extract_latent(ssl)
            semantic = " ".join(str(v) for v in codes[0, 0, :].tolist())
            results.append(f"{wav_name}\t{semantic}")
            if progress_cb is not None:
                progress_cb(idx, len(lines), wav_name)
        except Exception:
            print(line, traceback.format_exc())

    out_path.write_text("\n".join(results), encoding="utf-8")
    return out_path
