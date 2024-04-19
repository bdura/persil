from typing import Callable, TypeVar

from persil import Parser
from persil.result import Err, Ok, Result
from persil.utils import noop

T = TypeVar("T", str, bytes)


def tag(
    expected: T,
    transform: Callable[[T], T] = noop,
) -> Parser[T, T]:
    """
    Returns a parser that expects `expected` and returns the matched value.

    Optionally, a transform function can be passed, which will be used on both
    the expected and tested input.

    Parameters
    ----------
    expected
        The expected sequence.
    transform
        An optional transform, applied to the expected value as well as
        the input stream.
    """

    slen = len(expected)
    transformed_s = transform(expected)

    @Parser
    def tag_parser(stream: T, index: int) -> Result[T]:
        matched = stream[index : index + slen]
        if transform(matched) == transformed_s:
            return Ok(matched, index + slen)
        else:
            return Err(index, [str(expected)], stream)

    return tag_parser
