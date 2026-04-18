"""InferenceSession — thin wrapper over TTS_infer_pack.TTS.

Exposes a programmatic API (for CLI sessions, future MCP/REST servers).
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from voxprep.extract.models_path import ModelsPaths


_VERSION_VOCODER_MAP = {"v1", "v2", "v2Pro", "v2ProPlus"}  # versions with internal vocoder (no BigVGAN)


@dataclass(frozen=True)
class InferenceInputs:
    text: str
    text_lang: str = "ko"
    ref_audio: Path | None = None
    prompt_text: str = ""
    prompt_lang: str = "ko"
    top_k: int = 20
    top_p: float = 0.6
    temperature: float = 0.6
    speed_factor: float = 1.0
    seed: int = -1


class InferenceSession:
    def __init__(
        self,
        sovits_weights: Path,
        gpt_weights: Path,
        version: str = "v2Pro",
        models: ModelsPaths | None = None,
        device: str = "cpu",
        is_half: bool = False,
    ) -> None:
        from voxprep.inference.tts_pack.TTS import TTS, TTS_Config

        paths = models or ModelsPaths()
        configs = {
            version: {
                "device": device,
                "is_half": is_half,
                "version": version,
                "t2s_weights_path": str(gpt_weights),
                "vits_weights_path": str(sovits_weights),
                "cnhuhbert_base_path": str(paths.cnhubert_dir),
                "bert_base_path": str(paths.bert_dir),
            }
        }
        tts_config = TTS_Config({"default": configs[version], "custom": configs[version]})
        tts_config.version = version
        tts_config.device = device
        tts_config.is_half = is_half
        tts_config.t2s_weights_path = str(gpt_weights)
        tts_config.vits_weights_path = str(sovits_weights)
        tts_config.cnhuhbert_base_path = str(paths.cnhubert_dir)
        tts_config.bert_base_path = str(paths.bert_dir)

        self.tts = TTS(tts_config)
        self.version = version

    def synthesize(self, inputs: InferenceInputs) -> tuple[int, np.ndarray]:
        if inputs.ref_audio is None or not Path(inputs.ref_audio).exists():
            raise FileNotFoundError(f"reference audio required: {inputs.ref_audio}")
        payload = {
            "text": inputs.text,
            "text_lang": inputs.text_lang,
            "ref_audio_path": str(inputs.ref_audio),
            "prompt_text": inputs.prompt_text,
            "prompt_lang": inputs.prompt_lang,
            "top_k": inputs.top_k,
            "top_p": inputs.top_p,
            "temperature": inputs.temperature,
            "text_split_method": "cut0",
            "batch_size": 1,
            "speed_factor": inputs.speed_factor,
            "seed": inputs.seed,
            "parallel_infer": True,
        }
        results = list(self.tts.run(payload))
        if not results:
            raise RuntimeError("no audio produced")
        # results is a list of (sr, audio) tuples if streaming; single tuple otherwise
        sr, audio = results[-1]
        return sr, audio

    @staticmethod
    def save_wav(path: Path, sr: int, audio: np.ndarray) -> None:
        if audio.dtype != np.int16:
            audio = audio.astype(np.int16)
        path.parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(str(path), sr, audio)
