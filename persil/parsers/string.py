from typing import Callable

from persil.parser import Parser
from persil.utils import noop

from .regex import regex
from .tag import tag


def string(
    expected: str,
    transform: Callable[[str], str] = noop,
) -> Parser[str, str]:
    """
    Returns a parser that expects `expected` and returns the matched value.

    Optionally, a transform function can be passed, which will be used on both
    the expected and tested input.

    Breaking change from `parsy`: the matched string will be returned.
    You may achieve `parsy`'s behaviour by chaining the `result` method:

    ```python
    expected = "TesT"

    # Not parsy-compatible
    parser = tag(expected, transform=lambda s: s.lower())

    # `parsy`-compatible
    parser = parser.result(expected)
    ```
    """
    return tag(expected=expected, transform=transform)


whitespace = regex(r"\s+")
