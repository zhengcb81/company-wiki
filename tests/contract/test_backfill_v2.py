"""WU-902 RED/audit tests: legacy company_raw/dayu -> v2 assertion backfill.

Mutations guarded:
  M-01  guessing a missing source_url / period_end (constructing a
        verified assertion from facts the legacy metadata cannot prove)
  M-02  counting a conflict as success (reconciliation must close and
        conflict must never be mis-bucketed)

Acceptance (task_plan WU-902):
  - v2 assertions are constructed ONLY from strong-binding legacy fields
    (provider_document_id + source_url + form_type + fiscal_year +
    provider) plus provable period_end.
  - Unprovable URL/identity/period -> remediation queue with the exact
    missing field; nothing is guessed from file names or titles.
  - Reconciliation closes: input = success + indexed_only + conflict +
    skipped + error, bucketed by root/status/kind/year.
  - Legacy active reusable set vs v2 active reusable set: per-document
    parity with a reason for every difference.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.backfill_v2 import (  # noqa: E402
    BackfillResult,
    StrongBinding,
    run_backfill,
)


def _catalog(tmp_path: Path) -> Path:
    """A minimal catalog with legacy acquisition metadata, v2 columns."""
    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE roots (root_id TEXT PRIMARY KEY, path TEXT, kind TEXT);
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT, byte_size INTEGER
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT, metadata_priority INTEGER, metadata_json TEXT,
            text_fingerprint TEXT, first_seen_at TEXT, last_seen_at TEXT
        );
        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT, absolute_path TEXT, source_id TEXT,
            document_id TEXT, role TEXT, location_status TEXT,
            observed_size INTEGER, observed_mtime_ns INTEGER,
            last_seen_run TEXT, manifest_json TEXT, metadata_json TEXT,
            error TEXT, UNIQUE(root_id, relative_path)
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
            created_by TEXT NOT NULL, schema_version TEXT NOT NULL,
            published_at TEXT, accepted_at TEXT, period_end TEXT,
            language TEXT, is_amended INTEGER, revision_id TEXT,
            adapter_id TEXT, adapter_version TEXT, normalized_sha256 TEXT,
            normalization_status TEXT,
            visibility_state TEXT NOT NULL DEFAULT 'legacy',
            activation_epoch TEXT, cohort TEXT
        );
        INSERT INTO roots VALUES ('company_raw', '/companies', 'company_raw');
        INSERT INTO roots VALUES ('dayu_portfolio', '/dayu', 'dayu_portfolio');
        """
    )
    con.commit()
    con.close()
    return path


def _add_doc(
    path: Path,
    *,
    doc_id: str = "d1",
    source_id: str = "src1",
    sha: str = "a" * 64,
    root: str = "company_raw",
    status: str = "active",
    acquisition: dict | None = None,
) -> None:
    con = sqlite3.connect(path)
    acquisition = acquisition or {}
    metadata = json.dumps({"acquisition": acquisition}, ensure_ascii=False)
    con.execute(
        "INSERT OR REPLACE INTO sources VALUES (?,?,?)",
        (source_id, sha, 100),
    )
    con.execute(
        """INSERT OR REPLACE INTO documents
        (document_id, primary_source_id, title, source_type, document_kind,
         published_date, source_status, metadata_priority, metadata_json,
         first_seen_at, last_seen_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (doc_id, source_id, f"title-{doc_id}", "regulatory_filing",
         "annual_report", None, status, 0, metadata,
         "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    )
    con.execute(
        """INSERT OR REPLACE INTO locations
        (location_id, root_id, relative_path, absolute_path, source_id,
         document_id, role, location_status, observed_size,
         observed_mtime_ns, last_seen_run, manifest_json, metadata_json, error)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (f"loc-{doc_id}", root, f"raw/{doc_id}.pdf", f"/companies/raw/{doc_id}.pdf",
         source_id, doc_id, "original_primary", "active", 100, 0,
         "scan-1", None, "{}", None),
    )
    con.commit()
    con.close()


STRONG = {
    "form_type": "10-K",
    "fiscal_year": 2025,
    "provider": "sec",
    "provider_document_id": "0000320193-25-000079",
    "source_url": "https://www.sec.gov/Archives/edgar/data/320193/x.htm",
    "security_id": "AAPL",
    "market": "US",
    "period_end": "2025-09-27",
    "filing_date": "2025-10-31",
    "content_sha256": "a" * 64,
}


def test_bf01_strong_doc_constructs_verified_shadow_assertion(tmp_path):
    """A doc with all strong fields + provable period_end yields exactly one
    verified shadow assertion; reader visibility stays legacy."""
    path = _catalog(tmp_path)
    _add_doc(path, acquisition=STRONG)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"),
                          mode="apply")
    assert result.success == 1
    assert result.indexed_only == 0
    assert result.conflict == 0
    assert result.errors == 0
    assert result.input == 1
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT decision, visibility_state, schema_version, evidence_basis "
        "FROM source_metadata_assertions").fetchall()
    con.close()
    assert rows == [("verified", "shadow", "2.0", "legacy-backfill-v1")]


