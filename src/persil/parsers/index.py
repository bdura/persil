from typing import Sequence, TypeVar

from persil import Parser
from persil.result import Ok, Result
from persil.utils import RowCol, line_info_at

T = TypeVar("T", bound=Sequence)
S = TypeVar("S", str, bytes)


@Parser
def index(stream: T, index: int) -> Result[int]:
    """Return the current index"""
    return Ok(index, index)


@Parser
def line_info(stream: S, index: int) -> Result[RowCol]:
    """Return the line information (row, col)"""
    return Ok(line_info_at(stream, index), index)
