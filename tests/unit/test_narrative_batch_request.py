"""Explicit, finite requests normalize to one reproducible execution identity."""

from copy import deepcopy

import pytest

from company_wiki.source_contract import source_id_for_sha256


def _request():
    return {
        "schema_version": "narrative-batch-request/1", "run_id": "sample-run",
        "sources": [{"schema_version": "2.0", "document_id": "doc-1",
            "source_id": source_id_for_sha256("a" * 64), "content_sha256": "a" * 64,
            "byte_size": 100, "mime_type": "text/plain"}],
        "profile": "P2", "max_seconds": 30, "max_tokens": 60000, "max_cost_usd": "0.10",
        "model": {"model_id": "model", "endpoint": "https://example.org/chat/completions", "api_key_env": "MODEL_TEST_KEY"},
        "pricing": {"version": "test-rates/2026-10-03", "input_micro_usd_per_million_tokens": 300000, "output_micro_usd_per_million_tokens": 1200000},
    }


def _parse(value):
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
    return NarrativeBatchRequest.from_dict(value)


def test_exact_sources_are_folded_and_money_is_integer_micro_usd():
    raw = _request()
    expected = _parse(raw)
    raw["sources"].append(deepcopy(raw["sources"][0]))
    actual = _parse(raw)
    assert len(actual.sources) == 1
    assert actual.max_micro_usd == 100000
    assert actual.input_hash == expected.input_hash
    assert actual.model_options["max_output_tokens"] == 2400


@pytest.mark.parametrize("field,value", [("sources", []), ("profile", "P8"), ("max_seconds", 0), ("max_seconds", float("inf")), ("max_tokens", True), ("max_tokens", -1), ("max_cost_usd", "NaN"), ("max_cost_usd", "-1"), ("max_cost_usd", "0.0000009"), ("schema_version", "2"), ("run_id", " ")])
def test_invalid_finite_request_is_refused_before_materializing_jobs(field, value):
    raw = _request()
    raw[field] = value
    with pytest.raises(ValueError):
        _parse(raw)


def test_zero_cost_allows_a_run_that_can_skip_but_will_not_fund_a_paid_attempt():
    raw = _request()
    raw["max_cost_usd"] = "0"
    assert _parse(raw).max_micro_usd == 0


def test_changes_of_prompt_model_pricing_or_limits_do_not_reuse_a_run_hash():
    original = _parse(_request()).input_hash
    for field, value in [("max_tokens", 10), ("profile", "P4")]:
        raw = _request()
        raw[field] = value
        assert _parse(raw).input_hash != original
    raw = _request()
    raw["model"]["model_id"] = "different-model"
    assert _parse(raw).input_hash != original
    raw = _request()
    raw["pricing"]["version"] = "different-rates"
    assert _parse(raw).input_hash != original


def test_secret_values_are_never_accepted_as_runtime_options():
    raw = _request()
    raw["model"]["api_key"] = "synthetic-secret-value"
    with pytest.raises(ValueError) as error:
        _parse(raw)
    assert "synthetic-secret-value" not in str(error.value)


def test_conflicting_ref_for_the_same_document_is_refused():
    raw = _request()
    second = deepcopy(raw["sources"][0])
    second.update(content_sha256="b" * 64, source_id=source_id_for_sha256("b" * 64))
    raw["sources"].append(second)
    with pytest.raises(ValueError):
        _parse(raw)


def test_normalized_request_can_be_serialized_and_resumed_without_hash_drift():
    request = _parse(_request())
    resumed = _parse(request.to_dict())
    assert resumed.input_hash == request.input_hash
    assert resumed.max_micro_usd == request.max_micro_usd
