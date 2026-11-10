"""Hashes, validation helpers, and ForecastInputError for revenue contracts.

This module contains the pure utilities that every other contract and validation
function depends on.  They import only the standard library so that nothing in
``contracts.*`` creates an import cycle with ``revenue_core``.
"""

from __future__ import annotations

import base64
import contextlib
import contextvars
import hashlib
import json
import math
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from contracts.source_clock import (
    InformationEligibility, SourceClockError, source_information_eligibility,
    validate_source_events,
)
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Error contract
# ---------------------------------------------------------------------------


class ForecastInputError(ValueError):
    """Raised when an input violates the auditable revenue contract."""


class MultiValidationError(ForecastInputError):
    """Carries many violations collected in a single collect-all validation pass."""

    def __init__(self, errors: list[tuple[str, str]]) -> None:
        self.errors = list(errors)
        grouped: dict[str, list[str]] = {}
        for gate, message in self.errors:
            grouped.setdefault(gate, []).append(message)
        lines = [f"{len(self.errors)} validation problem(s) found:"]
        for gate, messages in grouped.items():
            lines.append(f"[{gate}]")
            for message in messages:
                lines.append(f"  - {message}")
        super().__init__("\n".join(lines))


class Collector:
    """Accumulates validation violations tagged with the current gate label."""

    __slots__ = ("errors", "gate")

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.gate = "document"

    def add(self, message: str) -> None:
        self.errors.append((self.gate, message))


_COLLECTOR: contextvars.ContextVar[Collector | None] = contextvars.ContextVar(
    "forecast_input_collector", default=None
)


@contextlib.contextmanager
def collect_mode(collector: Collector):
    """Activate *collector* for the current context so ``require`` appends instead of raising."""
    token = _COLLECTOR.set(collector)
    try:
        yield
    finally:
        _COLLECTOR.reset(token)


def require(condition: Any, message: str) -> None:
    # Truthiness gate (bool in intent); data-validation callers pass
    # isinstance()/fullmatch() results, so the parameter is Any.
    """Raise ``ForecastInputError`` when *condition* is falsy.

    When a :class:`Collector` is active for the current context (set via
    :func:`collect_mode`), a falsy *condition* appends to that collector instead
    of raising, enabling a single collect-all pass. With no collector active the
    behavior is unchanged (raise on the first violation).
    """
    if condition:
        return
    collector = _COLLECTOR.get()
    if collector is not None:
        collector.add(message)
    else:
        raise ForecastInputError(message)


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def finite_number(value: Any, field: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{field} must be numeric",
    )
    number = float(value)
    require(math.isfinite(number), f"{field} must be finite")
    return number


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def parse_iso_date(value: Any, field: str) -> date:
    require(
        isinstance(value, str) and bool(value.strip()), f"{field} must be an ISO date"
    )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ForecastInputError(f"{field} must use YYYY-MM-DD") from exc


def period_year(value: Any, field: str) -> int:
    require(
        isinstance(value, str) and re.fullmatch(r"FY\d{4}", value) is not None,
        f"{field} must use strict FYyyyy format",
    )
    return int(value[2:])


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def validate_claim_ids(
    claim_ids: Any,
    claim_index: dict[str, dict[str, Any]],
    target_type: str,
    target_id: str,
    field: str,
    support_type: str | None = None,
) -> list[dict[str, Any]]:
    require(isinstance(claim_ids, list) and claim_ids, f"{field} requires claim_ids")
    require(
        len(claim_ids) == len(set(claim_ids)), f"{field} contains duplicate claim_ids"
    )
    claims: list[dict[str, Any]] = []
    for claim_id in claim_ids:
        require(claim_id in claim_index, f"unknown claim_id {claim_id} in {field}")
        claim = claim_index[claim_id]
        require(
            claim["target_type"] == target_type and claim["target_id"] == target_id,
            f"claim {claim_id} does not support {target_type}:{target_id}",
        )
        if support_type is not None:
            require(
                claim["support_type"] == support_type,
                f"claim {claim_id} must use {support_type}",
            )
        claims.append(claim)
    return claims


# ---------------------------------------------------------------------------
# Evidence-capture constants
# ---------------------------------------------------------------------------

EVIDENCE_CAPTURE_SCHEMA_VERSION = "1.0"

