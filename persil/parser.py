from typing import Callable, Generic, Sequence, TypeVar, cast

from .result import Err, Ok, Result

Input = TypeVar("Input", bound=Sequence)
Output = TypeVar("Output")

T = TypeVar("T")
In = TypeVar("In", bound=Sequence)


class Parser(Generic[Input, Output]):
    """
    A Parser is an object that wraps a function whose arguments are
    a string to be parsed and the index on which to begin parsing.
    The function should return either `Result.success(next_index, value)`,
    where the next index is where to continue the parse and the value is
    the yielded value, or `Result.failure(index, expected)`, where expected
    is a string indicating what was expected, and the index is the index
    of the failure.
    """

    def __init__(
        self,
        wrapped_fn: Callable[[Input, int], Result[Output]],
    ):
        self.wrapped_fn = wrapped_fn

    def __call__(self, stream: Input, index: int) -> Result[Output]:
        return self.wrapped_fn(stream, index)

    def cut(self) -> "Parser[Input, Output]":
        """
        Commit to the current branch by raising the error one is returned.

        Without `cut`, the error is _returned_, not _raised_, and bubles up
        until it is handled by another parser (see `optional` for an example),
        or raised by the `parse(_partial)` top-level method.
        """

        @Parser
        def cut_parser(stream: Input, index: int) -> Result[Output]:
            result = self(stream, index)
            return result.ok_or_raise()

        return cut_parser

    def then(self, other: "Parser[In, T]") -> "Parser[Input, T]":
        """
        Returns a parser which, if the initial parser succeeds, will
        continue parsing with `other`. This will produce the
        value produced by `other`.

        Parameters
        ----------
        other
            Other parser to apply if the initial parser succeeds.
        """

        @Parser
        def then_parser(stream: Input, index: int) -> Result[T]:
            result = self(stream, index)

            if isinstance(result, Err):
                return result

            return other(stream, result.index)  # type: ignore

        return then_parser

    def skip(self, other: "Parser") -> "Parser[Input, Output]":
        """
        Returns a parser which, if the initial parser succeeds, will
        continue parsing with `other`. It will produce the
        value produced by the initial parser.

        Parameters
        ----------
        other
            Other parser to apply if the initial parser succeeds.
        """

        @Parser
        def skip_parser(stream: Input, index: int) -> Result[Output]:
            result = self(stream, index)

            if isinstance(result, Err):
                return result

            other_result = other(stream, result.index)

            if isinstance(other_result, Err):
                return other_result

            return result

        return skip_parser

    # >>
    def __rshift__(
        self,
        other: "Parser[In, T]",
    ) -> "Parser[Input, T]":
        return self.then(other)

    # <<
    def __lshift__(
        self,
        other: "Parser",
    ) -> "Parser[Input, Output]":
        return self.skip(other)

    def combine(
        self,
        other: "Parser[Input, T]",
    ) -> "Parser[Input, tuple[Output, T]]":
        """
        Returns a parser which, if the initial parser succeeds, will
        continue parsing with `other`. It will produce a tuple
        containing the results from both parsers, in order.

        The resulting parser fails if `other` fails.

        Parameters
        ----------
        other
            Other parser to combine.
        """

        @Parser
        def combined_parser(stream: Input, index: int) -> Result[tuple[Output, T]]:
            res1 = self(stream, index)

            if isinstance(res1, Err):
                return res1

            res2 = other(stream, res1.index)

            if isinstance(res2, Err):
                return res2

            return Ok((res1.value, res2.value), res2.index)

        return combined_parser

    def __and__(
        self,
        other: "Parser[Input, T]",
    ) -> "Parser[Input, tuple[Output, T]]":
        return self.combine(other)

    def parse(
        self,
        stream: Input,
    ) -> Output:
        """
        Parses a string or list of tokens and returns the result or raise a ParseError.

        Parameters
        ----------
        stream
            Input to match the parser against.
        """
        (result, _) = (self << eof).parse_partial(stream)
        return result

    def parse_partial(
        self,
        stream: Input,
    ) -> tuple[Output, Input]:
        """
        Parses the longest possible prefix of a given string.
        Returns a tuple of the result and the unparsed remainder,
        or raises `ParseError`.

        Parameters
        ----------
        stream
            Input to match the parser against.
        """

        result = self(stream, 0)

        if isinstance(result, Err):
            raise result

        value = result.value
        remainder = cast(Input, stream[result.index :])

        return (value, remainder)

    def map(
        self,
        map_function: Callable[[Output], T],
    ) -> "Parser[Input, T]":
        """
        Returns a parser that transforms the produced value of the initial parser
        with `map_function`.
        """

        @Parser
        def mapped_parser(stream: Input, index: int) -> Result[T]:
            res = self(stream, index)
            return res.map(map_function)

        return mapped_parser

    def result(self, value: T) -> "Parser[Input, T]":
        """
        Returns a parser that, if the initial parser succeeds, always produces
        the passed in `value`.
        """

        @Parser
        def result_parser(stream: Input, index: int) -> Result[T]:
            res = self(stream, index)

            if isinstance(res, Err):
                return res

            return Ok(value, res.index)

        return result_parser

    def times(
        self,
        min: int,
        max: int | None = None,
    ) -> "Parser[Input, list[Output]]":
        """
        Returns a parser that expects the initial parser at least `min` times,
        and at most `max` times, and produces a list of the results. If only one
        argument is given, the parser is expected exactly that number of times.

        Parameters
        ----------
        min
            Minimal number of times the parser should match.
        max
            Maximal number of times the parser should match.
            Equals to `min` by default
        """
        if max is None:
            max = min

        @Parser
        def times_parser(stream: Input, index: int) -> Result[list[Output]]:
            values = []
            times = 0
            result = None

            while times < max:
                result = self(stream, index)
                if isinstance(result, Ok):
                    values.append(result.value)
                    index = result.index
                    times += 1
                elif times >= min:
                    break
                else:
                    return result

            return Ok(values, index)

        return times_parser

    def many(self) -> "Parser[Input, list[Output]]":
        """
        Returns a parser that expects the initial parser 0 or more times, and
        produces a list of the results.
        """
        return self.times(0, 9999999)

    def at_most(self, n: int) -> "Parser[Input, list[Output]]":
        """
        Returns a parser that expects the initial parser at most `n` times, and
        produces a list of the results.

        Parameters
        ----------
        n
            Maximum number of times the parser should match.
        """
        return self.times(0, n)

    def at_least(self, n: int) -> "Parser[Input, list[Output]]":
        """
        Returns a parser that expects the initial parser at least `n` times, and
        produces a list of the results.

        Parameters
        ----------
        n
            Minimum number of times the parser should match.
        """
        return self.times(n) + self.many()

    def optional(self, default: T | None = None) -> "Parser[Input, Output | T | None]":
        """
        Returns a parser that expects the initial parser zero or once, and maps
        the result to a given default value in the case of no match. If no default
        value is given, `None` is used.

        Parameters
        ----------
        default
            Default value to output.
        """

        @Parser
        def optional_parser(stream: Input, index: int) -> Result[Output | T | None]:
            res = self(stream, index)

            if isinstance(res, Ok):
                return Ok(res.value, res.index)

            return Ok(default, index)

        return optional_parser

    def until(
        self,
        other: "Parser[Input, T]",
        min: int = 0,
        max: int = 999999,
    ) -> "Parser[Input, tuple[list[Output], T]]":
        """
        Returns a parser that expects the initial parser followed by `other`.
        The initial parser is expected at least `min` times and at most `max` times.

        The new parser consumes `other` and returns it as part of an output tuple.
        If you are looking for a non-consuming parser, checkout `until_and_discard`.

        Parameters
        ----------
        other
            Other parser to check.
        min
            Minimum number of times that the initial parser should match before
            matching `other`
        max
            Maximum number of times that the initial parser should match before
            matching `other`
        """

        @Parser
        def until_parser(stream: Input, index: int) -> Result[tuple[list[Output], T]]:
            values: list[Output] = []
            times = 0

            while True:
                # try parser first
                res = other(stream, index)

                if isinstance(res, Ok) and times >= min:
                    return Ok((values, res.value), index)

                # exceeded max?
                if isinstance(res, Ok) and times >= max:
                    # return failure, it matched parser more than max times
                    return Err(index, [f"at most {max} items"], stream)

                # failed, try parser
                result = self(stream, index)

                if isinstance(result, Ok):
                    values.append(result.value)
                    index = result.index
                    times += 1
                    continue

                if times >= min:
                    # return failure, parser is not followed by other
                    return Err(index, ["did not find other parser"], stream)
                else:
                    # return failure, it did not match parser at least min times
                    return Err(
                        index,
                        [f"at least {min} items; got {times} item(s)"],
                        stream,
                    )

        return until_parser

    def until_and_discard(
        self,
        other: "Parser[Input, T]",
        min: int = 0,
        max: int = 999999,
    ) -> "Parser[Input, list[Output]]":
        """
        Returns a parser that expects the initial parser followed by `other`.
        The initial parser is expected at least `min` times and at most `max` times.

        Does not consume `other`. If you are looking for that behaviour,
        checkout `until`.

        Parameters
        ----------
        other
            Other parser to check.
        min
            Minimum number of times that the initial parser should match before
            matching `other`.
        max
            Maximum number of times that the initial parser should match before
            matching `other`.
        """

        def discard_next_value(output: tuple[list[Output], T]) -> list[Output]:
            values, _ = output
            return values

        return self.until(other, min=min, max=max).map(discard_next_value)

    def sep_by(
        self,
        sep: "Parser",
        *,
        min: int = 0,
        max: int = 999999,
    ) -> "Parser[Input, list[Output]]":
        """
        Returns a new parser that repeats the initial parser and
        collects the results in a list. Between each item, the `sep` parser
        is run (and its return value is discarded). By default it
        repeats with no limit, but minimum and maximum values can be supplied.

        Parameters
        ----------
        sep
            Parser that separates values.
        min
            Minimum number of times that the initial parser should match.
        max
            Maximum number of times that the initial parser should match.
        """
        zero_times: Parser[Input, list[Output]] = success([])

        if max == 0:
            return zero_times
        res = self.times(1) + (sep >> self).times(min - 1, max - 1)
        if min == 0:
            res |= zero_times
        return res

    def desc(
        self,
        description: str,
    ) -> "Parser[Input, Output]":
        """
        Returns a new parser with a description added, which is used in the error message
        if parsing fails.

        Parameters
        ----------
        description
            Description in case of failure.
        """

        @Parser
        def desc_parser(stream: Input, index: int) -> Result[Output]:
            result = self(stream, index)
            if isinstance(result, Ok):
                return result
            return Err(index, [description], stream)

        return desc_parser

    def should_fail(
        self,
        description: str,
    ) -> "Parser[Input, Result[Output]]":
        """
        Returns a parser that fails when the initial parser succeeds, and succeeds
        when the initial parser fails (consuming no input). A description must
        be passed which is used in parse failure messages.

        This is essentially a negative lookahead.

        Parameters
        ----------
        description
            Description in case of failure.
        """

        @Parser
        def fail_parser(stream: Input, index: int):
            res = self(stream, index)
            if isinstance(res, Ok):
                return Err(index, [description], stream)
            return Ok(res, index)

        return fail_parser

    def __add__(self, other: "Parser[Input, Output]") -> "Parser[Input, Output]":
        @Parser
        def inner(stream: Input, index: int) -> Result[Output]:
            res1 = self(stream, index)

            if isinstance(res1, Err):
                return res1

            res2 = other(stream, res1.index)

            if isinstance(res2, Err):
                return res2

            return Ok(res1.value + res2.value, res2.index)  # type: ignore

        return inner

    def __or__(
        self,
        other: "Parser[Input, T]",
    ) -> "Parser[Input, Output | T]":
        @Parser
        def alt_parser(stream: Input, index: int) -> Result[Output | T]:
            res1 = self(stream, index)

            if isinstance(res1, Ok):
                return Ok(res1.value, res1.index)

            res2 = other(stream, index)

            if isinstance(res2, Err):
                return res2

            return Ok(res2.value, res2.index)

        return alt_parser


def success(
    value: T,
) -> Parser[Input, T]:
    """
    Returns a parser that does not consume any of the stream, but
    produces `value`.

    Parameters
    ----------
    value
        Value to return.
    """
    return Parser(lambda _, index: Ok(value, index))


@Parser
def eof(stream: Input, index: int) -> Result[None]:
    """
    A parser that only succeeds if the end of the stream has been reached.
    """

    if index >= len(stream):
        return Ok(None, index)
    else:
        return Err(index, ["EOF"], stream)
