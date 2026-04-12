from dataclasses import dataclass
from functools import singledispatch


@dataclass
class RowCol:
    index: int

    row: int
    col: int

    def __str__(self) -> str:
        return f"{self.row}:{self.col}"


@dataclass
class Span[T]:
    start: RowCol
    stop: RowCol

    value: T


@singledispatch
def line_info_at(stream: str | bytes, index: int) -> RowCol:
    raise TypeError


@line_info_at.register
def _(stream: bytes, index: int) -> RowCol:
    row = stream.count(b"\n", 0, index)
    last_nl = stream.rfind(b"\n", 0, index)
    col = index - (last_nl + 1)
    return RowCol(index, row, col)


@line_info_at.register
def _(stream: str, index: int) -> RowCol:
    row = stream.count("\n", 0, index)
    last_nl = stream.rfind("\n", 0, index)
    col = index - (last_nl + 1)
    return RowCol(index, row, col)
