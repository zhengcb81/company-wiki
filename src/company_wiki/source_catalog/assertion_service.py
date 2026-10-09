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
from datetime import date, datetime, timezone
import re
from typing import Any
from urllib.parse import urlsplit

from .store import CatalogStore, canonical_json
from .document_kinds import SOURCE_FACT_KINDS


def _evidence_payload(raw: Any, assertion_id: str) -> dict[str, Any]:
    """F-B10R2-MISSINGFILE family, site 2 (owner instruction 2026-09-18).

    `upsert_verified_assertion` copies an existing assertion's evidence forward, and the
    parse used to be bare: a malformed `evidence_json` column escaped as a JSONDecodeError
    from a service whose refusals are named `ValueError`s.  Copying a value we cannot read
    would also be wrong - the new assertion would carry evidence nobody verified - so this
    fails closed by name, and it never raises an unnamed parse error.
    """
    try:
        payload = json.loads(raw or "{}")
    except (json.JSONDecodeError, TypeError, RecursionError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"assertion {assertion_id} has an unreadable evidence_json "
            f"({type(exc).__name__}); refusing to copy unverified evidence forward"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"assertion {assertion_id} evidence_json is not an object; refusing to copy it"
        )
    return payload

ASSERTION_SCHEMA_VERSION = "1.0.0"
ASSERTION_REQUIRED_FIELDS = frozenset(
    {"source_id", "document_id", "content_sha256", "evidence_basis", "decision"}
)

SOURCE_FACT_FIELDS = frozenset({
    "entity", "market", "security_id", "document_kind", "published_date",
    "source_url", "provider", "provider_document_id", "filing_date",
    "fiscal_year", "fiscal_period", "period_end", "language", "title", "form_type",
})


def _validate_source_facts(facts: dict[str, Any], evidence: dict[str, Any]) -> None:
    if not isinstance(facts, dict) or not facts or not set(facts) <= SOURCE_FACT_FIELDS:
        raise ValueError("source facts must be a nonempty object of known fields")
    if not isinstance(evidence, dict) or set(evidence) != set(facts):
        raise ValueError("each changed fact needs matching field evidence")
    for key, value in facts.items():
        if key == "fiscal_year":
            if value is not None and (type(value) is not int or not 1900 <= value <= 9999):
                raise ValueError("fiscal_year must be an integer year or unknown")
        elif value is not None and (not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 2048):
            raise ValueError(f"{key} must be trimmed nonempty text or unknown")
        if key in {"published_date", "filing_date", "period_end"} and value is not None:
            if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
                raise ValueError(f"{key} must be an ISO date")
        if key == "document_kind" and value not in SOURCE_FACT_KINDS:
            raise ValueError("unknown document kind")
        if key == "market" and value not in {None, "CN", "HK", "US"}:
            raise ValueError("unknown market")
        if key == "security_id" and value is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,19}", value):
            raise ValueError("security_id must be a code, not a display name or path")
        if key == "source_url" and value is not None:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("source_url must be a public HTTP URL")
        observation = evidence[key]
        if not isinstance(observation, dict) or not isinstance(observation.get("locator"), str) or not observation["locator"].strip():
            raise ValueError(f"{key} has no field locator")
        if "value" not in observation or observation["value"] != value:
            raise ValueError(f"{key} disagrees with its field evidence")
    if len(canonical_json(evidence).encode("utf-8")) > 65536:
        raise ValueError("source fact evidence exceeds byte limit")


def record_source_facts(catalog: Any, *, ref: Any, facts: dict[str, Any],
                        evidence: dict[str, Any]) -> dict[str, Any]:
    """Verify bytes; append facts and update their query projection atomically.

    Captures stay unchanged. Explicit unknowns survive later corrections. No
    candidate, review receipt, rollout flag or second task store is introduced.
    """
    from .lock import CatalogOperationLock
    from .source_reader import SourceRef, SourceVersionReader

    if not isinstance(ref, SourceRef):
        raise TypeError("ref must be SourceRef")
    _validate_source_facts(facts, evidence)
    with CatalogOperationLock(catalog.config.catalog_dir, operation="source_facts"):
        reader = SourceVersionReader(catalog)
        reader.verify_version(ref, purpose="source_export")
        current = reader.describe_version(ref)
        assertion, projection, assertion_id = _prepare_source_fact_write(catalog, ref, current, facts, evidence)
        if assertion is not None:
            with catalog.store.transaction() as connection:
                _write_source_fact_projection(connection, ref, assertion, projection)
        return {"status": "recorded" if assertion is not None else "unchanged",
                "assertion_id": assertion_id, "document_id": ref.document_id, "source_id": ref.source_id}


