import re
from enum import Enum
from dataclasses import dataclass

from voxprep.parsing.list_file import ListEntry


class Severity(Enum):
    INFO = "info"
    WARN = "warn"
    SUSPICIOUS_DELETE_CANDIDATE = "suspicioud_delete_candidate"


MIN_TEXT_LEN = 3
MAX_TEXT_LEN = 60
INTERJECTIONS = {"아", "어", "오", "음", "응", "에이"}
KOREAN_RATIO_THRESHOLD = 0.5


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str


def check_empty_text(entry: ListEntry) -> Issue | None:
    if not entry.text.strip():
        return Issue("empty_text", Severity.WARN, "Text is empty")
    return None


def check_too_short(entry: ListEntry) -> Issue | None:
    if len(entry.text.strip()) <= MIN_TEXT_LEN:
        return Issue("too_short", Severity.WARN, "Text is too short")
    return None

def check_too_long(entry: ListEntry) -> Issue | None:
    if len(entry.text.strip()) >= MAX_TEXT_LEN:
        return Issue("too_long", Severity.WARN, "Text is too long")
    return None

def check_interjection_only(entry: ListEntry) -> Issue | None:
    normalized = re.sub(r"(.)\1+", r"\1", entry.text.strip())
    if normalized in INTERJECTIONS:
        return Issue("interjection_only", Severity.WARN, "Interjection only")
    return None

def check_non_korean_noise(entry: ListEntry) -> Issue | None:
    if entry.language != "ko":
        return None
    text = entry.text.strip()
    if not text:
        return None
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return None
    korean_count = sum(1 for c in non_space if "\uac00" <= c <= "\ud7a3")
    ratio = korean_count / len(non_space)
    if ratio < KOREAN_RATIO_THRESHOLD:
        return Issue("non_korean_noise", Severity.WARN, "Non-Korean text in Korean entry")
    return None

def check_punctuation_only(entry: ListEntry) -> Issue | None:
    text = entry.text.strip()
    if not text:
        return None
    if any(c.isalpha() for c in text):
        return None
    return Issue("punctuation_only", Severity.WARN, "Punctuation or digits only")


ALL_CHECKS = [
    check_empty_text,
    check_too_short,
    check_interjection_only,
    check_non_korean_noise,
    check_too_long,
    check_punctuation_only,
]

def inspect(entry: ListEntry, checks=ALL_CHECKS) -> list[Issue]:
    return [issue for check in checks if (issue := check(entry)) is not None]