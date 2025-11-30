from typing import Any

from persil import Parser
from persil.result import Ok, Result
from persil.utils import RowCol, line_info_at


@Parser
def index(stream: Any, index: int) -> Result[int]:
    """Return the current index"""
    return Ok(index, index)


@Parser
def line_info[S: (str, bytes)](stream: S, index: int) -> Result[RowCol]:
    """Return the line information (row, col)"""
    return Ok(line_info_at(stream, index), index)
