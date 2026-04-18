"""Select good reference audio candidates from a .list file.

Heuristics (no audio inspection — just text + duration):
- duration 4~8s, closest to 6s preferred
- text length 15~50 chars, longer preferred
- penalty for trailing ellipsis (mid-sentence cuts)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from voxprep.parsing.list_file import ListEntry, read_list_file


_IDEAL_DURATION = 6.0
_MIN_DURATION = 4.0
_MAX_DURATION = 8.0
_MIN_TEXT = 15
_MAX_TEXT = 50


@dataclass(frozen=True)
class RefCandidate:
    entry: ListEntry
    duration: float
    score: float

    @property
    def audio_path(self) -> Path:
        return Path(self.entry.audio_path)

    @property
    def text(self) -> str:
        return self.entry.text.strip()


def _duration_from_name(name: str, sample_rate: int = 44100) -> float | None:
    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) < 2:
        return None
    try:
        start = int(parts[-2])
        end = int(parts[-1])
    except ValueError:
        return None
    return (end - start) / sample_rate


def _score(duration: float, text: str) -> float:
    length = len(text)
    if duration < _MIN_DURATION or duration > _MAX_DURATION:
        return -1.0
    if length < _MIN_TEXT or length > _MAX_TEXT:
        return -1.0
    duration_score = 1.0 - abs(duration - _IDEAL_DURATION) / (_MAX_DURATION - _IDEAL_DURATION)
    length_score = min(length / _MAX_TEXT, 1.0)
    penalty = 0.25 if text.endswith("...") or text.endswith("..") else 0.0
    return duration_score * 0.6 + length_score * 0.4 - penalty


def rank_candidates(
    list_file: Path,
    sample_rate: int = 44100,
    limit: int = 8,
) -> list[RefCandidate]:
    entries = read_list_file(list_file)
    scored: list[RefCandidate] = []
    for e in entries:
        d = _duration_from_name(e.audio_path, sample_rate)
        if d is None:
            continue
        text = e.text.strip()
        s = _score(d, text)
        if s < 0:
            continue
        scored.append(RefCandidate(entry=e, duration=d, score=s))
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:limit]
