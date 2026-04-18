"""CNHuBERT wrapper — ported from GPT-SoVITS/feature_extractor/cnhubert.py."""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from transformers import HubertModel, Wav2Vec2FeatureExtractor
from transformers import logging as tf_logging

tf_logging.set_verbosity_error()


class CNHubert(nn.Module):
    def __init__(self, base_path: Path) -> None:
        super().__init__()
        if not Path(base_path).exists():
            raise FileNotFoundError(base_path)
        self.model = HubertModel.from_pretrained(str(base_path), local_files_only=True)
        self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
            str(base_path), local_files_only=True
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        values = self.feature_extractor(
            x, return_tensors="pt", sampling_rate=16000
        ).input_values.to(x.device)
        return self.model(values)["last_hidden_state"]


def load_cnhubert(base_path: Path) -> CNHubert:
    model = CNHubert(base_path)
    model.eval()
    return model
