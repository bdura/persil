import pytest
from persil import string

parser = string("TeSt", transform=lambda s: s.lower())

EXAMPLES = [
    "test",
    "TeSt",
    "TEST",
]


@pytest.mark.parametrize("message", EXAMPLES)
def test_string_parser(message: str):
    parser.parse(message)
