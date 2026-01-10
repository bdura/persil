"""Machinery to create lazily-evaluated parsers.

Lazy evaluation enables the creation of self-referential parsers.

## The problem

Let's say we want to create a parser a JSON parser:

```python
array = left_bracket >> value.sep_by(comma) << right_bracket
value = string | integer | floating | array
```

This does not work, since `array` references `value`, which itself requires `array`.

## The solution

One solution to this problem is to use a parser that lazily creates the parser
when it is first called, i.e. once the required parser is actually defined:

```python
type Value = str | int | float | list[Value]

@lazy
def array() -> Parser[str, list[Value]]:
    # This function depends on `value`, but only when it's called
    # By then, `value` is properly defined.
    return left_bracket >> value.sep_by(comma) << right_bracket

value = string | integer | floating | array
```
"""

from typing import Callable, Sequence

from .result import Result
from .parser import Parser, Wrapped


def lazy[In: Sequence, Out](fn: Callable[[], Parser[In, Out]]) -> Parser[In, Out]:
    """Create a parser that delays creating the parser until parse time.

    This is particularly useful to create self-referential parsers,
    that could not be referenced otherwise.
    """

    wrapped_fn: Wrapped[In, Out] | None = None

    @Parser
    def lazy_parser(stream: In, index: int) -> Result[Out]:
        nonlocal wrapped_fn
        if wrapped_fn is None:
            wrapped_fn = fn().wrapped_fn
        return wrapped_fn(stream, index)

    return lazy_parser
