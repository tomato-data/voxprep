"""HuBERT + 32kHz resample — ported from GPT-SoVITS/prepare_datasets/2-get-hubert-wav32k.py."""
from __future__ import annotations

import os
import shutil
import traceback
from pathlib import Path
from time import time as _now

import librosa
import numpy as np
import torch
from scipy.io import wavfile

from voxprep.extract.cnhubert import load_cnhubert
from voxprep.extract.models_path import ModelsPaths, select_device


_MAXX = 0.95
_ALPHA = 0.5


def _safe_torch_save(tensor: torch.Tensor, dst: Path) -> None:
    tmp = Path(f"{_now()}.pth")
    torch.save(tensor, tmp)
    shutil.move(str(tmp), str(dst))


def _load_audio_32k(path: Path) -> np.ndarray:
    y, _ = librosa.load(str(path), sr=32000, mono=True)
    return y.astype(np.float32)


def _clean_path(p: str) -> str:
    return p.strip().strip('"').strip("'").strip()


def extract_hubert_features(
    list_file: Path,
    wav_dir: Path | None,
    opt_dir: Path,
    models: ModelsPaths,
    is_half: bool = False,
    progress_cb=None,
) -> tuple[Path, Path]:
    """Run HuBERT feature extraction + 32kHz resample for every audio in list_file.

    Outputs:
      - {opt_dir}/4-cnhubert/*.pt   (HuBERT SSL features)
      - {opt_dir}/5-wav32k/*.wav    (resampled 32kHz audio)
    """
    base = models.require(models.cnhubert_dir, "CNHuBERT pretrained")
    device, is_half = select_device(prefer_half=is_half)

    hubert_out = opt_dir / "4-cnhubert"
    wav32_out = opt_dir / "5-wav32k"
    hubert_out.mkdir(parents=True, exist_ok=True)
    wav32_out.mkdir(parents=True, exist_ok=True)

    model = load_cnhubert(base)
    if is_half:
        model = model.half().to(device)
    else:
        model = model.to(device)

    def _process_one(wav_name: str, wav_path: Path, half: bool) -> bool:
        target = hubert_out / f"{wav_name}.pt"
        if target.exists():
            return True
        audio = _load_audio_32k(wav_path)
        peak = np.abs(audio).max()
        if peak > 2.2:
            print(f"{wav_name} filtered (peak={peak})")
            return True
        audio32_int = (audio / peak * (_MAXX * _ALPHA * 32768)) + ((1 - _ALPHA) * 32768) * audio
        audio32_small = (audio / peak * (_MAXX * _ALPHA * 1145.14)) + ((1 - _ALPHA) * 1145.14) * audio
        audio_16k = librosa.resample(audio32_small, orig_sr=32000, target_sr=16000)
        wav_t = torch.from_numpy(audio_16k)
        wav_t = wav_t.half().to(device) if half else wav_t.to(device)
        ssl = model.model(wav_t.unsqueeze(0))["last_hidden_state"].transpose(1, 2).cpu()
        if np.isnan(ssl.detach().numpy()).sum() != 0:
            print(f"nan filtered: {wav_name}")
            return False
        wavfile.write(str(wav32_out / wav_name), 32000, audio32_int.astype("int16"))
        _safe_torch_save(ssl, target)
        return True

    with open(list_file, "r", encoding="utf-8") as f:
        lines = [ln for ln in f.read().strip("\n").split("\n") if ln.strip()]

    nan_retries: list[tuple[str, Path]] = []
    for idx, line in enumerate(lines, 1):
        try:
            wav_name, _spk, _lang, _text = line.split("|")
            wav_name = _clean_path(wav_name)
            if wav_dir is not None:
                wav_name = os.path.basename(wav_name)
                wav_path = wav_dir / wav_name
            else:
                wav_path = Path(wav_name)
                wav_name = wav_path.name
            ok = _process_one(wav_name, wav_path, half=is_half)
            if not ok:
                nan_retries.append((wav_name, wav_path))
            if progress_cb is not None:
                progress_cb(idx, len(lines), wav_name)
        except Exception:
            print(line, traceback.format_exc())

    if nan_retries and is_half:
        print(f"Retrying {len(nan_retries)} nan failures in fp32...")
        model = model.float()
        for wav_name, wav_path in nan_retries:
            try:
                _process_one(wav_name, wav_path, half=False)
            except Exception:
                print(wav_name, traceback.format_exc())

    return hubert_out, wav32_out
