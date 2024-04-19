from functools import wraps
from typing import Any, Callable, Generator, Sequence, TypeVar, overload

from .parser import Parser
from .result import Err, Ok, Result

Input = TypeVar("Input", bound=Sequence)
Output = TypeVar("Output")

ParseGen = Generator[Parser[Input, Any], Any, Output]


def _generate(
    gen: Callable[[], ParseGen[Input, Output]],
) -> Parser[Input, Output]:
    @Parser
    @wraps(gen)
    def generated(stream: Input, index: int) -> Result[Output]:
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
            return_value: Output = stop.value
            return Ok(return_value, index)

    return generated


@overload
def generate(gen: Callable[[], ParseGen[Input, Output]]) -> Parser[Input, Output]: ...
@overload
def generate(
    gen: str,
) -> Callable[[Callable[[], ParseGen[Input, Output]]], Parser[Input, Output]]: ...


def generate(gen):
    """
    Create a complex parser using the generator syntax.

    You should prefer the `from_stream` syntax, which is an alternative that
    plays better with types.
    """
    if isinstance(gen, str):
        return lambda f: _generate(f).desc(gen)

    else:
        return _generate(gen)
