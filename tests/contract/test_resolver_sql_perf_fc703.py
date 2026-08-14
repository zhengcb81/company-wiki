"""FC-703 RED/acceptance tests: 来源无关 SQL 与性能.

query_filing_candidates pushes document_kind/source_status/entity and an
advisory fiscal_year filter into SQL — never a full-table Python scan
(OPS-03).  The candidate cap is enforced; resolution is deterministic
across repeated calls (EX-07 resolver-level); a noise document of a
different kind never leaks into the slice.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _seed_company(
    tmp_path: Path, company: str, pdoc: str, kind: str, *, fy: int = 2024, n: int = 1
) -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        name = f"{pdoc}-{i}" if n > 1 else pdoc
        (raw / f"{name}.pdf").write_bytes(
            b"%PDF-1.4 " + company.encode("utf-8") + name.encode("utf-8")
        )
        (raw / f"{name}.pdf.source.json").write_text(
            json.dumps(
                {
                    "market": "CN",
                    "security_id": "601899",
                    "source_title": f"{company} {fy} #{i}",
                    "fiscal_year": fy,
                    "filing_date": f"{fy + 1}-03-20",
                    "form_type": kind,
                    "document_kind": kind,
                    "provider": "cninfo",
                    "provider_document_id": name,
                    "source_url": f"https://provider.example/{name}",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return tmp_path / "companies"


def _catalog(tmp_path: Path, tree: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(
                RootSpec(
                    "company_raw",
                    tree,
                    "company_raw",
                    priority=10,
                    adapter_id="company_raw_v1",
                    read_only=False,
                    reusable_for_filing=True,
                    canonical_write_target="companies",
                ),
            ),
        )
    )


def _resolve(catalog, *, security="601899", fy=2024, kind="annual_report", pdoc=None):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Acme",
            market="CN",
            security_id=security,
            document_kind=kind,
            form_type=kind,
            fiscal_year=fy,
            provider="cninfo",
            provider_document_id=pdoc,
            as_of_date="2026-08-11",
            mode="exact",
        )
    )


def test_fc703_sql_pushdown_kind_status_filtered(tmp_path):
    """SQL filters kind+status: a noise document of a different kind is
    never in the candidate slice — no Python full-table scan."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "annual-doc", "annual_report")
    _seed_company(tmp_path, "Acme", "noise-quarterly", "quarterly_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    assert result.status in (
        ResolutionStatus.REUSED_EXACT,
        ResolutionStatus.REUSED_EQUIVALENT,
    )
    assert all("annual" in m.provider_document_id for m in result.matches), (
        f"quarterly noise leaked into the annual slice: {result.matches}"
    )


def test_fc703_sql_pushdown_entity_filtered(tmp_path):
    """The entity filter narrows the slice: another company's documents
    are never candidates for an Acme request."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "acme-doc", "annual_report")
    _seed_company(tmp_path, "OtherCo", "other-doc", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    assert result.status in (
        ResolutionStatus.REUSED_EXACT,
        ResolutionStatus.REUSED_EQUIVALENT,
    )
    assert all("acme" in m.provider_document_id for m in result.matches)


def test_fc703_candidate_cap_enforced(tmp_path):
    """The candidate cap limits the slice (never unbounded)."""
    tree = _seed_company(tmp_path, "Acme", "doc", "annual_report", n=50)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    capped = catalog.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",), limit=10
    )
    assert len(capped) <= 10
    full = catalog.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",), limit=1000
    )
    assert len(full) >= 50


def test_fc703_deterministic_across_calls(tmp_path):
    """EX-07 resolver-level: the same request resolves to the same handle
    across repeated calls (order/state independent)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc", "annual_report", n=10)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    first = _resolve(catalog, pdoc="doc-0")
    second = _resolve(catalog, pdoc="doc-0")
    assert first.status is second.status is ResolutionStatus.REUSED_EXACT
    assert first.matches[0].canonical_path == second.matches[0].canonical_path
    assert first.matches[0].document_id == second.matches[0].document_id


def _where_region(sql: str) -> str:
    """The text between the first WHERE and ORDER BY (or end) — the region
    that must carry the pushed-down predicates."""
    where_idx = sql.find("WHERE")
    assert where_idx != -1, f"no WHERE clause in: {sql[:200]}"
    end = sql.find("ORDER BY", where_idx)
    if end == -1:
        end = len(sql)
    return sql[where_idx:end]


def test_fc703_query_uses_where_clauses(tmp_path):
    """The DOCUMENTS query carries WHERE predicates for kind + status +
    fiscal year — the pushdown is real (rows filtered in SQL), not a
    Python post-filter.  Assertions target the WHERE region, not the
    SELECT projection: dropping any predicate must fail this test."""
    tree = _seed_company(tmp_path, "Acme", "doc", "annual_report", n=3)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    # ZR-203: the read path runs on the zero-write reader — capture its SQL.
    reader = catalog.reader
    captured = []
    original = reader.fetchall

    def spy(sql, *args, **kwargs):
        captured.append(sql)
        return original(sql, *args, **kwargs)

    reader.fetchall = spy
    try:
        catalog.query_filing_candidates(
            document_kind="annual_report",
            source_statuses=("active",),
            fiscal_year=2024,
            limit=100,
        )
        # second call without fiscal_year — kind+status must still be SQL
        catalog.query_filing_candidates(
            document_kind="annual_report", source_statuses=("active",), limit=100
        )
    finally:
        reader.fetchall = original
    docs_sqls = [s for s in captured if "FROM documents" in s]
    assert len(docs_sqls) >= 2, f"expected 2 documents queries, got {len(docs_sqls)}"
    where = _where_region(docs_sqls[0])
    import re

    assert re.search(r"document_kind\s*=\s*\?", where), (
        f"kind predicate not in WHERE region: {where[:300]}"
    )
    assert re.search(r"source_status\s*IN\s*\(", where), (
        f"status predicate not in WHERE region: {where[:300]}"
    )
    assert "fiscal_year" in where, (
        f"fiscal predicate not in WHERE region: {where[:300]}"
    )
    # without fiscal_year the kind+status predicates must still be pushed
    # down (a Python post-filter would leave the WHERE region empty)
    where2 = _where_region(docs_sqls[1])
    assert re.search(r"document_kind\s*=\s*\?", where2)
    assert re.search(r"source_status\s*IN\s*\(", where2)
