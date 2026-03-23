from enum import Enum
from typing import Any, Callable

from persil import Parser
from persil.utils import noop

from .outcome import fail
from .tag import tag


def from_enum[E: Enum](
    enum_cls: type[E],
    transform: Callable[[str], Any] = noop,
) -> Parser[str, E]:
    """
    Given a class that is an [`enum.Enum`] class, return a parser that
    will parse the values (or the string representations of the values)
    and return the corresponding enum item.

    Note
    ----
    The enum variants are tested in decreasing order of length.

    Parameters
    ----------
    enum_cls
        Enum class to parse

    [`enum.Enum`]: https://docs.python.org/3/library/enum.html
    """

    items = sorted(
        ((str(enum_item.value), enum_item) for enum_item in enum_cls),
        key=lambda t: len(t[0]),
        reverse=True,
    )

    if not items:
        return fail("empty enum")

    parsers = [tag(key, transform=transform).result(value) for key, value in items]

    parser = parsers[0]

    for p in parsers[1:]:
        parser = parser | p

    return parser
