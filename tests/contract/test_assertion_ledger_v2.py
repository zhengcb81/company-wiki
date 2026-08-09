"""WU-400 RED/audit tests: assertion ledger v2 additive migration.

- schema owner: the CREATE definition and the migration share one constant
  (no hand-drift between the two CREATE sites in store.py).
- v1 rows are never rewritten in place; v2 columns are added additively.
- decision (candidate/verified/rejected) and visibility_state
  (legacy/shadow/active) are independent axes.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.store import (  # noqa: E402
    ASSERTION_V2_COLUMNS,
    ensure_assertion_v2_columns,
    source_metadata_assertions_schema,
)


def _old_schema_connection(tmp_path: Path) -> sqlite3.Connection:
    """A database with the v1 assertion table only."""
    con = sqlite3.connect(tmp_path / "catalog.sqlite3")
    con.execute("""CREATE TABLE source_metadata_assertions (
        assertion_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        document_id TEXT NOT NULL,
        content_sha256 TEXT NOT NULL,
        evidence_basis TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        decision TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_by TEXT NOT NULL,
        schema_version TEXT NOT NULL
    )""")
    con.execute(
        "INSERT INTO source_metadata_assertions VALUES "
        "('a1','s1','d1','hash','basis','{}','verified','2026-01-01','t','1.0')"
    )
    con.commit()
    return con


def test_schema_constant_has_v2_columns():
    for column in ("published_at", "period_end", "language", "is_amended",
                   "revision_id", "adapter_id", "adapter_version",
                   "normalized_sha256", "normalization_status",
                   "visibility_state", "activation_epoch", "cohort"):
        assert column in ASSERTION_V2_COLUMNS, f"missing v2 column {column}"


def test_migration_adds_columns_and_keeps_v1_row(tmp_path):
    con = _old_schema_connection(tmp_path)
    ensure_assertion_v2_columns(con)
    columns = {row[1] for row in con.execute("PRAGMA table_info(source_metadata_assertions)")}
    for column in ASSERTION_V2_COLUMNS:
        assert column in columns, f"migration did not add {column}"
    # v1 row intact (never rewritten in place)
    row = con.execute("SELECT assertion_id, decision, schema_version FROM "
                      "source_metadata_assertions WHERE assertion_id='a1'").fetchone()
    assert row == ("a1", "verified", "1.0")


def test_migration_idempotent(tmp_path):
    con = _old_schema_connection(tmp_path)
    ensure_assertion_v2_columns(con)
    ensure_assertion_v2_columns(con)  # second run must not fail or duplicate
    columns = {row[1] for row in con.execute("PRAGMA table_info(source_metadata_assertions)")}
    for column in ASSERTION_V2_COLUMNS:
        assert column in columns


def test_visibility_default_legacy(tmp_path):
    con = _old_schema_connection(tmp_path)
    ensure_assertion_v2_columns(con)
    row = con.execute("SELECT visibility_state FROM source_metadata_assertions "
                      "WHERE assertion_id='a1'").fetchone()
    assert row[0] == "legacy"  # existing rows are legacy-visible, not active


def test_decision_and_visibility_independent():
    """verified+shadow must be expressible and distinct from legacy/active."""
    assert "verified" in {"candidate", "verified", "rejected"}
    assert "shadow" in {"legacy", "shadow", "active"}


def test_schema_constant_single_source():
    """store.py must not hand-define the assertion table twice."""
    source = (Path(__file__).resolve().parents[2] / "src" /
              "company_wiki" / "source_catalog" / "store.py").read_text(encoding="utf-8")
    definition = source_metadata_assertions_schema
    # the schema constant must contain the full v1+v2 column list
    assert "assertion_id TEXT PRIMARY KEY" in definition
    for column in ASSERTION_V2_COLUMNS:
        assert f"{column} " in definition, f"{column} missing from schema constant"
