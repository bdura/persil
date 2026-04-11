import pytest
from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from persil import regex, string
from persil.stream import Stream, from_stream

from persil.result import Err

year_parser = regex(r"\d{4}").map(int)
month_parser = regex(r"(?:0\d|1[012])").map(int)
day_parser = regex(r"(?:[012]\d|3[01])").map(int)


@from_stream
def datetime_parser(stream: Stream[str]) -> datetime:
    year = stream.apply(year_parser)
    stream.apply(string("-"))
    month = stream.apply(month_parser)
    stream.apply(string("-"))
    day = stream.apply(day_parser)

    return datetime(year, month, day)


@given(
    st.datetimes(
        min_value=datetime(1000, 1, 1),
        max_value=datetime(9999, 12, 31),
    )
)
def test_datetime_parser_from_stream(dt: datetime):
    dt = datetime(dt.year, dt.month, dt.day)
    text = dt.strftime("%Y-%m-%d")
    assert datetime_parser.parse(text) == dt


def test_from_stream_failure_path():
    @from_stream
    def must_see_hello(stream: Stream[str]) -> str:
        return stream.apply(string("hello"))

    with pytest.raises(Err):
        must_see_hello.parse("goodbye")


def test_from_stream_with_desc():
    @from_stream(desc="a greeting")
    def must_see_hello(stream: Stream[str]) -> str:
        return stream.apply(string("hello"))

    assert must_see_hello.parse("hello") == "hello"

    with pytest.raises(Err, match="greeting"):
        must_see_hello.parse("goodbye")


@given(text=st.from_regex(r"[a-z]+", fullmatch=True))
def test_from_stream_single_apply_equivalent(text: str):
    """A from_stream parser that applies a single inner parser must produce
    the same result as calling the inner parser directly."""
    inner = regex(r"[a-z]+")

    @from_stream
    def via_stream(stream: Stream[str]) -> str:
        return stream.apply(inner)

    assert via_stream.parse(text) == inner.parse(text)
