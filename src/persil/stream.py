from functools import wraps
from typing import Callable, Sequence, overload

from .parser import Parser
from .result import Err, Ok, ParseError, Result


class Backtrack(Exception):
    """Control-flow signal raised by `Stream.apply` when a parser returns `Err`.

    This is *not* a user-facing error. It is caught internally by `_from_stream`
    to convert the failure back into a returned `Err`, allowing combinators
    like `|` to try alternatives.

    By contrast, `ParseError` represents a *committed* failure (e.g. after `Parser.cut`)
    and is never caught by `_from_stream`.
    """

    def __init__(self, inner: Err) -> None:
        self.inner = inner
        super().__init__()


class Stream[In: Sequence]:
    """Wrapper around the input to allow applying parsers sequentially while
    maintaining the necessary bookeeping.

    See `from_stream` for more information.
    """

    def __init__(self, inner: In, index: int = 0):
        self.inner = inner
        self.index = index

    def apply[Out](self, parser: Parser[In, Out]) -> Out:
        res = parser(self.inner, self.index)

        if isinstance(res, Err):
            raise Backtrack(res)

        self.index = res.index

        return res.value


def _from_stream[In: Sequence, Out](
    func: Callable[[Stream[In]], Out],
) -> Parser[In, Out]:
    @Parser
    @wraps(func)
    def fn(stream: In, index: int) -> Result[Out]:
        st = Stream(inner=stream, index=index)
        try:
            out = func(st)
        except Backtrack as e:
            return e.inner
        except ParseError:
            # NOTE: A cut() inside the stream function raises ParseError;
            # re-raise so it propagates past the caller.
            raise
        return Ok(out, st.index)

    return fn


@overload
def from_stream[In: Sequence, Out](
    func: Callable[[Stream[In]], Out],
) -> Parser[In, Out]: ...
@overload
def from_stream[In: Sequence, Out](
    func: Callable[[Stream[In]], Out],
    *,
    desc: str,
) -> Parser[In, Out]: ...
@overload
def from_stream[In: Sequence, Out](
    *,
    desc: str,
) -> Callable[[Callable[[Stream[In]], Out]], Parser[In, Out]]: ...


def from_stream[In: Sequence, Out](
    func: Callable[[Stream[In]], Out] | None = None,
    *,
    desc: str | None = None,
) -> (
    Parser[In, Out]
    | Callable[
        [Callable[[Stream[In]], Out]],
        Parser[In, Out],
    ]
):
    r"""Create a parser from a function that operates on a `Stream`.

    Can be used as a bare decorator, a decorator with a description, or
    called directly with a function and an optional description.

    Examples:

        @from_stream
        def my_parser(stream: Stream[str]) -> int: ...

        @from_stream(desc="my parser")
        def my_parser(stream: Stream[str]) -> int: ...

        parser = from_stream(my_func, desc="my parser")

        @from_stream
        def datetime_parser(stream: Stream[str]) -> datetime:
            year = stream.apply(regex(r"\d{4}").map(int))
            stream.apply(string("/"))
            month = stream.apply(regex(r"\d{2}").map(int))
            stream.apply(string("/"))
            day = stream.apply(regex(r"\d{2}").map(int))
            return datetime(year, month, day)
    """

    def _wrap(f: Callable[[Stream[In]], Out]) -> Parser[In, Out]:
        p = _from_stream(f)
        return p.desc(desc) if desc is not None else p

    if func is not None:
        return _wrap(func)

    return _wrap
