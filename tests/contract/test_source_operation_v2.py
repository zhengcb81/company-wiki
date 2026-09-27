from __future__ import annotations

from dataclasses import asdict

from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.source_operation import project_operation_result


SHA = "a" * 64
DOCUMENT = "urn:company-wiki:document:sha256:" + "b" * 64
SOURCE = "urn:company-wiki:source:sha256:" + SHA


class _Reader:
    def query_ref(self, document_id: str, source_id: str, sha256: str) -> SourceRef:
        assert (document_id, source_id, sha256) == (DOCUMENT, SOURCE, SHA)
        return SourceRef(DOCUMENT, SOURCE, SHA, 42, "application/pdf")

    def describe_candidate(self, ref: SourceRef) -> dict:
        assert ref == SourceRef(DOCUMENT, SOURCE, SHA, 42, "application/pdf")
        return {
            "source_ref": asdict(ref),
            "document_id": DOCUMENT,
            "source_id": SOURCE,
            "snapshot_sha256": SHA,
            "byte_size": 42,
            "mime_type": "application/pdf",
            "title": "ACME FY2025 filing",
            "document_kind": "annual_report",
            "fiscal_year": 2025,
            "published_date": "2026-02-20",
            "provider": "sec",
            "provider_document_id": "acc-2025",
            "capture_ready": True,
            "prompt_injection_status": "not_detected",
        }


def _contains_physical_field(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            any(token in str(key).lower() for token in ("path", "location", "root", "bundle"))
            or _contains_physical_field(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_physical_field(child) for child in value)
    return False


def _private_path(tmp_path, name: str) -> str:
    return str(tmp_path / name)


def test_ensure_v2_projects_source_and_acquisition_receipt_without_paths(tmp_path) -> None:
    payload = {
        "status": "imported",
        "request_id": "urn:req:1",
        "resolution": {
            "status": "reused_exact",
            "request_id": "urn:req:1",
            "matches": [{
                "document_id": DOCUMENT,
                "source_id": SOURCE,
                "snapshot_sha256": SHA,
                "byte_size": 42,
                "mime_type": "application/pdf",
                "canonical_path": _private_path(tmp_path, "raw.pdf"),
                "source_bundle": {"path": _private_path(tmp_path, "bundle.json")},
            }],
            "resolution_envelope": {
                "outcome": "downloaded_new",
                "download_events": 1,
                "policy_hash": "d" * 64,
                "policy_export": {"roots": [{"path": str(tmp_path)}]},
            },
        },
        "attempt": {"outcome": "downloaded_new"},
    }

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    assert result["operation_schema_version"] == "1.0"
    assert result["operation"] == "ensure"
    assert result["status"] == "completed"
    assert result["request_id"] == "urn:req:1"
    assert result["outcome"] == "downloaded_new"
    assert result["download_events"] == 1
    assert result["policy_hash"] == "d" * 64
    assert result["source_ref"] == {
        "schema_version": "2.0",
        "document_id": DOCUMENT,
        "source_id": SOURCE,
        "content_sha256": SHA,
        "byte_size": 42,
        "mime_type": "application/pdf",
    }
    assert result["candidate"]["prompt_injection_status"] == "not_detected"
    assert result["gap_plan"] is None
    assert not _contains_physical_field(result)
    assert str(tmp_path) not in str(result)


def test_ensure_v2_preserves_metadata_gap_without_paths_or_false_not_found(tmp_path) -> None:
    payload = {
        "status": "gap",
        "request_id": "urn:req:latest",
        "acquisition_result": {
            "gap_plan": {
                "schema_version": "1.0",
                "request_id": "urn:req:latest",
                "as_of_date": "2026-09-27",
                "document_kind": "annual_report",
                "entity": "ACME",
                "market": "US",
                "missing": [{
                    "provider": "sec",
                    "provider_document_id": "acc-2025",
                    "canonical_path": _private_path(tmp_path, "raw.pdf"),
                }],
                "newer_revision": [],
                "future": [],
                "gap_hash": "c" * 64,
                "provider_unavailable": False,
                "debug_path": _private_path(tmp_path, "debug.json"),
            },
        },
        "resolution": {"status": "missing", "matches": []},
    }

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    assert result["status"] == "gap"
    assert result["download_events"] == 0
    assert result["source_ref"] is None
    assert result["candidate"] is None
    assert result["gap_plan"]["gap_hash"] == "c" * 64
    assert result["gap_plan"]["missing"] == [{
        "provider": "sec",
        "provider_document_id": "acc-2025",
    }]
    assert not _contains_physical_field(result)
    assert str(tmp_path) not in str(result)


def test_close_gap_v2_records_the_committed_version_without_exposing_path(tmp_path) -> None:
    payload = {
        "status": "completed",
        "request_id": "urn:req:closed",
        "outcome": "downloaded_new",
        "fetch_events": 1,
        "resolution": {
            "status": "reused_exact",
            "request_id": "urn:req:closed",
            "matches": [{
                "document_id": DOCUMENT,
                "source_id": SOURCE,
                "snapshot_sha256": SHA,
                "byte_size": 42,
                "mime_type": "application/pdf",
                "canonical_path": _private_path(tmp_path, "raw.pdf"),
            }],
        },
        "envelope": {
            "outcome": "downloaded_new",
            "download_events": 1,
            "bundle": {"path": _private_path(tmp_path, "bundle.json")},
        },
    }

    result = project_operation_result(payload, operation="close-gap", reader=_Reader())

    assert result["status"] == "completed"
    assert result["outcome"] == "downloaded_new"
    assert result["download_events"] == 1
    assert result["source_ref"]["content_sha256"] == SHA
    assert not _contains_physical_field(result)
    assert str(tmp_path) not in str(result)
