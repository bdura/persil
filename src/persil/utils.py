from dataclasses import dataclass
from functools import singledispatch
from typing import Sequence, TypeVar

T = TypeVar("T")


def noop(x: T) -> T:
    return x


@dataclass
class RowCol:
    row: int
    col: int

    def __str__(self) -> str:
        return f"{self.row}:{self.col}"


@singledispatch
def line_info_at(stream: Sequence, index: int) -> RowCol:
    raise TypeError


@line_info_at.register
def _(stream: bytes, index: int) -> RowCol:
    row = stream.count(b"\n", 0, index)
    last_nl = stream.rfind(b"\n", 0, index)
    col = index - (last_nl + 1)
    return RowCol(row, col)


@line_info_at.register
def _(stream: str, index: int) -> RowCol:
    row = stream.count("\n", 0, index)
    last_nl = stream.rfind("\n", 0, index)
    col = index - (last_nl + 1)
    return RowCol(row, col)


def line_info(stream: Sequence, index: int) -> str:
    if isinstance(stream, (str, bytes)):
        return str(line_info_at(stream, index))
    else:
        return str(index)
