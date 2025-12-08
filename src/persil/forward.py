from typing import Sequence

from .result import Ok
from .parser import Parser


class Forward(Parser):
    def __init__(
        self,
    ):
        self.wrapped_fn = lambda _, index: Ok(None, index)

    def become[In: Sequence, Out](self, parser: Parser[In, Out]) -> Parser[In, Out]:
        self.wrapped_fn = parser.wrapped_fn
        return self


def forward_declaration() -> Forward:
    return Forward()
