from voxprep.parsing.list_file import ListEntry
from voxprep.review.issues import (
    check_empty_text, 
    check_too_short, 
    check_interjection_only,
    check_non_korean_noise,
    check_too_long,
    check_punctuation_only,
    inspect,
    Severity,
)


def test_empty_text_returns_war():
    entry = ListEntry("a.wav", "s", "ko", "")

    issue = check_empty_text(entry)

    assert issue is not None
    assert issue.code == "empty_text"
    assert issue.severity == Severity.WARN


def test_whitespace_only_text_returns_war():
    entry = ListEntry("a.wav", "s", "ko", "   ")

    assert check_empty_text(entry) is not None


def test_non_empty_text_returns_none():
    entry = ListEntry("a.wav", "s", "ko", "hi")

    assert check_empty_text(entry) is None


def test_too_short_three_chars_or_less():
    for text in ["", "아", "안녕"]:
        entry = ListEntry("a.wav", "s", "ko", text)
        assert check_too_short(entry) is not None, f"{text!r} should flag"


def test_three_chars_exactly_is_boundary():
    entry = ListEntry("a.wav", "s", "ko", "안녕요")

    assert check_too_short(entry) is not None


def test_four_chars_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세")

    assert check_too_short(entry) is None


def test_interjection_only():
    for text in ["아", "어어어", "음", "에이", "오", "응", "응응응"]:
        entry = ListEntry("a.wav", "s", "ko", text)
        assert check_interjection_only(entry) is not None, f"{text!r} should flag"


def test_non_interjection_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세요")

    assert check_interjection_only(entry) is None


def test_non_korean_text_in_korean_entry_flags():
    entry = ListEntry("a.wav", "s", "ko", "こんにちは")

    issue = check_non_korean_noise(entry)

    assert issue is not None
    assert issue.code == "non_korean_noise"


def test_korean_text_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세요")

    assert check_non_korean_noise(entry) is None


def test_mixed_with_majority_korean_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕하세요 hello")

    assert check_non_korean_noise(entry) is None


def test_non_ko_language_entry_skipped():
    entry = ListEntry("a.wav", "s", "en", "hello world")

    assert check_non_korean_noise(entry) is None


def test_too_long_flags():
    entry = ListEntry("a.wav", "s", "ko", "가" * 60)

    issue = check_too_long(entry)

    assert issue is not None
    assert issue.code == "too_long"


def test_59_chars_passes():
    entry = ListEntry("a.wav", "s", "ko", "가" * 59)

    assert check_too_long(entry) is None


def test_punctuation_only_flags():
    for text in ["???", "...", "123", "!@#"]:
        entry = ListEntry("a.wav", "s", "ko", text)
        assert check_punctuation_only(entry) is not None, f"{text!r} should flag"


def test_punctuation_with_letters_passes():
    entry = ListEntry("a.wav", "s", "ko", "안녕!")

    assert check_punctuation_only(entry) is None


def test_inspect_runs_all_checks():
    entry = ListEntry("a.wav", "s", "ko", "")

    issues = inspect(entry)

    codes = {i.code for i in issues}
    assert "empty_text" in codes
    assert "too_short" in codes