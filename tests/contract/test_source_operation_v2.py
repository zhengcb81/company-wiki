from __future__ import annotations

from dataclasses import asdict

import pytest

from company_wiki.source_catalog.acquisition import (
    AcquisitionResult,
    AcquisitionStatus,
)
from company_wiki.source_catalog.acquisition_journal import AcquisitionAttempt
from company_wiki.source_catalog.acquisition_service import (
    SourceEnsureResult,
    SourceEnsureStatus,
)
from company_wiki.source_catalog.close_gap import CloseGapResult
from company_wiki.source_catalog.gap_plan import GapPlan
from company_wiki.source_catalog.resolver import (
    ResolutionResult,
    ResolutionStatus,
    SourceHandle,
)
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.source_operation import (
    SourceOperationProjectionError,
    project_operation_result,
)


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


def _attempt(request_id: str, outcome: str) -> AcquisitionAttempt:
    return AcquisitionAttempt(
        schema_version="1.0",
        attempt_id="urn:company-wiki:attempt:sha256:" + "e" * 64,
        recorded_at="2026-09-27T00:00:00Z",
        request_id=request_id,
        outcome=outcome,
    )


def _resolved_handle(tmp_path) -> SourceHandle:
    return SourceHandle(
        schema_version="1.0",
        document_id=DOCUMENT,
        source_id=SOURCE,
        entity_ids=("ticker:ACME",),
        title="ACME FY2025 filing",
        source_type="filing",
        document_kind="annual_report",
        published_date="2026-02-20",
        fiscal_year=2025,
        fiscal_period=None,
        form_type="10-K",
        language="en",
        provider="sec",
        provider_document_id="acc-2025",
        https_url="https://sec.gov/x/2025",
        canonical_location_id="location-1",
        canonical_path=_private_path(tmp_path, "raw.pdf"),
        content_sha256=SHA,
        snapshot_sha256=SHA,
        mime_type="application/pdf",
        byte_size=42,
        retrieved_at="2026-02-21T00:00:00Z",
        collector_name="sec_edgar",
        collector_version="1.0",
        source_status="active",
        duplicate_group_id="group-1",
        exact_duplicate_location_count=1,
        capture_ready=True,
        missing_capture_fields=(),
    )


def _formal_completed_payload(tmp_path) -> dict:
    request_id = "urn:req:1"
    resolution = ResolutionResult(
        schema_version="1.0",
        request_id=request_id,
        status=ResolutionStatus.REUSED_EXACT,
        reason="exact_match",
        download_required=False,
        download_allowed=False,
        matches=(_resolved_handle(tmp_path),),
    )
    ensure = SourceEnsureResult(
        schema_version="1.0",
        status=SourceEnsureStatus.REUSED,
        acquisition=AcquisitionResult(
            schema_version="1.0",
            status=AcquisitionStatus.REUSED,
            resolution=resolution,
        ),
        resolution=resolution,
        attempt=_attempt(request_id, "reused_before_download"),
    )
    payload = ensure.to_dict()
    payload["resolution"]["resolution_envelope"] = {
        "outcome": "reused_before_download",
        "download_events": 0,
        "policy_hash": "d" * 64,
        "policy_export": {"roots": [{"path": str(tmp_path)}]},
    }
    return payload


def _formal_gap_payload(tmp_path) -> dict:
    request_id = "urn:req:latest"
    resolution = ResolutionResult(
        schema_version="1.0",
        request_id=request_id,
        status=ResolutionStatus.MISSING,
        reason="no_matching_source",
        download_required=True,
        download_allowed=False,
        matches=(),
    )
    gap = GapPlan(
        schema_version="1.0",
        request_id=request_id,
        as_of_date="2026-09-27",
        document_kind="annual_report",
        entity="ACME",
        market="US",
        missing=({
            "provider": "sec",
            "provider_document_id": "acc-2025",
            "canonical_path": _private_path(tmp_path, "raw.pdf"),
        },),
        gap_hash="c" * 64,
    )
    ensure = SourceEnsureResult(
        schema_version="1.0",
        status=SourceEnsureStatus.GAP,
        acquisition=AcquisitionResult(
            schema_version="1.0",
            status=AcquisitionStatus.GAP,
            resolution=resolution,
            gap_plan=gap,
        ),
        resolution=resolution,
        attempt=_attempt(request_id, "gap_plan"),
    )
    return {"source_ensure": ensure.to_dict()}


