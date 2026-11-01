"""Derived identity-token candidate index, never a source-fact authority.

The writer refreshes only dirty source rows in its existing transaction. Native
SQLite triggers mark external changes dirty without custom SQL functions, so
ordinary SQLite maintenance remains usable. Readers include dirty rows and
always run the established metadata/identity qualification afterwards.
"""

from __future__ import annotations

import json
from typing import Any

from .security_identity import _normalize_text

_IDENTITY_FIELDS = (
    "display_name",
    "canonical_entity_id",
    "security_id",
    "company_name",
    "ticker",
)


def _object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value) if isinstance(value, (str, bytes)) else None
    except (ValueError, UnicodeDecodeError, RecursionError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _tokens(values) -> set[str]:
    return {
        token
        for value in values
        if value and (token := _normalize_text(str(value)))
    }


def metadata_identity_tokens(value: object, *, assertion: bool = False) -> set[str]:
    payload = _object(value)
    if assertion:
        patch = _object(payload.get("source_fact_patch"))
        return _tokens(
            patch.get(key) for key in ("entity", "canonical_entity_id", "security_id")
        )
    result: set[str] = set()
    # This is a candidate superset, including superseded declarations. Only
    # _source_metadata decides which declaration is currently authoritative.
    for container in ("acquisition", "dayu_meta"):
        record = _object(payload.get(container))
        result.update(_tokens(record.get(key) for key in _IDENTITY_FIELDS))
    return result


def request_identity_tokens(entity: str, resolver) -> tuple[str, ...]:
    """Use the resolver's same issuer-alias authority, without reimplementing it."""
    wanted = _normalize_text(entity)
    token_to_issuer, issuer_tokens = resolver._issuer_index()
    issuer = token_to_issuer.get(wanted)
    return tuple(sorted({wanted, *issuer_tokens.get(issuer, ())} - {""}))


def ensure_identity_projection(connection) -> None:
    """Optional derived indexes are installed by an explicit writer only."""
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name='source_identity_tokens'"
    ).fetchone():
        return
    connection.execute("""CREATE TABLE source_identity_tokens (
        document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        token TEXT NOT NULL, PRIMARY KEY(document_id,token))""")
    connection.execute(
        "CREATE INDEX idx_source_identity_token ON source_identity_tokens(token,document_id)"
    )
    connection.execute("""CREATE TABLE source_identity_dirty (
        document_id TEXT PRIMARY KEY REFERENCES documents(document_id) ON DELETE CASCADE)""")
    for event in ("INSERT", "UPDATE"):
        connection.execute(f"""CREATE TRIGGER source_identity_documents_{event.lower()}
            AFTER {event} ON documents BEGIN
            INSERT INTO source_identity_dirty SELECT NEW.document_id
            WHERE NOT EXISTS (SELECT 1 FROM source_identity_dirty WHERE document_id=NEW.document_id); END""")
    for table, key in (
        ("document_entities", "document_id"),
        ("source_metadata_assertions", "document_id"),
    ):
        for event in ("INSERT", "UPDATE", "DELETE"):
            row = "OLD" if event == "DELETE" else "NEW"
            related = (
                f"document_id={row}.{key}"
                if table == "document_entities"
                else f"primary_source_id={row}.source_id"
            )
            connection.execute(f"""CREATE TRIGGER source_identity_{table}_{event.lower()}
                AFTER {event} ON {table} BEGIN
                INSERT INTO source_identity_dirty
                SELECT document_id FROM documents WHERE {related}
                AND NOT EXISTS (SELECT 1 FROM source_identity_dirty dirty WHERE dirty.document_id=documents.document_id); END""")
        # An UPDATE may move an association to another source/document.
        old_related = (
            "document_id=OLD.document_id"
            if table == "document_entities"
            else "primary_source_id=OLD.source_id"
        )
        connection.execute(f"""CREATE TRIGGER source_identity_{table}_old_update
            AFTER UPDATE ON {table} BEGIN
            INSERT INTO source_identity_dirty
            SELECT document_id FROM documents WHERE {old_related}
            AND NOT EXISTS (SELECT 1 FROM source_identity_dirty dirty WHERE dirty.document_id=documents.document_id); END""")
    connection.execute("""CREATE TRIGGER source_identity_entities_update AFTER UPDATE ON entities BEGIN
        INSERT INTO source_identity_dirty
        SELECT DISTINCT document_id FROM document_entities WHERE entity_id IN (OLD.entity_id,NEW.entity_id)
        AND NOT EXISTS (SELECT 1 FROM source_identity_dirty dirty WHERE dirty.document_id=document_entities.document_id); END""")
    for event, row in (("INSERT", "NEW"), ("DELETE", "OLD")):
        connection.execute(f"""CREATE TRIGGER source_identity_entities_{event.lower()} AFTER {event} ON entities BEGIN
            INSERT INTO source_identity_dirty
            SELECT DISTINCT document_id FROM document_entities WHERE entity_id={row}.entity_id
            AND NOT EXISTS (SELECT 1 FROM source_identity_dirty dirty WHERE dirty.document_id=document_entities.document_id); END""")
    connection.execute(
        "INSERT INTO source_identity_dirty SELECT document_id FROM documents"
    )


