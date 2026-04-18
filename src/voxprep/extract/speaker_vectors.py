"""Speaker vector extraction — ported from GPT-SoVITS/prepare_datasets/2-get-sv.py.

Only needed for v2Pro / v2ProPlus versions.
"""
from __future__ import annotations

import os
import shutil
import traceback
from pathlib import Path
from time import time as _now

import torch
import torchaudio

from voxprep.extract.eres2net.ERes2NetV2 import ERes2NetV2
from voxprep.extract.eres2net import kaldi as Kaldi
from voxprep.extract.models_path import ModelsPaths, select_device


def _safe_torch_save(tensor: torch.Tensor, dst: Path) -> None:
    tmp = Path(f"{_now()}.pth")
    torch.save(tensor, tmp)
    shutil.move(str(tmp), str(dst))


def _clean_path(p: str) -> str:
    return p.strip().strip('"').strip("'").strip()


class SpeakerEncoder:
    def __init__(self, sv_path: Path, device: str, is_half: bool) -> None:
        state = torch.load(sv_path, map_location="cpu", weights_only=False)
        model = ERes2NetV2(baseWidth=24, scale=4, expansion=4)
        model.load_state_dict(state)
        model.eval()
        self.resample = torchaudio.transforms.Resample(32000, 16000).to(device)
        self.model = model.half().to(device) if is_half else model.to(device)
        self.is_half = is_half
        self.device = device

    def embed(self, wav32k: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            wav = self.resample(wav32k)
            if self.is_half:
                wav = wav.half()
            feat = torch.stack(
                [
                    Kaldi.fbank(w.unsqueeze(0), num_mel_bins=80, sample_frequency=16000, dither=0)
                    for w in wav
                ]
            )
            return self.model.forward3(feat)


def extract_speaker_vectors(
    list_file: Path,
    opt_dir: Path,
    models: ModelsPaths,
    is_half: bool = False,
    progress_cb=None,
) -> Path:
    """Extract speaker vectors (v2Pro) from resampled 32kHz audio.

    Requires {opt_dir}/5-wav32k/ from hubert step.
    Output: {opt_dir}/7-sv_cn/*.pt
    """
    sv_path = models.require(models.sv_ckpt, "Speaker vector checkpoint")
    device, is_half = select_device(prefer_half=is_half)

    wav32_dir = opt_dir / "5-wav32k"
    out_dir = opt_dir / "7-sv_cn"
    out_dir.mkdir(parents=True, exist_ok=True)

    encoder = SpeakerEncoder(sv_path, device=device, is_half=is_half)

    with open(list_file, "r", encoding="utf-8") as f:
        lines = [ln for ln in f.read().strip("\n").split("\n") if ln.strip()]

    for idx, line in enumerate(lines, 1):
        try:
            wav_name, _spk, _lang, _text = line.split("|")
            wav_name = os.path.basename(_clean_path(wav_name))
            target = out_dir / f"{wav_name}.pt"
            if target.exists():
                continue
            wav_path = wav32_dir / wav_name
            wav32k, sr = torchaudio.load(str(wav_path))
            assert sr == 32000, f"expected 32kHz, got {sr} for {wav_path}"
            wav32k = wav32k.to(device)
            emb = encoder.embed(wav32k).cpu()
            _safe_torch_save(emb, target)
            if progress_cb is not None:
                progress_cb(idx, len(lines), wav_name)
        except Exception:
            print(line, traceback.format_exc())

    return out_dir
