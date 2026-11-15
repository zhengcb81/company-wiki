"""FF-1 B4: the pathless operation payload republishes candidates.

Contract (2026-11-15, shared verbatim with the FF consumer lane):
  * top-level optional "candidates": list[object], only for status
    ambiguous / not_found — never on completed / gap payloads;
  * per-item whitelist exactly: document_id, title, document_kind, provider,
    provider_document_id, form_type, fiscal_year, fiscal_period, language,
    content_sha256, byte_size, publication_status(known|unknown|future),
    exclusion_reason(closed set);
  * top-level optional "reason" from the closed resolver/coordinator
    vocabulary;
  * candidates capped at 5 in existing order;
  * physical paths / commands / credentials never appear (pathless guard);
  * operation_schema_version stays "1.0".
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.operation_contract import OPERATION_REASONS  # noqa: E402
from company_wiki.source_catalog.resolver import CANDIDATE_EXCLUSION_REASONS  # noqa: E402
from company_wiki.source_catalog.source_operation import (  # noqa: E402
    SourceOperationProjectionError,
    project_operation_result,
)
from contract.test_source_operation_v2 import _Reader  # noqa: E402

SHA = "a" * 64
OTHER_SHA = "b" * 64
DOCUMENT = "urn:company-wiki:document:sha256:" + "c" * 64

_CANDIDATE_FIELDS = {
    "document_id", "title", "document_kind", "provider", "provider_document_id",
    "form_type", "fiscal_year", "fiscal_period", "language", "content_sha256",
    "byte_size", "publication_status", "exclusion_reason",
}


def _contains_physical_field(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            any(token in str(key).lower() for token in ("path", "location", "root", "bundle"))
            or _contains_physical_field(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_physical_field(child) for child in value)
    return False


def _undated_candidate(document_id: str = DOCUMENT, sha: str = SHA, **extra) -> dict:
    return {
        "document_id": document_id,
        "title": "mdb-2025",
        "document_kind": "annual_report",
        "provider": "sec",
        "provider_document_id": "acc-1",
        "form_type": "10-K",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "language": "en",
        "content_sha256": sha,
        "byte_size": 42,
        "publication_status": "unknown",
        "exclusion_reason": "published_date_unknown",
        "qualification": {
            "schema_version": "source-qualification/1",
            "publication_status": "unknown",
            "as_of_date": "2026-10-08",
            "local_bytes_status": "verified",
            "historical_date_eligible": False,
            "historical_reuse_eligible": False,
        },
        "source_ref": {
            "schema_version": "2.0", "document_id": document_id,
            "source_id": "urn:company-wiki:source:sha256:" + sha,
            "content_sha256": sha, "byte_size": 42, "mime_type": "application/pdf",
        },
        **extra,
    }


def _ambiguous_payload(*, excluded=None, reason="unique_match_published_date_unknown",
                       matches=None) -> dict:
    return {"source_ensure": {
        "schema_version": "1.0",
        "status": "ambiguous",
        "request_id": "urn:req:undated",
        "acquisition": {
            "schema_version": "1.0",
            "status": "ambiguous",
            "reason": reason,
            "resolution": {
                "schema_version": "1.0",
                "request_id": "urn:req:undated",
                "status": "ambiguous",
                "reason": reason,
                "matches": matches if matches is not None else [],
                "excluded_candidates": list(excluded or []),
            },
        },
        "resolution": {
            "schema_version": "1.0",
            "request_id": "urn:req:undated",
            "status": "ambiguous",
            "reason": reason,
            "matches": matches if matches is not None else [],
            "excluded_candidates": list(excluded or []),
        },
        "attempt": {"request_id": "urn:req:undated", "outcome": "ambiguous"},
    }}


def _match(document_id: str, sha: str, title: str) -> dict:
    return {
        "document_id": document_id,
        "title": title,
        "document_kind": "annual_report",
        "form_type": "10-K",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "language": "en",
        "published_date": None,
        "snapshot_sha256": sha,
        "content_sha256": sha,
        "byte_size": 42,
    }


def test_ambiguous_payload_carries_whitelisted_candidates_and_reason() -> None:
    payload = _ambiguous_payload(excluded=[_undated_candidate()])

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    assert result["status"] == "ambiguous"
    assert result["reason"] == "unique_match_published_date_unknown"
    candidate, = result["candidates"]
    assert set(candidate) == _CANDIDATE_FIELDS
    assert candidate["document_id"] == DOCUMENT
    assert candidate["content_sha256"] == SHA
    assert candidate["publication_status"] == "unknown"
    assert candidate["exclusion_reason"] == "published_date_unknown"
    assert result["operation_schema_version"] == "1.0"
    assert not _contains_physical_field(result)


def test_multiple_matches_project_as_multiple_candidates() -> None:
    payload = _ambiguous_payload(
        reason="multiple_existing_sources_match_semantic_request",
        matches=[
            _match("urn:company-wiki:document:sha256:" + "1" * 64, "1" * 64, "rev-1"),
            _match("urn:company-wiki:document:sha256:" + "2" * 64, "2" * 64, "rev-2"),
        ],
    )

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    assert result["reason"] == "multiple_existing_sources_match_semantic_request"
    first, second = result["candidates"]
    assert first["exclusion_reason"] == "multiple_candidates"
    assert second["exclusion_reason"] == "multiple_candidates"
    assert first["document_id"].endswith("1" * 64) and second["document_id"].endswith("2" * 64)
    assert not _contains_physical_field(result)


def test_candidates_are_capped_at_five_in_existing_order() -> None:
    excluded = [
        _undated_candidate(document_id=f"urn:company-wiki:document:sha256:{index:x}{63 * '0'}",
                           sha=f"{index:x}{63 * '0'}")
        for index in range(7)
    ]
    payload = _ambiguous_payload(excluded=excluded)

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    candidates = result["candidates"]
    assert len(candidates) == 5
    assert [c["content_sha256"][0] for c in candidates] == ["0", "1", "2", "3", "4"]


def test_completed_and_gap_payloads_never_carry_candidates(tmp_path) -> None:
    from contract.test_source_operation_v2 import (
        _formal_completed_payload,
        _formal_gap_payload,
    )

    completed = _formal_completed_payload(tmp_path)
    completed["resolution"]["excluded_candidates"] = [_undated_candidate()]
    completed["resolution"]["reason"] = "unique_match_published_date_unknown"
    result = project_operation_result(completed, operation="ensure", reader=_Reader())
    assert result["status"] == "completed"
    assert "candidates" not in result
    assert "reason" not in result

    gap = _formal_gap_payload(tmp_path)
    gap["source_ensure"]["resolution"]["excluded_candidates"] = [_undated_candidate()]
    result = project_operation_result(gap, operation="ensure", reader=_Reader())
    assert result["status"] == "gap"
    assert "candidates" not in result
    assert "reason" not in result


def test_unknown_reason_is_omitted_not_invented() -> None:
    payload = _ambiguous_payload(reason="a_reason_outside_every_vocabulary")
    payload["source_ensure"]["acquisition"]["resolution"]["reason"] = (
        "a_reason_outside_every_vocabulary"
    )

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    assert result["status"] == "ambiguous"
    assert "reason" not in result


def test_pathless_guard_holds_for_candidate_details(tmp_path: Path) -> None:
    leaking = _undated_candidate()
    # Host-neutral absolute paths: the projection must strip a candidate
    # field that names a physical location, whatever the machine's root is.
    leaking["canonical_path"] = str(tmp_path / "companies" / "Acme" / "raw" / "2025.pdf")
    leaking["absolute_location"] = str(tmp_path / "elsewhere")
    payload = _ambiguous_payload(excluded=[leaking])

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    candidate, = result["candidates"]
    assert set(candidate) == _CANDIDATE_FIELDS
    assert not _contains_physical_field(result)
    assert "2025.pdf" not in str(result)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"content_sha256": "not-a-sha"}, "content_sha256"),
        ({"byte_size": -1}, "byte_size"),
        ({"publication_status": "eligible"}, "publication_status"),
        ({"exclusion_reason": "secretly_excluded"}, "exclusion_reason"),
        ({"fiscal_year": "2025"}, "fiscal_year"),
        ({"document_id": ""}, "document_id"),
    ],
)
def test_malformed_candidates_are_rejected(mutation: dict, message: str) -> None:
    payload = _ambiguous_payload(excluded=[_undated_candidate(**mutation)])

    with pytest.raises(SourceOperationProjectionError, match=message):
        project_operation_result(payload, operation="ensure", reader=_Reader())


def test_vocabulary_and_closed_sets_are_exported_for_the_consumer_lane() -> None:
    assert "unique_match_published_date_unknown" in OPERATION_REASONS
    assert "matching_sources_have_unknown_published_date" in OPERATION_REASONS
    assert "adapter_discovery_returned_multiple_candidates" in OPERATION_REASONS
    assert "multiple_existing_sources_match_semantic_request" in OPERATION_REASONS
    assert CANDIDATE_EXCLUSION_REASONS == frozenset({
        "published_date_unknown", "fiscal_year_mismatch", "multiple_candidates",
        "identity_mismatch", "capture_not_ready", "other_excluded",
    })
    assert hashlib.sha256(b"").hexdigest()  # sanity: stable digest helper import


def test_padded_titles_are_trimmed_in_both_candidate_branches() -> None:
    """F-R3: documents.title is free text and may carry whitespace padding.

    The FF consumer validates every candidate title with the strict shape
    rule ``value.strip() and value == value.strip()`` (filing-fetch
    ``scripts/fetch_filing.py::_validated_operation_candidates``, the
    ``title`` arm of the trimmed-text loop), refusing the WHOLE payload on a
    violation.  The producer therefore trims the projection output — the
    excluded branch (B1 diagnostic) and the matches branch
    (multiple_candidates) alike — while the stored documents row is
    untouched.  A trimmed title passes that consumer shape rule.
    """
    payload = _ambiguous_payload(excluded=[_undated_candidate(title="  mdb-2025  ")])

    result = project_operation_result(payload, operation="ensure", reader=_Reader())

    candidate, = result["candidates"]
    assert candidate["title"] == "mdb-2025"

    matched = _ambiguous_payload(
        reason="multiple_existing_sources_match_semantic_request",
        matches=[
            _match("urn:company-wiki:document:sha256:" + "1" * 64, "1" * 64, "  rev-1  "),
            _match("urn:company-wiki:document:sha256:" + "2" * 64, "2" * 64, "rev-2"),
        ],
    )

    result = project_operation_result(matched, operation="ensure", reader=_Reader())

    assert [item["title"] for item in result["candidates"]] == ["rev-1", "rev-2"]
    assert not _contains_physical_field(result)


def test_whitespace_only_title_fails_closed() -> None:
    """A whitespace-only title has no consumer-valid representation (the FF
    shape rule requires non-empty trimmed text), so the projection refuses
    to emit it instead of producing a payload the consumer must reject."""
    payload = _ambiguous_payload(excluded=[_undated_candidate(title="   ")])

    with pytest.raises(SourceOperationProjectionError, match="title"):
        project_operation_result(payload, operation="ensure", reader=_Reader())
