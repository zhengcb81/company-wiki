"""ZR-303 gate tests: unified readiness decision graph.

Composes ZR-301 (eight-stage readiness) with ZR-302 (safety guard): the
safety verdict comes from the guard's cache evaluation; every blocker has
a next action (no dead ends); the same inputs produce the same decision
(deterministic); not_reviewed is never faked green.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.prompt_injection import (  # noqa: E402
    PROMPT_INJECTION_REVIEW_KEY,
    PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
    record_prompt_injection_review,
)
from company_wiki.source_catalog.prompt_injection_guard import RULESET_HASH  # noqa: E402
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402
from company_wiki.source_catalog.readiness_graph import (  # noqa: E402
    READINESS_GRAPH_SCHEMA,
    READINESS_GRAPH_SCHEMA_VERSION,
    ReadinessBlocker,
    ReadinessDecision,
    evaluate_readiness,
)
from company_wiki.source_catalog.source_lifecycle import ConsumerRequirements  # noqa: E402

NOW = "2026-08-02T00:00:00Z"
TTL = 86400 * 30
S1 = "a" * 64


def _seed(path: Path, *, safety_status: str | None = "not_detected") -> Path:
    """Real schema: fully-satisfied source s1 + bare source s2."""
    db = path / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO catalog_meta VALUES ('schema_version','1.2.0');
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL,
            first_seen_at TEXT NOT NULL
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT,
            title TEXT NOT NULL, source_type TEXT NOT NULL,
            document_kind TEXT NOT NULL, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE artifacts (
            artifact_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            source_id TEXT, artifact_role TEXT NOT NULL, path TEXT NOT NULL,
            content_sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL, generator_name TEXT NOT NULL,
            generator_version TEXT NOT NULL, status TEXT NOT NULL,
            error TEXT, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE evidence_spans (
            span_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            source_id TEXT NOT NULL, locator TEXT NOT NULL,
            page_number INTEGER, paragraph_index INTEGER, table_index INTEGER,
            raw_text TEXT, span_json TEXT NOT NULL, parser_name TEXT NOT NULL,
            parser_version TEXT NOT NULL, parse_status TEXT NOT NULL,
            UNIQUE(source_id, locator)
        );
        CREATE TABLE source_metadata_assertions (
            assertion_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
            document_id TEXT NOT NULL, entity TEXT, market TEXT,
            security_id TEXT, document_kind TEXT, form_type TEXT,
            fiscal_year INTEGER, fiscal_period TEXT, provider TEXT,
            provider_document_id TEXT, source_url TEXT, filing_date TEXT,
            content_sha256 TEXT NOT NULL, evidence_basis TEXT NOT NULL,
            evidence_json TEXT NOT NULL, decision TEXT NOT NULL,
            supersedes_assertion_id TEXT, created_at TEXT NOT NULL,
            created_by TEXT NOT NULL, schema_version TEXT NOT NULL
        );
        """
    )
    con.execute(
        "INSERT INTO roots (root_id, path, kind, priority, last_scan_run, "
        "last_scanned_at) VALUES ('company_raw', '/tmp/companies', "
        "'company_raw', 10, '', '')"
    )
    con.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?)",
        ("s1", S1, 100, "application/pdf", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO documents (document_id, primary_source_id, title, "
        "source_type, document_kind, published_date, source_status, "
        "metadata_priority, metadata_json, first_seen_at, last_seen_at) "
        "VALUES ('d1','s1','Acme 2025 Annual','file','annual_report',"
        "'2026-03-20','active',10,?, '2026-01-01','2026-01-01')",
        (
            json.dumps(
                {
                    PROMPT_INJECTION_REVIEW_KEY: {
                        "schema_version": PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
                        "status": safety_status or "not_detected",
                        "reviewer": "zr303-probe",
                        "reviewed_at": "2026-08-01T00:00:00Z",
                        "evidence_sha256": "e" * 64,
                        "source_sha256": S1,
                        "policy_hash": RULESET_HASH,
                    }
                }
            ),
        ),
    )
    con.execute(
        "INSERT INTO locations (location_id, root_id, relative_path, "
        "absolute_path, source_id, document_id, role, location_status, "
        "observed_size, observed_mtime_ns, last_seen_run, metadata_json) "
        "VALUES ('l1','company_raw','a.pdf','/tmp/a.pdf','s1','d1',"
        "'original','active',100,0,'2026-01-01','{}')"
    )
    con.execute(
        "INSERT INTO artifacts (artifact_id, document_id, source_id, "
        "artifact_role, path, content_sha256, byte_size, mime_type, "
        "generator_name, generator_version, status, error, metadata_json, "
        "created_at) VALUES ('a1','d1','s1','normalized','/tmp/n.json',"
        "?, 10, 'application/json', 'normalizer', '1.0.0', 'completed', "
        "NULL, '{}', '2026-01-02')",
        ("c" * 64,),
    )
    con.execute(
        "INSERT INTO evidence_spans (span_id, document_id, source_id, "
        "locator, span_json, parser_name, parser_version, parse_status) "
        "VALUES ('sp1','d1','s1','p1','{}','parser','1.0.0','ok')"
    )
    con.execute(
        "INSERT INTO source_metadata_assertions (assertion_id, source_id, "
        "document_id, content_sha256, evidence_basis, evidence_json, "
        "decision, created_at, created_by, schema_version) VALUES "
        "('as1','s1','d1',?,'identity-match','{}','verified',"
        "'2026-01-01','zr303-probe','1.0')",
        (S1,),
    )
    con.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?)",
        ("s2", "e" * 64, 50, "application/pdf", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO locations (location_id, root_id, relative_path, "
        "absolute_path, source_id, document_id, role, location_status, "
        "observed_size, observed_mtime_ns, last_seen_run, metadata_json) "
        "VALUES ('l2','company_raw','b.pdf','/tmp/b.pdf','s2',NULL,"
        "'original','missing',0,0,'2026-01-01','{}')"
    )
    con.commit()
    con.close()
    return db


def _args(**overrides):
    base = {
        "policy_hash": RULESET_HASH,
        "source_sha256": S1,
        "now": NOW,
        "ttl_seconds": TTL,
    }
    base.update(overrides)
    return base


def test_schema_versioned() -> None:
    assert READINESS_GRAPH_SCHEMA_VERSION == "1.0"
    assert READINESS_GRAPH_SCHEMA == "readiness-graph-1.0"


def test_ready_source_all_stages(tmp_path) -> None:
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        decision = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(
                required_stages=(
                    "identity", "resolution", "freshness", "acquisition",
                    "safety", "artifact", "semantic", "consumer",
                )
            ),
            **_args(),
        )
        assert isinstance(decision, ReadinessDecision)
        assert decision.ready is True
        assert decision.blockers == ()
        assert decision.safety_cache_state == "hit"
    finally:
        reader.close()


