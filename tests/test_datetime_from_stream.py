from datetime import datetime

import pytest

from persil import Stream, from_stream, regex, string


@from_stream
def datetime_parser(stream: Stream[str]) -> datetime:
    year = stream.apply(regex(r"\d{4}").map(int))
    stream.apply(string("/"))
    month = stream.apply(regex(r"\d{2}").map(int))
    stream.apply(string("/"))
    day = stream.apply(regex(r"\d{2}").map(int))
    return datetime(year, month, day)


EXAMPLES = [
    ("2024/10/01", datetime(2024, 10, 1)),
]


@pytest.mark.parametrize("message,expected", EXAMPLES)
def test_datetime_from_stream(message: str, expected: datetime):
    dt = datetime_parser.parse(message)
    assert dt == expected
