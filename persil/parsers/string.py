from typing import Callable

from persil import Parser
from persil.result import Err, Ok, Result
from persil.utils import noop


def string(expected_string: str, transform: Callable[[str], str] = noop) -> Parser[str, str]:
    """
    Returns a parser that expects the ``expected_string`` and produces
    that string value.

    Optionally, a transform function can be passed, which will be used on both
    the expected string and tested string.
    """

    slen = len(expected_string)
    transformed_s = transform(expected_string)

    @Parser
    def string_parser(stream: str, index: int) -> Result[str]:
        if transform(stream[index : index + slen]) == transformed_s:
            return Ok(expected_string, index + slen)
        else:
            return Err(index, [expected_string], stream)

    return string_parser