def refresh_identity_projection(connection) -> None:
    """Refresh a source-owned projection in the caller's transaction, once."""
    while rows := connection.execute(
        "SELECT document_id FROM source_identity_dirty LIMIT 500"
    ).fetchall():
        ids = [row[0] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        tokens: dict[str, set[str]] = {document_id: {""} for document_id in ids}
        for row in connection.execute(
            f"SELECT document_id,metadata_json FROM documents WHERE document_id IN ({placeholders})",
            ids,
        ):
            tokens[row[0]].update(metadata_identity_tokens(row[1]))
        for row in connection.execute(
            f"""SELECT de.document_id,e.entity_id,e.name
            FROM document_entities de JOIN entities e ON e.entity_id=de.entity_id
            WHERE de.document_id IN ({placeholders})""",
            ids,
        ):
            tokens[row[0]].update(_tokens(row[1:]))
        for row in connection.execute(
            f"""SELECT d.document_id,a.entity,a.security_id,a.evidence_json
            FROM documents d JOIN source_metadata_assertions a ON a.source_id=d.primary_source_id
            WHERE a.decision='verified' AND d.document_id IN ({placeholders})""",
            ids,
        ):
            tokens[row[0]].update(_tokens(row[1:3]))
            tokens[row[0]].update(metadata_identity_tokens(row[3], assertion=True))
        connection.executemany(
            "DELETE FROM source_identity_tokens WHERE document_id=?",
            ((d,) for d in ids),
        )
        connection.executemany(
            "INSERT INTO source_identity_tokens VALUES(?,?)",
            ((d, t) for d, values in tokens.items() for t in values),
        )
        connection.executemany(
            "DELETE FROM source_identity_dirty WHERE document_id=?", ((d,) for d in ids)
        )


def register_identity_read_functions(connection) -> None:
    """Compatibility for pre-index catalogs; this changes no database bytes."""
    connection.create_function(
        "cwp_identity_token",
        1,
        lambda value: _normalize_text(str(value)) if value else "",
        deterministic=True,
    )
    connection.create_function(
        "cwp_identity_member",
        3,
        lambda value, wanted, assertion: bool(
            metadata_identity_tokens(value, assertion=bool(assertion))
            & set(json.loads(wanted))
        ),
        deterministic=True,
    )


def identity_candidate_clause(reader, values: tuple[str, ...]) -> tuple[str, tuple]:
    """Return a bounded candidate superset; no period or availability filter."""
    tokens = tuple(sorted(_tokens(values)))
    if not tokens:
        return "AND 0", ()
    marks = ",".join("?" for _ in tokens)
    present = reader.fetchone(
        "SELECT 1 FROM sqlite_master WHERE name='source_identity_tokens'"
    )
    if present:
        return (
            f"""AND d.document_id IN (
            SELECT document_id FROM source_identity_tokens WHERE token IN ({marks})
            UNION SELECT document_id FROM source_identity_dirty)""",
            tokens,
        )
    # Historical read-only catalogs cannot be migrated on query. Narrow their
    # candidates in SQL instead of materializing every document in Python.
    wanted = json.dumps(tokens)
    return (
        f"""AND (d.document_id IN (
        SELECT de.document_id FROM document_entities de JOIN entities e ON e.entity_id=de.entity_id
        WHERE cwp_identity_token(e.entity_id) IN ({marks}) OR cwp_identity_token(e.name) IN ({marks}))
        OR cwp_identity_member(d.metadata_json,?,0)
        OR d.primary_source_id IN (SELECT a.source_id FROM source_metadata_assertions a
            WHERE a.decision='verified' AND (cwp_identity_token(a.entity) IN ({marks})
              OR cwp_identity_token(a.security_id) IN ({marks})
              OR cwp_identity_member(a.evidence_json,?,1))))""",
        (*tokens, *tokens, wanted, *tokens, *tokens, wanted),
    )