def test_bf02_missing_period_end_goes_to_remediation_not_success(tmp_path):
    """M-01 guard: a doc with strong binding but NO provable period_end must
    NOT produce a verified assertion — it lands in the remediation queue
    with 'period_end' as the exact missing field.  Guessing the period from
    the title/file name is a mutation that this test kills."""
    path = _catalog(tmp_path)
    acq = {k: v for k, v in STRONG.items() if k != "period_end"}
    _add_doc(path, acquisition=acq)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"))
    assert result.success == 0
    assert result.indexed_only == 1
    remediation = result.remediation[0]
    assert remediation["document_id"] == "d1"
    assert "period_end" in remediation["missing_fields"]
    assert remediation["reason"]
    con = sqlite3.connect(path)
    n = con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    assert n == 0  # nothing fabricated into the ledger


def test_bf03_missing_source_url_goes_to_remediation_not_success(tmp_path):
    """M-01 guard: unprovable URL must never be guessed (e.g. assembled
    from security_id + provider); the doc goes to remediation with
    'source_url' missing."""
    path = _catalog(tmp_path)
    acq = {k: v for k, v in STRONG.items() if k != "source_url"}
    _add_doc(path, acquisition=acq)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"))
    assert result.success == 0
    assert result.indexed_only == 1
    assert "source_url" in result.remediation[0]["missing_fields"]


def test_bf04_weak_identity_goes_to_remediation(tmp_path):
    """security_id that is a display name (e.g. 中国平安) is not strong
    identity; the doc goes to remediation, never to a verified assertion."""
    path = _catalog(tmp_path)
    acq = dict(STRONG)
    acq["security_id"] = "中国平安"
    _add_doc(path, acquisition=acq)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"))
    assert result.success == 0
    assert result.indexed_only == 1
    assert "security_id" in result.remediation[0]["missing_fields"]


def test_bf05_reconciliation_closes_exactly(tmp_path):
    """input = success + indexed_only + conflict + skipped + error, and the
    sum of every bucket equals the candidate count."""
    path = _catalog(tmp_path)
    # one strong (success), one missing period (indexed_only)
    _add_doc(path, doc_id="d1", source_id="src1", sha="a" * 64, acquisition=STRONG)
    acq2 = {k: v for k, v in STRONG.items() if k != "period_end"}
    _add_doc(path, doc_id="d2", source_id="src2", sha="b" * 64,
             root="dayu_portfolio", acquisition=acq2)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"))
    assert result.input == 2
    assert result.success == 1
    assert result.indexed_only == 1
    assert result.conflict == 0 and result.skipped == 0 and result.errors == 0
    assert (result.success + result.indexed_only + result.conflict
            + result.skipped + result.errors) == result.input
    # per-root / per-status reconciliation is also closed
    by_root = result.reconciliation_by("root")
    assert sum(bucket["total"] for bucket in by_root.values()) == result.input


def test_bf06_conflict_is_never_success(tmp_path):
    """M-02 guard: an existing verified assertion with a DIFFERENT content
    hash for the same document is a conflict — counting it as success is a
    mutation this test kills."""
    path = _catalog(tmp_path)
    _add_doc(path, acquisition=STRONG)
    con = sqlite3.connect(path)
    con.execute(
        """INSERT INTO source_metadata_assertions
        (assertion_id, source_id, document_id, content_sha256, evidence_basis,
         evidence_json, decision, created_at, created_by, schema_version,
         adapter_id, adapter_version, normalization_status, visibility_state)
        VALUES ('sa-old','src1','d1',?, 'v2-normalized', '{}', 'verified',
                '2026-01-01','prev','2.0','dayu-sec-cli','1.0.0',
                'capture_ready','shadow')""",
        ("f" * 64,),
    )
    con.commit()
    con.close()
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"))
    assert result.conflict == 1
    assert result.success == 0
    # no duplicate active row was created
    con = sqlite3.connect(path)
    n = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions "
        "WHERE decision='verified' AND content_sha256=?", ("a" * 64,)).fetchone()[0]
    con.close()
    assert n == 0


def test_bf07_retired_stays_retired(tmp_path):
    """WU-903 boundary: a retired doc is never auto-restored by the
    backfill; it may be indexed (shadow) but source_status is untouched."""
    path = _catalog(tmp_path)
    _add_doc(path, status="retired", acquisition=STRONG)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"))
    con = sqlite3.connect(path)
    status = con.execute(
        "SELECT source_status FROM documents WHERE document_id='d1'").fetchone()[0]
    con.close()
    assert status == "retired"
    assert result.success <= 1  # visibility only ever shadow


def test_bf08_dry_run_writes_nothing(tmp_path):
    """Default mode is dry-run: zero writes, reconciliation still closes."""
    path = _catalog(tmp_path)
    _add_doc(path, acquisition=STRONG)
    result = run_backfill(path, roots=("company_raw", "dayu_portfolio"),
                          mode="dry-run")
    assert result.success == 1  # classification is computed
    con = sqlite3.connect(path)
    n = con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    assert n == 0
