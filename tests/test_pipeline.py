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


def test_pipeline_merges_partial_chunks_into_schema_valid_whole(monkeypatch):
    """No individual chunk satisfies `required`, but the merged output does."""
    monkeypatch.setattr("main.sleep", lambda *_: None)
    monkeypatch.setattr(SchemaProcessor, "optimize_chunk_size", lambda *_: 2)
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "number"},
        },
        "required": ["name", "price"],
    }
    client = _client_returning({"name": "widget"}, {"price": 9.99})

    result, failed = process_with_schema(
        "a\nb\nc\nd", schema, client, SchemaProcessor()
    )

    assert result == {"name": "widget", "price": 9.99}
    assert failed == []


def test_pipeline_returns_partial_result_when_merged_output_invalid(monkeypatch, caplog):
    monkeypatch.setattr("main.sleep", lambda *_: None)
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    client = _client_returning({"other": 1})

    with caplog.at_level("WARNING"):
        result, failed = process_with_schema(
            "single line", schema, client, SchemaProcessor()
        )

    assert result == {"other": 1}
    assert failed == []
    assert any("does not match schema" in r.message for r in caplog.records)
