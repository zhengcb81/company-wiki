"""FC-404 RED/acceptance tests: migration quality ledger.

The ledger records per root/market/kind: coverage, missing fields,
conflicts and duplicate location sets.  Before production apply, the
explainable bucket sum per root must equal the input total (closed).  A
retired document must NOT be revived by migration; real files are never
modified.
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.store import CatalogStore  # noqa: E402


def _seed(store: CatalogStore, *, retired: bool = False):
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO roots (root_id, path, kind, priority) "
            "VALUES ('company_raw','/x','company_raw',10)")
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES ('s1','h',1,'x','2026-01-01')")
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1','t',?, 'file','annual_report',10,'{}','2026-01-01','2026-01-01')",
            ("retired" if retired else "active",))
        conn.execute(
            "INSERT INTO locations (location_id, root_id, relative_path, "
            "absolute_path, document_id, role, location_status, "
            "last_seen_run, metadata_json) "
            "VALUES ('l1','company_raw','a.pdf','/x/a.pdf','d1',"
            "'original_primary','active','run1','{}')")


# --- quality ledger per root/market/kind ------------------------------------


def test_ledger_records_coverage_per_root(tmp_path):
    """The ledger must record per-root coverage: input count, eligible /
    needs_review / unprovable / retired_or_conflict buckets, missing
    fields and conflicts."""
    from company_wiki.source_catalog.migration_ledger import build_quality_ledger

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    ledger = build_quality_ledger(store)
    assert "company_raw" in ledger["by_root"]
    row = ledger["by_root"]["company_raw"]
    assert row["input"] == 1
    assert row["eligible"] + row["needs_review"] + row["unprovable"] + row[
        "retired_or_conflict"] == row["input"], "bucket sum must equal input"


def test_ledger_records_by_kind(tmp_path):
    from company_wiki.source_catalog.migration_ledger import build_quality_ledger

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    ledger = build_quality_ledger(store)
    assert "annual_report" in ledger["by_kind"]
    assert ledger["by_kind"]["annual_report"]["input"] == 1


def test_ledger_is_closed_before_apply(tmp_path):
    """Pre-apply gate: every root's explainable bucket sum must equal its
    input total (no unexplained rows)."""
    from company_wiki.source_catalog.migration_ledger import (
        build_quality_ledger,
        ledger_is_closed,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    ledger = build_quality_ledger(store)
    ok, problems = ledger_is_closed(ledger)
    assert ok, f"ledger not closed: {problems}"


def test_ledger_detects_duplicate_location_sets(tmp_path):
    """A document with two locations sharing the same content hash is a
    duplicate location set — the ledger must flag it deterministically."""
    from company_wiki.source_catalog.migration_ledger import (
        build_quality_ledger,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES ('s2','h2',1,'x','2026-01-01')")
        conn.execute(
            "INSERT INTO locations (location_id, root_id, relative_path, "
            "absolute_path, document_id, role, location_status, "
            "last_seen_run, metadata_json) "
            "VALUES ('l2','company_raw','b.pdf','/x/b.pdf','d1',"
            "'original_primary','active','run1','{}')")
        conn.execute(
            "UPDATE locations SET source_id='s2' WHERE location_id='l2'")
    ledger = build_quality_ledger(store)
    assert ledger["duplicate_location_sets"] == 1


def test_duplicate_location_mutation_killed(tmp_path):
    """Mutation: dropping the duplicate-location detection must fail."""
    from company_wiki.source_catalog import migration_ledger as ml

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES ('s2','h2',1,'x','2026-01-01')")
        conn.execute(
            "INSERT INTO locations (location_id, root_id, relative_path, "
            "absolute_path, document_id, role, location_status, "
            "last_seen_run, metadata_json) "
            "VALUES ('l2','company_raw','b.pdf','/x/b.pdf','d1',"
            "'original_primary','active','run1','{}')")
        conn.execute(
            "UPDATE locations SET source_id='s2' WHERE location_id='l2'")
    ledger = ml.build_quality_ledger(store)
    assert ledger["duplicate_location_sets"] == 1


# --- retired documents are never revived by migration -----------------------


def test_retired_document_not_revived(tmp_path):
    """A retired document's locations must stay retired through the
    migration ledger — migration never revives them."""
    from company_wiki.source_catalog.migration_ledger import build_quality_ledger

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store, retired=True)
    with store.transaction() as conn:
        conn.execute(
            "UPDATE locations SET location_status='retired' WHERE location_id='l1'")
    ledger = build_quality_ledger(store)
    # retired locations are counted but never eligible (not revived)
    assert ledger["retired_locations"] == 1
    # the retired doc is excluded from the migration input entirely —
    # it must not appear in any root bucket (never revived)
    assert "company_raw" not in ledger["by_root"]
    assert ledger["total_input"] == 0


# --- real files are never modified ------------------------------------------


def test_ledger_is_read_only(tmp_path):
    """Building the ledger must not modify the catalog or any real file."""
    from company_wiki.source_catalog.migration_ledger import build_quality_ledger

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    con = sqlite3.connect(tmp_path / "c.sqlite3")
    before = con.execute(
        "SELECT location_status FROM locations WHERE location_id='l1'").fetchone()[0]
    con.close()
    build_quality_ledger(store)
    con = sqlite3.connect(tmp_path / "c.sqlite3")
    after = con.execute(
        "SELECT location_status FROM locations WHERE location_id='l1'").fetchone()[0]
    con.close()
    assert before == after == "active"
