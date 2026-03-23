from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Ok[T]:
    value: T
    index: int

    def ok_or_raise(self) -> Ok[T]:
        """No-op function."""
        return self

    def map[Out](self, map_function: Callable[[T], Out]) -> Ok[Out]:
        return Ok(value=map_function(self.value), index=self.index)

    def with_index(self, index: int) -> Ok[T]:
        return Ok(
            value=self.value,
            index=index,
        )


@dataclass
class Err(Exception):
    index: int
    expected: list[str]
    # Pre-formatted location string (e.g. "3:7" or "42"), computed once at
    # construction time so that Err does not retain a reference to the full
    # input stream.
    location: str

    def __str__(self) -> str:
        if len(self.expected) == 1:
            return f"expected {self.expected[0]} at {self.location}"
        else:
            return f"expected one of {', '.join(self.expected)} at {self.location}"

    def ok_or_raise(self):
        """Raise the error directly"""
        raise self

    def map(self, map_function: Callable) -> Err:
        return self

    def aggregate[T](self, other: Result[T]) -> Result[T]:
        if isinstance(other, Ok):
            return other

        # Keep the error that is furthest into the stream; its location string
        # already corresponds to that index.
        if self.index >= other.index:
            return Err(self.index, self.expected + other.expected, self.location)
        else:
            return Err(other.index, self.expected + other.expected, other.location)


type Result[T] = Ok[T] | Err
