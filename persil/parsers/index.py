from typing import Sequence

from persil import Parser
from persil.result import Ok, Result
from persil.utils import RowCol, line_info_at


@Parser
def index(stream: Sequence, index: int) -> Result[int]:
    return Ok(index, index)


@Parser
def line_info(stream: Sequence, index: int) -> Result[RowCol]:
    return Ok(line_info_at(stream, index), index)
