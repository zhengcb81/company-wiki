"""CW-1 contract tests for versioned upstream evidence spans."""

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ID = "urn:company-wiki:source:sha256:" + "a" * 64
REQUIRED_FIELDS = {
    "schema_version",
    "span_id",
    "source_id",
    "locator",
    "coordinates",
    "raw_text",
    "structured_value",
    "parser_name",
    "parser_version",
    "output_sha256",
    "parse_status",
    "quality_flags",
}
COORDINATE_FIELDS = {
    "page_number",
    "paragraph_index",
    "table_index",
    "row_index",
    "column_index",
    "char_start",
    "char_end",
}


def _contract():
    module_name = "company_wiki.source_contract"
    assert importlib.util.find_spec(module_name) is not None, (
        "versioned company_wiki.source_contract is not implemented"
    )
    return importlib.import_module(module_name)


def _coordinates(module, **overrides):
    values = {field: None for field in COORDINATE_FIELDS}
    values.update({"page_number": 3, "paragraph_index": 5})
    values.update(overrides)
    return module.EvidenceCoordinates(**values)


def _span(module, **overrides):
    values = {
        "source_id": SOURCE_ID,
        "coordinates": _coordinates(module),
        "raw_text": "公司实现营业收入 185.6 亿元",
        "structured_value": {
            "metric": "revenue",
            "unit": "CNY 100m",
            "value": 185.6,
        },
        "parser_name": "pdf-layout-parser",
        "parser_version": "2.1.0",
        "parse_status": module.ParseStatus.PARSED,
        "quality_flags": (),
    }
    values.update(overrides)
    return module.EvidenceSpan.create(**values)


def _canonical_hash(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_schema_is_versioned_strict_and_packaged():
    module = _contract()
    schema = module.load_evidence_span_schema()

    assert module.EVIDENCE_SPAN_SCHEMA_VERSION == "1.0.0"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:company-wiki:schema:evidence-span:1.0.0"
    assert set(schema["required"]) == REQUIRED_FIELDS
    assert set(schema["properties"]) == REQUIRED_FIELDS
    assert schema["additionalProperties"] is False
    coordinates = schema["$defs"]["coordinates"]
    assert set(coordinates["required"]) == COORDINATE_FIELDS
    assert set(coordinates["properties"]) == COORDINATE_FIELDS
    assert coordinates["additionalProperties"] is False
    assert schema["properties"]["quality_flags"]["uniqueItems"] is True


def test_create_builds_canonical_text_locator_and_content_hashes():
    module = _contract()
    span = _span(module)

    assert span.locator == "loc:v1/page:3/paragraph:5"
    expected_output = _canonical_hash(
        {
            "raw_text": "公司实现营业收入 185.6 亿元",
            "structured_value": {
                "metric": "revenue",
                "unit": "CNY 100m",
                "value": 185.6,
            },
        }
    )
    assert span.output_sha256 == expected_output
    expected_span = _canonical_hash(
        {
            "locator": span.locator,
            "output_sha256": expected_output,
            "source_id": SOURCE_ID,
        }
    )
    assert span.span_id == f"urn:company-wiki:evidence-span:sha256:{expected_span}"
    assert json.loads(span.canonical_json()) == span.to_dict()


def test_create_builds_table_cell_and_character_locator_in_fixed_order():
    module = _contract()
    coordinates = module.EvidenceCoordinates(
        page_number=12,
        paragraph_index=None,
        table_index=2,
        row_index=3,
        column_index=1,
        char_start=900,
        char_end=913,
    )
    span = _span(module, coordinates=coordinates)

    assert (
        span.locator
        == "loc:v1/page:12/table:2/row:3/column:1/chars:900-913"
    )
    assert span.coordinates.to_dict() == {
        "page_number": 12,
        "paragraph_index": None,
        "table_index": 2,
        "row_index": 3,
        "column_index": 1,
        "char_start": 900,
        "char_end": 913,
    }


def test_parser_upgrade_with_identical_output_preserves_span_identity():
    module = _contract()
    old = _span(module, parser_version="2.1.0")
    new = _span(module, parser_version="3.0.0")

    assert old.output_sha256 == new.output_sha256
    assert old.span_id == new.span_id
    assert old.canonical_json() != new.canonical_json()


def test_structured_json_key_order_does_not_change_output_or_span_identity():
    module = _contract()
    first = _span(module, structured_value={"b": [2, 3], "a": {"x": True}})
    second = _span(module, structured_value={"a": {"x": True}, "b": [2, 3]})

    assert first.output_sha256 == second.output_sha256
    assert first.span_id == second.span_id
    assert first.canonical_json() == second.canonical_json()


def test_structured_value_is_recursively_immutable():
    module = _contract()
    span = _span(module, structured_value={"items": [{"value": 1}]})

    with pytest.raises(TypeError):
        span.structured_value["items"] = []
    assert isinstance(span.structured_value["items"], tuple)
    with pytest.raises(TypeError):
        span.structured_value["items"][0]["value"] = 2


@pytest.mark.parametrize(
    "kwargs",
    (
        {},
        {"page_number": 0},
        {"paragraph_index": -1},
        {"char_start": 2},
        {"char_end": 4},
        {"char_start": 4, "char_end": 4},
        {"row_index": 1},
        {"column_index": 1},
        {"paragraph_index": 1, "table_index": 0},
        {"page_number": True},
    ),
)
def test_coordinates_reject_ambiguous_or_invalid_combinations(kwargs):
    module = _contract()
    values = {field: None for field in COORDINATE_FIELDS}
    values.update(kwargs)
    with pytest.raises((TypeError, ValueError)):
        module.EvidenceCoordinates(**values)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_id", "gk-bh-2025-ar"),
        ("parser_name", ""),
        ("parser_version", "latest"),
        ("parse_status", "accepted"),
        ("quality_flags", ("accepted",)),
        ("raw_text", b"bytes are not canonical JSON text"),
    ),
)
def test_span_rejects_invalid_contract_values(field, value):
    module = _contract()
    with pytest.raises((TypeError, ValueError)):
        _span(module, **{field: value})


