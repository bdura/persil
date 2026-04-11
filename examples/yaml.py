"""Minimal YAML AST parser with source locations.

Parses YAML into an AST where every key and value carries a Span (start/stop
RowCol), suitable for use in an LSP.

Supports: block mappings, block sequences, flow sequences/mappings,
scalars (plain, double-quoted, single-quoted), integers, floats,
booleans (true/false), null (null/~), comments, multi-document (---/...).

Not supported: anchors/aliases (&/*), tags (!!), multi-line block scalars
(|/>), complex keys (? key), merge keys (<<).
"""

import sys
from dataclasses import dataclass
from typing import Any, Sequence, cast

from rich import print as rprint

from persil import Parser, lazy, line_info, regex, string
from persil.parser import eof
from persil.stream import SoftError, Stream, from_stream
from persil.utils import Span, line_info_at

# ==============================================================================
# AST node types
# ==============================================================================


@dataclass
class YamlKeyValue:
    key: Span[str]
    value: Span["YamlValue"]


# Mappings are stored as list[YamlKeyValue] to preserve key spans for the LSP.
type YamlValue = (
    int
    | float
    | bool
    | str
    | list[YamlValue]
    | list[YamlKeyValue]
    | dict[str, YamlValue]
    | None
)


@dataclass
class YamlDocument:
    value: Span[YamlValue]


@dataclass
class YamlStream:
    documents: list[YamlDocument]


# ==============================================================================
# Whitespace & comments
# ==============================================================================

# Inline whitespace only (spaces and tabs, not newlines).
ws = regex(r"[ \t]*")

# A comment runs from '#' to end of line (preceded by whitespace).
comment = regex(r"#[^\n]*")

# A blank or comment-only line.
blank_line = ws >> comment.optional() >> string("\n")

# End of a meaningful line: optional trailing comment, then newline or EOF.
line_end = ws >> comment.optional() >> (string("\n") | eof())


def lexeme[In: Sequence, Out](p: Parser[In, Out]) -> Parser[In, Out]:
    return p << ws


# ==============================================================================
# Scalar parsers (context-free combinators)
# ==============================================================================

# Null
yaml_null = (string("null") | string("~")).result(None).desc("null")

# Booleans
yaml_true = string("true").result(True)
yaml_false = string("false").result(False)
yaml_boolean = (yaml_true | yaml_false).desc("boolean")

# Floats — must be tried before integers because "1.0" starts with digits.
yaml_special_float = regex(r"[+-]?\.(inf|Inf|INF)").map(float) | string(".nan").result(
    float("nan")
)
yaml_float = (
    yaml_special_float
    | regex(r"-?[0-9]+(\.[0-9]+)([eE][+-]?[0-9]+)?").map(float)
    | regex(r"-?[0-9]+[eE][+-]?[0-9]+").map(float)
).desc("float")

# Integers: decimal, hex, octal.
yaml_hex_int = regex(r"0x[0-9a-fA-F]+").map(lambda s: int(s, 16))
yaml_oct_int = regex(r"0o[0-7]+").map(lambda s: int(s, 8))
yaml_dec_int = regex(r"-?[0-9]+").map(int)
yaml_integer = (yaml_hex_int | yaml_oct_int | yaml_dec_int).desc("integer")

# Double-quoted strings with escape sequences.
ESCAPE_MAP = {
    "\\": "\\",
    '"': '"',
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "0": "\0",
}
dq_char = regex(r'[^"\\]+')
dq_esc = string("\\") >> regex(r'[\\/"bfnrt0]|u[0-9a-fA-F]{4}').map(
    lambda s: ESCAPE_MAP[s] if s in ESCAPE_MAP else chr(int(s[1:], 16))
)
double_quoted = (
    string('"') >> (dq_char | dq_esc).many().map("".join) << string('"')
).desc("double-quoted string")

# Single-quoted strings (no escapes, '' is an escaped single quote).
sq_char = regex(r"[^']+")
sq_escape = string("''").result("'")
single_quoted = (
    string("'") >> (sq_char | sq_escape).many().map("".join) << string("'")
).desc("single-quoted string")

