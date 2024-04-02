import pytest
from pydantic import BaseModel

from persil import regex
from persil.stream import Stream, from_stream


class Flight(BaseModel):
    carrier: str
    flight_number: int


@from_stream("Flight parser")
def flight_parser(stream: Stream[str]) -> Flight:
    carrier = stream.apply(regex(r"[A-Z]{2}"))
    flight_number = stream.apply(regex(r"\d{2,4}").map(int))

    return Flight(carrier=carrier, flight_number=flight_number)


EXAMPLES = [
    ("AF071", Flight(carrier="AF", flight_number=71)),
    ("LY180", Flight(carrier="LY", flight_number=180)),
]


@pytest.mark.parametrize("message,expected", EXAMPLES)
def test_generate(message: str, expected: Flight):
    flight = flight_parser.parse(message)
    assert flight == expected
