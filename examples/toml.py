"""TOML AST parser with source locations.

Parses TOML into an AST where every key and value carries a Span (start/stop
RowCol), suitable for use in an LSP.

Supports: bare keys, dotted keys, basic/literal strings, integers, floats,
booleans, arrays, inline tables, and [table] / [[array-of-tables]] headers.

Not supported: multi-line strings, datetime types, unicode escapes beyond
\\uXXXX, or the full TOML spec edge cases.
"""

import sys
from dataclasses import dataclass
from typing import Any, Sequence

from rich import print as rprint

from persil import Parser, lazy, regex, string
from persil.parser import eof
from persil.stream import Backtrack, Stream, from_stream
from persil.utils import Span

# ==============================================================================
# AST node types
# ==============================================================================

type TomlValue = int | float | bool | str | list[TomlValue] | dict[str, TomlValue]


@dataclass
class TomlKeyValue:
    key: Span[list[str]]
    value: Span[TomlValue]


@dataclass
class TomlTableHeader:
    key: Span[list[str]]


@dataclass
class TomlArrayTableHeader:
    key: Span[list[str]]


@dataclass
class TomlTable:
    header: TomlTableHeader | TomlArrayTableHeader | None
    entries: list[TomlKeyValue]


@dataclass
class TomlDocument:
    tables: list[TomlTable]


# ==============================================================================
# Whitespace & comments
# ==============================================================================

# Inline whitespace only (spaces and tabs, not newlines).
ws = regex(r"[ \t]*")

# A comment runs from '#' to end of line.
comment = regex(r"#[^\n]*")

# A single newline, possibly preceded by inline whitespace and a comment.
blank_line = ws >> comment.optional() >> regex(r"\n")

# Optional blank lines (used between array elements).
skip_newlines = blank_line.many()


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
basic_str_esc = string("\\") >> regex(r"[\\\"bfnrt]|u[0-9a-fA-F]{4}").map(
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
# Line-level parsers (single-pass, consuming trailing newline or EOF)
# ==============================================================================

# Trailing content after a meaningful line: optional comment, then newline or EOF.
line_end = ws >> comment.optional() >> (string("\n") | eof())

# [table] header line.
table_header_line = (
    ws >> string("[") >> ws >> dotted_key.span() << ws << string("]") << line_end
).map(TomlTableHeader)

# [[array-of-tables]] header line. Must be tried before table_header_line
# because `[` is a prefix of `[[`.
array_table_header_line = (
    ws >> string("[[") >> ws >> dotted_key.span() << ws << string("]]") << line_end
).map(TomlArrayTableHeader)

# Key = value line.
kv_line = ((ws >> dotted_key.span() << equals) & (toml_value.span() << line_end)).map(
    lambda pair: TomlKeyValue(key=pair[0], value=pair[1])
)

# A single document entry: a header or a key-value pair.
entry = array_table_header_line | table_header_line | kv_line


# ==============================================================================
# Full document parser
# ==============================================================================


@from_stream(desc="TOML document")
def toml_document(stream: Stream[str]) -> TomlDocument:
    tables: list[TomlTable] = []
    current_header: TomlTableHeader | TomlArrayTableHeader | None = None
    current_entries: list[TomlKeyValue] = []

    while True:
        # Skip blank/comment-only lines.
        try:
            while True:
                stream.apply(blank_line)
        except Backtrack:
            pass

        # Check for end of input.
        try:
            stream.apply(eof())
            break
        except Backtrack:
            pass

        # Parse the next entry (header or key-value pair).
        item = stream.apply(entry)
        if isinstance(item, (TomlTableHeader, TomlArrayTableHeader)):
            # Flush the current table and start a new one.
            tables.append(TomlTable(header=current_header, entries=current_entries))
            current_header = item
            current_entries = []
        else:
            current_entries.append(item)

    # Flush the final table.
    tables.append(TomlTable(header=current_header, entries=current_entries))
    return TomlDocument(tables=tables)


# ==============================================================================
# Resolution: AST -> nested dict
# ==============================================================================


def set_nested(root: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set a value in a nested dict, creating intermediate tables as needed."""
    for key in keys[:-1]:
        if key not in root:
            root[key] = {}
        root = root[key]
    root[keys[-1]] = value


def resolve(doc: TomlDocument) -> dict[str, Any]:
    """Convert a TomlDocument AST into a plain nested dict, dropping spans."""
    root: dict[str, Any] = {}

    for table in doc.tables:
        # Determine the target table for this section's key-value pairs.
        target = root
        if table.header is not None:
            keys = table.header.key.value
            if isinstance(table.header, TomlArrayTableHeader):
                # Navigate to the parent, creating intermediate tables as needed.
                for key in keys[:-1]:
                    if key not in target:
                        target[key] = {}
                    target = target[key]
                # Append a new dict to the array.
                last = keys[-1]
                if last not in target:
                    target[last] = []
                target[last].append({})
                target = target[last][-1]
            else:
                # Navigate/create the nested table.
                for key in keys:
                    if key not in target:
                        target[key] = {}
                    target = target[key]

        for entry in table.entries:
            set_nested(target, entry.key.value, entry.value.value)

    return root


if __name__ == "__main__":
    text = sys.stdin.read()
    doc = toml_document.parse(text)
    rprint(doc)
    print("---")
    rprint(resolve(doc))