def _prepare_source_fact_write(catalog, ref, current, facts, evidence):
    """One semantic correction builder shared by active updates and atomic restoration."""
    prior = get_verified_assertion(catalog.reader, ref.source_id, ref.content_sha256, reader="steady")
    previous_evidence = _evidence_payload(prior["evidence_json"], prior["assertion_id"]) if prior else {}
    patch = dict(previous_evidence.get("source_fact_patch") or {})
    field_evidence = dict(previous_evidence.get("source_fact_evidence") or {})
    patch.update(facts)
    field_evidence.update(evidence)
    _validate_source_facts(patch, field_evidence)
    evidence_payload = {"source_fact_patch": patch, "source_fact_evidence": field_evidence}
    def semantic_evidence(value: dict[str, Any]) -> dict[str, Any]:
        fields = value.get("source_fact_evidence") or {}
        return {"source_fact_patch": value.get("source_fact_patch"),
                "source_fact_evidence": {key: {k: v for k, v in proof.items() if k != "observed_at"}
                                         for key, proof in fields.items()}}
    if prior and prior["evidence_basis"] == "source-facts" and semantic_evidence(previous_evidence) == semantic_evidence(evidence_payload):
        return None, {}, prior["assertion_id"]
    values = {key: current.get(key) for key in SOURCE_FACT_FIELDS}
    values["entity"] = current.get("display_name")
    if prior:
        for key in SOURCE_FACT_FIELDS - {"published_date"}:
            if values.get(key) is None and key in prior:
                values[key] = prior[key]
    values.update(patch)
    assertion = _build_assertion(
        source_id=ref.source_id, document_id=ref.document_id, content_sha256=ref.content_sha256,
        **{key: value for key, value in values.items() if key not in {"published_date", "language", "title"}},
        evidence_basis="source-facts", evidence_json=evidence_payload, decision="verified",
        supersedes_assertion_id=prior["assertion_id"] if prior else None,
        created_by="automated-source-facts",
    )
    assertion.update(published_at=values["published_date"], language=values["language"])
    projection = {}
    if "document_kind" in facts:
        projection.update(document_kind=facts["document_kind"], source_type=SOURCE_FACT_KINDS[facts["document_kind"]])
    if "published_date" in facts:
        projection["published_date"] = facts["published_date"]
    if facts.get("title") is not None:
        projection["title"] = facts["title"]
    return assertion, projection, assertion["assertion_id"]


def _write_source_fact_projection(connection, ref, assertion, projection):
    columns = tuple(assertion)
    connection.execute(
        f"INSERT INTO source_metadata_assertions ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        tuple(assertion[key] for key in columns),
    )
    if projection:
        connection.execute(
            f"UPDATE documents SET {','.join(key+'=?' for key in projection)} WHERE document_id=?",
            (*projection.values(), ref.document_id),
        )


