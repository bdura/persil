from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Never, Self, Sequence

from persil.utils import RowCol, line_info_at


@dataclass
class Ok[T]:
    """A successful parse result.

    Attributes
    ----------
    value
        The value produced by the parser.
    index
        The stream position immediately after the consumed input.
    """

    value: T
    index: int

    def ok(self) -> Ok[T]:
        """No-op: returns self.

        Mirrors :meth:`Err.ok` so that :type:`Result` can be used
        uniformly — calling ``.ok()`` on success is a no-op, while
        calling it on failure raises :class:`ParseError`.
        """
        return self

    def map[Out](self, map_function: Callable[[T], Out]) -> Ok[Out]:
        """Apply *map_function* to the value, preserving the index."""
        return Ok(value=map_function(self.value), index=self.index)

    def with_index(self, index: int) -> Ok[T]:
        """Return a copy with a different stream index."""
        return Ok(
            value=self.value,
            index=index,
        )


@dataclass
class Err:
    """A parse error carrying structured location and expectation info.

    This is a plain dataclass — it is never raised directly. Use
    :class:`ParseError` to convert it into a raisable exception.
    """

    index: int
    expected: frozenset[str]
    location: RowCol | int

    @classmethod
    def from_stream(
        cls,
        index: int,
        expected: str,
        stream: Sequence,
    ) -> Self:
        """Build an :class:`Err` from a stream position.

        For ``str`` and ``bytes`` streams the location is computed as a
        :class:`RowCol`; for other sequence types it falls back to the
        raw integer index.
        """
        if isinstance(stream, (str, bytes)):
            location: RowCol | int = line_info_at(stream, index)
        else:
            location = index
        return cls(index, frozenset({expected}), location)

    def __str__(self) -> str:
        items = sorted(self.expected)
        if len(items) == 1:
            return f"expected {items[0]} at {self.location}"
        return f"expected one of {', '.join(items)} at {self.location}"

    def ok(self) -> Never:
        """Raise as a :class:`ParseError`."""
        raise ParseError(self)

    def map(self, map_function: Callable) -> Self:
        """No-op: errors propagate unchanged through ``map``."""
        return self

    def aggregate[T](self, other: Result[T]) -> Result[T]:
        """Merge two errors, keeping the one furthest into the stream.

        If *other* is :class:`Ok`, it wins unconditionally.  When both
        are :class:`Err`, the error at the higher index is kept.  If the
        indices are equal, expectations from both branches are merged so
        the message lists every alternative that was tried at that
        position.
        """
        if isinstance(other, Ok):
            return other

        # Keep only the error that is furthest into the stream.
        # Expectations from an earlier index are irrelevant — they
        # describe what was expected at a position already parsed past.
        if self.index > other.index:
            return self
        if self.index < other.index:
            return other

        # Same index: merge expectations from both branches.
        return Err(
            self.index,
            self.expected | other.expected,
            self.location,
        )


class ParseError(Exception):
    """Raised when parsing fails.

    Wraps an :class:`Err` so that structured error data is available
    via the :attr:`err` attribute, while still being a proper exception.
    """

    def __init__(self, err: Err) -> None:
        self.err = err
        super().__init__(str(err))

    @property
    def index(self) -> int:
        """Stream index where the error occurred."""
        return self.err.index

    @property
    def expected(self) -> frozenset[str]:
        """Set of descriptions of what was expected at this position."""
        return self.err.expected

    @property
    def location(self) -> RowCol | int:
        """Structured location (row/col for text, raw index otherwise)."""
        return self.err.location


type Result[T] = Ok[T] | Err
"""The result of applying a parser: either :class:`Ok` or :class:`Err`."""
