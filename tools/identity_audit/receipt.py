"""Frozen vocabulary and shared helpers for `identity-audit-receipt/1`.

Only the statuses and error codes published for this package appear here.  A
value that is unknown stays ``None`` -- it is never rewritten as ``""``, ``0``
or ``[]``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

P3_REQUEST_SCHEMA = "identity-audit-request/1"
P3_RECEIPT_SCHEMA = "identity-audit-receipt/1"

# Card section 5.2/5.4: the frozen per-run ceilings.
MAX_SOURCE_REFS = 500
MAX_EVIDENCE_SPANS = 5000
MAX_RECEIPT_BYTES = 16 * 1024 * 1024
MAX_REQUEST_BYTES = 16 * 1024 * 1024

# Top-level statuses (INTERFACES section 2: only the first five are allowed).
TOP_OK = "ok"
TOP_PARTIAL = "partial"
TOP_FAIL = "fail"
TOP_BLOCKED = "blocked"
TOP_UNAVAILABLE = "unavailable"
TOP_STATUSES = frozenset({TOP_OK, TOP_PARTIAL, TOP_FAIL, TOP_BLOCKED, TOP_UNAVAILABLE})

# Per-check statuses.  `source_availability_unknown` is the one card-specific
# value (section 5.3); it is a refusal to claim availability, never a pass.
CHECK_PASS = "pass"
CHECK_FAIL = "fail"
CHECK_NOT_APPLICABLE = "not_applicable"
CHECK_NOT_EVALUATED = "not_evaluated"
CHECK_AVAILABILITY_UNKNOWN = "source_availability_unknown"
CHECK_STATUSES = frozenset(
    {
        CHECK_PASS,
        CHECK_FAIL,
        CHECK_NOT_APPLICABLE,
        CHECK_NOT_EVALUATED,
        CHECK_AVAILABILITY_UNKNOWN,
    }
)

# Published error codes (INTERFACES section 3).
P3_REF_MISMATCH = "p3_ref_mismatch"
P3_BYTES_MISMATCH = "p3_bytes_mismatch"
P3_SPAN_UNGROUNDED = "p3_span_ungrounded"
P3_IDENTITY_CONFLICT = "p3_identity_conflict"
P3_PERIOD_CONFLICT = "p3_period_conflict"
P3_UNIT_MISMATCH = "p3_unit_mismatch"
P3_AVAILABILITY_FABRICATED = "p3_availability_fabricated"
INVALID_JSON = "invalid_json"
INVALID_ARGUMENT = "invalid_argument"
LIMIT_EXCEEDED = "limit_exceeded"
RECEIPT_TOO_LARGE = "receipt_too_large"
DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
NOT_CONFIGURED = "not_configured"

# The declarations this lane stands behind, printed in every receipt.
LIMITATIONS = [
    "synthetic fixture catalog only; the production catalog was never opened",
    "PDF/DOCX span offsets are not verified; only exact UTF-8 text/plain spans are",
    "unit tokens are compared as notation only: no conversion, no currency fill-in, no magnitude inference",
    "card section 5.4(5) names source_url/captured_at, which the current availability evidence does not carry; the observed keys are passed through verbatim",
    "publication dates are reported as observed manifest values and are never replaced by a retrieval time",
]

_RECEIPT_KEYS = (
    "schema_version",
    "status",
    "generated_at",
    "inputs",
    "counts",
    "limitations",
    "sources",
)


def utc_now() -> str:
    """One clock source for the whole receipt: UTC ISO-8601, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def receipt_keys() -> tuple[str, ...]:
    return _RECEIPT_KEYS


__all__ = [
    "CHECK_AVAILABILITY_UNKNOWN",
    "CHECK_FAIL",
    "CHECK_NOT_APPLICABLE",
    "CHECK_NOT_EVALUATED",
    "CHECK_PASS",
    "CHECK_STATUSES",
    "DEPENDENCY_UNAVAILABLE",
    "INVALID_ARGUMENT",
    "INVALID_JSON",
    "LIMIT_EXCEEDED",
    "LIMITATIONS",
    "MAX_EVIDENCE_SPANS",
    "MAX_RECEIPT_BYTES",
    "MAX_REQUEST_BYTES",
    "MAX_SOURCE_REFS",
    "NOT_CONFIGURED",
    "P3_AVAILABILITY_FABRICATED",
    "P3_BYTES_MISMATCH",
    "P3_IDENTITY_CONFLICT",
    "P3_PERIOD_CONFLICT",
    "P3_REF_MISMATCH",
    "P3_RECEIPT_SCHEMA",
    "P3_REQUEST_SCHEMA",
    "P3_SPAN_UNGROUNDED",
    "P3_UNIT_MISMATCH",
    "RECEIPT_TOO_LARGE",
    "TOP_BLOCKED",
    "TOP_FAIL",
    "TOP_OK",
    "TOP_PARTIAL",
    "TOP_STATUSES",
    "TOP_UNAVAILABLE",
    "canonical_json",
    "is_sha256",
    "receipt_keys",
    "sha256_hex",
    "utc_now",
]
