import pytest

from persil import tag
from persil.result import Err

parser = tag("TeSt", transform=lambda s: s.lower())

EXAMPLES = [
    "test",
    "TeSt",
    "TEST",
]


@pytest.mark.parametrize("message", EXAMPLES)
def test_string_parser(message: str):
    parser.parse(message)


def test_transformed_tag_no_match():
    with pytest.raises(Err):
        parser.parse("nope")


def test_string_bytes_parser():
    parser_bytes = tag(b"TeSt").map(lambda b: b.decode())
    assert parser_bytes.parse(b"TeSt") == "TeSt"