# A plain scalar on a single line. Grabs everything up to newline or comment,
# then strips trailing whitespace.
plain_scalar_re = regex(r"[^\n#]+").map(str.strip)

# Typed scalar parser: tries to interpret a string as a specific type.
typed_scalar = (yaml_null | yaml_boolean | yaml_float | yaml_integer).desc(
    "typed scalar"
)


# ==============================================================================
# Flow constructs (JSON-like, no indentation sensitivity)
# ==============================================================================

flow_ws = regex(r"[ \t]*")


def flow_lexeme[In: Sequence, Out](p: Parser[In, Out]) -> Parser[In, Out]:
    return p << flow_ws


flow_comma = flow_lexeme(string(","))
flow_colon = flow_lexeme(string(":"))

# Flow scalars: same as inline but also allow plain scalars with restricted
# character set (no commas, colons, brackets, braces).
flow_plain_scalar = regex(r"[^\n\[\]{},:# \t][^\n\[\]{},:#]*").map(str.strip)
flow_scalar = (
    yaml_null
    | yaml_boolean
    | yaml_float
    | yaml_integer
    | double_quoted
    | single_quoted
    | flow_plain_scalar
).desc("flow scalar")


@lazy
def flow_value() -> Parser[str, YamlValue]:
    return cast(
        Parser[str, YamlValue],
        flow_scalar | flow_sequence | flow_mapping,
    )


@lazy
def flow_sequence() -> Parser[str, list[YamlValue]]:
    return (
        flow_lexeme(string("["))
        >> flow_ws
        >> flow_value.sep_by(flow_comma)
        << flow_lexeme(string(",")).optional()
        << flow_lexeme(string("]"))
    )


@lazy
def flow_pair() -> Parser[str, tuple[str, YamlValue]]:
    key = flow_lexeme(
        double_quoted
        | single_quoted
        | regex(r"[^\n\[\]{},:# \t][^\n\[\]{},:#]*").map(str.strip)
    )
    return (key << flow_colon) & flow_value


@lazy
def flow_mapping() -> Parser[str, dict[str, YamlValue]]:
    return (
        flow_lexeme(string("{"))
        >> flow_ws
        >> flow_pair.sep_by(flow_comma).map(dict)
        << flow_lexeme(string(",")).optional()
        << flow_lexeme(string("}"))
    )


# ==============================================================================
# Block parsing (indentation-sensitive, using Stream API)
# ==============================================================================

# A mapping key followed by `: ` or `:\n`. The key itself is a bare or quoted
# scalar on the same line.
mapping_key = (
    double_quoted
    | single_quoted
    | regex(r"[^\n:# \t][^\n:#]*?(?=\s*:\s)").map(str.strip)
).desc("mapping key")


def skip_blank_lines(stream: Stream[str]) -> None:
    """Consume blank and comment-only lines."""
    try:
        while True:
            stream.apply(blank_line)
    except SoftError:
        pass


def at_eof(stream: Stream[str]) -> bool:
    """Check if we've reached the end of input without consuming."""
    try:
        stream.apply(eof())
        return True
    except SoftError:
        return False


def peek_indent(stream: Stream[str]) -> int:
    """Return the column of the next non-blank content without consuming it.

    Skips blank/comment lines, then measures leading whitespace on the first
    content line. Returns -1 if at EOF.
    """
    saved = stream.index
    skip_blank_lines(stream)
    if at_eof(stream):
        stream.index = saved
        return -1
    # Consume leading whitespace to find the column of the first non-blank char.
    stream.apply(ws)
    col = stream.apply(line_info()).col
    stream.index = saved
    return col


def consume_indent(stream: Stream[str]) -> int:
    """Consume leading whitespace and return the column position reached.

    This must be called at the start of a line.
    """
    stream.apply(ws)
    return stream.apply(line_info()).col


