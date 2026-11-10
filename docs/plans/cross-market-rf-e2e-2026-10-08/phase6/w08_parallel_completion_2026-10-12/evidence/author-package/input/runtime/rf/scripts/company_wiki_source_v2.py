"""Build RF source records from company-wiki's verified SourceRef v2 read."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
from typing import Any

from company_wiki_source import (
    CompanyWikiSourceError,
    _PROMPT_INJECTION_STATUSES,
    _SHA256_RE,
    _SOURCE_TYPES,
    _canonical_sha256,
    _iso_date,
    _required_text,
)
from contracts.evidence import build_host_receipt, valid_source_url
from contracts.source_clock import (
    InformationEligibility, SourceClockError, qualify_source_information,
    validate_availability_evidence, validate_source_events,
)
from source_period_semantics import valid_fiscal_year


_REF_FIELDS = {
    "schema_version", "document_id", "source_id", "content_sha256",
    "byte_size", "mime_type",
}
_RECEIPT_FIELDS = {
    "schema_version", "status", "document_id", "source_id",
    "content_sha256", "byte_size", "policy_sha256",
    "source_read_policy_sha256", "read_at", "review",
}
_MANIFEST_FIELDS = {
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
    "title", "document_kind", "published_date", "source_url", "retrieved_at",
    "collector_name", "collector_version", "canonical_entity_id", "display_name",
    "market", "security_id", "fiscal_year", "fiscal_period", "period_end",
    "form_type", "provider", "provider_document_id", "language",
}
_REVIEW_FIELDS = {
    "status", "source_sha256", "evidence_sha256", "policy_hash", "reviewed_at",
}
_OUTCOMES = {"reused_existing", "reused_after_discovery", "downloaded_new"}
_FORBIDDEN_LOCATION_FIELDS = {
    "path", "canonical_path", "relative_path", "storage_path",
    "canonical_location_id", "root_path", "filesystem_path",
}
_TOOL_NAME = "company-wiki-source-version-reader"


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CompanyWikiSourceError(f"{label} must be an object")
    return value


def _same(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is not type(expected) or actual != expected:
        raise CompanyWikiSourceError(f"{label} mismatch")


def _aware_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CompanyWikiSourceError(f"{label} must be timezone-aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompanyWikiSourceError(f"{label} must be timezone-aware") from exc
    offset = parsed.utcoffset()
    if parsed.tzinfo is None or offset is None:
        raise CompanyWikiSourceError(f"{label} must be timezone-aware")
    if offset.total_seconds() != 0:
        raise CompanyWikiSourceError(f"{label} must be UTC")
    return parsed


def _validate_ref_schema(ref: dict[str, Any]) -> None:
    if set(ref) != _REF_FIELDS or ref.get("schema_version") != "2.0":
        raise CompanyWikiSourceError("source_ref fields/schema are unsupported")


def _validate_ref_metadata(ref: dict[str, Any]) -> None:
    for field in ("document_id", "source_id", "mime_type"):
        _required_text(ref.get(field), f"source_ref.{field}")


def _validate_ref_digest_and_size(ref: dict[str, Any]) -> None:
    digest = ref.get("content_sha256")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise CompanyWikiSourceError("source_ref content_sha256 is invalid")
    size = ref.get("byte_size")
    if type(size) is not int or size < 0:
        raise CompanyWikiSourceError("source_ref byte_size is invalid")


def _validate_ref(source_ref: Any) -> dict[str, Any]:
    ref = _object(source_ref, "source_ref")
    _validate_ref_schema(ref)
    _validate_ref_metadata(ref)
    _validate_ref_digest_and_size(ref)
    return ref


def _validate_receipt(receipt_value: Any, ref: dict[str, Any]) -> dict[str, Any]:
    receipt = _object(receipt_value, "read_receipt")
    expected = _RECEIPT_FIELDS if receipt.get("schema_version") == "2.1" else _RECEIPT_FIELDS | {"availability_evidence"}
    if receipt.get("schema_version") not in {"2.1", "2.2"} or set(receipt) != expected:
        raise CompanyWikiSourceError("source read receipt fields/schema are invalid")
    if receipt.get("status") != "ok":
        raise CompanyWikiSourceError("source read receipt is not successful")
    for field in ("document_id", "source_id", "content_sha256", "byte_size"):
        _same(receipt.get(field), ref[field], f"source read receipt {field}")
    for field in ("policy_sha256", "source_read_policy_sha256"):
        value = receipt.get(field)
        if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
            raise CompanyWikiSourceError(f"source read receipt {field} is invalid")
    _aware_datetime(receipt.get("read_at"), "source read receipt read_at")
    _validate_review(receipt.get("review"), ref)
    try:
        validate_availability_evidence(receipt.get("availability_evidence"), ref["content_sha256"])
    except SourceClockError as exc:
        raise CompanyWikiSourceError(str(exc)) from exc
    return receipt


def _validate_review_shape(review: dict[str, Any]) -> None:
    if set(review) != _REVIEW_FIELDS:
        raise CompanyWikiSourceError("source read receipt review is invalid")
    if review.get("status") not in _PROMPT_INJECTION_STATUSES:
        raise CompanyWikiSourceError("source read receipt review is invalid")


def _validate_review_source(review: dict[str, Any], ref: dict[str, Any]) -> None:
    digest = review.get("source_sha256")
    if digest is not None and digest != ref["content_sha256"]:
        raise CompanyWikiSourceError("source read receipt review source mismatch")


def _validate_review_hashes(review: dict[str, Any]) -> None:
    for field in ("evidence_sha256", "policy_hash"):
        digest = review.get(field)
        if digest is not None and (
            not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest)
        ):
            raise CompanyWikiSourceError(f"source read receipt review {field} is invalid")


def _validate_review(review: Any, ref: dict[str, Any]) -> None:
    if review is None:
        return
    value = _object(review, "source read receipt review")
    _validate_review_shape(value)
    _validate_review_source(value, ref)
    _validate_review_hashes(value)
    reviewed_at = value.get("reviewed_at")
    if reviewed_at is not None:
        _aware_datetime(reviewed_at, "source read receipt review reviewed_at")


def _validate_manifest_identity(
    manifest: dict[str, Any], ref: dict[str, Any],
) -> None:
    fields = ("document_id", "source_id", "content_sha256", "byte_size", "mime_type")
    for field in fields:
        _same(manifest.get(field), ref[field], f"source manifest {field}")


def _validate_manifest_metadata(manifest: dict[str, Any]) -> None:
    title = manifest.get("title")
    if title is not None and not isinstance(title, str):
        raise CompanyWikiSourceError("source manifest title must be text or null")
    _required_text(manifest.get("document_kind"), "source manifest document_kind")
    if not valid_fiscal_year(manifest["document_kind"], manifest.get("fiscal_year")):
        raise CompanyWikiSourceError("source manifest fiscal_year is invalid")
    fields = (
        "collector_name", "collector_version", "canonical_entity_id", "display_name",
        "market", "security_id", "form_type", "provider", "provider_document_id",
        "language",
    )
    for field in fields:
        if manifest.get(field) is not None:
            _required_text(manifest[field], f"source manifest {field}")


def _validate_manifest_dates(
    manifest: dict[str, Any], as_of: date, *, availability_evidence: Any = None,
    current_read_at: str | None = None,
) -> InformationEligibility:
    try:
        information = qualify_source_information(
            source_sha256=manifest["content_sha256"], published_date=manifest.get("published_date"),
            as_of=as_of, availability_evidence=availability_evidence,
        )
        validate_source_events(eligibility=information,
            original_retrieved_at=manifest.get("retrieved_at"), current_read_at=current_read_at)
    except SourceClockError as exc:
        raise CompanyWikiSourceError(str(exc)) from exc
    period_end = manifest.get("period_end")
    if period_end is not None and _iso_date(period_end, "source manifest period_end") > information.available_by:
        label = "publication" if information.published_date is not None else "verified availability"
        raise CompanyWikiSourceError(f"source manifest period ends after {label}")
    return information


def _validate_manifest_url(manifest: dict[str, Any]) -> None:
    source_url = _required_text(manifest.get("source_url"), "source manifest source_url")
    if not valid_source_url(source_url):
        raise CompanyWikiSourceError("source manifest source_url is invalid")


def _validate_manifest(
    manifest_value: Any, ref: dict[str, Any], as_of: date, *,
    availability_evidence: Any = None, current_read_at: str | None = None,
) -> tuple[dict[str, Any], InformationEligibility]:
    manifest = _object(manifest_value, "source_manifest")
    if set(manifest) != _MANIFEST_FIELDS:
        raise CompanyWikiSourceError("source manifest fields are invalid")
    _validate_manifest_identity(manifest, ref)
    _validate_manifest_metadata(manifest)
    published = _validate_manifest_dates(manifest, as_of,
        availability_evidence=availability_evidence, current_read_at=current_read_at)
    _validate_manifest_url(manifest)
    return manifest, published


def _validate_candidate(
    candidate_value: Any, ref: dict[str, Any], manifest: dict[str, Any],
) -> dict[str, Any]:
    candidate = _object(candidate_value, "source_candidate")
    if _FORBIDDEN_LOCATION_FIELDS & set(candidate):
        raise CompanyWikiSourceError("source candidate contains a storage location")
    candidate_ref = _validate_ref(candidate.get("source_ref"))
    _same(candidate_ref, ref, "source candidate source_ref")
    if candidate.get("status") == "source_candidate":
        expected_fields = {"status", "source_ref", "byte_verification", "document_kind",
                           "fiscal_year", "fiscal_period", "resolution_outcome", "download_events"}
        if set(candidate) != expected_fields:
            raise CompanyWikiSourceError("v2 source candidate fields are invalid")
        _same(candidate["byte_verification"], "pending_verified_open", "byte verification")
        for field in ("document_kind", "fiscal_year", "fiscal_period"):
            _same(candidate[field], manifest[field], f"source candidate {field}")
        outcome = candidate["resolution_outcome"]
        if not isinstance(outcome, str) or outcome not in _OUTCOMES:
            raise CompanyWikiSourceError("source candidate outcome invalid")
        _same(candidate["download_events"], int(outcome == "downloaded_new"), "download events")
        return candidate
    pairs = {
        "document_id": "document_id", "source_id": "source_id",
        "snapshot_sha256": "content_sha256", "byte_size": "byte_size",
        "mime_type": "mime_type", "title": "title",
        "document_kind": "document_kind", "fiscal_year": "fiscal_year",
        "published_date": "published_date", "https_url": "source_url",
        "retrieved_at": "retrieved_at", "provider": "provider",
        "provider_document_id": "provider_document_id",
    }
    for candidate_field, manifest_field in pairs.items():
        _same(candidate.get(candidate_field), manifest.get(manifest_field),
              f"source candidate {candidate_field}")
    if candidate.get("content_sha256") is not None:
        _same(candidate["content_sha256"], ref["content_sha256"],
              "source candidate content_sha256")
    identity = candidate.get("company_identity")
    if identity is not None:
        identity = _object(identity, "source candidate company_identity")
        for field in ("market", "security_id"):
            if identity.get(field) is not None:
                _same(identity[field], manifest.get(field),
                      f"source candidate company_identity.{field}")
    return candidate


def _diagnostic_status(
    supplied: Any, candidate: dict[str, Any], receipt: dict[str, Any],
) -> str:
    candidate_status = candidate.get("prompt_injection_status")
    for value in (supplied, candidate_status):
        if value is not None and value not in _PROMPT_INJECTION_STATUSES:
            raise CompanyWikiSourceError("invalid prompt_injection_status")
    review = receipt.get("review")
    if isinstance(review, dict):
        return review["status"]
    status = supplied if supplied is not None else candidate_status
    return status if status is not None else "not_reviewed"


def _display_title(manifest: dict[str, Any]) -> str:
    """Supply an RF display label without inventing an upstream title fact."""
    title = manifest.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return f"{manifest['document_kind']} [{manifest['source_id']}]"


def build_revenue_source_record_from_verified_read(
    *,
    source_ref: dict[str, Any],
    read_receipt: dict[str, Any],
    source_bytes: bytes,
    source_manifest: dict[str, Any],
    source_candidate: dict[str, Any],
    as_of_date: str,
    source_type: str,
    publisher: str,
    page_or_section: str,
    prompt_injection_status: str | None = "not_reviewed",
) -> dict[str, Any]:
    """Build a pathless, byte-verified source record with a read receipt."""
    ref = _validate_ref(source_ref)
    receipt = _validate_receipt(read_receipt, ref)
    if not isinstance(source_bytes, bytes):
        raise CompanyWikiSourceError("verified source bytes must be bytes")
    if len(source_bytes) != ref["byte_size"] or hashlib.sha256(source_bytes).hexdigest() != ref["content_sha256"]:
        raise CompanyWikiSourceError("verified source bytes SHA-256/size mismatch")
    as_of = _iso_date(as_of_date, "as_of_date")
    manifest, information = _validate_manifest(source_manifest, ref, as_of,
        availability_evidence=receipt.get("availability_evidence"), current_read_at=receipt["read_at"])
    candidate = _validate_candidate(source_candidate, ref, manifest)
    if source_type not in _SOURCE_TYPES:
        raise CompanyWikiSourceError(f"unsupported revenue source_type: {source_type}")
    publisher = _required_text(publisher, "publisher")
    locator = _required_text(page_or_section, "page_or_section")
    status = _diagnostic_status(prompt_injection_status, candidate, receipt)
    read_at = receipt["read_at"]
    # Original collection remains in the manifest; this capture is the actual
    # verified read, including a legitimate later historical-analysis replay.
    captured_date = _aware_datetime(read_at, "source capture timestamp").date().isoformat()
    capture = {
        "capture_schema_version": "1.0",
        "capture_method": "local_document",
        "tool_name": _TOOL_NAME,
        "tool_call_id": f"{ref['source_id']}|{read_at}",
        "captured_date": captured_date,
        "snapshot_sha256": ref["content_sha256"],
        "content_treatment": "untrusted_data_only",
        "prompt_injection_status": status,
    }
    capture["host_receipt"] = build_host_receipt(
        issuer="company-wiki",
        environment="host-runtime",
        tool_name=_TOOL_NAME,
        action="verified_read",
        event_sha256=ref["content_sha256"],
        timestamp=read_at,
    )
    capture["receipt_sha256"] = _canonical_sha256(capture)
    record = {
        "source_id": ref["source_id"],
        "source_type": source_type,
        "title": _display_title(manifest),
        "publisher": publisher,
        "url": manifest["source_url"],
        "published_date": information.published_date.isoformat() if information.published_date else None,
        "accessed_date": captured_date,
        "page_or_section": locator,
        "capture": capture,
        "company_wiki_trace": {
            "source_ref": dict(ref),
            "read_receipt": dict(receipt),
            "source_manifest": dict(manifest),
            "source_candidate": {
                "resolution_outcome": candidate.get("resolution_outcome"),
                "download_events": candidate.get("download_events"),
            },
        },
    }
    if receipt.get("availability_evidence") is not None:
        record["availability_evidence"] = dict(receipt["availability_evidence"])
    return record


__all__ = ["build_revenue_source_record_from_verified_read"]
