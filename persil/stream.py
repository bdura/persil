from functools import wraps
from typing import Callable, Generic, Sequence, TypeVar, overload

from .parser import Parser
from .result import Err, Ok, Result

In = TypeVar("In", bound=Sequence)
Out = TypeVar("Out")


class SoftError(Exception):
    inner: Err


class Stream(Generic[In]):
    inner: In
    index: int

    def __init__(self, inner: In, index: int = 0):
        self.inner = inner
        self.index = index

    def apply(self, parser: Parser[In, Out]) -> Out:
        res = parser(self.inner, self.index)

        if isinstance(res, Err):
            raise SoftError(res)

        self.index = res.index

        return res.value


def _from_stream(func: Callable[[Stream[In]], Out]) -> Parser[In, Out]:
    @Parser
    @wraps(func)
    def fn(stream: In, index: int) -> Result[Out]:
        st = Stream(inner=stream, index=index)
        try:
            out = func(st)
        except SoftError as e:
            return e.inner
        return Ok(out, st.index)

    return fn


@overload
def from_stream(func: Callable[[Stream[In]], Out]) -> Parser[In, Out]: ...
@overload
def from_stream(
    func: str,
) -> Callable[[Callable[[Stream[In]], Out]], Parser[In, Out]]: ...


def from_stream(func: str | Callable[[Stream[In]], Out]):
    if isinstance(func, str):
        return lambda f: _from_stream(f).desc(func)

    else:
        return _from_stream(func)
