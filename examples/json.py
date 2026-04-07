import sys
from typing import Sequence, cast

from rich import print as rprint

from persil import regex, string
from persil import Parser
from persil import lazy

ws = regex(r"\s*")


def lexeme[In: Sequence, Out](p: Parser[In, Out]) -> Parser[In, Out]:
    return p << ws


# Punctuation
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
lbrack = lexeme(string("["))
rbrack = lexeme(string("]"))
colon = lexeme(string(":"))
comma = lexeme(string(","))


# Primitives
json_true = lexeme(string("true")).result(True)
json_false = lexeme(string("false")).result(False)
json_boolean = (json_true | json_false).desc("boolean")
json_null = lexeme(string("null")).result(None).desc("null")


def parse_number(s: str) -> int | float:
    if "." in s or "e" in s or "E" in s:
        return float(s)
    return int(s)


json_number = (
    lexeme(regex(r"-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?"))
    .map(parse_number)
    .desc("number")
)

ESCAPE_MAP = {
    "\\": "\\",
    "/": "/",
    '"': '"',
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}

string_part = regex(r'[^"\\]+')
string_esc = string("\\") >> regex(r'[\\/"bfnrt]|u[0-9a-fA-F]{4}').map(
    lambda s: ESCAPE_MAP.get(s, chr(int(s[1:], 16)))
)
quoted = lexeme(
    string('"')
    >> (string_part | string_esc).many().map(lambda s: "".join(s))
    << string('"')
).desc("string")


type JsonValue = (
    int | float | bool | str | list[JsonValue] | dict[str, JsonValue] | None
)


@lazy
def json_array() -> Parser[str, list[JsonValue]]:
    return lbrack >> json_value.sep_by(comma) << rbrack


@lazy
def object_pair() -> Parser[str, tuple[str, JsonValue]]:
    return (quoted << colon) & json_value


@lazy
def json_object() -> Parser[str, dict[str, JsonValue]]:
    return lbrace >> object_pair.sep_by(comma).map(dict) << rbrace


# Everything
json_value = cast(
    Parser[str, JsonValue],
    (quoted | json_boolean | json_null | json_number | json_object | json_array).desc(
        "JSON value"
    ),
)

json_doc = ws >> json_value


if __name__ == "__main__":
    text = sys.stdin.read()
    result = json_doc.parse(text)
    rprint(result)
