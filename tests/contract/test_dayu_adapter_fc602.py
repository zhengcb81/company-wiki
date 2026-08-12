"""FC-602 RED/acceptance tests: DayuAdapter 等价 — dayu metadata normalized
SCENARIO: EX-02
by the adapter, not special-cased by the scanner.

The adapter enumerates dayu groups (portfolio/{ticker}/filings/...),
merges the group meta.json with the v1 enrichment (provider/language
mapping, security_id/market backfill, EDGAR URL construction), selects
the preferred primary, and skips metadata-only groups (byte-less
placeholders never become documents — the real capture-incomplete
cause).  A frozen corpus shows v1/v2 trace parity; EX-02 proves dayu-only
exact reuse with the dayu location and zero writes.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _dayu_filing(root: Path, ticker: str, filing_id: str, *,
                 fy: int | None = 2024, provider: str = "cninfo",
                 source_url: str | None = "https://example.com/x.pdf",
                 market: str = "CN", ingest_complete: bool = True,
                 add_docling: bool = True) -> Path:
    """One dayu filing group: meta.json + preferred PDF (+ docling)."""
    group = root / ticker / "filings" / filing_id
    group.mkdir(parents=True)
    meta = {
        "document_id": filing_id,
        "ticker": ticker,
        "form_type": "FY",
        "fiscal_year": fy,
        "fiscal_period": "FY",
        "filing_date": "2025-03-24",
        "source_provider": provider,
        "source_id": "1216222070",
        "source_url": source_url,
        "source_language": "zh",
        "source_title": f"{ticker} FY{fy} report",
        "amended": False,
        "ingest_complete": ingest_complete,
        "primary_document": f"{filing_id}.pdf",
    }
    (group / "meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                     encoding="utf-8")
    (group / f"{filing_id}.pdf").write_bytes(b"%PDF-1.4 " + ticker.encode())
    if add_docling:
        (group / f"{filing_id}.pdf_docling.json").write_text(
            json.dumps({"text": "x"}), encoding="utf-8")
    entity_meta = {"company_id": f"{ticker}_SSE", "company_name": ticker,
                   "ticker": ticker, "market": market}
    (root / ticker / "meta.json").write_text(
        json.dumps(entity_meta, ensure_ascii=False), encoding="utf-8")
    return root


def _dayu_root(tmp_path: Path) -> Path:
    root = tmp_path / "portfolio"
    root.mkdir()
    _dayu_filing(root, "601899", "fil_cn_aaa", fy=2024)
    _dayu_filing(root, "601899", "fil_cn_bbb", fy=2023, add_docling=False)
    return root


def _dayu_root_spec(path: Path) -> RootSpec:
    return RootSpec(
        root_id="dayu_portfolio",
        path=path,
        kind="dayu_portfolio",
        adapter_id="dayu_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )


# --- adapter normalization (golden values) -----------------------------------


def test_fc602_adapter_enriches_dayu_metadata(tmp_path):
    """The adapter output carries the v1-enriched identity: security_id from
    ticker, market from entity meta, provider/language mapping, and the
    group meta fields at top level."""
    from company_wiki.source_catalog.adapters.dayu import DayuAdapter

    root = _dayu_root(tmp_path)
    candidates = DayuAdapter().enumerate(root)
    primary = next(c for c in candidates
                   if c.role == "original_primary" and "fil_cn_aaa" in str(c.relative_path))
    assert primary.normalized["security_id"] == "601899"
    assert primary.normalized["market"] == "CN"
    assert primary.normalized["provider"] == "cninfo"
    assert primary.normalized["language"] == "zh"
    assert primary.normalized["fiscal_year"] == 2024
    assert primary.normalized["form_type"] == "FY"
    assert primary.normalized["source_url"] == "https://example.com/x.pdf"
    assert primary.group_key.endswith("fil_cn_aaa")


def test_fc602_edgar_url_constructed(tmp_path):
    """A US SEC dayu filing without source_url gets the deterministic EDGAR
    URL from accession_number/company_id/primary_document."""
    from company_wiki.source_catalog.adapters.dayu import DayuAdapter

    root = tmp_path / "portfolio"
    root.mkdir()
    group = root / "AAPL" / "filings" / "fil_us_x"
    group.mkdir(parents=True)
    (group / "meta.json").write_text(json.dumps({
        "document_id": "fil_us_x", "ticker": "AAPL",
        "form_type": "10-K", "fiscal_year": 2024, "fiscal_period": "FY",
        "filing_date": "2025-10-31", "source_provider": "sec",
        "source_language": "en", "source_title": "AAPL 10-K",
        "accession_number": "0000320193-25-000123",
        "company_id": "320193",
        "primary_document": "aapl-20240928.htm",
        "ingest_complete": True,
    }, ensure_ascii=False), encoding="utf-8")
    (group / "aapl-20240928.htm").write_bytes(b"<html>x</html>")
    (root / "AAPL" / "meta.json").write_text(json.dumps(
        {"ticker": "AAPL", "market": "US"}, ensure_ascii=False), encoding="utf-8")
    primary = next(c for c in DayuAdapter().enumerate(root)
                   if c.role == "original_primary")
    assert primary.normalized["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/0000320193/"
        "000032019325000123/aapl-20240928.htm"
    )
    assert primary.normalized["market"] == "US"


def test_fc602_metadata_only_group_skipped(tmp_path):
    """A filing group with meta.json but no primary file (byte-less
    placeholder — the real capture-incomplete cause) never becomes a
    candidate."""
    from company_wiki.source_catalog.adapters.dayu import DayuAdapter

    root = tmp_path / "portfolio"
    root.mkdir()
    _dayu_filing(root, "601899", "fil_cn_aaa")
    group = root / "601899" / "filings" / "fil_cn_empty"
    group.mkdir(parents=True)
    (group / "meta.json").write_text(json.dumps({
        "document_id": "fil_cn_empty", "ticker": "601899",
        "fiscal_year": 2022, "source_provider": "cninfo",
        "ingest_complete": False, "primary_document": "missing.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    candidates = DayuAdapter().enumerate(root)
    assert all("fil_cn_empty" not in str(c.relative_path) for c in candidates)
    assert any("fil_cn_aaa" in str(c.relative_path) for c in candidates)


# --- v1/v2 trace parity over the frozen corpus -------------------------------


def test_fc602_frozen_dayu_trace_parity(tmp_path):
    """v1 and v2 produce the same source/location/handle/bundle traces on a
    frozen dayu corpus (explainable status diffs via the ledger)."""
    from company_wiki.source_catalog.shadow_parity import (
        register_migration_rule,
        reset_migration_ledger,
    )
    from company_wiki.source_catalog.trace_parity import run_trace_parity

    reset_migration_ledger()
    root = _dayu_root_spec(_dayu_root(tmp_path))
    report = run_trace_parity(root, ())
    for diff in report.blockers:
        if diff.field == "provider":
            register_migration_rule(
                (diff.path, "provider"),
                "v2 adapter resolves provider from source_provider; v1 dayu "
                "branch carries source_provider only (FC-602 normalization)",
                against=report,
            )
        else:
            raise AssertionError(
                f"unexplainable dayu trace diff: {diff.path}:{diff.field} "
                f"v1={diff.v1_value!r} v2={diff.v2_value!r}"
            )
    report = run_trace_parity(root, ())
    assert report.ok, (
        f"dayu trace diffs remain: {[(d.path, d.field) for d in report.blockers]}"
    )


# --- EX-02: dayu-only exact reuse ---------------------------------------------


def test_fc602_ex02_dayu_only_exact_reuse(tmp_path):
    """A dayu-only request resolves REUSED_EXACT with the dayu location and
    no download path."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    tree = _dayu_root(tmp_path)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("dayu_portfolio",),
            roots=(RootSpec("dayu_portfolio", tree, "dayu_portfolio"),),
        )
    )
    catalog.scan()
    request = SourceRequest(
        entity="601899", market="CN", security_id="601899",
        document_kind="annual_report", form_type="FY",
        fiscal_year=2024, provider_document_id="1216222070",
        as_of_date="2026-08-10", mode="exact",
    )
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.download_required is False
    handle = result.matches[0]
    assert handle.provider_document_id == "1216222070"
    assert handle.fiscal_year == 2024
    assert handle.capture_ready is True
    assert "fil_cn_aaa" in handle.canonical_path


