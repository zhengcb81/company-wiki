"""Opt-in exact-version source read through company-wiki's binary CLI.

The caller supplies a pathless SourceRef and a catalog configuration path.
Only the catalog chooses a physical location; this adapter checks its returned
bytes, receipt, identity, period and information date before use by RF.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from source_period_semantics import valid_fiscal_year
from filing_upstream_cause import validated_source_failure_reason
from contracts.source_clock import (
    SourceClockError, qualify_source_information, validate_availability_evidence,
    validate_source_events,
)


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_REF_FIELDS = frozenset({
    "schema_version", "document_id", "source_id", "content_sha256",
    "byte_size", "mime_type",
})
_RECEIPT_FIELDS = frozenset({
    "schema_version", "status", "document_id", "source_id",
    "content_sha256", "byte_size", "policy_sha256",
    "source_read_policy_sha256", "read_at", "manifest", "review",
})
_MANIFEST_FIELDS = frozenset({
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
    "title", "document_kind", "published_date", "source_url", "retrieved_at",
    "collector_name", "collector_version", "canonical_entity_id", "display_name",
    "market", "security_id", "fiscal_year", "fiscal_period", "period_end",
    "form_type", "provider", "provider_document_id", "language",
})
_REVIEW_FIELDS = frozenset({
    "status", "source_sha256", "evidence_sha256", "policy_hash", "reviewed_at",
})
_REVIEW_STATUSES = frozenset({
    "not_detected", "detected_and_ignored", "not_reviewed",
})
_REFUSAL_STATUSES = frozenset({
    "not_found", "not_indexed", "unavailable", "blocked", "ambiguous",
})
_REFUSAL_REASON = re.compile(r"[a-z][a-z0-9_]{0,80}\Z")


class SourceVersionTransportError(RuntimeError):
    """An exact source version could not be opened and verified."""

    def __init__(self, message: str, *, source_failure_reason: str | None = None):
        super().__init__(message)
        self.source_failure_reason = validated_source_failure_reason(source_failure_reason)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SourceVersionTransportError("duplicate JSON key in source receipt")
        result[key] = value
    return result


def _reject_nonfinite(_value: str) -> None:
    raise SourceVersionTransportError("nonfinite JSON number in source receipt")


def _one_json_line(raw: bytes) -> dict[str, Any]:
    try:
        decoded = raw.decode("utf-8", errors="strict")
        if not decoded.endswith("\n") or len(decoded.splitlines()) != 1:
            raise SourceVersionTransportError("source receipt must be one JSON line")
        value = json.loads(
            decoded, object_pairs_hook=_unique_pairs, parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SourceVersionTransportError("source receipt is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SourceVersionTransportError("source receipt must be a JSON object")
    return value


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise SourceVersionTransportError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SourceVersionTransportError(f"{field} must be an ISO date") from exc


def _check_datetime_zone(parsed: datetime, field: str, require_utc: bool) -> None:
    offset = parsed.utcoffset()
    if parsed.tzinfo is None or offset is None:
        raise SourceVersionTransportError(f"{field} must be timezone-aware")
    if require_utc and offset.total_seconds() != 0:
        raise SourceVersionTransportError(f"{field} must be UTC")


def _datetime(value: Any, field: str, *, require_utc: bool = False) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SourceVersionTransportError(f"{field} must be timezone-aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceVersionTransportError(f"{field} must be timezone-aware") from exc
    _check_datetime_zone(parsed, field, require_utc)
    return parsed.astimezone(UTC)


def _valid_ref_text(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value.strip()) and value == value.strip()
        and all(ord(char) >= 32 for char in value)
    )


def _validate_ref_identifiers(source_ref: dict[str, Any]) -> None:
    for field in ("document_id", "source_id", "mime_type"):
        if not _valid_ref_text(source_ref[field]):
            raise SourceVersionTransportError(f"source_ref {field} is invalid")


def _validate_ref(source_ref: dict[str, Any]) -> None:
    if not isinstance(source_ref, dict) or set(source_ref) != _REF_FIELDS:
        raise SourceVersionTransportError("source_ref fields are not exact")
    if source_ref["schema_version"] != "2.0":
        raise SourceVersionTransportError("source_ref schema is unsupported")
    _validate_ref_identifiers(source_ref)
    if not _valid_sha256(source_ref["content_sha256"]):
        raise SourceVersionTransportError("source_ref SHA-256 is invalid")
    size = source_ref["byte_size"]
    if type(size) is not int or size < 0:
        raise SourceVersionTransportError("source_ref byte_size is invalid")


def _run_reader(
    source_ref: dict[str, Any], config: Path, timeout_seconds: float, *,
    source_reader_receipt_version: str = "2.1",
) -> subprocess.CompletedProcess[bytes]:
    command = [
        sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli",
        "--config", str(config),
        "--document-id", source_ref["document_id"],
        "--source-id", source_ref["source_id"],
        "--content-sha256", source_ref["content_sha256"],
        "--purpose", "filing_reuse",
    ]
    if source_reader_receipt_version == "2.2":
        command.append("--include-availability-evidence")
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]
    try:
        return subprocess.run(
            command, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout_seconds, check=False,
            shell=False, creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SourceVersionTransportError("source reader CLI unavailable", source_failure_reason="reader_unavailable") from exc


def _validate_review_shape(review: dict[str, Any]) -> None:
    if set(review) != _REVIEW_FIELDS:
        raise SourceVersionTransportError("source receipt review shape invalid")
    if review["status"] not in _REVIEW_STATUSES:
        raise SourceVersionTransportError("source receipt review status invalid")


def _validate_review_hashes(review: dict[str, Any]) -> None:
    for field in ("evidence_sha256", "policy_hash"):
        if review[field] is not None and not _valid_sha256(review[field]):
            raise SourceVersionTransportError(f"source receipt review {field} invalid")


def _validate_review(review: Any, source_ref: dict[str, Any]) -> None:
    # The review is diagnostic. It is not an authorization or a precondition.
    if review is None:
        return
    if not isinstance(review, dict):
        raise SourceVersionTransportError("source receipt review shape invalid")
    _validate_review_shape(review)
    if review["source_sha256"] is not None and (
        review["source_sha256"] != source_ref["content_sha256"]
    ):
        raise SourceVersionTransportError("source receipt review source mismatch")
    _validate_review_hashes(review)
    if review["reviewed_at"] is not None:
        _datetime(review["reviewed_at"], "source receipt review reviewed_at")


def _validate_manifest_identity(
    manifest: dict[str, Any], source_ref: dict[str, Any],
) -> None:
    fields = ("document_id", "source_id", "content_sha256", "byte_size", "mime_type")
    for field in fields:
        if type(manifest[field]) is not type(source_ref[field]) or (
            manifest[field] != source_ref[field]
        ):
            raise SourceVersionTransportError(f"source manifest {field} mismatch", source_failure_reason="source_identity_mismatch")


def _validate_manifest_period(
    manifest: dict[str, Any], as_of: date, fiscal_year: int | None, *,
    availability_evidence: Any = None, current_read_at: str | None = None,
) -> None:
    if not valid_fiscal_year(manifest["document_kind"], manifest["fiscal_year"]) or (
        type(manifest["fiscal_year"]) is not type(fiscal_year) or manifest["fiscal_year"] != fiscal_year
    ):
        raise SourceVersionTransportError("source manifest fiscal_year mismatch", source_failure_reason="fiscal_year_mismatch")
    try:
        information = qualify_source_information(
            source_sha256=manifest["content_sha256"], published_date=manifest["published_date"],
            as_of=as_of, availability_evidence=availability_evidence,
        )
        validate_source_events(eligibility=information,
            original_retrieved_at=manifest["retrieved_at"], current_read_at=current_read_at)
    except SourceClockError as exc:
        raise SourceVersionTransportError(str(exc), source_failure_reason=validated_source_failure_reason(str(exc).partition(":")[0])) from exc
    period_end = manifest["period_end"]
    if period_end is not None and _date(period_end, "source manifest period_end") > information.available_by:
        label = "publication" if information.published_date is not None else "verified availability"
        raise SourceVersionTransportError(f"source manifest period ends after {label}")


def _validate_manifest(
    manifest: Any, source_ref: dict[str, Any], as_of: date, fiscal_year: int | None, *,
    availability_evidence: Any = None, current_read_at: str | None = None,
) -> dict[str, Any]:
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
        raise SourceVersionTransportError("source receipt manifest fields invalid")
    _validate_manifest_identity(manifest, source_ref)
    _validate_manifest_period(manifest, as_of, fiscal_year,
        availability_evidence=availability_evidence, current_read_at=current_read_at)
    return manifest


def _validate_timeout(timeout_seconds: float) -> None:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise SourceVersionTransportError("source reader timeout is invalid")
    if timeout_seconds <= 0 or not math.isfinite(timeout_seconds):
        raise SourceVersionTransportError("source reader timeout is invalid")


def _validate_open_request(
    source_ref: dict[str, Any], catalog_config: Path, as_of_date: str,
    expected_fiscal_year: int | None, timeout_seconds: float,
) -> date:
    _validate_ref(source_ref)
    if not isinstance(catalog_config, Path) or not catalog_config.is_absolute():
        raise SourceVersionTransportError("catalog_config must be an absolute Path")
    _validate_timeout(timeout_seconds)
    as_of = _date(as_of_date, "as_of_date")
    if expected_fiscal_year is not None and (type(expected_fiscal_year) is not int or expected_fiscal_year < 1):
        raise SourceVersionTransportError("expected_fiscal_year is invalid")
    return as_of


def _valid_refusal(refusal: dict[str, Any]) -> bool:
    return (
        set(refusal) == {"schema_version", "status", "reason"}
        and isinstance(refusal["schema_version"], str)
        and refusal["schema_version"] in {"2.1", "2.2"}
        and isinstance(refusal["status"], str)
        and refusal["status"] in _REFUSAL_STATUSES
        and isinstance(refusal["reason"], str)
        and _REFUSAL_REASON.fullmatch(refusal["reason"]) is not None
    )


def _raise_reader_refusal(opened: subprocess.CompletedProcess[bytes]) -> None:
    if opened.stdout:
        raise SourceVersionTransportError("source reader emitted partial bytes on refusal")
    try:
        refusal = _one_json_line(opened.stderr)
    except SourceVersionTransportError:
        raise SourceVersionTransportError("source reader refused current version") from None
    if _valid_refusal(refusal):
        reason = validated_source_failure_reason(refusal["reason"])
        message = f"source reader refused: {reason}" if reason is not None else "source reader refused current version"
        raise SourceVersionTransportError(message, source_failure_reason=reason)
    raise SourceVersionTransportError("source reader refused current version")


def validate_source_reader_receipt_version(value: Any) -> str:
    if not isinstance(value, str) or value not in {"2.1", "2.2"}:
        raise SourceVersionTransportError("source reader receipt capability must be 2.1 or 2.2")
    return value


def _validate_receipt_shape(receipt: dict[str, Any], *, source_reader_receipt_version: str = "2.1") -> None:
    expected = _RECEIPT_FIELDS if source_reader_receipt_version == "2.1" else _RECEIPT_FIELDS | {"availability_evidence"}
    if set(receipt) != expected or receipt.get("schema_version") != source_reader_receipt_version or receipt.get("status") != "ok":
        raise SourceVersionTransportError("source receipt fields/status invalid")


def _validate_receipt_identity(
    receipt: dict[str, Any], source_ref: dict[str, Any],
) -> None:
    fields = ("document_id", "source_id", "content_sha256", "byte_size")
    for field in fields:
        if type(receipt[field]) is not type(source_ref[field]) or (
            receipt[field] != source_ref[field]
        ):
            raise SourceVersionTransportError(f"source receipt {field} mismatch", source_failure_reason="source_identity_mismatch")


def _validate_receipt_policies(receipt: dict[str, Any]) -> None:
    fields = ("policy_sha256", "source_read_policy_sha256")
    for field in fields:
        if not _valid_sha256(receipt[field]):
            raise SourceVersionTransportError(f"source receipt {field} invalid")


def _validate_success_receipt(
    receipt: dict[str, Any], source_ref: dict[str, Any], as_of: date,
    fiscal_year: int | None, *, source_reader_receipt_version: str = "2.1",
) -> dict[str, Any]:
    _validate_receipt_shape(receipt, source_reader_receipt_version=source_reader_receipt_version)
    _validate_receipt_identity(receipt, source_ref)
    _validate_receipt_policies(receipt)
    _datetime(receipt["read_at"], "source receipt read_at", require_utc=True)
    _validate_review(receipt["review"], source_ref)
    try:
        validate_availability_evidence(receipt.get("availability_evidence"), source_ref["content_sha256"])
    except SourceClockError as exc:
        raise SourceVersionTransportError(str(exc), source_failure_reason=validated_source_failure_reason(str(exc).partition(":")[0])) from exc
    return _validate_manifest(receipt["manifest"], source_ref, as_of, fiscal_year,
        availability_evidence=receipt.get("availability_evidence"), current_read_at=receipt["read_at"])


def _verify_bytes(body: bytes, source_ref: dict[str, Any]) -> None:
    if len(body) != source_ref["byte_size"] or (
        hashlib.sha256(body).hexdigest() != source_ref["content_sha256"]
    ):
        raise SourceVersionTransportError("source bytes SHA-256/size mismatch", source_failure_reason="source_bytes_mismatch")


def open_source_version_v2(
    *, source_ref: dict[str, Any], catalog_config: Path,
    as_of_date: str, expected_fiscal_year: int | None,
    timeout_seconds: float = 30.0, source_reader_receipt_version: str = "2.1",
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Return verified source bytes, a pathless receipt, and a same-call manifest."""
    version = validate_source_reader_receipt_version(source_reader_receipt_version)
    as_of = _validate_open_request(
        source_ref, catalog_config, as_of_date, expected_fiscal_year, timeout_seconds,
    )
    reader_options = {"source_reader_receipt_version": version} if version == "2.2" else {}
    opened = _run_reader(source_ref, catalog_config, timeout_seconds, **reader_options)
    if opened.returncode != 0:
        _raise_reader_refusal(opened)
    receipt = _one_json_line(opened.stderr)
    manifest = _validate_success_receipt(
        receipt, source_ref, as_of, expected_fiscal_year, source_reader_receipt_version=version,
    )
    _verify_bytes(opened.stdout, source_ref)
    bare_receipt = {key: value for key, value in receipt.items() if key != "manifest"}
    return opened.stdout, bare_receipt, manifest


__all__ = ["SourceVersionTransportError", "open_source_version_v2"]
