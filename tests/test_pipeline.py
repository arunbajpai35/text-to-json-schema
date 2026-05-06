import json
from unittest.mock import MagicMock

from main import process_with_schema
from utils.schema_processor import SchemaProcessor


SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}


def _client_returning(*payloads):
    client = MagicMock()
    client.get_completion.side_effect = [json.dumps(p) for p in payloads]
    return client


def test_pipeline_merges_data_across_chunks(monkeypatch):
    monkeypatch.setattr("main.sleep", lambda *_: None)
    monkeypatch.setattr(SchemaProcessor, "optimize_chunk_size", lambda *_: 2)
    client = _client_returning(
        {"name": "first", "tags": ["a"]},
        {"name": "second", "tags": ["b", "c"]},
    )

    result, failed = process_with_schema(
        "a\nb\nc\nd", SCHEMA, client, SchemaProcessor()
    )

    assert client.get_completion.call_count == 2
    assert result["name"] == "first"
    assert result["tags"] == ["a", "b", "c"]
    assert failed == []


def test_pipeline_records_invalid_json_chunks(monkeypatch):
    monkeypatch.setattr("main.sleep", lambda *_: None)
    monkeypatch.setattr(SchemaProcessor, "optimize_chunk_size", lambda *_: 2)
    client = MagicMock()
    client.get_completion.side_effect = [
        "not json at all",
        json.dumps({"name": "ok"}),
    ]

    result, failed = process_with_schema(
        "a\nb\nc\nd", SCHEMA, client, SchemaProcessor()
    )

    assert result == {"name": "ok"}
    assert len(failed) == 1
    assert "JSON decode error" in failed[0]["error"]


def test_pipeline_records_schema_violations(monkeypatch):
    monkeypatch.setattr("main.sleep", lambda *_: None)
    monkeypatch.setattr(
        SchemaProcessor, "optimize_chunk_size", lambda *_: 5
    )
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }
    client = _client_returning({"unexpected": 1})

    result, failed = process_with_schema(
        "single line", schema, client, SchemaProcessor(), chunk_size=10
    )

    assert result == {}
    assert len(failed) == 1
    assert failed[0]["error"] == "Schema validation failed"
