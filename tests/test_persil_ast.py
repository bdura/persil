"""Smoke tests for the persil-ast package."""

from pathlib import Path

from persil_ast import (
    TomlDocument,
    YamlStream,
    json_doc,
    toml_document,
    toml_resolve,
    yaml_resolve,
    yaml_stream,
)

ASSETS = Path(__file__).parent / "assets"


def test_json_parse():
    result = json_doc.parse('{"key": [1, 2, true, null]}')
    assert result == {"key": [1, 2, True, None]}


def test_toml_parse():
    text = (ASSETS / "test.toml").read_text()
    doc = toml_document.parse(text)
    assert isinstance(doc, TomlDocument)
    resolved = toml_resolve(doc)
    assert resolved["title"] == "TOML Example"
    assert resolved["database"]["ports"] == [8000, 8001, 8002]
    assert resolved["fruits"] == [{"name": "apple"}, {"name": "banana"}]


def test_yaml_parse():
    text = (ASSETS / "test.yaml").read_text()
    result = yaml_stream.parse(text)
    assert isinstance(result, YamlStream)
    assert len(result.documents) == 1
    resolved = yaml_resolve(result.documents[0])
    assert resolved["name"] == "John Doe"
    assert resolved["tags"] == ["python", "yaml", "parser"]
    assert resolved["colors"] == ["red", "green", "blue"]
