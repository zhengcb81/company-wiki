"""Historical information availability, independent of actual research events.

The upstream publisher/capture proof establishes availability for an exact raw
version. Actual retrieval/read/check clocks stay real; they are not the study's
information cutoff. This module performs no IO and grants no source access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import re
from typing import Any

SOURCE_CLOCK_VERSION = "source-clock/1"
AVAILABILITY_SCHEMA_VERSION = "source-availability-evidence/1"
_AVAILABILITY_FIELDS = {"schema_version", "source_sha256", "available_by", "basis", "evidence_ref", "locator"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


class SourceClockError(ValueError):
    """Named information gap, future source or contradictory actual event."""


@dataclass(frozen=True)
class InformationEligibility:
    available_by: date
    basis: str
    source_sha256: str | None
    published_date: date | None


def iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise SourceClockError(f"source_clock_invalid_date: {field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SourceClockError(f"source_clock_invalid_date: {field} must be an ISO date") from exc


def utc_timestamp(value: Any, field: str, *, require_utc: bool = True) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SourceClockError(f"source_clock_invalid_date: {field} must be timezone-aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceClockError(f"source_clock_invalid_date: {field} must be timezone-aware") from exc
    offset = parsed.utcoffset()
    if parsed.tzinfo is None or offset is None:
        raise SourceClockError(f"source_clock_invalid_date: {field} must be timezone-aware")
    if require_utc and offset.total_seconds() != 0:
        raise SourceClockError(f"source_clock_invalid_date: {field} must be UTC")
    return parsed.astimezone(UTC)


def validate_availability_evidence(value: Any, source_sha256: str | None) -> dict[str, Any] | None:
    """Validate the published DTO; upstream resolves the actual immutable proof.

    A timestamp/mtime supplied alone is never proof. This structural check does
    not claim external authenticity: callers obtain this DTO from the declared
    public source-reader producer and retain that transport in their lineage.
    """
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != _AVAILABILITY_FIELDS:
        raise SourceClockError("source_availability_invalid: proof fields are not exact")
    if value["schema_version"] != AVAILABILITY_SCHEMA_VERSION:
        raise SourceClockError("source_availability_invalid: unsupported proof schema")
    if value["basis"] not in {"prior_verified_capture", "primary_archive"}:
        raise SourceClockError("source_availability_invalid: unsupported proof basis")
    digest = value["source_sha256"]
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise SourceClockError("source_availability_invalid: source_sha256 must be SHA-256")
    if digest != source_sha256:
        raise SourceClockError("source_availability_version_mismatch: proof/source_sha256")
    iso_date(value["available_by"], "availability_evidence.available_by")
    for field in ("evidence_ref", "locator"):
        text = value[field]
        if not isinstance(text, str) or not text.strip() or text != text.strip() or len(text) > 2048 or any(ord(c) < 32 for c in text):
            raise SourceClockError(f"source_availability_invalid: {field} is invalid")
    ref = value["evidence_ref"]
    if ref.startswith(("/", "\\", "file:")) or re.match(r"[A-Za-z]:[\\/]", ref):
        raise SourceClockError("source_availability_invalid: evidence_ref must be pathless")
    return dict(value)


def qualify_source_information(
    *, source_sha256: str | None, published_date: Any,
    as_of: date, availability_evidence: Any = None,
) -> InformationEligibility:
    """Use the current CWP publication cutoff semantics, with exact-version proof.

    Known publication always controls the cutoff. Reliable prior availability
    can qualify an unknown publication, but never manufactures a publication
    date or carries over to changed raw bytes.
    """
    if not isinstance(as_of, date) or isinstance(as_of, datetime):
        raise SourceClockError("source_clock_invalid_date: as_of must be a date")
    published = None if published_date is None or published_date == "" else iso_date(published_date, "published_date")
    if published is not None and published > as_of:
        raise SourceClockError("source_publication_after_asof: published_date is outside as_of_date (future information leak)")
    proof = validate_availability_evidence(availability_evidence, source_sha256)
    if published is not None:
        return InformationEligibility(published, "publication", source_sha256, published)
    if proof is None:
        raise SourceClockError("source_availability_unknown: publication unknown and no reliable prior availability proof")
    available = iso_date(proof["available_by"], "availability_evidence.available_by")
    if available > as_of:
        raise SourceClockError("source_availability_after_asof: available_by is outside as_of_date")
    return InformationEligibility(available, proof["basis"], source_sha256, None)


def source_information_eligibility(source: dict[str, Any], as_of: date) -> InformationEligibility:
    """Consume an RF source fact; optional proof retains its public producer link."""
    capture = source.get("capture")
    digest = capture.get("snapshot_sha256") if isinstance(capture, dict) else None
    proof = source.get("availability_evidence")
    if proof is not None:
        trace = source.get("company_wiki_trace")
        receipt = trace.get("read_receipt") if isinstance(trace, dict) else None
        ref = trace.get("source_ref") if isinstance(trace, dict) else None
        manifest = trace.get("source_manifest") if isinstance(trace, dict) else None
        if not (isinstance(receipt, dict) and receipt.get("schema_version") == "2.2"
                and receipt.get("availability_evidence") == proof
                and receipt.get("content_sha256") == digest
                and isinstance(ref, dict) and ref.get("content_sha256") == digest
                and isinstance(manifest, dict) and manifest.get("content_sha256") == digest
                and manifest.get("published_date") == source.get("published_date")):
            raise SourceClockError("source_availability_invalid: proof has no matching public source receipt lineage")
    return qualify_source_information(source_sha256=digest, published_date=source.get("published_date"),
                                      as_of=as_of, availability_evidence=proof)


def _conflict(first: str, first_value: Any, second: str, second_value: Any) -> None:
    raise SourceClockError(f"source_clock_conflict: {first}={first_value!r}, {second}={second_value!r}")


def validate_source_events(
    *, eligibility: InformationEligibility, original_retrieved_at: Any = None,
    current_read_at: Any = None, capture_date: Any = None,
    claim_verified_date: Any = None, host_timestamp: Any = None,
) -> None:
    """Check actual event consistency without a historical as-of ceiling."""
    original = None if original_retrieved_at is None else utc_timestamp(original_retrieved_at, "retrieved_at", require_utc=False)
    read = None if current_read_at is None else utc_timestamp(current_read_at, "read_at")
    captured = None if capture_date is None else iso_date(capture_date, "captured_date")
    checked = None if claim_verified_date is None else iso_date(claim_verified_date, "verified_date")
    if original is not None and eligibility.published_date is not None and original.date() < eligibility.published_date:
        _conflict("retrieved_at", original_retrieved_at, "published_date", eligibility.published_date.isoformat())
    if original is not None and read is not None and original > read:
        _conflict("retrieved_at", original_retrieved_at, "read_at", current_read_at)
    if read is not None and read.date() < eligibility.available_by:
        _conflict("read_at", current_read_at, "availability", eligibility.available_by.isoformat())
    if captured is not None and captured < eligibility.available_by:
        _conflict("captured_date", capture_date, "availability", eligibility.available_by.isoformat())
    if read is not None and captured is not None and captured != read.date():
        _conflict("captured_date", capture_date, "read_at", current_read_at)
    if host_timestamp is not None and captured is not None:
        # Existing capture1.0 host receipts may have a date-only timestamp.
        host_day = iso_date(host_timestamp, "timestamp") if isinstance(host_timestamp, str) and _DATE.fullmatch(host_timestamp) else utc_timestamp(host_timestamp, "timestamp", require_utc=False).date()
        if host_day != captured:
            _conflict("captured_date", capture_date, "timestamp", host_timestamp)
    if checked is not None and captured is not None and checked < captured:
        _conflict("verified_date", claim_verified_date, "captured_date", capture_date)
    if checked is not None and checked < eligibility.available_by:
        _conflict("verified_date", claim_verified_date, "availability", eligibility.available_by.isoformat())
