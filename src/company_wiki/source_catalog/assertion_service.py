"""Source metadata assertion service — append-only identity enrichment for legacy files.

Contracts:
- Immutable: once written, never updated or deleted.
- Correction: new assertion with ``supersedes_assertion_id``.
- Hash-bound: assertion invalidated if content_sha256 changes.
- Only ``verified`` assertions may be consumed by the resolver.
- ``candidate`` assertions exist only as review hints.
- ``verified`` means source identity/extraction quality passes; NOT investment conclusion.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .store import CatalogStore, canonical_json

ASSERTION_SCHEMA_VERSION = "1.0.0"
ASSERTION_REQUIRED_FIELDS = frozenset(
    {"source_id", "document_id", "content_sha256", "evidence_basis", "decision"}
)


def _build_assertion(
    *,
    source_id: str,
    document_id: str,
    content_sha256: str,
    entity: str | None = None,
    market: str | None = None,
    security_id: str | None = None,
    document_kind: str | None = None,
    form_type: str | None = None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    provider: str | None = None,
    provider_document_id: str | None = None,
    source_url: str | None = None,
    filing_date: str | None = None,
    evidence_basis: str,
    evidence_json: dict[str, Any] | None = None,
    decision: str,
    supersedes_assertion_id: str | None = None,
    created_by: str,
) -> dict[str, Any]:
    return {
        "assertion_id": f"sa-{uuid.uuid4().hex}",
        "source_id": source_id,
        "document_id": document_id,
        "entity": entity,
        "market": market,
        "security_id": security_id,
        "document_kind": document_kind,
        "form_type": form_type,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "provider": provider,
        "provider_document_id": provider_document_id,
        "source_url": source_url,
        "filing_date": filing_date,
        "content_sha256": content_sha256,
        "evidence_basis": evidence_basis,
        "evidence_json": canonical_json(evidence_json or {}),
        "decision": decision,
        "supersedes_assertion_id": supersedes_assertion_id,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "created_by": created_by,
        "schema_version": ASSERTION_SCHEMA_VERSION,
    }


def _get_active_verified_assertions(
    store: CatalogStore, source_id: str
) -> list[dict[str, Any]]:
    """Return the active (non-superseded) verified assertions for a source."""
    rows = store.fetchall(
        """SELECT * FROM source_metadata_assertions
        WHERE source_id=? AND decision='verified'
        ORDER BY created_at DESC""",
        (source_id,),
    )
    superseded_ids = {
        r["supersedes_assertion_id"]
        for r in rows
        if r["supersedes_assertion_id"] is not None
    }
    return [dict(r) for r in rows if r["assertion_id"] not in superseded_ids]


def _resolve_active_verified(
    active: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve active verified assertions to the authoritative one.

    A single active row is authoritative.  Multiple active rows that all share
    the same evidence key (source_id, document_id, content_sha256) resolve to
    the latest (rows arrive in created_at DESC order) — Phase 18.2: verifying a
    corrected candidate supersedes the prior one, and pre-fix rows that were
    never linked still resolve to the newest correction.  Rows with genuinely
    different evidence keys remain an unresolved conflict (None, fail closed).
    """
    if len(active) == 1:
        return active[0]
    if len(active) > 1:
        keys = {
            (a["source_id"], a["document_id"], a["content_sha256"]) for a in active
        }
        if len(keys) == 1:
            return active[0]
    return None


def get_verified_assertion(
    store: CatalogStore,
    source_id: str,
    content_sha256: str,
) -> dict[str, Any] | None:
    """Return the active verified assertion for a source, or None.

    Must match both source_id and current content_sha256.  Multiple verified
    assertions sharing the same evidence resolve to the latest (Phase 18.2
    correction chain); different evidence remains a conflict (None, fail
    closed).
    """
    active = _get_active_verified_assertions(store, source_id)
    matching = [a for a in active if a["content_sha256"] == content_sha256]
    return _resolve_active_verified(matching)


