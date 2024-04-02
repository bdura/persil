from typing import Sequence

from persil import Parser
from persil.result import Err, Result


def fail(expected: str) -> Parser:
    """
    Returns a parser that always fails with the provided error message.
    """

    @Parser
    def fail_parser(stream: Sequence, index: int) -> Result:
        return Err(index, [expected], stream)

    return fail_parser
