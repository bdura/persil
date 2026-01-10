import json
from typing import Sequence, cast

import pytest

from persil import regex, string
from persil import Parser
from persil import lazy

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
boolean = (true | false).desc("boolean")
null = lexeme(string("null")).result(None).desc("null")
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


@lazy
def json_array() -> Parser[str, list[JsonValue]]:
    return lbrack >> json_value.sep_by(comma) << rbrack


@lazy
def object_pair() -> Parser[str, tuple[str, JsonValue]]:
    return (quoted << colon).combine(json_value)


@lazy
def json_object() -> Parser[str, dict[str, JsonValue]]:
    return lbrace >> object_pair.sep_by(comma).map(dict) << rbrace


# Everything
json_value = cast(
    Parser[str, JsonValue],
    quoted | number | json_object | json_array | boolean | null,
)

json_doc = whitespace >> json_value


@pytest.mark.parametrize(
    "payload",
    [
        0,
        None,
        [0, 0, 42],
        dict(a=2, b='test"'),
        [dict(a_test=[1, 2, 3.4], b='test"', c=dict())],
    ],
)
@pytest.mark.parametrize("indent", [0, 2, 3, 5])
def test_values(
    payload: JsonValue,
    indent: int,
):
    text = json.dumps(payload, indent=indent)
    assert json_doc.parse(text) == payload
