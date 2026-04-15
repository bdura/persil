"""Tests for the persil-ast package: JSON, TOML, and YAML AST parsers."""

from pathlib import Path

from persil.utils import RowCol, Span

from persil_ast import (
    JsonDocument,
    JsonObject,
    TomlArrayTableHeader,
    TomlDocument,
    TomlTableHeader,
    YamlDocument,
    YamlKeyValue,
    YamlStream,
    json_doc,
    json_resolve,
    toml_document,
    toml_resolve,
    yaml_resolve,
    yaml_stream,
)

ASSETS = Path(__file__).parent / "assets"


# ==========================================================================
# JSON
# ==========================================================================


class TestJsonAst:
    def test_document_wraps_top_level_span(self):
        doc = json_doc.parse("42")
        assert isinstance(doc, JsonDocument)
        assert doc.value.value == 42
        assert doc.value.start == RowCol(index=0, row=0, col=0)
        assert doc.value.stop == RowCol(index=2, row=0, col=2)

    def test_object_key_value_spans(self):
        #                          0123456789...
        doc = json_doc.parse('{"key": "val"}')
        obj = doc.value.value
        assert isinstance(obj, JsonObject)
        kv = obj.entries[0]

        # Key: "key" starts at col 1.
        assert kv.key.value == "key"
        assert kv.key.start.col == 1

        # Value: "val"
        assert kv.value.value == "val"
        assert kv.value.start.col == 8

    def test_multiline_object_spans(self):
        text = '{\n  "a": 1,\n  "b": 2\n}'
        doc = json_doc.parse(text)
        obj = doc.value.value
        assert isinstance(obj, JsonObject)
        entries = obj.entries
        assert len(entries) == 2

        # "a" is on row 1
        assert entries[0].key.start.row == 1
        assert entries[0].key.start.col == 2
        assert entries[0].value.value == 1

        # "b" is on row 2
        assert entries[1].key.start.row == 2
        assert entries[1].key.start.col == 2
        assert entries[1].value.value == 2

    def test_array_element_spans(self):
        doc = json_doc.parse("[10, 20, 30]")
        arr = doc.value.value
        assert isinstance(arr, list) and isinstance(arr[0], Span)
        assert [item.value for item in arr] == [10, 20, 30]

        # 10 starts at col 1, 20 at col 5, 30 at col 9
        assert arr[0].start.col == 1
        assert arr[1].start.col == 5
        assert arr[2].start.col == 9

    def test_nested_array_in_object(self):
        doc = json_doc.parse('{"xs": [1, 2]}')
        obj = doc.value.value
        assert isinstance(obj, JsonObject)
        kv = obj.entries[0]
        assert kv.key.value == "xs"
        arr = kv.value.value
        assert isinstance(arr, list) and isinstance(arr[0], Span)
        assert [item.value for item in arr] == [1, 2]

    def test_primitives(self):
        assert json_doc.parse("true").value.value is True
        assert json_doc.parse("false").value.value is False
        assert json_doc.parse("null").value.value is None
        assert json_doc.parse('"hello"').value.value == "hello"
        assert json_doc.parse("3.14").value.value == 3.14

    def test_escape_sequences(self):
        doc = json_doc.parse('"hello\\nworld"')
        assert doc.value.value == "hello\nworld"

    def test_resolve_round_trip(self):
        text = '{"a": [1, true, null], "b": {"c": "d"}}'
        doc = json_doc.parse(text)
        resolved = json_resolve(doc)
        assert resolved == {"a": [1, True, None], "b": {"c": "d"}}

    def test_resolve_empty_object(self):
        assert json_resolve(json_doc.parse("{}")) == {}

    def test_resolve_empty_array(self):
        assert json_resolve(json_doc.parse("[]")) == []


# ==========================================================================
# TOML
# ==========================================================================


class TestTomlAst:
    def test_document_structure(self):
        text = (ASSETS / "test.toml").read_text()
        doc = toml_document.parse(text)
        assert isinstance(doc, TomlDocument)
        # The fixture has: top-level, [owner], [database], [servers.alpha],
        # [servers.beta], [product], [[fruits]] x2 = 8 tables.
        assert len(doc.tables) == 8

    def test_top_level_kv_spans(self):
        doc = toml_document.parse('title = "TOML Example"\n')
        table = doc.tables[0]
        assert table.header is None
        kv = table.entries[0]

        assert kv.key.value == ["title"]
        assert kv.key.start == RowCol(index=0, row=0, col=0)

        assert kv.value.value == "TOML Example"
        # Value span starts at the opening quote.
        assert kv.value.start.col == 8

    def test_table_header_span(self):
        text = "[owner]\nname = 'Tom'\n"
        doc = toml_document.parse(text)

        # tables[0] is the implicit top-level (no entries before [owner]).
        header = doc.tables[1].header
        assert isinstance(header, TomlTableHeader)
        assert header.key.value == ["owner"]
        assert header.key.start.row == 0

    def test_dotted_table_header(self):
        text = "[servers.alpha]\nip = '10.0.0.1'\n"
        doc = toml_document.parse(text)
        header = doc.tables[1].header
        assert isinstance(header, TomlTableHeader)
        assert header.key.value == ["servers", "alpha"]

    def test_array_of_tables_header(self):
        text = "[[fruits]]\nname = 'apple'\n\n[[fruits]]\nname = 'banana'\n"
        doc = toml_document.parse(text)
        # tables[0] is implicit top-level, tables[1] and [2] are [[fruits]].
        assert isinstance(doc.tables[1].header, TomlArrayTableHeader)
        assert doc.tables[1].header.key.value == ["fruits"]
        assert isinstance(doc.tables[2].header, TomlArrayTableHeader)

    def test_kv_value_types(self):
        text = 'a = 42\nb = 3.14\nc = true\nd = "hello"\ne = [1, 2]\n'
        doc = toml_document.parse(text)
        entries = doc.tables[0].entries
        values = {e.key.value[0]: e.value.value for e in entries}
        assert values == {
            "a": 42,
            "b": 3.14,
            "c": True,
            "d": "hello",
            "e": [1, 2],
        }

    def test_kv_multiline_spans(self):
        text = "a = 1\nb = 2\nc = 3\n"
        doc = toml_document.parse(text)
        entries = doc.tables[0].entries
        # Each key starts at col 0, on successive rows.
        for i, entry in enumerate(entries):
            assert entry.key.start.row == i
            assert entry.key.start.col == 0

    def test_inline_table(self):
        text = "meta = {x = 1, y = 2}\n"
        doc = toml_document.parse(text)
        val = doc.tables[0].entries[0].value.value
        assert val == {"x": 1, "y": 2}

    def test_resolve_fixture(self):
        text = (ASSETS / "test.toml").read_text()
        doc = toml_document.parse(text)
        resolved = toml_resolve(doc)
        assert resolved["title"] == "TOML Example"
        assert resolved["enabled"] is True
        assert resolved["pi"] == 3.14159
        assert resolved["database"]["ports"] == [8000, 8001, 8002]
        assert resolved["servers"]["alpha"]["ip"] == "10.0.0.1"
        assert resolved["product"]["metadata"] == {"weight": 12, "unit": "kg"}
        assert resolved["fruits"] == [{"name": "apple"}, {"name": "banana"}]

    def test_hex_integer(self):
        doc = toml_document.parse("val = 0xDEAD_BEEF\n")
        assert doc.tables[0].entries[0].value.value == 0xDEADBEEF


