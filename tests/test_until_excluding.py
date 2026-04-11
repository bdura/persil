import pytest
from hypothesis import given, strategies as st

from persil import regex, string
from persil.result import Err

any_char = regex(r"[\s\S]")


def test_until_excluding_max_exceeded():
    parser = any_char.until_excluding(string("|"), max=2)
    with pytest.raises(Err, match="at most"):
        parser.parse_partial("abcd|")


def test_until_excluding_min_not_met_inner_fails():
    # The inner parser itself fails before min is reached and before
    # `other` matches.
    digit = regex(r"\d")
    parser = digit.until_excluding(string("|"), min=3)
    with pytest.raises(Err, match="at least"):
        parser.parse_partial("12x|")


def test_until_excluding_other_not_found():
    # `self` keeps failing but min is already met — produces the
    # "did not find other parser" branch.
    digit = regex(r"\d")
    parser = digit.until_excluding(string("|"), min=0)
    with pytest.raises(Err):
        parser.parse_partial("12x")


@given(
    content=st.text(
        alphabet=st.characters(min_codepoint=1, blacklist_characters="|"),
        min_size=0,
        max_size=50,
    ),
    max_items=st.integers(min_value=0, max_value=50),
)
def test_until_excluding_max_property(content: str, max_items: int):
    """until_excluding(max=n) succeeds iff len(content) <= n, and does not
    consume the separator."""
    parser = any_char.until_excluding(string("|"), max=max_items)
    if len(content) <= max_items:
        result, remainder = parser.parse_partial(content + "|")
        assert result == list(content)
        # Separator must still be in the remainder.
        assert remainder.startswith("|")
    else:
        with pytest.raises(Err):
            parser.parse_partial(content + "|")


@given(
    content=st.text(
        alphabet=st.characters(min_codepoint=1, blacklist_characters="|"),
        min_size=0,
        max_size=50,
    ),
    min_items=st.integers(min_value=0, max_value=50),
)
def test_until_excluding_min_property(content: str, min_items: int):
    """until_excluding(min=n) succeeds iff len(content) >= n."""
    parser = any_char.until_excluding(string("|"), min=min_items)
    if len(content) >= min_items:
        result, remainder = parser.parse_partial(content + "|")
        assert result == list(content)
        assert remainder.startswith("|")
    else:
        with pytest.raises(Err):
            parser.parse_partial(content + "|")
