from enum import Enum
from typing import TypeVar

from persil import Parser
from persil.utils import noop

from .tag import tag

E = TypeVar("E", bound=Enum)


def from_enum(enum_cls: type[E], transform=noop) -> Parser[str, E]:
    """
    Given a class that is an `enum.Enum` class
    https://docs.python.org/3/library/enum.html , returns a parser that
    will parse the values (or the string representations of the values)
    and return the corresponding enum item.

    Parameters
    ----------
    enum_cls
        Enum class to parse
    """

    items = sorted(
        ((str(enum_item.value), enum_item) for enum_item in enum_cls),
        key=lambda t: len(t[0]),
        reverse=True,
    )

    parsers = [tag(key, transform=transform).result(value) for key, value in items]

    parser = parsers[0]

    for p in parsers[1:]:
        parser = parser | p

    return parser
