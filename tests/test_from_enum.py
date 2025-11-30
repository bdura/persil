import enum

import pytest

from persil import from_enum


class Defcon(enum.Enum):
    FIVE = "5"
    FOUR = "4"
    THREE = "3"
    TWO = "2"
    ONE = "1"


parser = from_enum(Defcon)


@pytest.mark.parametrize(
    "message,expected",
    [
        ("5", Defcon.FIVE),
        ("3", Defcon.THREE),
        ("1", Defcon.ONE),
    ],
)
def test_from_enums(message: str, expected: Defcon):
    res = parser.parse(message)
    assert res == expected
