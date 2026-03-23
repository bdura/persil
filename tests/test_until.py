import pytest
from hypothesis import given, strategies as st

from persil import regex, string
from persil.result import Err

# Matches any single character, including newlines.
any_char = regex(r"[\s\S]")


def test_until_basic():
    chars, sep = any_char.until(
        string("|"),
        return_other=True,
    ).parse("abc|")
    assert chars == ["a", "b", "c"]
    assert sep == "|"


def test_until_empty_content():
    chars, sep = any_char.until(
        string("|"),
        return_other=True,
    ).parse("|")
    assert chars == []
    assert sep == "|"


def test_until_consumes_other():
    # The stream should be advanced past `other` after a successful parse.
    result, remainder = any_char.until(
        string("|"),
        return_other=True,
    ).parse_partial("abc|rest")
    chars, sep = result
    assert chars == ["a", "b", "c"]
    assert sep == "|"
    assert remainder == "rest"


def test_until_and_discard():
    # until_and_discard does not consume `|`, so we must consume it ourselves.
    chars = (any_char.until_excluding(string("|")) << string("|")).parse("abc|")
    assert chars == ["a", "b", "c"]


def test_until_min_satisfied():
    chars = any_char.until(string("|"), min=2).parse("ab|")
    assert chars == ["a", "b"]


def test_until_min_violated():
    # `other` matches after only 1 item, but min=2.
    with pytest.raises(Err):
        any_char.until(string("|"), min=2).parse("a|")


def test_until_max_satisfied():
    chars = any_char.until(string("|"), max=3).parse("abc|")
    assert chars == ["a", "b", "c"]


def test_until_max_violated():
    # 4 items appear before `other`, but max=3.
    with pytest.raises(Err):
        any_char.until(string("|"), max=3).parse("abcd|")


def test_until_max_zero():
    # max=0 means `other` must match immediately.
    chars = any_char.until(string("|"), max=0).parse("|")
    assert chars == []


def test_until_max_zero_violated():
    with pytest.raises(Err):
        any_char.until(string("|"), max=0).parse("a|")


@given(
    content=st.text(
        alphabet=st.characters(min_codepoint=1, blacklist_characters="|"),
        min_size=0,
        max_size=50,
    )
)
def test_until_roundtrip(content: str):
    """For any content without '|', parsing content+'|' collects every
    character and returns the separator."""
    chars, terminator = any_char.until(
        string("|"),
        return_other=True,
    ).parse(content + "|")
    assert chars == list(content)
    assert terminator == "|"


@given(
    content=st.text(
        alphabet=st.characters(min_codepoint=1, blacklist_characters="|"),
        min_size=0,
        max_size=50,
    ),
    max_items=st.integers(min_value=0, max_value=50),
)
def test_until_max_property(content: str, max_items: int):
    """until(max=n) succeeds iff len(content) <= max_items."""
    parser = any_char.until(string("|"), max=max_items)
    if len(content) <= max_items:
        chars = parser.parse(content + "|")
        assert chars == list(content)
    else:
        with pytest.raises(Err):
            parser.parse(content + "|")


@given(
    content=st.text(
        alphabet=st.characters(min_codepoint=1, blacklist_characters="|"),
        min_size=0,
        max_size=50,
    ),
    min_items=st.integers(min_value=0, max_value=50),
)
def test_until_min_property(content: str, min_items: int):
    """until(min=n) succeeds iff len(content) >= min_items."""
    parser = any_char.until(string("|"), min=min_items)
    if len(content) >= min_items:
        chars = parser.parse(content + "|")
        assert chars == list(content)
    else:
        with pytest.raises(Err):
            parser.parse(content + "|")
