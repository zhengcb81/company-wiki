"""F-BAR-12 regression: `bundle_status="available"` must not read as "artifacts usable".

Measured in R4 (2026-09-18) against a real reused filing: the envelope reported
`bundle_status: "available"` while `bundle.valid_handles` was EMPTY, because both derived
artifacts were invalid (`normalized` -> `artifact_status_not_completed`, `summary` ->
`artifact_source_sha_missing`).  `bundle_status` answers "was a real, snapshot-consistent
bundle provided" (FC-902 fail-closed, resolver.py's envelope docstring) - which is a
different question from "may a consumer reuse any of it", and only the second one matters to
the reader.

The fix is ADDITIVE (the envelope schema version stays "1.0", so an N-1 consumer that only
knows `bundle_status` keeps working): the envelope now also carries
`bundle_valid_handle_count`, `bundle_invalid_roles` and `bundle_usable`, derived from the
bundle's own contents.

Cases:
  * a bundle whose artifacts are ALL invalid -> available but NOT usable, with the invalid
    roles named (the measured production shape);
  * a bundle with one genuinely valid artifact -> usable, so the flag is not a constant;
  * NO bundle at all -> status stays "unavailable" and the new fields stay at their honest
    defaults (the fail-closed case must not be turned into something that looks usable).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.resolver import (  # noqa: E402
    ResolutionResult,
    ResolutionStatus,
    SourceHandle,
    build_resolution_envelope,
)

DIGEST = hashlib.sha256(b"r4bar12").hexdigest()


def _handle(canonical_path: str) -> SourceHandle:
    return SourceHandle(
        schema_version="1.0",
        document_id=f"urn:company-wiki:document:sha256:{DIGEST}",
        source_id=f"urn:company-wiki:source:sha256:{DIGEST}",
        entity_ids=("company-name:Acme",),
        title="Acme 2025 Annual Report",
        source_type="regulatory_filing",
        document_kind="annual_report",
        published_date="2026-02-20",
        fiscal_year=2025,
        fiscal_period=None,
        form_type="10-K",
        language="en",
        provider="sec",
        provider_document_id="doc-1",
        https_url="https://sec.gov/doc-1",
        canonical_location_id="urn:company-wiki:location:sha256:" + DIGEST,
        canonical_path=canonical_path,
        content_sha256=DIGEST,
        snapshot_sha256=DIGEST,
        mime_type="application/pdf",
        byte_size=42,
        retrieved_at="2026-02-20T00:00:00Z",
        collector_name="collector",
        collector_version="1.0.0",
        source_status="active",
        duplicate_group_id="",
        exact_duplicate_location_count=0,
        capture_ready=True,
        missing_capture_fields=(),
    )


def _resolution(tmp_path: Path) -> ResolutionResult:
    # Host-neutral path (the FC-1307 gate flags hard-coded absolute paths in tests, and this
    # handle is never opened - the envelope only carries the string).
    return ResolutionResult(
        schema_version="1.0",
        request_id="urn:company-wiki:source-request:sha256:" + DIGEST,
        status=ResolutionStatus.REUSED_EXACT,
        reason="one_existing_source_matches_provider_identity",
        download_required=False,
        download_allowed=False,
        matches=(_handle(str(tmp_path / "2025.pdf")),),
        debug_trace=("2025: matched",),
    )


def _bundle(*, valid: int, invalid: tuple[str, ...]) -> dict:
    return {
        "schema_version": "1.0",
        "valid_handles": {f"role{i}": {"role": f"role{i}"} for i in range(valid)},
        "invalid": {role: {"role": role, "reason": "artifact_status_not_completed"}
                    for role in invalid},
        "bundle_hash": DIGEST,
    }


def test_all_invalid_artifacts_are_reported_as_not_usable(tmp_path: Path) -> None:
    envelope = build_resolution_envelope(
        _resolution(tmp_path),
        bundle=_bundle(valid=0, invalid=("normalized", "summary")),
    ).to_dict()
    # the measured production shape: the bundle IS there, the artifacts are not
    assert envelope["bundle_status"] == "available"
    assert envelope["bundle_usable"] is False
    assert envelope["bundle_valid_handle_count"] == 0
    assert envelope["bundle_invalid_roles"] == ["normalized", "summary"]


def test_a_valid_artifact_marks_the_bundle_usable(tmp_path: Path) -> None:
    """The flag is derived, not constant."""
    envelope = build_resolution_envelope(
        _resolution(tmp_path),
        bundle=_bundle(valid=1, invalid=("summary",)),
    ).to_dict()
    assert envelope["bundle_status"] == "available"
    assert envelope["bundle_usable"] is True
    assert envelope["bundle_valid_handle_count"] == 1
    assert envelope["bundle_invalid_roles"] == ["summary"]


def test_no_bundle_stays_unavailable_and_not_usable(tmp_path: Path) -> None:
    envelope = build_resolution_envelope(_resolution(tmp_path), bundle=None).to_dict()
    assert envelope["bundle_status"] == "unavailable"
    assert envelope["bundle_usable"] is False
    assert envelope["bundle_valid_handle_count"] == 0
    assert envelope["bundle_invalid_roles"] == []


def test_the_added_fields_do_not_change_the_envelope_schema_version(tmp_path: Path) -> None:
    """N-1 consumers key off the version string; the fix is additive only."""
    envelope = build_resolution_envelope(
        _resolution(tmp_path), bundle=_bundle(valid=0, invalid=("normalized",))).to_dict()
    assert envelope["envelope_schema_version"] == "1.0"

