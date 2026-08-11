"""FC-905-a: prompt-injection review receipt (per document).

The capture safety status must come from an explicit scanner/reviewer
receipt, never from a consumer's assumption.  The receipt lives in
``documents.metadata_json["prompt_injection_review"]``:

    {"status": "not_detected" | "detected_and_ignored",
     "reviewer": <non-empty>, "reviewed_at": <UTC>,
     "evidence_sha256": <64-hex>, "schema_version": "1.0"}

Absent receipt == ``not_reviewed`` (the envelope reports that explicitly;
consumers block per policy — FC-905-b).  The writer validates fail-closed.
"""

from __future__ import annotations

import json
import re
from typing import Any

PROMPT_INJECTION_REVIEW_KEY = "prompt_injection_review"
PROMPT_INJECTION_REVIEW_SCHEMA_VERSION = "1.0"
PROMPT_INJECTION_REVIEW_STATUSES = frozenset(
    {"not_detected", "detected_and_ignored"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PromptInjectionReviewError(ValueError):
    """Raised when a review receipt cannot be written (fail closed)."""


def record_prompt_injection_review(
    connection: Any,
    document_id: str,
    *,
    status: str,
    reviewer: str,
    evidence_sha256: str,
    now: str,
    schema_version: str = PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
) -> dict[str, str]:
    """Write (or overwrite) the document's prompt-injection review receipt.

    ``connection`` must be a sqlite3.Connection (caller owns commit).
    Validates fail-closed: status enum, non-empty reviewer, sha256 evidence,
    non-empty document_id, schema version.
    """
    if not document_id or not document_id.strip():
        raise PromptInjectionReviewError("document_id must be non-empty")
    if status not in PROMPT_INJECTION_REVIEW_STATUSES:
        raise PromptInjectionReviewError(
            f"status must be one of "
            f"{sorted(PROMPT_INJECTION_REVIEW_STATUSES)}, got {status!r}")
    if not reviewer or not reviewer.strip():
        raise PromptInjectionReviewError("reviewer must be non-empty")
    if not _SHA256_RE.fullmatch(evidence_sha256):
        raise PromptInjectionReviewError(
            "evidence_sha256 must be a lowercase SHA-256")
    if schema_version != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
        raise PromptInjectionReviewError(
            f"schema_version must be "
            f"{PROMPT_INJECTION_REVIEW_SCHEMA_VERSION!r}")
    row = connection.execute(
        "SELECT metadata_json FROM documents WHERE document_id=?",
        (document_id,),
    ).fetchone()
    if row is None:
        raise PromptInjectionReviewError(f"unknown document {document_id}")
    try:
        metadata = json.loads(row[0] or "{}")
        if not isinstance(metadata, dict):
            metadata = {}
    except json.JSONDecodeError:
        metadata = {}
    receipt = {
        "schema_version": schema_version,
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": now,
        "evidence_sha256": evidence_sha256,
    }
    metadata[PROMPT_INJECTION_REVIEW_KEY] = receipt
    connection.execute(
        "UPDATE documents SET metadata_json=? WHERE document_id=?",
        (json.dumps(metadata, ensure_ascii=False), document_id),
    )
    return receipt


def read_prompt_injection_review(
    store: Any, document_id: str,
) -> dict[str, Any] | None:
    """Read the document's review receipt, or None when not reviewed.

    ``store`` must expose ``fetchone(sql, params)`` (CatalogStore-compatible).
    A malformed receipt (bad schema/status) fails closed as ``not_reviewed``
    rather than being trusted.
    """
    row = store.fetchone(
        "SELECT metadata_json FROM documents WHERE document_id=?",
        (document_id,),
    )
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
        return receipt
    except json.JSONDecodeError:
        return None
