"""ZR-304 gate tests: producer attempt journal + normalized artifact read
model (one production read semantics)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.artifact_read_model import (  # noqa: E402
    ARTIFACT_READ_MODEL_SCHEMA,
    ARTIFACT_READ_MODEL_SCHEMA_VERSION,
    read_artifact,
    read_artifacts,
)
from company_wiki.source_catalog.producer_journal import (  # noqa: E402
    PRODUCER_ATTEMPTS_DDL,
    ProducerJournalError,
    attempts_for,
    calls_this_request,
    record_attempt,
)
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402

# Registered generator for ArtifactHandle compatibility checks.
REGISTRY = {"normalizer": {"1.0.0"}, "llm": {"2.0.0"}}
NOW = "2099-12-31T23:59:59Z"


class _Store:
    def __init__(self, con: sqlite3.Connection):
        self._con = con
        self._con.row_factory = sqlite3.Row

    def fetchall(self, sql: str, params=()):
        return self._con.execute(sql, tuple(params)).fetchall()


def _seed_db(path: Path, *, with_binding: bool = True) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT,
            title TEXT NOT NULL, source_type TEXT NOT NULL,
            document_kind TEXT NOT NULL, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL,
            first_seen_at TEXT NOT NULL
        );
        CREATE TABLE artifacts (
            artifact_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            source_id TEXT, artifact_role TEXT NOT NULL, path TEXT NOT NULL,
            content_sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL, generator_name TEXT NOT NULL,
            generator_version TEXT NOT NULL, status TEXT NOT NULL,
            error TEXT, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE artifact_bindings (
            binding_id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL UNIQUE,
            source_id TEXT NOT NULL, document_id TEXT NOT NULL,
            content_sha256 TEXT NOT NULL, generator_name TEXT NOT NULL,
            generator_version TEXT NOT NULL, bundle_hash TEXT NOT NULL,
            evidence_basis TEXT NOT NULL, visibility_state TEXT NOT NULL,
            schema_version TEXT NOT NULL, created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        """
    )
    con.executescript(PRODUCER_ATTEMPTS_DDL)
    con.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?)",
        ("s1", "a" * 64, 100, "application/pdf", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO documents (document_id, primary_source_id, title, "
        "source_type, document_kind, published_date, source_status, "
        "metadata_priority, metadata_json, first_seen_at, last_seen_at) "
        "VALUES ('d1','s1','Acme 2025 Annual','file','annual_report',"
        "'2026-03-20','active',10,'{}','2026-01-01','2026-01-01')"
    )
    con.commit()
    return con


def _artifact_file(tmp_path: Path) -> Path:
    target = tmp_path / "artifacts" / "n.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'{"rows": []}')
    return target


def _seed_artifact(con: sqlite3.Connection, tmp_path: Path) -> str:
    import hashlib

    target = _artifact_file(tmp_path)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    con.execute(
        "INSERT INTO artifacts (artifact_id, document_id, source_id, "
        "artifact_role, path, content_sha256, byte_size, mime_type, "
        "generator_name, generator_version, status, error, metadata_json, "
        "created_at) VALUES ('a1','d1','s1','normalized',?,?,?,?,?,?,?,?,?,?)",
        (
            str(target), sha, target.stat().st_size, "application/json",
            "normalizer", "1.0.0", "completed", None,
            json.dumps({"schema_version": "1.0", "source_sha256": "a" * 64}),
            "2026-01-02T00:00:00Z",
        ),
    )
    con.execute(
        "INSERT INTO artifact_bindings (binding_id, artifact_id, source_id, "
        "document_id, content_sha256, generator_name, generator_version, "
        "bundle_hash, evidence_basis, visibility_state, schema_version, "
        "created_at, created_by) VALUES ('b1','a1','s1','d1',?,'normalizer',"
        "'1.0.0',?,'legacy-artifact-backfill','shadow','1.0',"
        "'2026-01-02T00:00:00Z','fc-901')",
        (sha, "c" * 64),
    )
    con.commit()
    return sha


# ---------------------------------------------------------------------------
# producer attempt journal
# ---------------------------------------------------------------------------


def test_record_attempt_failed_without_artifact(tmp_path) -> None:
    """A FAILED producer run is recorded even though no artifact exists."""
    con = _seed_db(tmp_path / "catalog.sqlite3")
    row = record_attempt(
        con, "d1", producer_name="llm", producer_version="2.0.0",
        outcome="failed", artifact_role="summary",
        created_at="2026-01-02T00:00:00Z", request_id="req-1",
    )
    con.commit()
    assert row["outcome"] == "failed"
    assert row["request_id"] == "req-1"
    attempts = attempts_for(_Store(con), "d1")
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "failed"
    assert attempts[0]["artifact_role"] == "summary"


def test_calls_this_request_separates_history(tmp_path) -> None:
    """calls_this_request counts ONLY the tagged request; historical
    attempts (request_id NULL) never leak into the count."""
    con = _seed_db(tmp_path / "catalog.sqlite3")
    record_attempt(con, "d1", producer_name="llm", producer_version="2.0.0",
                   outcome="succeeded", artifact_role="summary",
                   created_at="2026-01-01T00:00:00Z")  # history
    record_attempt(con, "d1", producer_name="llm", producer_version="2.0.0",
                   outcome="failed", artifact_role="summary",
                   created_at="2026-01-02T00:00:00Z", request_id="req-9")
    record_attempt(con, "d1", producer_name="parser", producer_version="1.0.0",
                   outcome="succeeded", artifact_role="normalized",
                   created_at="2026-01-02T00:00:01Z", request_id="req-9")
    con.commit()
    counts = calls_this_request(_Store(con), "d1", "req-9")
    assert counts == {"succeeded": 1, "failed": 1}
    assert len(attempts_for(_Store(con), "d1")) == 3


def test_record_attempt_validation(tmp_path) -> None:
    con = _seed_db(tmp_path / "catalog.sqlite3")
    with pytest.raises(ProducerJournalError, match="outcome"):
        record_attempt(con, "d1", producer_name="p", producer_version="1",
                       outcome="maybe", artifact_role="r",
                       created_at="2026-01-01T00:00:00Z")
    with pytest.raises(ProducerJournalError, match="document_id"):
        record_attempt(con, " ", producer_name="p", producer_version="1",
                       outcome="succeeded", artifact_role="r",
                       created_at="2026-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# normalized artifact read model
# ---------------------------------------------------------------------------


def test_read_model_schema_versioned() -> None:
    assert ARTIFACT_READ_MODEL_SCHEMA_VERSION == "1.0"
    assert ARTIFACT_READ_MODEL_SCHEMA == "artifact-read-model-1.0"


def test_read_artifact_bound_uses_binding(tmp_path) -> None:
    con = _seed_db(tmp_path / "catalog.sqlite3")
    _seed_artifact(con, tmp_path)
    reader = ReadOnlyCatalogReader(tmp_path / "catalog.sqlite3")
    try:
        artifact = read_artifact(
            reader, "a1", registry=REGISTRY, allowed_roots=(tmp_path,), now=NOW
        )
        assert artifact is not None
        assert artifact.binding == "bound"
        assert artifact.bundle_hash == "c" * 64
        assert artifact.visibility_state == "shadow"
        assert artifact.content_sha256 == artifact.content_sha256
        assert artifact.to_dict()["schema_version"] == "1.0"
    finally:
        reader.close()


def test_read_artifact_legacy_fallback(tmp_path) -> None:
    """Without a binding row, the read model falls back to the artifacts
    columns and marks binding='legacy' (still normalized + validated)."""
    con = _seed_db(tmp_path / "catalog.sqlite3")
    _seed_artifact(con, tmp_path)
    con.execute("DELETE FROM artifact_bindings")
    con.commit()
    reader = ReadOnlyCatalogReader(tmp_path / "catalog.sqlite3")
    try:
        artifact = read_artifact(
            reader, "a1", registry=REGISTRY, allowed_roots=(tmp_path,), now=NOW
        )
        assert artifact is not None
        assert artifact.binding == "legacy"
        assert artifact.bundle_hash is None
        assert artifact.source_id == "s1"
    finally:
        reader.close()


def test_read_artifact_missing_source_sha_fails_closed(tmp_path) -> None:
    con = _seed_db(tmp_path / "catalog.sqlite3")
    target = _artifact_file(tmp_path)
    con.execute(
        "INSERT INTO artifacts (artifact_id, document_id, source_id, "
        "artifact_role, path, content_sha256, byte_size, mime_type, "
        "generator_name, generator_version, status, error, metadata_json, "
        "created_at) VALUES ('a1','d1','s1','normalized',?,?,?,?,?,?,?,?,?,?)",
        (
            str(target), "", target.stat().st_size, "application/json",
            "normalizer", "1.0.0", "completed", None, "{}",
            "2026-01-02T00:00:00Z",
        ),
    )
    con.commit()
    reader = ReadOnlyCatalogReader(tmp_path / "catalog.sqlite3")
    try:
        with pytest.raises(ValueError, match="content_sha256"):
            read_artifact(reader, "a1", registry=REGISTRY,
                          allowed_roots=(tmp_path,), now=NOW)
    finally:
        reader.close()


def test_read_artifact_unknown_role_fails_closed(tmp_path) -> None:
    con = _seed_db(tmp_path / "catalog.sqlite3")
    target = _artifact_file(tmp_path)
    import hashlib

    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    con.execute(
        "INSERT INTO artifacts (artifact_id, document_id, source_id, "
        "artifact_role, path, content_sha256, byte_size, mime_type, "
        "generator_name, generator_version, status, error, metadata_json, "
        "created_at) VALUES ('a1','d1','s1','bogus_role',?,?,?,?,?,?,?,?,?,?)",
        (
            str(target), sha, target.stat().st_size, "application/json",
            "normalizer", "1.0.0", "completed", None,
            json.dumps({"schema_version": "1.0", "source_sha256": "a" * 64}),
            "2026-01-02T00:00:00Z",
        ),
    )
    con.commit()
    reader = ReadOnlyCatalogReader(tmp_path / "catalog.sqlite3")
    try:
        with pytest.raises(ValueError, match="unknown role"):
            read_artifact(reader, "a1", registry=REGISTRY,
                          allowed_roots=(tmp_path,), now=NOW)
    finally:
        reader.close()


def test_read_artifacts_orders_and_reads_all(tmp_path) -> None:
    con = _seed_db(tmp_path / "catalog.sqlite3")
    _seed_artifact(con, tmp_path)
    reader = ReadOnlyCatalogReader(tmp_path / "catalog.sqlite3")
    try:
        artifacts = read_artifacts(
            reader, "d1", registry=REGISTRY, allowed_roots=(tmp_path,), now=NOW
        )
        assert len(artifacts) == 1
        assert artifacts[0].artifact_id == "a1"
    finally:
        reader.close()
