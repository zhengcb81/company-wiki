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


def canonical_hash(fields: dict) -> str:
    """Deterministic hash over semantic fields only (non-semantic excluded)."""
    semantic = {
        k: v for k, v in fields.items()
        if k not in NON_SEMANTIC and v is not None
    }
    payload = json.dumps(semantic, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
