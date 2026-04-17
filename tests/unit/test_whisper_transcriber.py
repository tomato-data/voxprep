from pathlib import Path

from voxprep.transcription.types import Transcription
from voxprep.transcription.whisper import WhisperTranscriber
from voxprep.parsing.list_file import ListEntry

from tests.fixtures.doubles import FakeWhisperModel


def test_transcription_value_equality():
    a = Transcription(Path("a.wav"), "ko", "안녕")
    b = Transcription(Path("a.wav"), "ko", "안녕")

    assert a == b


def test_to_list_entry_with_speaker():
    t = Transcription(Path("data/01.wav"), "ko", "hi")

    entry = t.to_list_entry(speaker="narrator")

    assert entry == ListEntry("data/01.wav", "narrator", "ko", "hi")


def test_transcribe_concatenates_segments(tmp_path):
    audio = tmp_path / "x.wav"
    audio.touch()
    model = FakeWhisperModel(["Hello", " world"], language="en")
    transcriber = WhisperTranscriber(model=model)

    result = transcriber.transcribe(audio)

    assert result.text == "Hello world"
    assert result.language == "en"
    assert result.audio_path == audio


def test_transcribe_passes_options_to_model(tmp_path):
    audio = tmp_path / "x.wav"
    audio.touch()
    model = FakeWhisperModel([""], language="ko")
    transcriber = WhisperTranscriber(
        model=model,
        default_language="ko",
        beam_size=3,
        vad_filter=True,
        vad_min_silence_ms=500,
    )

    transcriber.transcribe(audio)

    call = model.calls[0]
    assert call["language"] == "ko"
    assert call["beam_size"] == 3
    assert call["vad_filter"] is True
    assert call["vad_parameters"] == {"min_silence_duration_ms": 500}


def test_auto_language_passed_as_none(tmp_path):
    audio = tmp_path / "x.wav"
    audio.touch()
    model = FakeWhisperModel([""], language="en")
    transcriber = WhisperTranscriber(model=model, default_language="auto")

    transcriber.transcribe(audio)

    assert model.calls[0]["language"] is None