@pytest.mark.parametrize(
    "structured_value",
    (
        float("nan"),
        float("inf"),
        {1: "non-string key"},
        object(),
        "e\u0301",
    ),
)
def test_span_rejects_noncanonical_or_non_json_structured_values(structured_value):
    module = _contract()
    with pytest.raises((TypeError, ValueError)):
        _span(module, structured_value=structured_value)


@pytest.mark.parametrize(
    ("status", "raw_text", "structured_value", "quality_flags"),
    (
        ("parsed", None, None, ()),
        ("partial", "partial", None, ()),
        ("failed", "unexpected output", None, ("parser_error",)),
        ("failed", None, None, ()),
        ("quarantined", "suspect", None, ()),
    ),
)
def test_parse_status_output_and_quality_invariants(
    status, raw_text, structured_value, quality_flags
):
    module = _contract()
    with pytest.raises(ValueError):
        _span(
            module,
            parse_status=status,
            raw_text=raw_text,
            structured_value=structured_value,
            quality_flags=quality_flags,
        )


def test_partial_failed_and_quarantined_statuses_have_valid_forms():
    module = _contract()
    partial = _span(
        module,
        parse_status="partial",
        quality_flags=("truncated", "ocr_used"),
    )
    failed = _span(
        module,
        parse_status="failed",
        raw_text=None,
        structured_value=None,
        quality_flags=("parser_error",),
    )
    quarantined = _span(
        module,
        parse_status="quarantined",
        quality_flags=("layout_ambiguous",),
    )

    assert partial.parse_status is module.ParseStatus.PARTIAL
    assert partial.quality_flags == ("ocr_used", "truncated")
    assert failed.parse_status is module.ParseStatus.FAILED
    assert quarantined.parse_status is module.ParseStatus.QUARANTINED


def test_create_normalizes_quality_flags_but_from_dict_rejects_duplicates():
    module = _contract()
    span = _span(
        module,
        parse_status="partial",
        quality_flags=("truncated", "ocr_used", "truncated"),
    )
    assert span.quality_flags == ("ocr_used", "truncated")

    data = span.to_dict()
    data["quality_flags"] = ["truncated", "truncated"]
    with pytest.raises(ValueError, match="quality_flags"):
        module.EvidenceSpan.from_dict(data)


def test_from_dict_rejects_unknown_or_missing_fields():
    module = _contract()
    data = _span(module).to_dict()
    data["rating"] = "buy"
    with pytest.raises(ValueError, match="unknown fields"):
        module.EvidenceSpan.from_dict(data)

    data.pop("rating")
    data.pop("parser_version")
    with pytest.raises(ValueError, match="missing fields"):
        module.EvidenceSpan.from_dict(data)


def test_from_dict_rejects_unknown_coordinate_fields():
    module = _contract()
    data = _span(module).to_dict()
    data["coordinates"]["bbox"] = [0, 0, 10, 10]
    with pytest.raises(ValueError, match="coordinate.*unknown fields"):
        module.EvidenceSpan.from_dict(data)


@pytest.mark.parametrize("tampered", ("locator", "output_sha256", "span_id"))
def test_from_dict_rejects_locator_output_hash_or_identity_mismatch(tampered):
    module = _contract()
    data = _span(module).to_dict()
    replacements = {
        "locator": "loc:v1/page:99",
        "output_sha256": "b" * 64,
        "span_id": "urn:company-wiki:evidence-span:sha256:" + "b" * 64,
    }
    data[tampered] = replacements[tampered]
    with pytest.raises(ValueError, match=tampered):
        module.EvidenceSpan.from_dict(data)


def test_quality_flags_are_extraction_only_and_schema_has_no_research_state():
    module = _contract()
    flag_values = {item.value for item in module.QualityFlag}
    status_values = {item.value for item in module.ParseStatus}
    forbidden = {"accepted", "rejected", "buy", "sell", "valuation", "rating"}

    assert not (flag_values | status_values) & forbidden
    assert {
        "ocr_used",
        "low_ocr_confidence",
        "layout_ambiguous",
        "truncated",
        "parser_error",
        "unsupported_format",
    } <= flag_values
    assert status_values == {"parsed", "partial", "failed", "quarantined"}
    assert not REQUIRED_FIELDS & {"rating", "target_price", "review_decision"}


def test_schema_documentation_lists_every_field_and_semantic_boundary():
    _contract()
    text = (ROOT / "docs" / "contracts" / "evidence-span-v1.md").read_text(
        encoding="utf-8"
    )
    for field in REQUIRED_FIELDS | COORDINATE_FIELDS:
        assert f"`{field}`" in text
    assert "accepted investment conclusion" in text
    assert "StockWiki" in text
    assert "end exclusive" in text