def get_verified_assertion_by_document(
    store: CatalogStore,
    document_id: str,
    content_sha256: str | None = None,
) -> dict[str, Any] | None:
    """Return the active verified assertion for a document, or None (Phase
    15.5).

    Documents without a primary source (placeholders) surface ``source_id``
    as NULL to the resolver, so source_id-based lookups can never match them;
    assertions carry ``document_id`` and are resolved by it here.  When
    ``content_sha256`` is given it must match.  Multiple active verified
    assertions sharing the same evidence resolve to the latest (Phase 18.2
    correction chain); different evidence is a conflict and returns None
    (fail closed).
    """
    rows = store.fetchall(
        """SELECT * FROM source_metadata_assertions
        WHERE document_id=? AND decision='verified'
        ORDER BY created_at DESC""",
        (document_id,),
    )
    superseded_ids = {
        r["supersedes_assertion_id"]
        for r in rows
        if r["supersedes_assertion_id"] is not None
    }
    active = [dict(r) for r in rows if r["assertion_id"] not in superseded_ids]
    if content_sha256 is not None:
        active = [a for a in active if a["content_sha256"] == content_sha256]
    return _resolve_active_verified(active)


def preview_assertion(
    store: CatalogStore,
    *,
    source_id: str,
    document_id: str,
    content_sha256: str,
    entity: str | None = None,
    market: str | None = None,
    security_id: str | None = None,
    document_kind: str | None = None,
    form_type: str | None = None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    provider: str | None = None,
    provider_document_id: str | None = None,
    source_url: str | None = None,
    filing_date: str | None = None,
    evidence_basis: str,
    evidence_json: dict[str, Any] | None = None,
    created_by: str = "cw-2.28-automation",
) -> dict[str, Any]:
    """Generate and write a candidate assertion to the catalog.

    The candidate is written immediately so that it can be later verified or
    rejected by its assertion_id. Candidates are never consumed by the
    resolver — only verified assertions are.
    """
    existing = store.fetchall(
        "SELECT * FROM source_metadata_assertions WHERE source_id=? AND decision='verified'",
        (source_id,),
    )
    conflicts = []
    for e in existing:
        if (
            e["entity"] == entity
            and e["market"] == market
            and e["security_id"] == security_id
        ):
            pass
        elif e["entity"] != entity or e["security_id"] != security_id:
            conflicts.append(e["assertion_id"])

    a = _build_assertion(
        source_id=source_id,
        document_id=document_id,
        content_sha256=content_sha256,
        entity=entity,
        market=market,
        security_id=security_id,
        document_kind=document_kind,
        form_type=form_type,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        provider=provider,
        provider_document_id=provider_document_id,
        source_url=source_url,
        filing_date=filing_date,
        evidence_basis=evidence_basis,
        evidence_json=evidence_json,
        decision="candidate",
        created_by=created_by,
    )

    with store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions
            (assertion_id, source_id, document_id, entity, market, security_id,
             document_kind, form_type, fiscal_year, fiscal_period, provider,
             provider_document_id, source_url, filing_date, content_sha256,
             evidence_basis, evidence_json, decision, supersedes_assertion_id,
             created_at, created_by, schema_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                a["assertion_id"],
                a["source_id"],
                a["document_id"],
                a["entity"],
                a["market"],
                a["security_id"],
                a["document_kind"],
                a["form_type"],
                a["fiscal_year"],
                a["fiscal_period"],
                a["provider"],
                a["provider_document_id"],
                a["source_url"],
                a["filing_date"],
                a["content_sha256"],
                a["evidence_basis"],
                a["evidence_json"],
                a["decision"],
                a["supersedes_assertion_id"],
                a["created_at"],
                a["created_by"],
                a["schema_version"],
            ),
        )
    return a
    conflicts = []
    for e in existing:
        if (
            e["entity"] == entity
            and e["market"] == market
            and e["security_id"] == security_id
        ):
            pass  # same identity, superseded
        elif e["entity"] != entity or e["security_id"] != security_id:
            conflicts.append(e["assertion_id"])

    return _build_assertion(
        source_id=source_id,
        document_id=document_id,
        content_sha256=content_sha256,
        entity=entity,
        market=market,
        security_id=security_id,
        document_kind=document_kind,
        form_type=form_type,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        provider=provider,
        provider_document_id=provider_document_id,
        source_url=source_url,
        filing_date=filing_date,
        evidence_basis=evidence_basis,
        evidence_json=evidence_json,
        decision="candidate",
        supersedes_assertion_id=None,
        created_by=created_by,
    )


