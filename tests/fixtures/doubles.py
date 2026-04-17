class FakeSegment:
    def __init__(self, text: str):
        self.text = text


class FakeInfo:
    def __init__(self, language: str):
        self.language = language


class FakeWhisperModel:
    def __init__(self, segments: list[str], language: str):
        self._segments = segments
        self._language = language
        self.calls: list[dict] = []

    def transcribe(self, audio, **kwargs):
        self.calls.append({"audio": audio, **kwargs})
        return (
            (FakeSegment(s) for s in self._segments),
            FakeInfo(self._language),
        )