def test_ensure_v2_projects_source_and_acquisition_receipt_without_paths(tmp_path) -> None:
    payload = _formal_completed_payload(tmp_path)

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    assert result["operation_schema_version"] == "1.0"
    assert result["operation"] == "ensure"
    assert result["status"] == "completed"
    assert result["request_id"] == "urn:req:1"
    assert result["outcome"] == "reused_before_download"
    assert result["download_events"] == 0
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
    payload = _formal_gap_payload(tmp_path)

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


def test_ensure_gap_rejects_nonexistent_acquisition_result_alias() -> None:
    payload = {
        "source_ensure": {
            "schema_version": "1.0",
            "status": "gap",
            "acquisition_result": {"gap_plan": {"request_id": "urn:req:bad"}},
            "resolution": {
                "schema_version": "1.0",
                "request_id": "urn:req:bad",
                "status": "missing",
                "matches": [],
            },
        },
    }

    with pytest.raises(SourceOperationProjectionError, match="acquisition"):
        project_operation_result(payload, operation="ensure", reader=_Reader())


def test_ensure_rejects_unknown_producer_schema() -> None:
    payload = {
        "source_ensure": {
            "schema_version": "9.9",
            "status": "missing",
            "acquisition": {"schema_version": "1.0", "status": "missing"},
            "resolution": {
                "schema_version": "1.0",
                "request_id": "urn:req:schema",
                "status": "missing",
                "matches": [],
            },
        },
    }

    with pytest.raises(SourceOperationProjectionError, match="schema_version"):
        project_operation_result(payload, operation="ensure", reader=_Reader())


def test_ensure_gap_rejects_mismatched_request_identity(tmp_path) -> None:
    payload = _formal_gap_payload(tmp_path)
    payload["source_ensure"]["resolution"]["request_id"] = "urn:req:other"

    with pytest.raises(SourceOperationProjectionError, match="request_id"):
        project_operation_result(payload, operation="ensure", reader=_Reader())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("download_events", -1, "download event"),
        ("policy_hash", "NOT-A-SHA", "policy hash"),
    ],
)
def test_ensure_rejects_invalid_receipt_fields(
    tmp_path, field: str, value: object, message: str,
) -> None:
    payload = _formal_completed_payload(tmp_path)
    payload["resolution"]["resolution_envelope"][field] = value

    with pytest.raises(SourceOperationProjectionError, match=message):
        project_operation_result(payload, operation="ensure", reader=_Reader())


@pytest.mark.parametrize(
    ("field", "value"),
    [("byte_size", 41), ("mime_type", "text/plain")],
)
def test_ensure_rejects_resolved_version_drift(
    tmp_path, field: str, value: object,
) -> None:
    payload = _formal_completed_payload(tmp_path)
    payload["resolution"]["matches"][0][field] = value

    with pytest.raises(SourceOperationProjectionError, match="version changed"):
        project_operation_result(payload, operation="ensure", reader=_Reader())


def test_ensure_rejects_reader_candidate_with_physical_path(tmp_path) -> None:
    class LeakingReader(_Reader):
        def describe_candidate(self, ref: SourceRef) -> dict:
            candidate = super().describe_candidate(ref)
            candidate["canonical_path"] = _private_path(tmp_path, "raw.pdf")
            return candidate

    with pytest.raises(SourceOperationProjectionError, match="physical field"):
        project_operation_result(
            _formal_completed_payload(tmp_path),
            operation="ensure",
            reader=LeakingReader(),
        )


def test_close_gap_v2_records_the_committed_version_without_exposing_path(tmp_path) -> None:
    payload = CloseGapResult(
        schema_version="1.0",
        txn_id="urn:txn:closed",
        status="completed",
        reason="committed",
        outcome="downloaded_new",
        fetch_events=1,
        resolution={
            "schema_version": "1.0",
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
        envelope={
            "outcome": "downloaded_new",
            "download_events": 1,
            "bundle": {"path": _private_path(tmp_path, "bundle.json")},
        },
    ).to_dict()

    result = project_operation_result(payload, operation="close-gap", reader=_Reader())

    assert result["status"] == "completed"
    assert result["outcome"] == "downloaded_new"
    assert result["download_events"] == 1
    assert result["source_ref"]["content_sha256"] == SHA
    assert not _contains_physical_field(result)
    assert str(tmp_path) not in str(result)
