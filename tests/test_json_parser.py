"""A simple JSON parser.

Adapted from <https://parsy.readthedocs.io/en/latest/howto/other_examples.html>
"""

import json
from typing import Sequence, cast

import pytest

from persil import regex, string
from persil import forward_declaration
from persil import Parser

# Utilities
whitespace = regex(r"\s*")


def lexeme[In: Sequence, Out](p: Parser[In, Out]) -> Parser[In, Out]:
    return p << whitespace


# Punctuation
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
lbrack = lexeme(string("["))
rbrack = lexeme(string("]"))
colon = lexeme(string(":"))
comma = lexeme(string(","))

# Primitives
true = lexeme(string("true")).result(True)
false = lexeme(string("false")).result(False)
null = lexeme(string("null")).result(None)
number = lexeme(regex(r"-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?")).map(float)
string_part = regex(r'[^"\\]+')
string_esc = string("\\") >> (
    string("\\")
    | string("/")
    | string('"')
    | string("b").result("\b")
    | string("f").result("\f")
    | string("n").result("\n")
    | string("r").result("\r")
    | string("t").result("\t")
    | regex(r"u[0-9a-fA-F]{4}").map(lambda s: chr(int(s[1:], 16)))
)
quoted = lexeme(
    string('"')
    >> (string_part | string_esc).many().map(lambda s: "".join(s))
    << string('"')
)


type JsonValue = float | bool | str | list[JsonValue] | dict[str, JsonValue] | None

# Data structures
json_value = forward_declaration()
object_pair = (quoted << colon).combine(json_value)
json_object = lbrace >> object_pair.sep_by(comma).map(dict) << rbrace
array = lbrack >> json_value.sep_by(comma) << rbrack

# Everything
json_value = json_value.become(
    quoted | number | json_object | array | true | false | null
)
json_value = cast(Parser[str, JsonValue], json_value)
json_doc = whitespace >> json_value


@pytest.mark.parametrize(
    "payload",
    [
        0,
        None,
        [0, 0, 42],
        dict(a=2, b='test"'),
    ],
)
@pytest.mark.parametrize("indent", [0, 2, 3, 5])
def test_values(
    payload: JsonValue,
    indent: int,
):
    text = json.dumps(payload, indent=indent)
    assert json_doc.parse(text) == payload
