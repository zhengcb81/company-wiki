"""Pure synthetic records: never open originals, databases or model clients."""
from copy import deepcopy
import json

import pytest

from tools.source_case_receipt import encode_source_receipt


def record():
    return {
        "status": "COMPLETED_ENGINEERING_NOT_SIGNOFF",
        "required_units": [{"unit_id": "u1", "represented": True}],
        "context_original_member_checks": [{"all_original_members": True}],
        "source_excerpt_units": [{"unit_id": "u1", "raw_text": "完整的业务原话。"}],
        "span_original_member_index": [{
            "span_id": "s1", "locator": "page=2", "raw_text": "完整的业务原话。",
            "native_members": [{"unit_id": "u1", "valid_slice": True}],
        }],
        "citation_view_index": [{"support_evidence_ids": ["s1"]}],
        "source_package_index": [{"package_id": "p1", "member_unit_ids": ["u1"]}],
        "closure": {"missing_selected_ids": [], "all_source_ids_match": True},
        "reading_context_observations": {"source_processing_complete": False, "coverage_complete": True},
        "source_ref": {"source_id": "source1", "source_sha256": "a" * 64},
        "runtime_before": {"files": 12, "sha256": "b" * 64},
        "runtime_after": {"files": 12, "sha256": "b" * 64},
        "runtime_unchanged": True,
        "database_before": {"catalog": {"exists": True, "sha256": "c" * 64}},
        "database_after": {"catalog": {"exists": True, "sha256": "c" * 64}},
        "database_comparison": {"unchanged": True}, "database_unchanged": True,
        "original_files_before": {"original.pdf": {"exists": True, "sha256": "d" * 64}},
        "original_files_after": {"original.pdf": {"exists": True, "sha256": "d" * 64}},
        "original_files_comparison": {"unchanged": True}, "original_files_unchanged": True,
    }


def decode(value):
    encoded = encode_source_receipt(value)
    assert isinstance(encoded, bytes)
    return json.loads(encoded)


def test_complete_record_is_exact_deterministic_unmodified_even_above_old_limit():
    value = record()
    value["source_excerpt_units"][0]["raw_text"] = "中🙂" * 100000
    value["reading_context_observations"]["selection_trace"] = ["debug" * 10000] * 40
    value["source_package_index"] = [{"member_unit_ids": ["u" * 100] * 5000}]
    value["span_original_member_index"][0].update(raw_text="business" * 100000, raw_text_sha256="producer-value")
    before = deepcopy(value)
    first = encode_source_receipt(value)
    assert len(first) > 300000
    assert first == encode_source_receipt(value)
    result = json.loads(first)
    assert result == value == before
    full = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    assert first == full


def test_failed_source_remains_failed_with_all_large_diagnostics():
    value = record()
    value.update(status="FAILED", error={"type": "TimeoutError"})
    value["reading_context_observations"]["diagnostics"] = ["d" * 10000] * 40
    result = decode(value)
    assert result["status"] == "FAILED" and result["error"] == value["error"]
    assert result["reading_context_observations"] == value["reading_context_observations"]


def test_non_json_value_keeps_failure_checkpoint_without_repr():
    class Unserializable:
        def __repr__(self):
            raise AssertionError("do not render arbitrary object bodies")
    value = record()
    value.update(status="FAILED", debug=Unserializable())
    result = decode(value)
    assert result["status"] == "OBSERVATION_INCOMPLETE"
    assert result["source_status"] == "FAILED"
    assert result["encoding_error"]["type"] == "TypeError"
    assert result["integrity_checkpoints"]["database_unchanged"] is True
    assert "debug" in result["unretained_fields"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_values_never_write_nonstandard_json(bad):
    value = record()
    value["bad"] = bad
    result = decode(value)
    assert result["status"] == "OBSERVATION_INCOMPLETE"
    assert result["encoding_error"]["type"] == "ValueError"


def test_circular_input_keeps_integrity_fallback():
    value = record()
    value["cycle"] = value
    result = decode(value)
    assert result["status"] == "OBSERVATION_INCOMPLETE"
    assert result["integrity_checkpoints"]["runtime_unchanged"] is True
    assert "cycle" in result["unretained_fields"]


def test_invalid_unicode_key_cannot_destroy_the_failure_receipt():
    value = record()
    value["\ud800"] = "not valid UTF-8"
    result = decode(value)
    assert result["status"] == "OBSERVATION_INCOMPLETE"
    assert result["source_status"] == value["status"]
    assert result["encoding_error"]["type"] == "UnicodeEncodeError"
