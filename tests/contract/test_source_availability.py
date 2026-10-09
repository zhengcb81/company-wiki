"""Historical availability is a stored byte-bound capture, never a filename date."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.source_availability import verified_availability_evidence


SHA = hashlib.sha256(b"original fixture").hexdigest()
REF = SourceRef("doc-example", "src-example", SHA, 16, "text/plain")


def capture_payload():
    receipt = {
        "schema_version": "1.0", "candidate_id": "accession-example",
        "provider": "sec", "provider_document_id": "accession-example",
        "source_url": "https://www.sec.gov/Archives/example.txt",
        "staged_path": "staging/example.txt", "content_sha256": SHA,
        "byte_size": 16, "mime_type": "text/plain",
        "retrieved_at": "2026-10-07T23:30:00Z", "http_status": 200,
        "adapter_name": "sec-reader", "adapter_version": "1.0.0",
        "etag": None, "last_modified": None,
    }
    return {
        "schema_version": "1.0", "request_id": "example-request",
        **{k: receipt[k] for k in (
            "provider", "provider_document_id", "source_url", "content_sha256",
            "byte_size", "mime_type", "retrieved_at", "adapter_name", "adapter_version",
        )},
        "candidate": {k: receipt[k] for k in (
            "provider", "provider_document_id", "source_url",
        )},
        "receipt": receipt,
    }


def fixture_catalog(tmp_path, payload, *, relative="original.txt", cap=1):
    root = tmp_path / "lake"
    root.mkdir()
    path = root / "original.txt.source.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    class Reader:
        def exact_source_locations(self, document_id, source_id):
            assert (document_id, source_id) == (REF.document_id, REF.source_id)
            return [{"root_id": "lake", "relative_path": relative,
                     "location_status": "present", "role": "original_primary"}] * cap

    return SimpleNamespace(
        config=SimpleNamespace(roots=(SimpleNamespace(root_id="lake", path=root),)),
        reader=Reader(),
    )


def test_prior_http_capture_is_read_from_exact_provenance_not_its_mtime(tmp_path):
    catalog = fixture_catalog(tmp_path, capture_payload())
    result = verified_availability_evidence(catalog, REF)
    assert result["available_by"] == "2026-10-07"
    assert result["source_sha256"] == SHA
    assert result["basis"] == "prior_verified_capture"
    assert result["schema_version"] == "source-availability-evidence/1"
    assert "content_sha256" in result["locator"] and "retrieved_at" in result["locator"]
    assert str(tmp_path) not in json.dumps(result)
    assert result["evidence_ref"].startswith("source-provenance:doc-example:")


@pytest.mark.parametrize("mutation", [
    "wrong_sha", "wrong_size", "different_time", "different_url", "failed_http",
    "local_possession", "bare_sidecar", "missing_capture", "invalid_time",
])
def test_unverified_or_conflicting_capture_is_not_historical_proof(tmp_path, mutation):
    payload = capture_payload()
    if mutation == "wrong_sha":
        payload["receipt"]["content_sha256"] = "a" * 64
    elif mutation == "wrong_size":
        payload["byte_size"] = 17
    elif mutation == "different_time":
        payload["retrieved_at"] = "2026-10-06T00:00:00Z"
    elif mutation == "different_url":
        payload["candidate"]["source_url"] = "https://www.sec.gov/other"
    elif mutation == "failed_http":
        payload["receipt"]["http_status"] = 503
    elif mutation == "local_possession":
        payload["receipt"].pop("http_status")
        payload["provenance_extensions"] = {"official_capture": {
            "content_sha256": SHA, "response_bytes": 16,
            "captured_at": "2026-10-07T00:00:00Z", "capture_method": "local_document",
        }}
    elif mutation in {"bare_sidecar", "missing_capture"}:
        payload.pop("receipt")
        if mutation == "bare_sidecar":
            payload.pop("candidate")
            payload["collector_name"] = "sec_edgar"
    else:
        payload["retrieved_at"] = payload["receipt"]["retrieved_at"] = "2026-99-07T00:00:00Z"
    assert verified_availability_evidence(fixture_catalog(tmp_path, payload), REF) is None


@pytest.mark.parametrize("relative", ["../original.txt", "/outside.txt"])
def test_proof_location_cannot_escape_selected_root(tmp_path, relative):
    assert verified_availability_evidence(
        fixture_catalog(tmp_path, capture_payload(), relative=relative), REF,
    ) is None


def test_absolute_fixture_path_is_not_a_relative_proof_location(tmp_path):
    assert verified_availability_evidence(
        fixture_catalog(tmp_path, capture_payload(), relative=str(tmp_path / "outside.txt")), REF,
    ) is None


def test_proof_read_is_bounded_and_does_not_scan_roots(tmp_path):
    catalog = fixture_catalog(tmp_path, capture_payload())
    path = catalog.config.roots[0].path / "original.txt.source.json"
    path.write_bytes(b" " * (64 * 1024 + 1))
    assert verified_availability_evidence(catalog, REF) is None


def test_excess_locations_do_not_expand_work(tmp_path):
    assert verified_availability_evidence(
        fixture_catalog(tmp_path, capture_payload(), cap=65), REF,
    ) is None