def restore_document_facts(catalog, *, ref, facts, evidence, retirement_observation,
                           budget=None, fact_replay=None):
    """Verify inactive bytes, supersede facts and restore only verified locations atomically.

    The observation is an optimistic concurrency pin; it does not authorize an
    arbitrary retirement. There is no intermediate fake-active read.
    """
    from .local_inventory import (LocalPrepareLimits, LocalReadBudget,
                                  metadata_retirement, observe_document, verify_registered_original)
    from .lock import CatalogOperationLock
    from .source_reader import SourceReadError, SourceRef
    from .resolver import _source_metadata
    from .metadata_observation import observe_metadata

    if not isinstance(ref, SourceRef):
        raise TypeError("ref must be SourceRef")
    _validate_source_facts(facts, evidence)
    required = {"entity", "market", "security_id", "document_kind", "published_date"}
    if any(not facts.get(key) for key in required):
        raise SourceReadError("blocked", "local_metadata_incomplete")
    budget = budget or LocalReadBudget(LocalPrepareLimits())
    with CatalogOperationLock(catalog.config.catalog_dir, operation="local_source_reconcile"):
        budget.check()
        observed = observe_document(catalog, ref.document_id)
        if observed != retirement_observation:
            raise SourceReadError("unavailable", "local_observation_changed")
        status = observed["version"]["source_status"]
        if status not in {"active", "retired"} or (status == "retired" and not metadata_retirement(observed)):
            raise SourceReadError("blocked", "retirement_not_metadata_only")
        original = verify_registered_original(catalog, ref, budget=budget)
        if fact_replay is not None:
            replayed_facts, replayed_evidence = fact_replay(original)
            if (replayed_facts,replayed_evidence) != (facts,evidence):
                raise SourceReadError("unavailable", "local_fact_observation_changed")
        row = observed["version"]
        metadata = observe_metadata(row["metadata_json"]).metadata
        current = _source_metadata({"source_id":ref.source_id, "metadata":metadata},
                                   store=catalog.reader, reader="steady")
        current.update(document_kind=row["document_kind"],
                       published_date=current.get("published_date",row["published_date"]),
                       display_name=current.get("display_name") or current.get("company_name"))
        assertion, projection, assertion_id = _prepare_source_fact_write(catalog,ref,current,facts,evidence)
        audit_id = f"restore-{uuid.uuid4().hex}" if status == "retired" else None
        with catalog.store.transaction() as connection:
            if observe_document(catalog,ref.document_id) != observed:
                raise SourceReadError("unavailable", "local_observation_changed")
            budget.check()
            if assertion is not None:
                _write_source_fact_projection(connection,ref,assertion,projection)
            if status == "retired":
                connection.execute("UPDATE documents SET source_status='active' WHERE document_id=?",(ref.document_id,))
                for location_id, _path, _root in original.locations:
                    connection.execute("UPDATE locations SET location_status='active' WHERE location_id=? AND source_id=? AND location_status='retired'",(location_id,ref.source_id))
                connection.execute("INSERT INTO document_restore_audit(audit_id,document_id,reason,created_by,created_at) VALUES(?,?,?,?,?)",
                    (audit_id,ref.document_id,"verified local original and corrected source facts; prior retirement audits retained",
                     "automated-local-reconcile",datetime.now(tz=timezone.utc).isoformat()))
            budget.check()
        return {"status":"restored" if audit_id else ("recorded" if assertion is not None else "unchanged"),
                "source_ref":ref, "assertion_id":assertion_id, "restore_audit_id":audit_id,
                "verified_locations":len(original.locations)}


def source_fact_projection(connection: Any, *, document_id: str,
                           source_id: str | None) -> dict[str, Any]:
    """Indexed single-source facts for scan projection; no discovery or raw reads."""
    if not source_id:
        return {}
    row = connection.execute(
        """SELECT a.evidence_basis,a.evidence_json FROM source_metadata_assertions a
        JOIN sources s ON s.source_id=a.source_id AND s.content_sha256=a.content_sha256
        WHERE a.document_id=? AND a.source_id=? AND a.decision='verified'
          AND a.visibility_state IN ('legacy','active')
        ORDER BY a.created_at DESC LIMIT 1""", (document_id, source_id),
    ).fetchone()
    if row is None or row["evidence_basis"] != "source-facts":
        return {}
    evidence = _evidence_payload(row["evidence_json"], document_id)
    patch = evidence.get("source_fact_patch")
    _validate_source_facts(patch, evidence.get("source_fact_evidence"))
    projection = {}
    if "document_kind" in patch:
        projection.update(document_kind=patch["document_kind"], source_type=SOURCE_FACT_KINDS[patch["document_kind"]])
    if "published_date" in patch:
        projection["published_date"] = patch["published_date"]
    if patch.get("title") is not None:
        projection["title"] = patch["title"]
    return projection


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
    period_end: str | None = None,
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
        "period_end": period_end,
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


