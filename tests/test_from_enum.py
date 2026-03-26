import enum

import pytest
from hypothesis import given, strategies as st

from persil import from_enum
from persil.result import Err


class Defcon(enum.Enum):
    FIVE = "5"
    FOUR = "4"
    THREE = "3"
    TWO = "2"
    ONE = "1"


class EmptyEnum(enum.Enum):
    pass


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


def test_from_enum_empty_does_not_crash():
    # Constructing a parser from an empty enum must not raise IndexError.
    # Parsing any input should raise a parse error, not a Python exception.
    empty_parser = from_enum(EmptyEnum)
    with pytest.raises(Err):
        empty_parser.parse("anything")


@given(member=st.sampled_from(list(Defcon)))
def test_from_enum_all_members(member: Defcon):
    """from_enum parses every member value and returns the correct member."""
    assert parser.parse(str(member.value)) == member
