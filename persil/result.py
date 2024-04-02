from dataclasses import dataclass
from typing import Callable, Generic, Sequence, TypeVar

from persil.utils import line_info

T = TypeVar("T")
T2 = TypeVar("T2")


@dataclass
class Ok(Generic[T]):
    value: T
    index: int

    def ok_or_raise(self) -> "Ok[T]":
        """No-op function."""
        return self

    def map(self, map_function: Callable[[T], T2]) -> "Ok[T2]":
        return Ok(value=map_function(self.value), index=self.index)


@dataclass
class Err(Exception):
    index: int
    expected: list[str]
    stream: Sequence

    def __str__(self) -> str:
        li = line_info(self.stream, self.index)

        if len(self.expected) == 1:
            return f"expected {self.expected[0]} at {li}"
        else:
            return f"expected one of {', '.join(self.expected)} at {li}"

    def ok_or_raise(self):
        """Raise the error directly"""
        raise self

    def map(self, map_function: Callable) -> "Err":
        return self

    def aggregate(self, other: "Result[T]") -> "Result[T]":
        if isinstance(other, Ok):
            return other

        furthest = max(self.index, other.index)
        expected = self.expected + other.expected

        return Err(furthest, expected, self.stream)


Result = Ok[T] | Err
