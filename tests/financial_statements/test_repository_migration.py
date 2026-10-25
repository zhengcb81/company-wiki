"""Neutral RED: schema 1.3.0 migration chain, repository idempotency, read-only queries."""

from __future__ import annotations

import sqlite3

import pytest

from company_wiki.source_catalog.financial_statements import normalize
from company_wiki.source_catalog.financial_statements.repository import (
    FinancialStatementRepository,
    StatementSecurity,
    StatementSource,
    query_financial_statements_readonly,
)
from company_wiki.source_catalog.store import CatalogStore

from . import fixtures


def _db(tmp_path):
    return tmp_path / "project" / ".source_catalog" / "catalog.sqlite3"


def _store(tmp_path) -> CatalogStore:
    return CatalogStore(_db(tmp_path))


def _schema_version(db_path) -> str:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone()[0]


def _tables(db_path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


class TestSchemaMigration:
    def test_fresh_database_is_1_3_0_with_financial_tables(self, tmp_path):
        db = _db(tmp_path)
        store = CatalogStore(db)
        assert _schema_version(db) == "1.3.0"
        tables = _tables(db)
        assert "financial_statement_versions" in tables
        assert "financial_statement_values" in tables
        del store

    def test_upgrade_from_1_2_0_preserves_old_data(self, tmp_path):
        db = _db(tmp_path)
        CatalogStore(db)
        with sqlite3.connect(db) as conn:
            conn.execute(
                "INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at)"
                " VALUES('sid-old','old' || 'a' * 60, 10, 'application/pdf', '2026-01-01T00:00:00Z')"
            )
            conn.execute(
                "INSERT INTO documents(document_id, title, source_type, document_kind,"
                " source_status, metadata_priority, metadata_json, first_seen_at, last_seen_at)"
                " VALUES('did-old','old doc','regulatory_filing','annual_report','active',"
                " 1, '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
            )
            conn.execute("DROP TABLE financial_statement_versions")
            conn.execute("DROP TABLE financial_statement_values")
            conn.execute(
                "UPDATE catalog_meta SET value='1.2.0' WHERE key='schema_version'"
            )
        store = CatalogStore(db)
        assert _schema_version(db) == "1.3.0"
        with sqlite3.connect(db) as conn:
            kept = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE document_id='did-old'"
            ).fetchone()[0]
        assert kept == 1
        tables = _tables(db)
        assert {"financial_statement_versions", "financial_statement_values"} <= tables
        del store

    @pytest.mark.parametrize("old_version", ["1.0.0", "1.1.0", "1.2.0"])
    def test_all_upgradeable_versions_reach_current(self, tmp_path, old_version):
        db = _db(tmp_path)
        CatalogStore(db)
        with sqlite3.connect(db) as conn:
            conn.execute(
                "UPDATE catalog_meta SET value=? WHERE key='schema_version'",
                (old_version,),
            )
        CatalogStore(db)
        assert _schema_version(db) == "1.3.0"

    def test_unknown_future_version_fails_closed_before_writes(self, tmp_path):
        db = _db(tmp_path)
        CatalogStore(db)
        with sqlite3.connect(db) as conn:
            conn.execute(
                "UPDATE catalog_meta SET value='9.9.9' WHERE key='schema_version'"
            )
        before = _tables(db)
        with pytest.raises(ValueError, match="unsupported source catalog schema version"):
            CatalogStore(db)
        assert _tables(db) == before  # zero partial writes

    def test_concurrent_double_initialization(self, tmp_path):
        import threading

        db = _db(tmp_path)
        errors: list[Exception] = []

        def open_store():
            try:
                CatalogStore(db)
            except Exception as exc:  # noqa: BLE001 - collected for assertion
                errors.append(exc)

        threads = [threading.Thread(target=open_store) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert errors == []
        assert _schema_version(db) == "1.3.0"


class TestPublishAndQuery:
    @staticmethod
    def _security() -> StatementSecurity:
        return StatementSecurity(
            entity="中微公司",
            market="CN",
            security_id="688012",
            exchange="SSE",
            code="688012",
        )

    @staticmethod
    def _source(page_number: int = 1) -> StatementSource:
        return StatementSource(
            source_id="urn:company-wiki:source:" + "a" * 64,
            document_id="urn:company-wiki:document:" + "a" * 64,
            content_sha256="a" * 64,
            page_number=page_number,
            url="https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
            "?paperCode=sh688012&source=lrb&type=0&page=1&num=10",
        )

    @classmethod
    def _reports(cls, count: int = 1):
        page = normalize.normalize_page(
            fixtures.fixture_bytes("sh688012-lrb-type0-page1-num10.json.gz"),
            statement_type="income_statement",
            page_number=1,
        )
        return page.reports[:count]

    def _seed_source(self, tmp_path, source: StatementSource):
        with CatalogStore(_db(tmp_path)).transaction() as conn:
            conn.execute(
                "INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at)"
                " VALUES(?,?,?,?, '2026-10-25T00:00:00Z')",
                (source.source_id, source.content_sha256, 196351, "application/json"),
            )
            conn.execute(
                "INSERT INTO documents(document_id, primary_source_id, title, source_type,"
                " document_kind, source_status, metadata_priority, metadata_json,"
                " first_seen_at, last_seen_at)"
                " VALUES(?,?, 'sina lrb','other','financial_statement_dataset','active',"
                " 1, '{}', '2026-10-25T00:00:00Z', '2026-10-25T00:00:00Z')",
                (source.document_id, source.source_id),
            )

    def test_publish_creates_version_and_exact_value_rows(self, tmp_path):
        store = _store(tmp_path)
        source = self._source()
        self._seed_source(tmp_path, source)
        repo = FinancialStatementRepository(store)
        outcome = repo.publish_reports(
            security=self._security(),
            source=source,
            reports=self._reports(1),
            retrieved_at="2026-10-25T12:00:00Z",
        )
        assert len(outcome.new_version_ids) == 1
        report = self._reports(1)[0]
        result = repo.query_statement_rows(
            security_id="688012", statement_type="income_statement"
        )
        assert len(result["versions"]) == 1
        version = result["versions"][0]
        assert version["period_end"] == "2026-06-30"
        assert version["period_kind"] == "semi_annual"
        assert version["consolidation"] == "consolidated"
        assert version["currency"] == "CNY"
        assert version["source_id"] == source.source_id
        assert version["document_id"] == source.document_id
        rows = version["rows"]
        assert len(rows) == len(report.rows)
        first = rows[0]
        assert first["provider_field"] == "BIZTOTINCO"
        assert first["value_decimal"] == "6691287327.670000"
        assert first["json_pointer"] == (
            "/result/data/report_list/20260630/data/0/item_value"
        )
        eps = next(r for r in rows if r["provider_field"] == "BASICEPS")
        assert eps["unit"] == "CNY/share"

    def test_republish_same_content_reuses_version(self, tmp_path):
        store = _store(tmp_path)
        source = self._source()
        self._seed_source(tmp_path, source)
        repo = FinancialStatementRepository(store)
        first = repo.publish_reports(
            security=self._security(),
            source=source,
            reports=self._reports(1),
            retrieved_at="2026-10-25T12:00:00Z",
        )
        second = repo.publish_reports(
            security=self._security(),
            source=source,
            reports=self._reports(1),
            retrieved_at="2026-10-25T13:00:00Z",
        )
        assert second.new_version_ids == []
        assert second.reused_version_ids == first.new_version_ids
        with store.transaction() as conn:
            versions = conn.execute(
                "SELECT COUNT(*) FROM financial_statement_versions"
            ).fetchone()[0]
            values = conn.execute(
                "SELECT COUNT(*) FROM financial_statement_values"
            ).fetchone()[0]
        assert versions == 1
        assert values == len(self._reports(1)[0].rows)

    def test_changed_content_keeps_old_version(self, tmp_path):
        store = _store(tmp_path)
        source = self._source()
        self._seed_source(tmp_path, source)
        repo = FinancialStatementRepository(store)
        first = repo.publish_reports(
            security=self._security(),
            source=source,
            reports=self._reports(1),
            retrieved_at="2026-10-25T12:00:00Z",
        )
        # frozen dataclass: rebuild via dataclasses.replace
        import dataclasses

        base = self._reports(1)[0]
        shorter = dataclasses.replace(base, rows=base.rows[:10])
        second = repo.publish_reports(
            security=self._security(),
            source=source,
            reports=[shorter],
            retrieved_at="2026-10-25T14:00:00Z",
        )
        assert len(second.new_version_ids) == 1
        assert second.new_version_ids != first.new_version_ids
        result = repo.query_statement_rows(
            security_id="688012", statement_type="income_statement"
        )
        assert len(result["versions"]) == 2

    def test_publish_requires_registered_source(self, tmp_path):
        store = _store(tmp_path)
        repo = FinancialStatementRepository(store)
        source = self._source()  # never inserted into sources/documents
        with pytest.raises(Exception):
            repo.publish_reports(
                security=self._security(),
                source=source,
                reports=self._reports(1),
                retrieved_at="2026-10-25T12:00:00Z",
            )
        with store.transaction() as conn:
            values = conn.execute(
                "SELECT COUNT(*) FROM financial_statement_values"
            ).fetchone()[0]
        assert values == 0  # half-published versions are not visible

    def test_query_filters_and_continuation(self, tmp_path):
        store = _store(tmp_path)
        source = self._source()
        self._seed_source(tmp_path, source)
        repo = FinancialStatementRepository(store)
        repo.publish_reports(
            security=self._security(),
            source=source,
            reports=self._reports(3),
            retrieved_at="2026-10-25T12:00:00Z",
        )
        # period range filter
        narrowed = repo.query_statement_rows(
            security_id="688012",
            statement_type="income_statement",
            period_end_from="2026-01-01",
            period_end_to="2026-12-31",
        )
        assert all(
            v["period_end"].startswith("2026") for v in narrowed["versions"]
        )
        # fields filter keeps the row subset without shifting ordinals
        fields = repo.query_statement_rows(
            security_id="688012",
            statement_type="income_statement",
            fields=("BASICEPS",),
        )
        for version in fields["versions"]:
            assert [r["provider_field"] for r in version["rows"]] == ["BASICEPS"]
        # row-limit continuation: no lost/duplicated rows across pages
        paged_rows: list[tuple] = []
        continuation = None
        while True:
            page = repo.query_statement_rows(
                security_id="688012",
                statement_type="income_statement",
                max_rows=50,
                continuation=continuation,
            )
            for version in page["versions"]:
                for row in version["rows"]:
                    paged_rows.append((version["statement_version_id"], row["row_ordinal"]))
            continuation = page.get("continuation")
            if not continuation:
                break
        full = repo.query_statement_rows(
            security_id="688012", statement_type="income_statement"
        )
        expected = [
            (v["statement_version_id"], r["row_ordinal"])
            for v in full["versions"]
            for r in v["rows"]
        ]
        assert paged_rows == expected


class TestReadOnlyQuery:
    def test_missing_database_is_named_gap_without_creation(self, tmp_path):
        db = tmp_path / "absent" / "catalog.sqlite3"
        result = query_financial_statements_readonly(
            db, security_id="688012", statement_type="income_statement"
        )
        assert result["available"] is False
        assert result["reason"] == "catalog_database_missing"
        assert not db.exists()

    def test_database_without_financial_tables_is_named_gap(self, tmp_path):
        db = tmp_path / "catalog.sqlite3"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE other(x)")
        result = query_financial_statements_readonly(
            db, security_id="688012", statement_type="income_statement"
        )
        assert result["available"] is False
        assert result["reason"] == "financial_statements_unavailable"
        # read-only: no tables were created
        with sqlite3.connect(db) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert tables == {"other"}

    def test_query_does_not_migrate_old_schema(self, tmp_path):
        db = tmp_path / "catalog.sqlite3"
        with sqlite3.connect(db) as conn:
            conn.execute(
                "CREATE TABLE catalog_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO catalog_meta VALUES('schema_version','1.2.0')"
            )
        result = query_financial_statements_readonly(
            db, security_id="688012", statement_type="income_statement"
        )
        assert result["available"] is False
        with sqlite3.connect(db) as conn:
            version = conn.execute(
                "SELECT value FROM catalog_meta WHERE key='schema_version'"
            ).fetchone()[0]
        assert version == "1.2.0"
