from persil import index, string
from persil.parsers.index import line_info
from persil.utils import RowCol


def test_index():
    parser = string("test") >> index()
    assert parser.parse("test") == 4


def test_line_info_parser():
    parser = string("hello\n") >> line_info
    result = parser.parse("hello\n")
    assert result == RowCol(index=6, row=1, col=0)