# ==========================================================================
# YAML
# ==========================================================================


class TestYamlAst:
    def test_stream_structure(self):
        text = (ASSETS / "test.yaml").read_text()
        result = yaml_stream.parse(text)
        assert isinstance(result, YamlStream)
        assert len(result.documents) == 1
        assert isinstance(result.documents[0], YamlDocument)

    def test_top_level_key_spans(self):
        text = "name: John\nage: 30\n"
        result = yaml_stream.parse(text)
        doc = result.documents[0]
        entries = doc.value.value
        assert isinstance(entries, list) and isinstance(entries[0], YamlKeyValue)

        assert entries[0].key.value == "name"
        assert entries[0].key.start == RowCol(index=0, row=0, col=0)

        assert entries[1].key.value == "age"
        assert entries[1].key.start == RowCol(index=11, row=1, col=0)

    def test_nested_mapping_value_span(self):
        text = "address:\n  street: 123 Main\n  city: Springfield\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        # "address" entry's value is a nested mapping.
        addr_entry = entries[0]
        assert addr_entry.key.value == "address"
        nested = addr_entry.value.value
        assert isinstance(nested, list) and isinstance(nested[0], YamlKeyValue)
        assert nested[0].key.value == "street"
        # "street" is indented 2 spaces on row 1.
        assert nested[0].key.start.row == 1
        assert nested[0].key.start.col == 2

    def test_sequence_items(self):
        text = "tags:\n  - python\n  - yaml\n  - parser\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        tags = entries[0].value.value
        assert isinstance(tags, list)
        assert tags == ["python", "yaml", "parser"]

    def test_flow_sequence(self):
        text = "colors: [red, green, blue]\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        assert entries[0].value.value == ["red", "green", "blue"]

    def test_flow_mapping(self):
        text = "point: {x: 1, y: 2}\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        assert entries[0].value.value == {"x": 1, "y": 2}

    def test_quoted_string_value(self):
        text = 'greeting: "hello\\nworld"\n'
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        assert entries[0].value.value == "hello\nworld"

    def test_special_values(self):
        text = "a: null\nb: ~\nc: true\nd: false\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        values = {e.key.value: e.value.value for e in entries}
        assert values == {"a": None, "b": None, "c": True, "d": False}

    def test_integer_types(self):
        text = "dec: 42\nhex: 0xFF\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        assert entries[0].value.value == 42
        assert entries[1].value.value == 255

    def test_sequence_of_mappings(self):
        text = "people:\n  - name: Alice\n    age: 25\n  - name: Bob\n    age: 32\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        people = entries[0].value.value
        assert isinstance(people, list) and len(people) == 2
        # Each item is a nested mapping (list[YamlKeyValue]).
        alice = people[0]
        assert isinstance(alice, list) and isinstance(alice[0], YamlKeyValue)
        assert alice[0].key.value == "name"
        assert alice[0].value.value == "Alice"

    def test_resolve_fixture(self):
        text = (ASSETS / "test.yaml").read_text()
        result = yaml_stream.parse(text)
        resolved = yaml_resolve(result.documents[0])
        assert resolved["name"] == "John Doe"
        assert resolved["age"] == 30
        assert resolved["active"] is True
        assert resolved["nothing"] is None
        assert resolved["tags"] == ["python", "yaml", "parser"]
        assert resolved["colors"] == ["red", "green", "blue"]
        assert resolved["point"] == {"x": 1, "y": 2, "z": 3}
        assert resolved["address"]["city"] == "Springfield"
        assert resolved["people"][0]["name"] == "Alice"
        assert resolved["people"][1]["age"] == 32

    def test_value_span_covers_nested_block(self):
        text = "items:\n  - a\n  - b\n"
        result = yaml_stream.parse(text)
        entries = result.documents[0].value.value
        # The value span for "items" should start after the colon (row 0)
        # and extend through the sequence items.
        items_val = entries[0].value
        assert items_val.start.row == 0
        assert items_val.stop.row >= 2
