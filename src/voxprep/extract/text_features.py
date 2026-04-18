"""Text + BERT feature extraction — ported from GPT-SoVITS/prepare_datasets/1-get-text.py."""
from __future__ import annotations

import os
import shutil
import traceback
from pathlib import Path
from time import time as _now
from typing import Iterable

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

from voxprep.extract.models_path import ModelsPaths, select_device
from voxprep.extract.text.cleaner import clean_text


_LANG_V1_TO_V2 = {
    "ZH": "zh", "zh": "zh",
    "JP": "ja", "jp": "ja", "JA": "ja", "ja": "ja",
    "EN": "en", "en": "en", "En": "en",
    "KO": "ko", "Ko": "ko", "ko": "ko",
    "yue": "yue", "YUE": "yue", "Yue": "yue",
}


def _safe_torch_save(tensor: torch.Tensor, dst: Path) -> None:
    # Work around non-ASCII path issues on some platforms
    tmp = Path(f"{_now()}.pth")
    torch.save(tensor, tmp)
    shutil.move(str(tmp), str(dst))


def _clean_path(p: str) -> str:
    return p.strip().strip('"').strip("'").strip()


class TextBertExtractor:
    def __init__(
        self,
        bert_dir: Path,
        device: str = "cpu",
        is_half: bool = False,
        version: str = "v2",
    ) -> None:
        if not bert_dir.exists():
            raise FileNotFoundError(f"BERT model dir not found: {bert_dir}")
        self.tokenizer = AutoTokenizer.from_pretrained(str(bert_dir))
        model = AutoModelForMaskedLM.from_pretrained(str(bert_dir))
        if is_half:
            model = model.half()
        self.model = model.to(device)
        self.device = device
        self.is_half = is_half
        self.version = version

    @torch.no_grad()
    def bert_feature(self, text: str, word2ph: list[int]) -> torch.Tensor:
        inputs = self.tokenizer(text, return_tensors="pt")
        for k in inputs:
            inputs[k] = inputs[k].to(self.device)
        res = self.model(**inputs, output_hidden_states=True)
        hidden = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()[1:-1]
        assert len(word2ph) == len(text)
        repeats = [hidden[i].repeat(word2ph[i], 1) for i in range(len(word2ph))]
        return torch.cat(repeats, dim=0).T


def extract_text_features(
    list_file: Path,
    opt_dir: Path,
    models: ModelsPaths,
    version: str = "v2",
    is_half: bool = False,
    progress_cb=None,
) -> Path:
    """Run text/BERT feature extraction for every line in list_file.

    Outputs:
      - {opt_dir}/2-name2text.txt   (phonemes + word2ph + normalized text)
      - {opt_dir}/3-bert/*.pt       (BERT features, Chinese only)
    """
    device, is_half = select_device(prefer_half=is_half)

    opt_dir.mkdir(parents=True, exist_ok=True)
    bert_out = opt_dir / "3-bert"
    bert_out.mkdir(exist_ok=True)

    todo: list[tuple[str, str, str]] = []
    with open(list_file, "r", encoding="utf-8") as f:
        for line in f.read().strip("\n").split("\n"):
            if not line.strip():
                continue
            try:
                wav_name, spk, lang, text = line.split("|")
            except ValueError:
                print(f"[skip] malformed line: {line}")
                continue
            if lang not in _LANG_V1_TO_V2:
                print(f"[skip] unsupported language {lang!r} for {wav_name}")
                continue
            todo.append((wav_name, text, _LANG_V1_TO_V2[lang]))

    needs_bert = any(lang == "zh" for _, _, lang in todo)
    extractor: TextBertExtractor | None = None
    if needs_bert:
        bert_dir = models.require(models.bert_dir, "BERT pretrained")
        extractor = TextBertExtractor(bert_dir, device=device, is_half=is_half, version=version)

    results: list[tuple[str, str, list[int] | None, str]] = []
    total = len(todo)
    for idx, (raw_name, text, lang) in enumerate(todo, 1):
        try:
            name = os.path.basename(_clean_path(raw_name))
            phones, word2ph, norm_text = clean_text(
                text.replace("%", "-").replace("￥", ","),
                lang,
                version,
            )
            bert_path = bert_out / f"{name}.pt"
            if lang == "zh" and extractor is not None and not bert_path.exists():
                feat = extractor.bert_feature(norm_text, word2ph)
                assert feat.shape[-1] == len(phones)
                _safe_torch_save(feat, bert_path)
            results.append((name, " ".join(phones), word2ph, norm_text))
            if progress_cb is not None:
                progress_cb(idx, total, name)
        except Exception:
            print(raw_name, text, traceback.format_exc())

    out_file = opt_dir / "2-name2text.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(f"{n}\t{p}\t{w}\t{t}" for n, p, w, t in results) + "\n")
    return out_file
