from utils.schema_processor import SchemaProcessor


def test_merge_deep_merges_dicts():
    p = SchemaProcessor()
    a = {"outer": {"x": 1, "y": None}}
    b = {"outer": {"y": 2, "z": 3}}
    assert p.merge_chunk_results([a, b]) == {"outer": {"x": 1, "y": 2, "z": 3}}


def test_merge_concatenates_arrays():
    p = SchemaProcessor()
    a = {"items": [1, 2]}
    b = {"items": [3, 4]}
    assert p.merge_chunk_results([a, b]) == {"items": [1, 2, 3, 4]}


def test_merge_first_non_null_wins_on_scalar_conflict():
    p = SchemaProcessor()
    a = {"name": "first", "missing": None}
    b = {"name": "second", "missing": "later"}
    assert p.merge_chunk_results([a, b]) == {"name": "first", "missing": "later"}


def test_merge_keeps_data_from_every_chunk():
    p = SchemaProcessor()
    chunks = [{"a": 1}, {"b": 2}, {"c": 3}]
    assert p.merge_chunk_results(chunks) == {"a": 1, "b": 2, "c": 3}


def test_merge_empty_inputs():
    p = SchemaProcessor()
    assert p.merge_chunk_results([]) == {}
    assert p.merge_chunk_results([{}, {}]) == {}


def test_validate_against_schema():
    p = SchemaProcessor()
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    ok, errors = p.validate_against_schema({"name": "ok"}, schema)
    assert ok is True
    assert errors == []

    ok, errors = p.validate_against_schema({}, schema)
    assert ok is False
    assert errors


def test_analyze_schema_complexity_handles_nullable_types():
    """JSON Schema allows `type` to be a list, e.g. ['string', 'null']."""
    p = SchemaProcessor()
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "isbn": {"type": ["string", "null"]},
        },
    }
    out = p.analyze_schema_complexity(schema)
    assert out["field_types"]["string"] >= 2
    assert out["field_types"]["null"] == 1


def test_analyze_schema_complexity_counts_depth():
    p = SchemaProcessor()
    schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "object",
                "properties": {
                    "b": {
                        "type": "object",
                        "properties": {"c": {"type": "string"}},
                    }
                },
            }
        },
    }
    out = p.analyze_schema_complexity(schema)
    assert out["max_depth"] == 2
    assert out["total_fields"] == 3
