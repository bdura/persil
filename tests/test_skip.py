from hypothesis import given, strategies as st

from persil.parsers import string


@given(
    first=st.characters(min_codepoint=1),
    second=st.characters(min_codepoint=1),
)
def test_string_parser(first: str, second: str):
    parser = string(first) << string(second)
    assert parser.parse(first + second) == first
