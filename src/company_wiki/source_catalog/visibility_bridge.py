"""WU-404: legacy metadata bridge + visibility separation (VIS-01..05).

Decision (candidate/verified/rejected) expresses evidence state; visibility
(legacy/shadow/active) + activation_epoch express reader rollout.  A v1
reader never sees shadow rows; a v2 reader only sees rows whose epoch
matches its snapshot.  The legacy bridge converts old acquisition/dayu_meta
payloads into in-memory v2 candidates — resolver SQL never reads those
containers directly.
"""

from __future__ import annotations

LEGACY_PROFILE_KEYS = ("acquisition", "dayu_meta")
SCHEMA_VERSION = "2.0"


def active_assertions(
    rows: list[dict],
    *,
    reader: str,
    current_epoch: str | None = None,
) -> list[dict]:
    """Filter assertion rows by reader visibility rules."""
    visible: list[dict] = []
    for row in rows:
        state = row.get("visibility_state", "legacy")
        if reader == "v1":
            if state == "legacy":
                visible.append(row)
            continue
        # v2 reader: only active rows in the current epoch
        if state == "active" and row.get("activation_epoch") == current_epoch:
            visible.append(row)
    return visible


def set_visibility(rows: list[dict], assertion_id: str, state: str) -> list[dict]:
    """VIS-04: flip visibility only; the record is never deleted."""
    if state not in {"legacy", "shadow", "active"}:
        raise ValueError(f"unknown visibility state {state!r}")
    updated = []
    for row in rows:
        if row.get("assertion_id") == assertion_id:
            row = dict(row)
            row["visibility_state"] = state
        updated.append(row)
    return updated


def legacy_bridge_candidate(legacy_payload: dict) -> dict:
    """Convert legacy acquisition/dayu_meta payload into an in-memory v2
    candidate (adapter-agnostic).  Missing facts stay missing; no guessing."""
    acquisition = legacy_payload.get("acquisition") or {}
    dayu = legacy_payload.get("dayu_meta") or {}
    merged = {**dayu, **acquisition}  # acquisition wins on conflicts
    candidate: dict = {
        "schema_version": SCHEMA_VERSION,
        "canonical_entity_id": merged.get("security_id"),
        "display_name": merged.get("company_name"),
        "market": merged.get("market"),
        "security_id": merged.get("security_id"),
        "document_kind": merged.get("form_type"),
        "fiscal_year": (
            str(merged["fiscal_year"])
            if merged.get("fiscal_year") is not None else None
        ),
        "period_end": merged.get("period_end"),
        "provider": merged.get("provider"),
        "provider_document_id": merged.get("provider_document_id"),
        "source_url": merged.get("source_url"),
        "filed_at": merged.get("filing_date"),
        "content_sha256": merged.get("content_sha256"),
        "adapter_id": "legacy_bridge_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "candidate",
        "evidence": {"source": {"origin": "legacy-bridge",
                                "source_pointer": "acquisition/dayu_meta"}},
    }
    return {k: v for k, v in candidate.items() if v is not None}
