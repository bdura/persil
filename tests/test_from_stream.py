from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from persil import regex, string
from persil.stream import Stream, from_stream

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


@given(st.datetimes())
def test_generate(dt: datetime):
    dt = datetime(dt.year, dt.month, dt.day)
    text = dt.strftime("%Y-%m-%d")
    assert datetime_parser.parse(text) == dt
