import pytest

from persil import regex, regex_groupdict, string

parser_plain = regex(r"\d{2}") >> string("/") >> regex(r"\d{2}") >> string("/") >> regex(r"\d{4}")
parser_groups = regex_groupdict(r"(?P<day>\d\d)/(?P<month>\d\d)/(?P<year>\d\d\d\d)")

EXAMPLES = [
    ("23/10/1993", dict(day="23", month="10", year="1993")),
]


@pytest.mark.parametrize("message,expected", EXAMPLES)
def test_string_parser(message: str, expected: dict):
    assert parser_groups.parse(message) == expected
    assert parser_plain.parse(message) == expected["year"]
