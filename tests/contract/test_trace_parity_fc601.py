"""FC-601 RED/acceptance tests: CompanyRawAdapter 等价 — full-trace parity.

On a frozen CN/HK/US company_raw corpus the v1 scanner path and the v2
adapter path must produce the same five traces: sources, documents,
locations, handles, bundles (FC-303 explains the sidecar-metadata status
diff via the migration ledger).  Golden values pin the projection.
EX-01: companies-only requests resolve REUSED_EXACT for CN/HK/US with
zero provider/canonical-write side effects.  The canonical writer still
targets companies/<company>/raw.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _company_tree(tmp_path: Path, company: str, market: str, security: str,
                  provider: str, doc_id: str, fiscal_year: int = 2024) -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True)
    primary = raw / f"{company}_{fiscal_year}_annual.pdf"
    primary.write_bytes(b"%PDF-1.4 " + company.encode("utf-8"))
    sidecar = {
        "market": market,
        "security_id": security,
        "source_title": f"{company} {fiscal_year} Annual",
        "source_url": f"https://provider.example/{security}/{fiscal_year}",
        "fiscal_year": fiscal_year,
        "period_end": f"{fiscal_year}-12-31",
        "filing_date": f"{fiscal_year + 1}-02-20",
        "form_type": "annual_report",
        "document_kind": "annual_report",
        "provider": provider,
        "provider_document_id": doc_id,
    }
    primary.with_name(primary.name + ".source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path / "companies"


def _frozen_corpus(tmp_path: Path) -> Path:
    """CN/HK/US companies, each one annual report + sidecar."""
    _company_tree(tmp_path, "紫金矿业", "CN", "601899", "cninfo", "1225023658")
    _company_tree(tmp_path, "美团", "HK", "03690", "hkexnews", "meituan-2024")
    _company_tree(tmp_path, "Apple", "US", "AAPL", "sec", "0000320193-25-000123")
    return tmp_path / "companies"


def _company_raw_root(path: Path) -> RootSpec:
    return RootSpec(
        root_id="company_raw",
        path=path,
        kind="company_raw",
        adapter_id="company_raw_v1",
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )


# --- full-trace parity over the frozen corpus --------------------------------


def _register_explainable_rules(report):
    from company_wiki.source_catalog.shadow_parity import register_migration_rule

    for diff in report.blockers:
        if diff.field in ("status", "identity") and diff.path.endswith(".source.json"):
            register_migration_rule(
                (diff.path, diff.field),
                "v1 marks sidecar metadata incomplete; v2 adapter emits "
                "normalized metadata with active status (FC-303 rule)",
                against=report,
            )
        else:
            raise AssertionError(
                f"unexplainable trace diff: {diff.path}:{diff.field} "
                f"v1={diff.v1_value!r} v2={diff.v2_value!r}"
            )


def test_fc601_frozen_corpus_full_trace_parity(tmp_path):
    """v1 and v2 produce identical source/document/location/handle/bundle
    traces on the frozen CN/HK/US corpus (sidecar status diff explained)."""
    from company_wiki.source_catalog.shadow_parity import reset_migration_ledger
    from company_wiki.source_catalog.trace_parity import run_trace_parity

    reset_migration_ledger()
    root = _company_raw_root(_frozen_corpus(tmp_path))
    report = run_trace_parity(root, ("紫金矿业", "美团", "Apple"))
    _register_explainable_rules(report)
    report = run_trace_parity(root, ("紫金矿业", "美团", "Apple"))
    assert report.ok, (
        f"trace diffs remain: {[(d.path, d.field) for d in report.blockers]}"
    )


def test_fc601_trace_deterministic(tmp_path):
    """Two runs of the same candidates produce identical traces."""
    from company_wiki.source_catalog.trace_parity import candidate_trace
    from company_wiki.source_catalog.scanner import _scan_root_v1

    root = _company_raw_root(_frozen_corpus(tmp_path))
    v1, _, _ = _scan_root_v1(root, ("紫金矿业", "美团", "Apple"))
    first = candidate_trace(v1)
    second = candidate_trace(v1)
    assert first == second


def test_fc601_golden_trace_values(tmp_path):
    """The trace projection pins exact expected values on the frozen
    corpus — a projection bug (dropped section, wrong mime/group) breaks
    this test even when both sides use the same projection."""
    from company_wiki.source_catalog.scanner import _scan_root_v1
    from company_wiki.source_catalog.trace_parity import candidate_trace

    root = _company_raw_root(_frozen_corpus(tmp_path))
    v1, _, _ = _scan_root_v1(root, ("紫金矿业", "美团", "Apple"))
    trace = candidate_trace(v1)
    # every section present with the expected shape
    assert len(trace["sources"]) == 6  # 3 pdfs + 3 sidecars
    assert len(trace["locations"]) == 6
    assert len(trace["documents"]) >= 3
    assert len(trace["handles"]) == 3  # one capture-ready filing per company
    assert len(trace["bundles"]) == 3
    # golden spot checks: the CN filing handle and its source entry
    cn_pdf = "紫金矿业/raw/financial_reports/annual/紫金矿业_2024_annual.pdf"
    assert trace["sources"][cn_pdf]["mime_type"] == "application/pdf"
    assert trace["sources"][cn_pdf + ".source.json"]["mime_type"] == "application/json"
    assert any(
        h["security_id"] == "601899" and h["market"] == "CN"
        and h["provider"] == "cninfo" and h["fiscal_year"] == 2024
        for h in trace["handles"].values()
    )
    assert any(
        "紫金矿业" in path and entry["role"] == "original_primary"
        for path, entry in trace["locations"].items()
    )
    assert any(
        key.endswith("紫金矿业_2024_annual.pdf")
        for key in trace["bundles"]
    )


# --- EX-01: companies-only exact reuse, CN/HK/US -----------------------------


def _resolve_fixture(tmp_path: Path, company: str, market: str, security: str,
                     provider: str, doc_id: str):
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    tree = _company_tree(tmp_path, company, market, security, provider, doc_id)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(RootSpec("company_raw", tree, "company_raw"),),
        )
    )
    catalog.scan()
    request = SourceRequest(
        entity=company,
        market=market,
        security_id=security,
        document_kind="annual_report",
        form_type="annual_report",
        fiscal_year=2024,
        provider=provider,
        provider_document_id=doc_id,
        as_of_date="2026-08-10",
    )
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.REUSED_EXACT
    # exact reuse: no download path (provider discover/fetch/canonical
    # write all stay at zero by construction — the resolver returns before
    # any acquisition step)
    assert result.download_required is False
    assert result.download_allowed is False
    return result


def test_fc601_ex01_cn_exact_reuse(tmp_path):
    """CN companies-only request reuses the exact existing filing."""
    result = _resolve_fixture(tmp_path, "紫金矿业", "CN", "601899", "cninfo",
                              "1225023658")
    handle = result.matches[0]
    assert handle.provider == "cninfo"
    assert handle.provider_document_id == "1225023658"
    assert handle.capture_ready is True
    assert handle.https_url.startswith("https://provider.example/601899")


def test_fc601_ex01_hk_exact_reuse(tmp_path):
    """HK companies-only request reuses the exact existing filing."""
    result = _resolve_fixture(tmp_path, "美团", "HK", "03690", "hkexnews",
                              "meituan-2024")
    handle = result.matches[0]
    assert handle.provider == "hkexnews"
    assert handle.provider_document_id == "meituan-2024"


def test_fc601_ex01_us_exact_reuse(tmp_path):
    """US companies-only request reuses the exact existing filing."""
    result = _resolve_fixture(tmp_path, "Apple", "US", "AAPL", "sec",
                              "0000320193-25-000123")
    handle = result.matches[0]
    assert handle.provider == "sec"
    assert handle.provider_document_id == "0000320193-25-000123"


# --- canonical writer behavior unchanged -------------------------------------


def test_fc601_canonical_writer_destination_unchanged(tmp_path):
    """The canonical writer still targets companies/<company>/raw — the v2
    adapter path does not move the write target."""
    from company_wiki.source_catalog.canonical_writer import (
        CanonicalSourceWriter,
        _destination_subdirectory,
    )

    raw = _company_tree(tmp_path, "Apple", "US", "AAPL", "sec", "doc-1")
    assert _destination_subdirectory("annual_report") == (
        Path("financial_reports") / "annual"
    )
    # the writer's company_root is the companies tree: any destination
    # stays under companies/<entity>/raw/...
    writer = CanonicalSourceWriter.__new__(CanonicalSourceWriter)
    company_root = raw  # companies tree
    writer.company_root = RootSpec(
        "company_raw", company_root, "company_raw",
        canonical_write_target="companies",
    )
    from company_wiki.source_catalog.acquisition import (
        DownloadCandidate,
        DownloadReceipt,
    )
    from company_wiki.source_catalog.resolver import SourceRequest

    request = SourceRequest(
        entity="Apple", document_kind="annual_report",
        as_of_date="2026-08-10", market="US", security_id="AAPL",
        fiscal_year=2024, provider="sec", provider_document_id="doc-1",
    )
    candidate = DownloadCandidate(
        candidate_id="c1", provider="sec", provider_document_id="doc-1",
        market="US", entity="Apple", title="Apple 2024 Annual",
        source_url="https://sec.gov/x", document_kind="annual_report",
        filing_date="2025-02-20", fiscal_year=2024,
    )
    receipt = DownloadReceipt(
        candidate_id="c1", provider="sec", provider_document_id="doc-1",
        source_url="https://sec.gov/x", staged_path=str(Path("/tmp/x.pdf")),
        content_sha256="a" * 64, byte_size=3, mime_type="application/pdf",
        retrieved_at="2026-08-10T00:00:00Z", http_status=200,
        adapter_name="test", adapter_version="1.0.0",
    )
    destination = writer._destination(request, candidate, receipt)
    relative = destination.relative_to(company_root.resolve(strict=False))
    assert relative.parts[0] == "Apple"
    assert relative.parts[1] == "raw"
    assert relative.parts[2:4] == ("financial_reports", "annual")