BLOCKED_HOSTS: set[str] = {
    "example.com",
    "www.example.com",
    "localhost",
    "127.0.0.1",
    "google.com",
    "www.google.com",
    "bing.com",
    "www.bing.com",
    "baidu.com",
    "www.baidu.com",
}

CAPTURE_METHODS: set[str] = {
    "browser_open",
    "api_response",
    "local_document",
    "structured_connector",
    "manual_open",
}

PROMPT_INJECTION_STATUSES: set[str] = {
    "not_reviewed", "not_detected", "detected_and_ignored",
}

HOST_RECEIPT_SCHEMA_VERSION = "1.0"


def build_host_receipt(
    *,
    issuer: str,
    environment: str,
    tool_name: str,
    action: str,
    event_sha256: str,
    timestamp: str,
) -> dict[str, Any]:
    """Build a machine-generated host attestation binding a tool event.

    Phase 6 A2: a self-declared ``tool_name``/``tool_call_id`` string is not an
    attestation.  A host receipt records who (issuer) in what environment
    executed which tool/action at what time, bound to a normalized event hash.
    """
    payload = {
        "host_receipt_schema_version": HOST_RECEIPT_SCHEMA_VERSION,
        "issuer": issuer,
        "environment": environment,
        "tool_name": tool_name,
        "action": action,
        "event_sha256": event_sha256,
        "timestamp": timestamp,
    }
    payload["receipt_sha256"] = canonical_sha256(payload)
    return payload


SIGNATURE_FIELDS = {"signature", "public_key_fingerprint"}