def parse_inline_value(stream: Stream[str]) -> YamlValue:
    """Parse a value that appears on the same line (after `: ` or `- `).

    Tries flow constructs and quoted strings first (these have unambiguous
    delimiters). For unquoted values, grabs the full plain text and then
    attempts to interpret it as a typed scalar (null, bool, int, float).
    """
    # Flow constructs have unambiguous start characters.
    try:
        return stream.apply(flow_sequence)
    except SoftError:
        pass
    try:
        return stream.apply(flow_mapping)
    except SoftError:
        pass
    # Quoted strings.
    try:
        return stream.apply(double_quoted)
    except SoftError:
        pass
    try:
        return stream.apply(single_quoted)
    except SoftError:
        pass
    # Plain scalar: grab the whole text, then try to parse as a typed value.
    text = stream.apply(plain_scalar_re)
    try:
        return typed_scalar.parse(text)
    except Exception:
        return text


def parse_value_spanned(stream: Stream[str], parent_indent: int) -> Span[YamlValue]:
    """Parse any YAML value and wrap it in a Span."""
    start = line_info_at(stream.inner, stream.index)
    value = parse_value(stream, parent_indent)
    stop = line_info_at(stream.inner, stream.index)
    return Span(start=start, stop=stop, value=value)


def parse_value(stream: Stream[str], parent_indent: int) -> YamlValue:
    """Parse any YAML value — block or inline.

    After skipping blank lines, looks at the indent of the next content:
    - If it starts with `- `, it's a block sequence.
    - If it looks like `key:`, it's a block mapping.
    - Otherwise, it's an inline value on the current line.
    """
    skip_blank_lines(stream)
    if at_eof(stream):
        return None

    # Peek at the indentation level and content of the next line.
    col = peek_indent(stream)
    if col == -1:
        return None

    # If indentation decreased to or below parent, this is an empty value.
    if col <= parent_indent and parent_indent >= 0:
        return None

    # Peek at the stripped line content to decide the block type.
    saved = stream.index
    stream.apply(ws)
    rest_of_line = stream.inner[stream.index :].split("\n", 1)[0]
    stream.index = saved

    # Block sequence: line starts with `- `.
    if rest_of_line.startswith("- ") or rest_of_line == "-":
        return parse_block_sequence(stream, col)

    # Block mapping: line looks like `key: ...` or `key:`.
    if _looks_like_mapping_key(rest_of_line):
        return parse_block_mapping(stream, col)

    # Inline value: consume indentation, parse value, consume line end.
    stream.apply(ws)
    value = parse_inline_value(stream)
    stream.apply(line_end)
    return value


def _looks_like_mapping_key(line: str) -> bool:
    """Heuristic: does this line look like a YAML mapping key?

    Checks for `key: ` or `key:` at end of line, skipping over quoted strings.
    """
    if line.startswith('"'):
        # Skip the quoted key.
        end = line.find('"', 1)
        if end == -1:
            return False
        rest = line[end + 1 :].lstrip()
        return rest.startswith(":")
    if line.startswith("'"):
        end = line.find("'", 1)
        if end == -1:
            return False
        rest = line[end + 1 :].lstrip()
        return rest.startswith(":")
    # Bare key: look for `: ` or trailing `:`.
    colon_pos = line.find(":")
    if colon_pos == -1:
        return False
    after = line[colon_pos + 1 :]
    return after == "" or after[0] in " \t\n"


def parse_block_sequence(stream: Stream[str], expected_indent: int) -> list[YamlValue]:
    """Parse a block sequence: lines starting with `- ` at the same indent."""
    items: list[YamlValue] = []

    while True:
        skip_blank_lines(stream)
        if at_eof(stream):
            break

        # Check indentation — peek without consuming.
        col = peek_indent(stream)
        if col != expected_indent:
            break

        # Peek at the content after indentation.
        saved = stream.index
        stream.apply(ws)
        rest = stream.inner[stream.index :]
        stream.index = saved

        if not (rest.startswith("- ") or rest.startswith("-\n") or rest == "-"):
            break

        # Consume the indentation and `- `.
        stream.apply(ws)
        stream.apply(string("-"))

        # After `-`, there may be a value on the same line or a nested block.
        # Try to consume at least one space after `-`.
        try:
            stream.apply(regex(r"[ \t]+"))
        except SoftError:
            # `-` followed immediately by newline → nested block value.
            stream.apply(line_end)
            value = parse_value(stream, expected_indent)
            items.append(value)
            continue

        # Check if rest of line is empty (value is a nested block).
        saved = stream.index
        try:
            stream.apply(line_end)
            value = parse_value(stream, expected_indent)
            items.append(value)
            continue
        except SoftError:
            stream.index = saved

        # Content on the same line after `- `.
        # It could be a nested mapping key or a scalar.
        inner_col = stream.apply(line_info()).col
        rest_of_line = stream.inner[stream.index :].split("\n", 1)[0]
        if _looks_like_mapping_key(rest_of_line):
            # Nested mapping starting on the same line as `- `.
            entries = parse_block_mapping(stream, inner_col)
            items.append(entries)
        else:
            value = parse_inline_value(stream)
            stream.apply(line_end)
            items.append(value)

    return items


