from typing import Sequence, cast

from persil import Parser
from persil.result import Ok, Result
from persil.utils import RowCol, line_info_at


@Parser
def _index(stream: Sequence, index: int) -> Result[int]:
    return Ok(index, index)


def index[In: Sequence]() -> Parser[In, int]:
    """
    A parser that returns the current index
    """
    return cast(Parser[In, int], _index)


@Parser
def _line_info(stream: str | bytes, index: int) -> Result[RowCol]:
    return Ok(line_info_at(stream, index), index)


def line_info[In: (str, bytes)]() -> Parser[In, RowCol]:
    """
    A parser that returns the line info (row & col)
    """
    return cast(Parser[In, RowCol], _line_info)