def verify_assertion(
    store: CatalogStore,
    *,
    assertion_id: str,
    current_sha256: str,
    confirmed_by: str = "cw-2.28-automation",
) -> dict[str, Any]:
    """Promote a candidate assertion to verified (supersedes previous verified if exists)."""
    existing = store.fetchone(
        "SELECT * FROM source_metadata_assertions WHERE assertion_id=?",
        (assertion_id,),
    )
    if existing is None:
        raise ValueError(f"Assertion not found: {assertion_id}")
    if existing["decision"] != "candidate":
        raise ValueError(f"Assertion {assertion_id} is not a candidate")
    if existing["content_sha256"] != current_sha256:
        raise ValueError("Current content_sha256 does not match assertion")

    # Phase 18.2: a verified correction supersedes the prior active verified
    # assertion on the same (source, document, content) instead of
    # self-superseding its own candidate, so lookups resolve to the latest
    # (GOOGL -> GOOG correction flow).  With no prior verified, keep pointing
    # at the candidate (existing behavior: a promoted candidate cannot be
    # rejected afterwards).
    prior_rows = store.fetchall(
        """SELECT * FROM source_metadata_assertions
        WHERE source_id=? AND document_id=? AND content_sha256=?
          AND decision='verified'
        ORDER BY created_at DESC""",
        (existing["source_id"], existing["document_id"], current_sha256),
    )
    superseded_ids = {
        r["supersedes_assertion_id"]
        for r in prior_rows
        if r["supersedes_assertion_id"] is not None
    }
    active_prior = [r for r in prior_rows if r["assertion_id"] not in superseded_ids]
    supersedes = active_prior[0]["assertion_id"] if active_prior else assertion_id

    new = _build_assertion(
        source_id=existing["source_id"],
        document_id=existing["document_id"],
        content_sha256=current_sha256,
        entity=existing["entity"],
        market=existing["market"],
        security_id=existing["security_id"],
        document_kind=existing["document_kind"],
        form_type=existing["form_type"],
        fiscal_year=existing["fiscal_year"],
        fiscal_period=existing["fiscal_period"],
        provider=existing["provider"],
        provider_document_id=existing["provider_document_id"],
        source_url=existing["source_url"],
        filing_date=existing["filing_date"],
        evidence_basis=existing["evidence_basis"],
        evidence_json=json.loads(existing["evidence_json"]),
        decision="verified",
        supersedes_assertion_id=supersedes,
        created_by=confirmed_by,
    )

    with store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions
            (assertion_id, source_id, document_id, entity, market, security_id,
             document_kind, form_type, fiscal_year, fiscal_period, provider,
             provider_document_id, source_url, filing_date, content_sha256,
             evidence_basis, evidence_json, decision, supersedes_assertion_id,
             created_at, created_by, schema_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                new["assertion_id"],
                new["source_id"],
                new["document_id"],
                new["entity"],
                new["market"],
                new["security_id"],
                new["document_kind"],
                new["form_type"],
                new["fiscal_year"],
                new["fiscal_period"],
                new["provider"],
                new["provider_document_id"],
                new["source_url"],
                new["filing_date"],
                new["content_sha256"],
                new["evidence_basis"],
                new["evidence_json"],
                new["decision"],
                new["supersedes_assertion_id"],
                new["created_at"],
                new["created_by"],
                new["schema_version"],
            ),
        )
    return new


def reject_assertion(
    store: CatalogStore,
    *,
    assertion_id: str,
    reason: str,
    rejected_by: str = "cw-2.28-automation",
) -> dict[str, Any]:
    """Record that a candidate assertion was rejected."""
    existing = store.fetchone(
        "SELECT * FROM source_metadata_assertions WHERE assertion_id=?",
        (assertion_id,),
    )
    if existing is None:
        raise ValueError(f"Assertion not found: {assertion_id}")
    if existing["decision"] != "candidate":
        raise ValueError(
            f"Assertion {assertion_id} cannot be rejected (decision={existing['decision']})"
        )
    superseded = store.fetchone(
        "SELECT 1 FROM source_metadata_assertions WHERE supersedes_assertion_id=? AND decision IN ('verified','rejected')",
        (assertion_id,),
    )
    if superseded is not None:
        raise ValueError(f"Assertion {assertion_id} has already been superseded")

    rejected = _build_assertion(
        source_id=existing["source_id"],
        document_id=existing["document_id"],
        content_sha256=existing["content_sha256"],
        entity=existing["entity"],
        market=existing["market"],
        security_id=existing["security_id"],
        evidence_basis=existing["evidence_basis"],
        evidence_json={"rejection_reason": reason},
        decision="rejected",
        supersedes_assertion_id=assertion_id,
        created_by=rejected_by,
    )

    with store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions
            (assertion_id, source_id, document_id, entity, market, security_id,
             document_kind, form_type, fiscal_year, fiscal_period, provider,
             provider_document_id, source_url, filing_date, content_sha256,
             evidence_basis, evidence_json, decision, supersedes_assertion_id,
             created_at, created_by, schema_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rejected["assertion_id"],
                rejected["source_id"],
                rejected["document_id"],
                rejected["entity"],
                rejected["market"],
                rejected["security_id"],
                rejected.get("document_kind"),
                rejected.get("form_type"),
                rejected.get("fiscal_year"),
                rejected.get("fiscal_period"),
                rejected.get("provider"),
                rejected.get("provider_document_id"),
                rejected.get("source_url"),
                rejected.get("filing_date"),
                rejected["content_sha256"],
                rejected["evidence_basis"],
                rejected["evidence_json"],
                rejected["decision"],
                rejected["supersedes_assertion_id"],
                rejected["created_at"],
                rejected["created_by"],
                rejected["schema_version"],
            ),
        )
    return rejected


