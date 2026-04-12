import re

import pytest
from hypothesis import given, strategies as st

from persil import regex
from persil.result import ParseError
from persil.parsers.regex import regex_groupdict


def test_regex_bytes_literal_raises():
    # Bytes patterns are not supported; passing one should raise TypeError
    # at construction time with a helpful message.
    with pytest.raises(TypeError, match="bytes"):
        regex(b"pattern")  # ty:ignore[invalid-argument-type]


def test_regex_compiled_bytes_raises():
    # A pre-compiled bytes pattern is equally unsupported.
    with pytest.raises(TypeError, match="bytes"):
        regex(re.compile(b"pattern"))  # ty:ignore[invalid-argument-type]


def test_regex_string_pattern_compiles():
    assert regex(r"\d+").parse("123") == "123"


def test_regex_precompiled_str_pattern():
    assert regex(re.compile(r"\d+")).parse("42") == "42"


def test_regex_no_match_raises():
    with pytest.raises(ParseError):
        regex(r"\d+").parse("abc")


@given(st.from_regex(r"\w+", fullmatch=True))
def test_regex_word_matches(s: str):
    """`regex(r'\\w+')` succeeds on any string that re.fullmatch considers
    a word, and returns the string unchanged."""
    assert regex(r"\w+").parse(s) == s


@given(st.from_regex(r"\d{3}-\d{4}", fullmatch=True))
def test_regex_phone_fragment_matches(s: str):
    assert regex(r"\d{3}-\d{4}").parse(s) == s


@given(
    valid=st.from_regex(r"[a-z]+", fullmatch=True),
    suffix=st.text(alphabet="0123456789", min_size=1),
)
def test_regex_partial_parse(valid: str, suffix: str):
    """parse_partial returns the matched prefix and leaves the rest."""
    result, remainder = regex(r"[a-z]+").parse_partial(valid + suffix)
    assert result == valid
    assert remainder == suffix


def test_regex_groupdict_success():
    parser = regex_groupdict(r"(?P<year>\d{4})-(?P<month>\d{2})")
    assert parser.parse("2026-04") == {"year": "2026", "month": "04"}


def test_regex_groupdict_failure():
    parser = regex_groupdict(r"(?P<year>\d{4})-(?P<month>\d{2})")
    with pytest.raises(ParseError):
        parser.parse("not-a-date")
