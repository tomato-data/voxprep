from faster_whisper import WhisperModel


def load_whisper(
    model_size: str = "large-v3-turbo",
    device: str = "auto",
    compute_type: str = "auto",
) -> WhisperModel:
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    return WhisperModel(model_size, device=device, compute_type=compute_type)
