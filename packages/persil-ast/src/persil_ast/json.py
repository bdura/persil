"""JSON AST parser with source locations.

Parses JSON into an AST where every key and value carries a Span (start/stop
RowCol), suitable for use in an LSP.
"""

from dataclasses import dataclass
from typing import Any, Sequence, cast

from persil import Parser, lazy, regex, string
from persil.utils import Span

# ==============================================================================
# AST node types
# ==============================================================================


@dataclass
class JsonKeyValue:
    key: Span[str]
    value: "Span[JsonValue]"


@dataclass
class JsonObject:
    """A JSON object, preserving key spans. Wraps a list of key-value pairs
    (rather than a plain list) so that empty objects are distinguishable from
    empty arrays."""

    entries: list[JsonKeyValue]


type JsonValue = int | float | bool | str | list["Span[JsonValue]"] | JsonObject | None


@dataclass
class JsonDocument:
    value: Span[JsonValue]


# ==============================================================================
# Whitespace
# ==============================================================================

ws = regex(r"\s*")


def lexeme[In: Sequence, Out](p: Parser[In, Out]) -> Parser[In, Out]:
    return p << ws


# ==============================================================================
# Punctuation
# ==============================================================================

lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
lbrack = lexeme(string("["))
rbrack = lexeme(string("]"))
colon = lexeme(string(":"))
comma = lexeme(string(","))

# ==============================================================================
# Primitive values
# ==============================================================================

json_true = lexeme(string("true")).result(True)
json_false = lexeme(string("false")).result(False)
json_boolean = (json_true | json_false).desc("boolean")
json_null = lexeme(string("null")).result(None).desc("null")


def _parse_number(s: str) -> int | float:
    if "." in s or "e" in s or "E" in s:
        return float(s)
    return int(s)


json_number = (
    lexeme(regex(r"-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?"))
    .map(_parse_number)
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

_string_part = regex(r'[^"\\]+')
_string_esc = string("\\") >> regex(r'[\\/"bfnrt]|u[0-9a-fA-F]{4}').map(
    lambda s: ESCAPE_MAP[s] if s in ESCAPE_MAP else chr(int(s[1:], 16))
)
json_string = lexeme(
    string('"')
    >> (_string_part | _string_esc).many().map(lambda s: "".join(s))
    << string('"')
).desc("string")

# ==============================================================================
# Compound values (arrays and objects)
# ==============================================================================


@lazy
def json_array() -> Parser[str, list[Span[JsonValue]]]:
    return lbrack >> json_value.span().sep_by(comma) << rbrack


@lazy
def _object_pair() -> Parser[str, JsonKeyValue]:
    return ((json_string.span() << colon) & json_value.span()).map(
        lambda pair: JsonKeyValue(key=pair[0], value=pair[1])
    )


@lazy
def json_object() -> Parser[str, JsonObject]:
    return (lbrace >> _object_pair.sep_by(comma) << rbrace).map(JsonObject)


# ==============================================================================
# Top-level value and document parsers
# ==============================================================================

json_value = cast(
    Parser[str, JsonValue],
    (
        json_string | json_boolean | json_null | json_number | json_object | json_array
    ).desc("JSON value"),
)

json_doc = (ws >> json_value.span()).map(JsonDocument)


# ==============================================================================
# Resolution: AST -> plain Python values
# ==============================================================================


def resolve(doc: JsonDocument) -> Any:
    """Convert a JsonDocument AST into plain Python values, dropping spans."""
    return _unwrap(doc.value.value)


def _unwrap(val: JsonValue) -> Any:
    if isinstance(val, JsonObject):
        return {kv.key.value: _unwrap(kv.value.value) for kv in val.entries}
    if isinstance(val, list):
        return [_unwrap(item.value) for item in val]
    return val