def parse_block_mapping(
    stream: Stream[str], expected_indent: int
) -> list[YamlKeyValue]:
    """Parse a block mapping: `key: value` pairs at the same indent."""
    entries: list[YamlKeyValue] = []

    while True:
        skip_blank_lines(stream)
        if at_eof(stream):
            break

        # Check indentation — peek without consuming.
        col = peek_indent(stream)
        if col != expected_indent:
            break

        # Consume leading whitespace.
        stream.apply(ws)

        # Parse the key with span.
        key_start = line_info_at(stream.inner, stream.index)
        key_val = stream.apply(mapping_key)
        key_stop = line_info_at(stream.inner, stream.index)
        key_span = Span(start=key_start, stop=key_stop, value=key_val)

        # Consume `:` and trailing inline whitespace.
        stream.apply(string(":"))
        stream.apply(ws)

        # Check if value is on the same line or on subsequent indented lines.
        val_start = line_info_at(stream.inner, stream.index)

        # Try consuming to end of line (empty value → nested block).
        saved = stream.index
        try:
            stream.apply(line_end)
            # Value is a nested block on subsequent lines.
            value = parse_value(stream, expected_indent)
            val_stop = line_info_at(stream.inner, stream.index)
            val_span = Span(start=val_start, stop=val_stop, value=value)
        except SoftError:
            stream.index = saved
            # Value is inline on the same line.
            value = parse_inline_value(stream)
            val_stop = line_info_at(stream.inner, stream.index)
            val_span = Span(start=val_start, stop=val_stop, value=value)
            stream.apply(line_end)

        entries.append(YamlKeyValue(key=key_span, value=val_span))

    return entries


# ==============================================================================
# Document / stream parser
# ==============================================================================

# Document separator markers.
doc_start = string("---") << line_end
doc_end = string("...") << line_end


@from_stream(desc="YAML stream")
def yaml_stream(stream: Stream[str]) -> YamlStream:
    documents: list[YamlDocument] = []

    while True:
        skip_blank_lines(stream)
        if at_eof(stream):
            break

        # Optionally consume document start marker `---`.
        try:
            stream.apply(doc_start)
            skip_blank_lines(stream)
        except SoftError:
            pass

        if at_eof(stream):
            break

        # Parse the document value.
        value = parse_value_spanned(stream, parent_indent=-1)
        documents.append(YamlDocument(value=value))

        # Optionally consume document end marker `...`.
        skip_blank_lines(stream)
        try:
            stream.apply(doc_end)
        except SoftError:
            pass

    return YamlStream(documents=documents)


# ==============================================================================
# Resolution: AST -> plain Python value
# ==============================================================================


def resolve(doc: YamlDocument) -> Any:
    """Unwrap a YamlDocument's spans into a plain Python value."""
    return _unwrap(doc.value.value)


def _unwrap(val: YamlValue) -> Any:
    if isinstance(val, list):
        # A list of YamlKeyValue represents a mapping; a plain list is a sequence.
        if val and isinstance(val[0], YamlKeyValue):
            val = cast(list[YamlKeyValue], val)
            return {kv.key.value: _unwrap(kv.value.value) for kv in val}
        val = cast(list[YamlValue], val)
        return [_unwrap(v) for v in val]
    return val


if __name__ == "__main__":
    text = sys.stdin.read()
    result = yaml_stream.parse(text)
    for i, doc in enumerate(result.documents):
        if i > 0:
            print("---")
        rprint(doc)
        print()
        rprint(resolve(doc))
