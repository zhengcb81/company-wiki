"""WU-401: NormalizedFilingMetadata v2 — product implementation.

Ported from the frozen Phase-2 contract (audit_review/2026-08-09_data_lake_
refactor_plan/tools/normalized_meta.py, ADR WU-202) with the same rules:
strong identity, fail-closed unknown versions/kinds, resolvable evidence
pointers, metadata_sha256 binding, canonical hash excluding non-semantic
fields.  Adapter-specific raw payloads stay immutable and are never read
by the resolver.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date

SUPPORTED_SCHEMA_VERSIONS = {"1.0", "2.0"}
KNOWN_KINDS = {"annual", "quarterly", "semi_annual", "regulatory_filing"}

REQUIRED_FIELDS = {
    "canonical_entity_id",
    "market",
    "security_id",
    "document_kind",
    "fiscal_year",
    "period_end",
    "content_sha256",
    "provider",
    "provider_document_id",
    "adapter_id",
    "adapter_version",
    "normalization_status",
}

DATE_FIELDS = {"period_end", "published_at", "filed_at", "accepted_at"}
HASH_FIELDS = {"content_sha256", "metadata_sha256"}
# non-semantic fields excluded from the canonical hash
NON_SEMANTIC = {
    "root_id", "canonical_path", "scanned_at", "location_id",
    "metadata_sha256",  # self-reference: the hash must not include itself
}

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_iso(value: str) -> bool:
    if not isinstance(value, str) or not _ISO_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_normalized_filing(fields: dict) -> tuple[bool, list[str]]:
    """Return (ok, reasons).  Fail-closed on anything questionable."""
    reasons: list[str] = []
    if not isinstance(fields, dict):
        return False, ["fields must be an object"]

    version = fields.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        reasons.append(f"schema_version {version!r} unsupported (fail closed)")

    # identity: strong fields required
    strong = ("canonical_entity_id", "market", "security_id")
    missing_identity = [f for f in strong if not fields.get(f)]
    if missing_identity:
        reasons.append(
            f"identity incomplete (missing {missing_identity}); display_name "
            "alone is never strong identity"
        )

    for field in ("document_kind", "fiscal_year", "period_end", "content_sha256"):
        if not fields.get(field):
            reasons.append(f"{field} missing (not capture-ready)")

    kind = fields.get("document_kind")
    if kind and kind not in KNOWN_KINDS:
        reasons.append(f"document_kind {kind!r} unknown (fail closed)")

    for field in DATE_FIELDS:
        value = fields.get(field)
        if value is not None and not _valid_iso(str(value)):
            reasons.append(f"{field} {value!r} is not a valid ISO date")

    for field in HASH_FIELDS:
        value = fields.get(field)
        if value is not None and (not isinstance(value, str) or len(value) != 64):
            reasons.append(f"{field} must be a 64-hex sha256")

    # metadata_sha256 binds the semantic fields: a mismatch means tampering
    metadata_hash = fields.get("metadata_sha256")
    if metadata_hash and metadata_hash != canonical_hash(fields):
        reasons.append(
            "metadata_sha256 does not match canonical semantic hash "
            "(tampered metadata, fail closed)"
        )

    evidence = fields.get("evidence") or {}
    if evidence:
        if not isinstance(evidence, dict):
            reasons.append("evidence must be an object")
        else:
            for field, entry in evidence.items():
                if not isinstance(entry, dict):
                    reasons.append(f"evidence[{field}] must be an object")
                    continue
                if not entry.get("origin"):
                    reasons.append(f"evidence[{field}] missing origin")
                pointer = entry.get("source_pointer")
                if pointer and not isinstance(pointer, str):
                    reasons.append(f"evidence[{field}] source_pointer must be str")
                elif pointer:
                    # the pointer's root segment must resolve to a real field
                    root = pointer.split(".")[0]
                    if root not in fields:
                        reasons.append(
                            f"evidence[{field}] source_pointer {pointer!r} does "
                            "not resolve to any field (broken pointer)"
                        )
                asserted = entry.get("asserted_value")
                if asserted is not None and asserted != fields.get(field):
                    reasons.append(
                        f"evidence[{field}] asserted_value {asserted!r} conflicts "
                        f"with field {fields.get(field)!r} (conflict)"
                    )

    adapter_ok = fields.get("adapter_id") and fields.get("adapter_version")
    if not adapter_ok:
        reasons.append("adapter_id/adapter_version missing (v2 requirement)")

    return (len(reasons) == 0, reasons)


def canonical_hash(fields: dict) -> str:
    """Deterministic hash over semantic fields only (non-semantic excluded)."""
    semantic = {
        k: v for k, v in fields.items()
        if k not in NON_SEMANTIC and v is not None
    }
    payload = json.dumps(semantic, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
