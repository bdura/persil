from typing import Any, Callable

from persil import Parser
from persil.result import Err, Ok, Result


def tag[T: (str, bytes)](
    expected: T,
    transform: Callable[[T], Any] | None = None,
) -> Parser[T, T]:
    """
    Returns a parser that expects `expected` and returns the matched value.

    Optionally, a transform function can be passed, which will be used on both
    the expected and tested input before comparison.

    Parameters
    ----------
    expected
        The expected sequence.
    transform
        An optional transform, applied to the expected value as well as
        the input stream before testing.
    """

    slen = len(expected)

    if transform is not None:
        transformed_s = transform(expected)

        @Parser
        def transformed_tag_parser(stream: T, index: int) -> Result[T]:
            matched = stream[index : index + slen]  # ty:ignore[invalid-argument-type]
            if transform(matched) == transformed_s:
                return Ok(matched, index + slen)
            return Err.from_stream(index, str(expected), stream)

        return transformed_tag_parser

    @Parser
    def tag_parser(stream: T, index: int) -> Result[T]:
        matched = stream[index : index + slen]  # ty:ignore[invalid-argument-type]
        if matched == expected:
            return Ok(matched, index + slen)
        return Err.from_stream(index, str(expected), stream)

    return tag_parser
