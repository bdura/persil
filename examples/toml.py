"""Minimal TOML parser.

Supports: bare keys, dotted keys, basic/literal strings, integers, floats,
booleans, arrays, inline tables, and [table] / [[array-of-tables]] headers.

Not supported: multi-line strings, datetime types, unicode escapes beyond
\\uXXXX, or the full TOML spec edge cases.
"""

import sys
from typing import Any, Sequence

from rich import print as rprint

from persil import Parser, lazy, regex, string

# ==============================================================================
# Whitespace & comments
# ==============================================================================

# Inline whitespace only (spaces and tabs, not newlines).
ws = regex(r"[ \t]*")

# A comment runs from '#' to end of line.
comment = regex(r"#[^\n]*")

# Newline: optional comment then line ending.
newline = ws >> comment.optional() >> regex(r"\n")

# One or more blank/comment lines.
newlines = newline.at_least(1)

# Optional blank lines (used between entries).
skip_newlines = newline.many()


def lexeme[In: Sequence, Out](p: Parser[In, Out]) -> Parser[In, Out]:
    return p << ws


# ==============================================================================
# Punctuation
# ==============================================================================

lbrack = lexeme(string("["))
rbrack = lexeme(string("]"))
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
comma = lexeme(string(","))
dot = lexeme(string("."))
equals = lexeme(string("="))

# ==============================================================================
# Primitive values
# ==============================================================================

toml_true = lexeme(string("true")).result(True)
toml_false = lexeme(string("false")).result(False)
toml_boolean = (toml_true | toml_false).desc("boolean")

# Integers: decimal, hex, octal, binary. Underscores allowed as separators.
toml_hex_int = regex(r"0x[0-9a-fA-F]([0-9a-fA-F_]*[0-9a-fA-F])?").map(
    lambda s: int(s.replace("_", ""), 16)
)
toml_oct_int = regex(r"0o[0-7]([0-7_]*[0-7])?").map(
    lambda s: int(s.replace("_", ""), 8)
)
toml_bin_int = regex(r"0b[01]([01_]*[01])?").map(lambda s: int(s.replace("_", ""), 2))
toml_dec_int = regex(r"[+-]?[0-9]([0-9_]*[0-9])?").map(
    lambda s: int(s.replace("_", ""))
)
toml_integer = (toml_hex_int | toml_oct_int | toml_bin_int | toml_dec_int).desc(
    "integer"
)

# Floats: must contain a dot or exponent to distinguish from integers.
toml_special_float = regex(r"[+-]?(inf|nan)").map(float).desc("float")
toml_regular_float = (
    regex(
        r"[+-]?[0-9]([0-9_]*[0-9])?"
        r"(\.[0-9]([0-9_]*[0-9])?)"
        r"([eE][+-]?[0-9]([0-9_]*[0-9])?)?"
        r"|"
        r"[+-]?[0-9]([0-9_]*[0-9])?"
        r"[eE][+-]?[0-9]([0-9_]*[0-9])?"
    )
    .map(lambda s: float(s.replace("_", "")))
    .desc("float")
)
toml_float = toml_special_float | toml_regular_float

# Strings — basic (double-quoted) with escape sequences.
ESCAPE_MAP = {
    "\\": "\\",
    '"': '"',
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}
basic_str_char = regex(r'[^"\\]+')
basic_str_esc = string("\\") >> regex(r'[\\/"bfnrt]|u[0-9a-fA-F]{4}').map(
    lambda s: ESCAPE_MAP.get(s, chr(int(s[1:], 16)))
)
basic_string = (
    string('"') >> (basic_str_char | basic_str_esc).many().map("".join) << string('"')
).desc("basic string")

# Strings — literal (single-quoted), no escapes.
literal_string = (string("'") >> regex(r"[^']*") << string("'")).desc("literal string")

toml_string = lexeme(basic_string | literal_string)


# ==============================================================================
# Keys
# ==============================================================================

# A bare key is alphanumeric, dashes, or underscores.
bare_key = regex(r"[A-Za-z0-9_-]+").desc("bare key")

# A single key is either bare or quoted.
simple_key = lexeme(bare_key | basic_string | literal_string)

# A dotted key like `a.b.c` is a list of simple keys.
dotted_key = simple_key.sep_by(dot, min=1).desc("key")


# ==============================================================================
# Compound values (arrays and inline tables)
# ==============================================================================

type TomlValue = int | float | bool | str | list[TomlValue] | dict[str, TomlValue]


@lazy
def toml_array() -> Parser[str, list[TomlValue]]:
    # Arrays allow trailing commas and newlines between elements.
    return (
        lbrack
        >> skip_newlines
        >> toml_value.sep_by(comma << skip_newlines)
        << (comma << skip_newlines).optional()
        << rbrack
    )


@lazy
def inline_pair() -> Parser[str, tuple[str, TomlValue]]:
    # Inline tables only allow simple keys (no dotted keys).
    return (simple_key << equals) & toml_value


@lazy
def inline_table() -> Parser[str, dict[str, TomlValue]]:
    return lbrace >> inline_pair.sep_by(comma).map(dict) << rbrace


toml_value = (
    toml_string | toml_boolean | toml_float | toml_integer | toml_array | inline_table
).desc("value")


# ==============================================================================
# Top-level document structure
# ==============================================================================

# A key-value pair on its own line: `key = value`.
key_value = (dotted_key << equals) & toml_value


def set_nested(root: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set a value in a nested dict, creating intermediate tables as needed."""
    for key in keys[:-1]:
        if key not in root:
            root[key] = {}
        root = root[key]
    root[keys[-1]] = value


def parse_toml(text: str) -> dict[str, Any]:
    """Parse a TOML document string into a nested dict.

    We parse individual lines/sections rather than building one giant parser
    for the whole document, because TOML's stateful table-header semantics
    (where `[table]` changes the "current table" for subsequent key-value
    pairs) don't map cleanly onto pure parser combinators.
    """
    root: dict[str, Any] = {}
    current_table: dict[str, Any] = root

    for line in text.split("\n"):
        line = line.strip()

        # Skip blank lines and comments.
        if not line or line.startswith("#"):
            continue

        # [[array-of-tables]] header.
        if line.startswith("[["):
            header = line.strip("[] \t")
            keys = dotted_key.parse(header)
            # Navigate to the parent, creating tables as needed.
            target = root
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            # Append a new table to the array.
            last = keys[-1]
            if last not in target:
                target[last] = []
            target[last].append({})
            current_table = target[last][-1]
            continue

        # [table] header.
        if line.startswith("["):
            header = line.strip("[] \t")
            keys = dotted_key.parse(header)
            # Navigate/create the nested table.
            target = root
            for key in keys:
                if key not in target:
                    target[key] = {}
                target = target[key]
            current_table = target
            continue

        # Key-value pair.
        (keys, value) = key_value.parse(line)
        set_nested(current_table, keys, value)

    return root


if __name__ == "__main__":
    text = sys.stdin.read()
    result = parse_toml(text)
    rprint(result)