def _trusted_signer_public_keys() -> dict[str, bytes]:
    """Load the trusted Ed25519 signer key set (fail closed on absence/corruption).

    Source: ``REVENUE_TRUSTED_SIGNER_PUBLIC_KEYS`` env (JSON file path) or the
    repo default ``config/trusted_signer_public_keys.json``.  A missing file
    means *no* trusted signer — any signature is rejected.
    """
    env = os.environ.get("REVENUE_TRUSTED_SIGNER_PUBLIC_KEYS")
    path = (
        Path(env).expanduser()
        if env
        else Path(__file__).resolve().parents[2] / "config" / "trusted_signer_public_keys.json"
    )
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        keys: dict[str, bytes] = {}
        for item in data.get("public_keys", []):
            public_bytes = base64.b64decode(item["public_key"])
            keys[item.get("fingerprint", hashlib.sha256(public_bytes).hexdigest()[:32])] = (
                public_bytes
            )
        return keys
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _validate_host_signature(receipt: dict[str, Any]) -> None:
    """Verify an Ed25519 signature over the unsigned host receipt payload."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ForecastInputError(
            "capture host_receipt signature verification unavailable"
        ) from exc
    signature = receipt.get("signature")
    fingerprint = receipt.get("public_key_fingerprint")
    require(
        isinstance(signature, str) and re.fullmatch(r"[0-9a-f]{128}", signature),
        "invalid capture host_receipt signature",
    )
    require(
        isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{32}", fingerprint),
        "invalid capture host_receipt public_key_fingerprint",
    )
    assert isinstance(signature, str)  # narrow; require() above enforced
    assert isinstance(fingerprint, str)  # narrow; require() above enforced
    trusted = _trusted_signer_public_keys()
    require(
        fingerprint in trusted,
        f"capture host_receipt signer {fingerprint[:12]} is not trusted",
    )
    payload = {
        key: value
        for key, value in receipt.items()
        if key not in ("signature", "public_key_fingerprint")
    }
    message = canonical_sha256(payload).encode("ascii")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(trusted[fingerprint])
        public_key.verify(bytes.fromhex(signature), message)
    except (InvalidSignature, ValueError) as exc:
        raise ForecastInputError(
            "capture host_receipt signature verification failed"
        ) from exc


def validate_host_receipt(receipt: Any) -> None:
    """Validate a machine-generated host receipt.  Raises on any drift.

    A receipt may carry an optional ``signature`` + ``public_key_fingerprint``
    pair (R2.2): when present the signature must verify against a trusted
    Ed25519 key; when absent the receipt is a plain self-reported attestation
    (subject to the R2.1 capability gate at publication time).
    """
    require(isinstance(receipt, dict), "capture host_receipt must be an object")
    required = {
        "host_receipt_schema_version",
        "issuer",
        "environment",
        "tool_name",
        "action",
        "event_sha256",
        "timestamp",
        "receipt_sha256",
    }
    require(
        set(receipt) <= required | SIGNATURE_FIELDS,
        "invalid capture host_receipt fields",
    )
    require(required <= set(receipt), "invalid capture host_receipt fields")
    require(
        set(SIGNATURE_FIELDS) & set(receipt) in (set(), SIGNATURE_FIELDS),
        "capture host_receipt signature fields must come together",
    )
    require(
        receipt["host_receipt_schema_version"] == HOST_RECEIPT_SCHEMA_VERSION,
        "unsupported host receipt schema version",
    )
    for field in ("issuer", "environment", "tool_name", "action", "timestamp"):
        require(
            isinstance(receipt[field], str) and receipt[field].strip(),
            f"capture host_receipt.{field} is required",
        )
    require(
        isinstance(receipt["event_sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", receipt["event_sha256"]),
        "invalid capture host_receipt event_sha256",
    )
    payload = {
        key: value
        for key, value in receipt.items()
        if key != "receipt_sha256" and key not in SIGNATURE_FIELDS
    }
    require(
        receipt["receipt_sha256"] == canonical_sha256(payload),
        "capture host_receipt receipt hash mismatch",
    )
    if SIGNATURE_FIELDS & set(receipt):
        _validate_host_signature(receipt)


# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------


def valid_source_url(url: Any) -> bool:
    """Validate public provenance without changing or fetching its original URL."""
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    if host in BLOCKED_HOSTS or host.endswith(".example"):
        return False
    return "." in host


def validate_source_capture(
    source: dict[str, Any], as_of: date, *,
    information_eligibility: InformationEligibility | None = None,
) -> dict[str, Any]:
    """Validate a tool-linked source snapshot without claiming external fact truth."""
    source_id = source.get("source_id", "<unknown>")
    capture = source.get("capture")
    require(isinstance(capture, dict), f"{source_id}.capture is required")
    assert isinstance(capture, dict)  # narrow for mypy; require() already enforced
    required = {
        "capture_schema_version",
        "capture_method",
        "tool_name",
        "tool_call_id",
        "captured_date",
        "snapshot_sha256",
        "content_treatment",
        "prompt_injection_status",
        "host_receipt",
        "receipt_sha256",
    }
    require(set(capture) == required, f"invalid capture fields for {source_id}")
    require(
        capture["capture_schema_version"] == EVIDENCE_CAPTURE_SCHEMA_VERSION,
        f"unsupported capture schema for {source_id}",
    )
    require(
        capture["capture_method"] in CAPTURE_METHODS,
        f"unsupported capture method for {source_id}",
    )
    for field in ("tool_name", "tool_call_id"):
        require(
            isinstance(capture[field], str) and capture[field].strip(),
            f"{source_id}.capture.{field} is required",
        )
    validate_host_receipt(capture.get("host_receipt"))
    captured = parse_iso_date(
        capture["captured_date"], f"{source_id}.capture.captured_date"
    )
    try:
        information = information_eligibility or source_information_eligibility(source, as_of)
        trace = source.get("company_wiki_trace")
        read_receipt = trace.get("read_receipt") if isinstance(trace, dict) else None
        current_read_at = read_receipt.get("read_at") if isinstance(read_receipt, dict) else None
        validate_source_events(eligibility=information, capture_date=captured.isoformat(),
            current_read_at=current_read_at, host_timestamp=capture["host_receipt"]["timestamp"])
    except SourceClockError as exc:
        raise ForecastInputError(f"{source_id}: {exc}") from exc
    require(
        source.get("accessed_date") == capture["captured_date"],
        f"source accessed_date/capture date mismatch: {source_id}",
    )
    require(
        isinstance(capture["snapshot_sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", capture["snapshot_sha256"]),
        f"invalid source snapshot hash: {source_id}",
    )
    require(
        capture["content_treatment"] == "untrusted_data_only",
        f"source content must be treated as untrusted data: {source_id}",
    )
    require(
        capture["prompt_injection_status"] in PROMPT_INJECTION_STATUSES,
        f"invalid prompt-injection status: {source_id}",
    )
    payload = {key: value for key, value in capture.items() if key != "receipt_sha256"}
    require(
        capture["receipt_sha256"] == canonical_sha256(payload),
        f"source capture receipt hash mismatch: {source_id}",
    )
    return dict(capture)
