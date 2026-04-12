import pytest
from hypothesis import assume, given, strategies as st

from persil.utils import RowCol, line_info_at


def test_line_info_at_bytes():
    stream = b"hello\nworld"
    rc = line_info_at(stream, 6)
    assert rc == RowCol(index=6, row=1, col=0)


def test_line_info_at_unsupported_type():
    with pytest.raises(TypeError):
        line_info_at([1, 2, 3], 1)


@given(
    text=st.text(
        alphabet=st.characters(min_codepoint=1, max_codepoint=127),
        min_size=1,
        max_size=200,
    ),
)
def test_line_info_at_str_bytes_agree_for_ascii(text: str):
    """For ASCII content, the str and bytes dispatches must produce identical
    RowCol values for every valid index."""
    encoded = text.encode("ascii")
    index = len(text) // 2
    assume(index < len(text))

    rc_str = line_info_at(text, index)
    rc_bytes = line_info_at(encoded, index)

    assert rc_str == rc_bytes


@given(
    text=st.text(min_size=1, max_size=2000),
)
def test_row_is_newline_count(text: str):
    """The row at any index equals the number of newlines before that index."""
    index = len(text) // 2
    assume(index < len(text))
    rc = line_info_at(text, index)
    assert rc.row == text[:index].count("\n")