def test_safety_guard_drives_graph(tmp_path) -> None:
    """safety verdict comes from the guard, not the raw receipt presence:
    a stale (expired) receipt blocks the graph."""
    db = _seed(tmp_path, safety_status="not_detected")
    reader = ReadOnlyCatalogReader(db)
    try:
        decision = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(required_stages=("safety",)),
            **_args(ttl_seconds=1),  # receipt reviewed 1 day ago, TTL 1s
        )
        assert decision.ready is False
        assert decision.safety_cache_state == "expired"
        safety = [b for b in decision.blockers if b.stage == "safety"]
        assert len(safety) == 1
        assert "re-review" in safety[0].next_action
    finally:
        reader.close()


def test_safety_tampered_blocks_with_action(tmp_path) -> None:
    """A tampered safety receipt (source bytes changed) blocks with a
    concrete next action — never faked green."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        decision = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(required_stages=("safety",)),
            **_args(source_sha256="b" * 64),  # bytes changed since review
        )
        assert decision.ready is False
        assert decision.safety_cache_state == "tampered"
        safety = [b for b in decision.blockers if b.stage == "safety"]
        assert len(safety) == 1
        assert "verify source bytes" in safety[0].next_action
    finally:
        reader.close()


def test_safety_ignored_blocks_with_action(tmp_path) -> None:
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        decision = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(required_stages=("safety",)),
            **_args(policy_hash="c" * 64),  # ruleset changed
        )
        assert decision.ready is False
        assert decision.safety_cache_state == "ignored"
        safety = [b for b in decision.blockers if b.stage == "safety"]
        assert len(safety) == 1
        assert "re-scan with the current ruleset" in safety[0].next_action
    finally:
        reader.close()


def test_safety_absent_blocks_with_action(tmp_path) -> None:
    db = _seed(tmp_path, safety_status=None)
    con = sqlite3.connect(db)
    con.execute(
        "UPDATE documents SET metadata_json='{}' WHERE document_id='d1'"
    )
    con.commit()
    con.close()
    reader = ReadOnlyCatalogReader(db)
    try:
        decision = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(required_stages=("safety",)),
            **_args(),
        )
        assert decision.ready is False
        assert decision.safety_cache_state == "absent"
        safety = [b for b in decision.blockers if b.stage == "safety"]
        assert len(safety) == 1
        assert "run the prompt-injection scanner" in safety[0].next_action
    finally:
        reader.close()


def test_bare_source_blockers_have_next_actions(tmp_path) -> None:
    """Every blocker of a bare source has a next action (no dead ends)."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        decision = evaluate_readiness(
            reader, "s2",
            requirements=ConsumerRequirements(
                required_stages=(
                    "identity", "resolution", "freshness", "acquisition",
                    "safety", "artifact", "semantic", "consumer",
                )
            ),
            **_args(),
        )
        assert decision.ready is False
        assert decision.blockers
        for blocker in decision.blockers:
            assert isinstance(blocker, ReadinessBlocker)
            assert blocker.next_action, f"{blocker.stage} has no next action"
    finally:
        reader.close()


def test_deterministic_same_inputs_same_decision(tmp_path) -> None:
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        args = _args()
        first = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(required_stages=("safety", "artifact")),
            **args,
        )
        second = evaluate_readiness(
            reader, "s1",
            requirements=ConsumerRequirements(required_stages=("safety", "artifact")),
            **args,
        )
        assert first == second
        assert first.ready == second.ready
        assert first.safety_cache_state == second.safety_cache_state
    finally:
        reader.close()


def test_requirements_drive_ready(tmp_path) -> None:
    """Empty requirements -> trivially ready; a required missing stage
    blocks."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        trivial = evaluate_readiness(reader, "s2", **_args())
        assert trivial.ready is True
        blocked = evaluate_readiness(
            reader, "s2",
            requirements=ConsumerRequirements(required_stages=("acquisition",)),
            **_args(),
        )
        assert blocked.ready is False
        acquisition = [b for b in blocked.blockers if b.stage == "acquisition"]
        assert len(acquisition) == 1
        assert "acquire/restore" in acquisition[0].next_action
    finally:
        reader.close()
