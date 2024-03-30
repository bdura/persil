import pytest
from pydantic import BaseModel

from persil import generate
from persil.parser import Parser
from persil.parsers import regex


class Flight(BaseModel):
    carrier: str
    flight_number: int

    @staticmethod
    def parser() -> Parser["Flight"]:
        @generate
        def parser():
            carrier = yield regex(r"[A-Z]{2}")
            flight_number = yield regex(r"\d{2,4}")
            return dict(
                carrier=carrier,
                flight_number=flight_number,
            )

        return parser.map(Flight.model_validate)


EXAMPLES = [
    ("AF071", Flight(carrier="AF", flight_number=71)),
    ("LY180", Flight(carrier="LY", flight_number=180)),
]

flight_parser = Flight.parser()


@pytest.mark.parametrize("message,expected", EXAMPLES)
def test_generate(message: str, expected: Flight):
    flight = flight_parser.parse(message)
    assert flight == expected