def upsert_verified_assertion(
    store: CatalogStore,
    *,
    source_id: str,
    document_id: str,
    content_sha256: str,
    adapter_id: str,
    adapter_version: str,
    metadata_hash: str,
    normalized: dict,
    created_by: str = "cw-2.28-automation",
) -> dict[str, Any]:
    """WU-402: idempotent verified-assertion upsert.

    Idempotency key = (source_id, content_sha256, adapter_id, adapter_version,
    metadata_hash).  Same key twice => return the existing assertion (no
    duplicate active rows).  Different metadata hash for the same content =>
    a NEW assertion is appended (conflict coexists; history is never
    overwritten).  All writes happen inside one transaction (TX-01).
    """
    from .normalized_meta import canonical_hash

    if metadata_hash != canonical_hash(normalized):
        raise ValueError(
            "metadata_hash does not match canonical_hash(normalized) — "
            "idempotency key would diverge from the stored value"
        )
    existing = store.fetchone(
        """SELECT * FROM source_metadata_assertions
        WHERE source_id=? AND content_sha256=? AND adapter_id=? AND
              adapter_version=? AND normalized_sha256=? AND decision='verified'
        ORDER BY created_at DESC LIMIT 1""",
        (source_id, content_sha256, adapter_id, adapter_version, metadata_hash),
    )
    if existing is not None:
        return dict(existing)

    evidence = normalized.get("evidence") or {}
    assertion = _build_assertion(
        source_id=source_id,
        document_id=document_id,
        content_sha256=content_sha256,
        entity=normalized.get("display_name"),
        market=normalized.get("market"),
        security_id=normalized.get("security_id"),
        document_kind=normalized.get("document_kind"),
        form_type=normalized.get("regulatory_form"),
        fiscal_year=(
            int(normalized["fiscal_year"])
            if str(normalized.get("fiscal_year", "")).isdigit() else None
        ),
        fiscal_period=normalized.get("period_kind"),
        provider=normalized.get("provider"),
        provider_document_id=normalized.get("provider_document_id"),
        source_url=normalized.get("source_url"),
        filing_date=normalized.get("filed_at"),
        evidence_basis="v2-normalized",
        evidence_json=evidence,
        decision="verified",
        created_by=created_by,
    )
    assertion["adapter_id"] = adapter_id
    assertion["adapter_version"] = adapter_version
    assertion["normalized_sha256"] = canonical_hash(normalized)
    assertion["normalization_status"] = "capture_ready"
    assertion["visibility_state"] = "shadow"  # never active until cutover

    with store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions
            (assertion_id, source_id, document_id, entity, market, security_id,
             document_kind, form_type, fiscal_year, fiscal_period, provider,
             provider_document_id, source_url, filing_date, content_sha256,
             evidence_basis, evidence_json, decision, supersedes_assertion_id,
             created_at, created_by, schema_version, adapter_id, adapter_version,
             normalized_sha256, normalization_status, visibility_state)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                assertion["assertion_id"],
                assertion["source_id"],
                assertion["document_id"],
                assertion["entity"],
                assertion["market"],
                assertion["security_id"],
                assertion["document_kind"],
                assertion["form_type"],
                assertion["fiscal_year"],
                assertion["fiscal_period"],
                assertion["provider"],
                assertion["provider_document_id"],
                assertion["source_url"],
                assertion["filing_date"],
                assertion["content_sha256"],
                assertion["evidence_basis"],
                assertion["evidence_json"],
                assertion["decision"],
                assertion["supersedes_assertion_id"],
                assertion["created_at"],
                assertion["created_by"],
                assertion["schema_version"],
                assertion["adapter_id"],
                assertion["adapter_version"],
                assertion["normalized_sha256"],
                assertion["normalization_status"],
                assertion["visibility_state"],
            ),
        )
    return assertion
