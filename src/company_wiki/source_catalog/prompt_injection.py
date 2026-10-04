"""Optional prompt-injection diagnostics stored with a source document.

The review-shaped JSON field is kept for compatibility with existing catalog
rows. Its status is descriptive only: no signature, reviewer receipt, TTL,
or storage failure can authorize or block source reads and exports.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from typing import Any

PROMPT_INJECTION_REVIEW_KEY = "prompt_injection_review"
PROMPT_INJECTION_REVIEW_AUDIT_KEY = "prompt_injection_review_audit"
PROMPT_INJECTION_REVIEW_SCHEMA_VERSION = "1.0"
PROMPT_INJECTION_REVIEW_STATUSES = frozenset(
    {"not_detected", "detected_and_ignored"}
)
STATE_DOMAIN_REVIEW = "review"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CAS_MAX_ATTEMPTS = 5


class PromptInjectionReviewError(ValueError):
    """Raised when an optional diagnostic cannot be written or read."""


def _require_sha256(value: str | None, field: str) -> None:
    if value is None or not _SHA256_RE.fullmatch(value):
        raise PromptInjectionReviewError(
            f"{field} must be a lowercase SHA-256"
        )


def _validate_review_inputs(
    *,
    document_id: str,
    status: str,
    reviewer: str,
    evidence_sha256: str,
    schema_version: str,
    source_sha256: str | None,
    policy_hash: str | None,
) -> None:
    if not document_id or not document_id.strip():
        raise PromptInjectionReviewError("document_id must be non-empty")
    if status not in PROMPT_INJECTION_REVIEW_STATUSES:
        raise PromptInjectionReviewError(
            f"status must be one of {sorted(PROMPT_INJECTION_REVIEW_STATUSES)}, "
            f"got {status!r}"
        )
    if not reviewer or not reviewer.strip():
        raise PromptInjectionReviewError("reviewer must be non-empty")
    if schema_version != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
        raise PromptInjectionReviewError(
            f"schema_version must be {PROMPT_INJECTION_REVIEW_SCHEMA_VERSION!r}"
        )
    _require_sha256(evidence_sha256, "evidence_sha256")
    _require_sha256(source_sha256, "source_sha256")
    _require_sha256(policy_hash, "policy_hash")


def _parse_metadata(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (json.JSONDecodeError, TypeError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


def record_prompt_injection_review(
    connection: Any,
    document_id: str,
    *,
    status: str,
    reviewer: str,
    evidence_sha256: str,
    now: str,
    schema_version: str = PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
    source_sha256: str | None = None,
    policy_hash: str | None = None,
    evidence_payload: str | bytes | None = None,
    state_domain: str | None = None,
) -> dict[str, Any]:
    """Store a source-bound diagnostic, without human authorization gates.

    The payload and its hash are checked so the reported scanner status is
    tied to the text examined. This status is never a prerequisite for
    querying, reading, exporting, or deriving a summary from the source.
    """
    _validate_review_inputs(
        document_id=document_id,
        status=status,
        reviewer=reviewer,
        evidence_sha256=evidence_sha256,
        schema_version=schema_version,
        source_sha256=source_sha256,
        policy_hash=policy_hash,
    )
    if state_domain is not None and state_domain != STATE_DOMAIN_REVIEW:
        raise PromptInjectionReviewError(
            f"state_domain must be {STATE_DOMAIN_REVIEW!r}"
        )
    if evidence_payload is None:
        raise PromptInjectionReviewError(
            "evidence_payload must be provided to bind the diagnostic"
        )
    payload_bytes = (
        evidence_payload.encode("utf-8")
        if isinstance(evidence_payload, str)
        else bytes(evidence_payload)
    )
    if hashlib.sha256(payload_bytes).hexdigest() != evidence_sha256:
        raise PromptInjectionReviewError(
            "evidence_sha256 does not match sha256(evidence_payload)"
        )

    from .prompt_injection_guard import scan_text

    text = (
        evidence_payload.decode("utf-8", "replace")
        if isinstance(evidence_payload, bytes)
        else evidence_payload
    )
    scan = scan_text(text)
    if scan.status != status:
        raise PromptInjectionReviewError(
            f"declared status {status!r} contradicts scanner result {scan.status!r}"
        )

    receipt: dict[str, Any] = {
        "schema_version": schema_version,
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": now,
        "evidence_sha256": evidence_sha256,
        "source_sha256": source_sha256,
        "policy_hash": policy_hash,
        "state_domain": STATE_DOMAIN_REVIEW,
        "writer_pid": str(os.getpid()),
        "writer_write_at": now,
        "writer_identity_note": "diagnostic label; not an authorization",
        "matches": list(scan.matches),
    }
    audit_entry = {
        "writer_pid": str(os.getpid()),
        "write_at": now,
        "evidence_sha256": evidence_sha256,
        "source_sha256": source_sha256,
        "policy_hash": policy_hash,
        "status": status,
    }
    try:
        for _attempt in range(_CAS_MAX_ATTEMPTS):
            row = connection.execute(
                "SELECT metadata_json FROM documents WHERE document_id=?",
                (document_id,),
            ).fetchone()
            if row is None:
                raise PromptInjectionReviewError(f"unknown document {document_id}")
            old_raw = row[0]
            metadata = _parse_metadata(old_raw)
            audit = metadata.get(PROMPT_INJECTION_REVIEW_AUDIT_KEY)
            if not isinstance(audit, list):
                audit = []
            metadata[PROMPT_INJECTION_REVIEW_AUDIT_KEY] = audit + [
                dict(audit_entry, seq=len(audit) + 1)
            ]
            metadata[PROMPT_INJECTION_REVIEW_KEY] = receipt
            new_raw = json.dumps(metadata, ensure_ascii=False)
            if old_raw is None:
                cursor = connection.execute(
                    "UPDATE documents SET metadata_json=? WHERE document_id=? "
                    "AND metadata_json IS NULL",
                    (new_raw, document_id),
                )
            else:
                cursor = connection.execute(
                    "UPDATE documents SET metadata_json=? WHERE document_id=? "
                    "AND metadata_json=?",
                    (new_raw, document_id, old_raw),
                )
            if cursor.rowcount == 1:
                connection.commit()
                return receipt
        connection.rollback()
        raise PromptInjectionReviewError(
            f"concurrent write conflict: document {document_id}"
        )
    except sqlite3.Error as exc:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
        raise PromptInjectionReviewError(
            f"store busy/lock timeout: {type(exc).__name__}: {exc}"
        ) from exc


def read_prompt_injection_review(
    store: Any, document_id: str,
) -> dict[str, Any] | None:
    """Read an old or current diagnostic record; absence/malformed means none.

    The result is descriptive metadata. Callers must never use it as a source
    access or external-model authorization decision.
    """
    try:
        row = store.fetchone(
            "SELECT metadata_json FROM documents WHERE document_id=?",
            (document_id,),
        )
    except sqlite3.Error as exc:
        raise PromptInjectionReviewError(
            f"store busy/lock timeout: {type(exc).__name__}: {exc}"
        ) from exc
    if row is None:
        return None
    try:
        metadata = json.loads(row[0] or "{}")
        if not isinstance(metadata, dict):
            return None
        receipt = metadata.get(PROMPT_INJECTION_REVIEW_KEY)
        if not isinstance(receipt, dict):
            return None
        if receipt.get("schema_version") != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
            return None
        if receipt.get("status") not in PROMPT_INJECTION_REVIEW_STATUSES:
            return None
        if receipt.get("state_domain") != STATE_DOMAIN_REVIEW:
            return None
        return receipt
    except (json.JSONDecodeError, TypeError, RecursionError, UnicodeDecodeError):
        return None


__all__ = [
    "PROMPT_INJECTION_REVIEW_AUDIT_KEY",
    "PROMPT_INJECTION_REVIEW_KEY",
    "PROMPT_INJECTION_REVIEW_SCHEMA_VERSION",
    "PROMPT_INJECTION_REVIEW_STATUSES",
    "PromptInjectionReviewError",
    "STATE_DOMAIN_REVIEW",
    "read_prompt_injection_review",
    "record_prompt_injection_review",
]
