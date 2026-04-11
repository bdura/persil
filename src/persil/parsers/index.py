from typing import Sequence, cast

from persil import Parser
from persil.result import Ok, Result
from persil.utils import RowCol, line_info_at


def index[In: Sequence]() -> Parser[In, int]:
    """
    A parser that returns the current index
    """

    @Parser
    def _index(stream: Sequence, index: int) -> Result[int]:
        return Ok(index, index)

    return cast(Parser[In, int], _index)


def line_info[In: (str, bytes)]() -> Parser[In, int]:
    """
    A parser that returns the current index
    """

    @Parser
    def _line_info(stream: Sequence, index: int) -> Result[RowCol]:
        return Ok(line_info_at(stream, index), index)

    return cast(Parser[In, int], _line_info)
