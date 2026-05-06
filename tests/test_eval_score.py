from evals.score import aggregate, flatten, score_case


def test_flatten_yields_dotted_paths():
    out = dict(flatten({"a": {"b": 1, "c": {"d": 2}}, "e": [1, 2]}))
    assert out == {"a.b": 1, "a.c.d": 2, "e": [1, 2]}


def test_score_case_perfect_match():
    expected = {"a": 1, "b": "x", "c": [1, 2]}
    actual = {"a": 1, "b": "x", "c": [2, 1]}  # array order should not matter
    score = score_case(expected, actual)
    assert score["matched"] == 3
    assert score["accuracy"] == 1.0
    assert score["misses"] == []


def test_score_case_partial_match_and_missing():
    expected = {"a": 1, "b": "x", "c": "y"}
    actual = {"a": 1, "b": "wrong"}
    score = score_case(expected, actual)
    assert score["matched"] == 1
    assert score["total"] == 3
    paths = {m["path"]: m for m in score["misses"]}
    assert paths["b"]["actual"] == "wrong"
    assert paths["c"]["missing"] is True


def test_score_case_missing_matches_expected_null():
    """Don't penalize the model for omitting a field that the input genuinely lacked."""
    expected = {"a": 1, "isbn": None}
    actual = {"a": 1}
    score = score_case(expected, actual)
    assert score["matched"] == 2
    assert score["accuracy"] == 1.0


def test_score_case_hallucinated_value_for_null_expected_is_a_miss():
    """A made-up value when the input had nothing to extract is wrong."""
    expected = {"isbn": None}
    actual = {"isbn": "978-fake"}
    score = score_case(expected, actual)
    assert score["matched"] == 0


def test_score_case_array_with_different_multiplicity_is_a_miss():
    expected = {"a": [1, 2, 2]}
    actual = {"a": [1, 2]}
    score = score_case(expected, actual)
    assert score["matched"] == 0


def test_score_case_handles_nested_structures():
    expected = {"outer": {"inner": {"leaf": 42}}}
    actual = {"outer": {"inner": {"leaf": 42}}}
    score = score_case(expected, actual)
    assert score["accuracy"] == 1.0


def test_aggregate_combines_cases():
    cases = [
        {"total": 4, "matched": 3, "accuracy": 0.75, "misses": []},
        {"total": 6, "matched": 6, "accuracy": 1.0, "misses": []},
    ]
    overall = aggregate(cases)
    assert overall == {"total": 10, "matched": 9, "accuracy": 0.9}


def test_aggregate_empty_is_perfect():
    assert aggregate([])["accuracy"] == 1.0
