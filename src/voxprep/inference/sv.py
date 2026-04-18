"""SV (speaker vector) encoder — ported from GPT-SoVITS/sv.py.

Uses ERes2NetV2 with fixed checkpoint path resolved via ModelsPaths.
"""
from __future__ import annotations

import torch

from voxprep.extract.eres2net.ERes2NetV2 import ERes2NetV2
from voxprep.extract.eres2net import kaldi as Kaldi
from voxprep.extract.models_path import ModelsPaths


class SV:
    def __init__(self, device, is_half, models: ModelsPaths | None = None):
        paths = models or ModelsPaths()
        sv_path = paths.require(paths.sv_ckpt, "Speaker vector checkpoint")
        state = torch.load(str(sv_path), map_location="cpu", weights_only=False)
        model = ERes2NetV2(baseWidth=24, scale=4, expansion=4)
        model.load_state_dict(state)
        model.eval()
        self.embedding_model = model.half().to(device) if is_half else model.to(device)
        self.is_half = is_half

    def compute_embedding3(self, wav):
        with torch.no_grad():
            if self.is_half:
                wav = wav.half()
            feat = torch.stack(
                [
                    Kaldi.fbank(w.unsqueeze(0), num_mel_bins=80, sample_frequency=16000, dither=0)
                    for w in wav
                ]
            )
            return self.embedding_model.forward3(feat)