def _visibility_sql(
    reader: str,
    current_epoch: str | None,
    active_cohorts: tuple[str, ...],
) -> tuple[str, tuple[Any, ...]]:
    """FC-202: decision AND visibility AND epoch AND cohort filter.

    v1 reader sees only ``legacy`` rows (active rows never visible even when
    present — CTRL-01).  v2 reader sees only ``active`` rows whose epoch
    matches and whose cohort is in the active set (CTRL-02); missing epoch
    or empty cohort set fails closed.
    """
    if reader == "v1":
        return "visibility_state='legacy'", ()
    if reader == "steady":
        return "visibility_state IN ('legacy','active')", ()
    if reader == "v2":
        if not current_epoch or not active_cohorts:
            return "1=0", ()  # fail closed
        placeholders = ",".join("?" for _ in active_cohorts)
        return (
            "visibility_state='active' AND activation_epoch=? "
            f"AND cohort IN ({placeholders})",
            (current_epoch, *active_cohorts),
        )
    raise ValueError(f"unknown reader {reader!r}")


def _get_active_verified_assertions(
    store: CatalogStore,
    source_id: str,
    *,
    reader: str = "v1",
    current_epoch: str | None = None,
    active_cohorts: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Return the active (non-superseded) verified assertions for a source,
    filtered by the pinned RuntimePolicySnapshot visibility contract
    (FC-202)."""
    visibility, extra = _visibility_sql(reader, current_epoch, active_cohorts)
    rows = store.fetchall(
        f"""SELECT * FROM source_metadata_assertions
        WHERE source_id=? AND decision='verified' AND {visibility}
        ORDER BY created_at DESC""",
        (source_id, *extra),
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
    *,
    reader: str = "v1",
    current_epoch: str | None = None,
    active_cohorts: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    """Return the active verified assertion for a source, or None.

    Must match both source_id and current content_sha256.  Multiple verified
    assertions sharing the same evidence resolve to the latest (Phase 18.2
    correction chain); different evidence remains a conflict (None, fail
    closed).  FC-202: visibility/epoch/cohort filtered by the pinned
    RuntimePolicySnapshot.
    """
    active = _get_active_verified_assertions(
        store, source_id, reader=reader, current_epoch=current_epoch,
        active_cohorts=active_cohorts,
    )
    matching = [a for a in active if a["content_sha256"] == content_sha256]
    return _resolve_active_verified(matching)


def get_verified_assertion_by_document(
    store: CatalogStore,
    document_id: str,
    content_sha256: str | None = None,
    *,
    reader: str = "v1",
    current_epoch: str | None = None,
    active_cohorts: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    """Return the active verified assertion for a document, or None (Phase
    15.5).

    Documents without a primary source (placeholders) surface ``source_id``
    as NULL to the resolver, so source_id-based lookups can never match them;
    assertions carry ``document_id`` and are resolved by it here.  When
    ``content_sha256`` is given it must match.  Multiple active verified
    assertions sharing the same evidence resolve to the latest (Phase 18.2
    correction chain); different evidence is a conflict and returns None
    (fail closed).  FC-202: visibility/epoch/cohort filtered by the pinned
    RuntimePolicySnapshot.
    """
    visibility, extra = _visibility_sql(reader, current_epoch, active_cohorts)
    rows = store.fetchall(
        f"""SELECT * FROM source_metadata_assertions
        WHERE document_id=? AND decision='verified' AND {visibility}
        ORDER BY created_at DESC""",
        (document_id, *extra),
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
        period_end=existing["period_end"] if "period_end" in existing.keys() else None,
        provider=existing["provider"],
        provider_document_id=existing["provider_document_id"],
        source_url=existing["source_url"],
        filing_date=existing["filing_date"],
        evidence_basis=existing["evidence_basis"],
        evidence_json=_evidence_payload(existing["evidence_json"], assertion_id),
        decision="verified",
        supersedes_assertion_id=supersedes,
        created_by=confirmed_by,
    )

    with store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions
            (assertion_id, source_id, document_id, entity, market, security_id,
             document_kind, form_type, fiscal_year, fiscal_period, period_end,
             provider, provider_document_id, source_url, filing_date,
             content_sha256, evidence_basis, evidence_json, decision,
             supersedes_assertion_id, created_at, created_by, schema_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                new["period_end"],
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
        period_end=normalized.get("period_end"),
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
             document_kind, form_type, fiscal_year, fiscal_period, period_end,
             provider, provider_document_id, source_url, filing_date,
             content_sha256, evidence_basis, evidence_json, decision,
             supersedes_assertion_id, created_at, created_by, schema_version,
             adapter_id, adapter_version, normalized_sha256,
             normalization_status, visibility_state)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                assertion["period_end"],
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