def test_fc602_incomplete_dayu_not_reused(tmp_path):
    """An incomplete dayu filing (no fiscal_year in meta) is never offered
    as an exact-reuse candidate."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    tree = tmp_path / "portfolio"
    tree.mkdir()
    _dayu_filing(tree, "601899", "fil_cn_aaa")
    group = tree / "601899" / "filings" / "fil_cn_inc"
    group.mkdir(parents=True)
    (group / "meta.json").write_text(json.dumps({
        "document_id": "fil_cn_inc", "ticker": "601899",
        "source_provider": "cninfo", "ingest_complete": True,
        "primary_document": "fil_cn_inc.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (group / "fil_cn_inc.pdf").write_bytes(b"%PDF-1.4 incomplete")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("dayu_portfolio",),
            roots=(RootSpec("dayu_portfolio", tree, "dayu_portfolio"),),
        )
    )
    catalog.scan()
    request = SourceRequest(
        entity="601899", market="CN", security_id="601899",
        document_kind="annual_report", form_type="FY",
        fiscal_year=2024, provider_document_id="1216222070",
        as_of_date="2026-08-10", mode="exact",
    )
    result = SourceResolver(catalog).resolve(request)
    # the complete 2024 filing reuses exactly; the incomplete one is absent
    assert result.status is ResolutionStatus.REUSED_EXACT
    handle = result.matches[0]
    assert "fil_cn_inc" not in handle.canonical_path
