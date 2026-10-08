"""Strict wire tests written before the narrative transport implementation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.automation.narrative_transport_contracts import (
    NarrativeReadRequest, NarrativeRef,
)
from company_wiki.source_contract import source_id_for_sha256
from company_wiki.automation.narrative_contracts import NarrativeBundle


def _reference() -> dict:
    digest = hashlib.sha256(b"source").hexdigest()
    return {
        "schema_version": "narrative-ref/1",
        "artifact_version_id": "narrative-test-version",
        "artifact_sha256": hashlib.sha256(b"bundle").hexdigest(),
        "byte_size": 100,
        "source_ref": {
            "schema_version": "2.0", "document_id": "doc-test",
            "source_id": source_id_for_sha256(digest), "content_sha256": digest,
            "byte_size": 6, "mime_type": "text/plain",
        },
    }


def _request() -> dict:
    return {
        "schema_version": "narrative-read-request/1", "narrative_ref": _reference(),
        "as_of_date": "2026-09-01",
        "expected_source": {
            "canonical_entity_id": "ent-acme", "market": "US", "security_id": "ACME",
            "document_kind": "investor_call_transcript", "fiscal_year": 2026,
            "fiscal_period": "Q2",
        },
    }


def test_wire_reference_and_read_request_roundtrip_without_path() -> None:
    assert NarrativeRef.from_dict(_reference()).to_dict() == _reference()
    assert NarrativeReadRequest.from_dict(_request()).to_dict() == _request()


@pytest.mark.parametrize("field,value", [
    ("schema_version", "narrative-ref/2"), ("artifact_version_id", ""),
    ("artifact_sha256", "ABC"), ("byte_size", True), ("byte_size", 0),
    ("byte_size", 1280 * 1024 + 1), ("path", "forbidden-storage-field"),
])
def test_reference_rejects_bad_version_type_hash_budget_and_extra_fields(field, value) -> None:
    payload = _reference()
    payload[field] = value
    with pytest.raises(ValueError):
        NarrativeRef.from_dict(payload)


@pytest.mark.parametrize("mutation", ["missing", "extra", "source_sha", "source_version"])
def test_nested_source_ref_is_not_weakened(mutation) -> None:
    payload = _reference()
    if mutation == "missing":
        del payload["source_ref"]["byte_size"]
    elif mutation == "extra":
        payload["source_ref"]["object_key"] = "objects/local"
    elif mutation == "source_sha":
        payload["source_ref"]["content_sha256"] = "0" * 64
    else:
        payload["source_ref"]["schema_version"] = "1.0"
    with pytest.raises(ValueError):
        NarrativeRef.from_dict(payload)


@pytest.mark.parametrize("date", ["2026-02-30", "20260901", "2026-09-01T00:00:00Z", ""])
def test_read_request_requires_real_iso_calendar_date(date) -> None:
    payload = _request()
    payload["as_of_date"] = date
    with pytest.raises(ValueError):
        NarrativeReadRequest.from_dict(payload)


@pytest.mark.parametrize("mutation", ["version", "missing_identity", "extra_identity", "boolean_year", "string_year", "path"])
def test_read_request_identity_contract_is_exact_and_typed(mutation) -> None:
    payload = deepcopy(_request())
    if mutation == "version":
        payload["schema_version"] = "narrative-read-request/2"
    elif mutation == "missing_identity":
        del payload["expected_source"]["fiscal_period"]
    elif mutation == "extra_identity":
        payload["expected_source"]["provider"] = "fmp"
    elif mutation == "boolean_year":
        payload["expected_source"]["fiscal_year"] = True
    elif mutation == "string_year":
        payload["expected_source"]["fiscal_year"] = "2026"
    else:
        payload["root_path"] = "forbidden-storage-field"
    with pytest.raises(ValueError):
        NarrativeReadRequest.from_dict(payload)


def test_identity_null_is_explicitly_unconstrained() -> None:
    payload = _request()
    payload["expected_source"] = {key: None for key in payload["expected_source"]}
    assert NarrativeReadRequest.from_dict(payload).to_dict() == payload


def test_frozen_producer_golden_contract_and_hash_bindings() -> None:
    directory = Path(__file__).resolve().parents[1] / "fixtures" / "narrative_transport_v1"
    metadata = json.loads((directory / "metadata.json").read_bytes())
    for name, digest in metadata["file_sha256"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
    bundle_data = (directory / "bundle.json").read_bytes()
    bundle = NarrativeBundle.from_dict(json.loads(bundle_data))
    reference_data = json.loads((directory / "reference.json").read_bytes())
    reference = NarrativeRef.from_dict(reference_data)
    assert reference.to_dict() == reference_data
    assert reference.source_ref == bundle.source_ref
    assert reference.artifact_sha256 == hashlib.sha256(bundle_data).hexdigest()
    assert reference.byte_size == len(bundle_data)
    request = json.loads((directory / "read_request.json").read_bytes())
    assert NarrativeReadRequest.from_dict(request).to_dict() == request
    assert request["narrative_ref"] == reference_data
    receipt = json.loads((directory / "read_receipt.json").read_bytes())
    assert receipt["narrative_ref"] == reference_data
    assert receipt["locator_count"] == len(bundle.evidence_spans)
    assert receipt["quality_status"] == bundle.quality_status
    with pytest.raises(ValueError):
        NarrativeReadRequest.from_dict(json.loads((directory / "invalid_request.json").read_bytes()))


@pytest.mark.parametrize("change", ["source", "language", "citation", "status"])
def test_standalone_persisted_bundle_rejects_unbound_summary(change) -> None:
    directory = Path(__file__).resolve().parents[1] / "fixtures" / "narrative_transport_v1"
    payload = json.loads((directory / "bundle.json").read_bytes())
    if change == "source":
        payload["summary"]["draft"]["source_sha256"] = "0" * 64
    elif change == "language":
        payload["summary"]["draft"]["language"] = "zh"
    elif change == "citation":
        payload["summary"]["draft"]["claims"][0]["evidence_ids"] = ["unknown-evidence"]
    else:
        payload["summary"]["status"] = "unknown_status"
    with pytest.raises(ValueError):
        NarrativeBundle.from_dict(payload)
