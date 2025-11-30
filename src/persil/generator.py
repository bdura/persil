from functools import wraps
from typing import Any, Callable, Generator, Sequence, overload
from warnings import deprecated

from .parser import Parser
from .result import Err, Ok, Result


type ParseGen[In: Sequence, Out] = Callable[[], Generator[Parser[In, Any], Any, Out]]


def _generate[In: Sequence, Out](
    gen: ParseGen[In, Out],
) -> Parser[In, Out]:
    @Parser
    @wraps(gen)
    def generated(stream: In, index: int) -> Result[Out]:
        # start up the generator
        iterator = gen()

        result = None
        value = None
        try:
            while True:
                next_parser = iterator.send(value)
                result = next_parser(stream, index)
                if isinstance(result, Err):
                    return result
                value = result.value
                index = result.index
        except StopIteration as stop:
            return_value: Out = stop.value
            return Ok(return_value, index)

    return generated


@overload
def generate[In: Sequence, Out](
    gen: ParseGen[In, Out],
) -> Parser[In, Out]: ...
@overload
def generate[In: Sequence, Out](
    gen: str,
) -> Callable[[ParseGen[In, Out]], Parser[In, Out]]: ...


@deprecated("The `generate` API is deprecated. Consider using `from_stream` instead.")
def generate[In: Sequence, Out](
    gen: str | ParseGen[In, Out],
) -> Parser[In, Out] | Callable[[ParseGen[In, Out]], Parser[In, Out]]:
    """
    Create a complex parser using the generator syntax.

    You should prefer the `from_stream` syntax, which is an alternative that
    plays better with types.
    """
    if isinstance(gen, str):
        return lambda f: _generate(f).desc(gen)

    else:
        return _generate(gen)
