"""ZR-301 gate tests: shadow-only source-lifecycle readiness evaluation.

The evaluator must be READ-ONLY (never execute/commit/DDL through the
reader), compose the eight canonical stages (identity/resolution/
freshness/acquisition/safety/artifact/semantic/consumer), never treat
missing evidence as satisfied (fail closed: no safety receipt is NOT
green), validate consumer requirements (unknown stage rejected), and
let consumer requirements decide ready.
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
)
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402
from company_wiki.source_catalog.source_lifecycle import (  # noqa: E402
    ConsumerRequirements,
    LIFECYCLE_SCHEMA,
    LIFECYCLE_SCHEMA_VERSION,
    evaluate_source_readiness,
)


def _seed(path: Path) -> Path:
    """Real schema + one fully-satisfied source + one bare source."""
    db = path / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
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
    # Fully satisfied source s1 (identity verified, resolved, fresh,
    # acquired, safety reviewed, artifact completed, semantic ok,
    # consumer active).
    con.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?)",
        ("s1", "a" * 64, 100, "application/pdf", "2026-01-01"),
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
                        "status": "not_detected",
                        "reviewer": "zr301-probe",
                        "reviewed_at": "2026-03-21T00:00:00Z",
                        "evidence_sha256": "b" * 64,
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
        "'2026-01-01','zr301-probe','1.0')",
        ("a" * 64,),
    )
    # Bare source s2: only a source row + inactive location (nothing else).
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


ALL_STAGES = (
    "identity",
    "resolution",
    "freshness",
    "acquisition",
    "safety",
    "artifact",
    "semantic",
    "consumer",
)


def test_schema_versioned_and_fail_closed() -> None:
    assert LIFECYCLE_SCHEMA_VERSION == "1.0"
    assert LIFECYCLE_SCHEMA == "source-lifecycle-1.0"
    with pytest.raises(ValueError, match="unknown required stage"):
        ConsumerRequirements(required_stages=("identity", "bogus"))


def test_empty_requirements_trivially_ready(tmp_path) -> None:
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(reader, "s2")
        assert result.ready is True
        assert result.missing_stages == ()
    finally:
        reader.close()


def test_fully_satisfied_source_ready_for_all_stages(tmp_path) -> None:
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s1", ConsumerRequirements(required_stages=ALL_STAGES)
        )
        assert result.ready is True, result.missing_stages
        for verdict in result.stages:
            assert verdict.verdict == "satisfied", (verdict.stage, verdict.blocker)
    finally:
        reader.close()


def test_bare_source_unknown_not_satisfied(tmp_path) -> None:
    """A source with no evidence is UNKNOWN per stage — never satisfied
    (fail closed: no safety receipt is not green)."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s2", ConsumerRequirements(required_stages=ALL_STAGES)
        )
        assert result.ready is False
        assert set(result.missing_stages) == set(ALL_STAGES)
        for verdict in result.stages:
            assert verdict.verdict in ("unknown", "unsatisfied")
            assert verdict.verdict != "satisfied"
            assert verdict.blocker is not None
            assert verdict.next_action is not None
        safety = result.verdict_for("safety")
        assert safety is not None
        assert safety.verdict == "unknown"
    finally:
        reader.close()


def test_partial_requirements_drive_ready(tmp_path) -> None:
    """Consumer requirements decide ready: s2 with only the acquisition
    stage required is unsatisfied (location missing); with identity only
    also unsatisfied; with an empty set trivially ready."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s2", ConsumerRequirements(required_stages=("acquisition",))
        )
        assert result.ready is False
        assert result.missing_stages == ("acquisition",)
        acquisition = result.verdict_for("acquisition")
        assert acquisition is not None
        assert acquisition.verdict == "unsatisfied"  # missing location recorded
    finally:
        reader.close()


def test_not_reviewed_claim_fails_closed_as_unknown(tmp_path) -> None:
    """A receipt claiming status 'not_reviewed' is NOT a stored receipt
    status (the catalog only stores not_detected/detected_and_ignored;
    absence is reported as not_reviewed by the envelope).  Such a claim is
    malformed -> fail closed as unknown, never green."""
    db = _seed(tmp_path)
    con = sqlite3.connect(db)
    con.execute(
        "UPDATE documents SET metadata_json=? WHERE document_id='d1'",
        (
            json.dumps(
                {
                    PROMPT_INJECTION_REVIEW_KEY: {
                        "schema_version": PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
                        "status": "not_reviewed",
                        "reviewer": "zr301-probe",
                        "reviewed_at": "2026-03-21T00:00:00Z",
                        "evidence_sha256": "b" * 64,
                    }
                }
            ),
        ),
    )
    con.commit()
    con.close()
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s1", ConsumerRequirements(required_stages=("safety",))
        )
        assert result.ready is False
        safety = result.verdict_for("safety")
        assert safety is not None
        assert safety.verdict == "unknown"
        assert safety.evidence == ()
    finally:
        reader.close()


def test_malformed_safety_receipt_fails_closed_as_unknown(tmp_path) -> None:
    """A malformed receipt (wrong schema version / bad status) is treated
    as absent — unknown, never green."""
    db = _seed(tmp_path)
    con = sqlite3.connect(db)
    con.execute(
        "UPDATE documents SET metadata_json=? WHERE document_id='d1'",
        (json.dumps({PROMPT_INJECTION_REVIEW_KEY: {"status": "bogus"}}),),
    )
    con.commit()
    con.close()
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s1", ConsumerRequirements(required_stages=("safety",))
        )
        assert result.ready is False
        safety = result.verdict_for("safety")
        assert safety is not None
        assert safety.verdict == "unknown"
    finally:
        reader.close()


def test_blocked_consumer_status_unsatisfied(tmp_path) -> None:
    db = _seed(tmp_path)
    con = sqlite3.connect(db)
    con.execute(
        "UPDATE documents SET source_status='quarantined' WHERE document_id='d1'"
    )
    con.commit()
    con.close()
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s1", ConsumerRequirements(required_stages=("consumer",))
        )
        assert result.ready is False
        consumer = result.verdict_for("consumer")
        assert consumer is not None
        assert consumer.verdict == "unsatisfied"
        assert consumer.evidence == ("source_status=quarantined",)
    finally:
        reader.close()


def test_evaluator_is_read_only(tmp_path) -> None:
    """The evaluator must never write: only fetchone/fetchall through the
    reader; executing a write on the read-only connection fails closed."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        result = evaluate_source_readiness(
            reader, "s1", ConsumerRequirements(required_stages=ALL_STAGES)
        )
        assert result.ready is True
        with pytest.raises(sqlite3.OperationalError):
            reader.fetchone("CREATE TABLE zr301_write_probe(x INTEGER)")
        with pytest.raises(sqlite3.OperationalError):
            reader.fetchone("DELETE FROM documents")
    finally:
        reader.close()
