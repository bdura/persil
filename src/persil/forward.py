from typing import Sequence
from warnings import deprecated

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


@deprecated("You should use `lazy` instead.")
def forward_declaration() -> Forward:
    """Creates a "placeholder" parser, that can be instantiated later on.

    This forward declaration scheme allows the creation of recursive parsers:

    ```python
    value = forward_declaration()
    array = left_bracket >> value.sep_by(comma) << right_bracket
    value.become(string | integer | floating | array)
    ```
    """
    return Forward()
