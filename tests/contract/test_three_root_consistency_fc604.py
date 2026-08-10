"""FC-604 RED/acceptance tests: 三根一致性 canary.

The same request matrix (CN/HK/US identity) resolves to a CONSISTENT
output contract across companies-only / dayu-only / Dropbox-only
catalogs: identical status, capture_ready, provider,
provider_document_id, fiscal_year, content_sha256, document_kind,
form_type, byte_size.  Only the root/location provenance
(canonical_path, canonical_location_id) differs.  Any root-specific
business branch in the resolver breaks the contract.

The architecture gate asserts the resolver carries NO root_id /
root_kind conditional that selects behavior per root (only the
config-driven reusable_root_kinds allowance is permitted).
"""
import ast
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402

# contract fields that MUST be identical across roots for the same request
CONTRACT_FIELDS = (
    "document_kind", "form_type", "fiscal_year", "published_date",
    "provider", "provider_document_id", "https_url", "content_sha256",
    "snapshot_sha256", "mime_type", "byte_size", "capture_ready",
    "source_status",
)
# provenance fields that legitimately differ per root
PROVENANCE_FIELDS = (
    "canonical_path", "canonical_location_id",
    "document_id", "source_id",  # derived from the canonical location
)


def _identity(market="CN", security="601899", pdoc="1225023658", fy=2025):
    return dict(market=market, security_id=security,
                provider_document_id=pdoc, fiscal_year=fy)


def _companies_fixture(tmp_path: Path, body: bytes, ident: dict) -> Path:
    raw = tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True)
    primary = raw / f"Acme_{ident['fiscal_year']}_annual.pdf"
    primary.write_bytes(body)
    (raw / f"Acme_{ident['fiscal_year']}_annual.pdf.source.json").write_text(
        json.dumps({
            "market": ident["market"], "security_id": ident["security_id"],
            "source_title": f"Acme {ident['fiscal_year']}",
            "source_url": f"https://provider.example/{ident['security_id']}/{ident['fiscal_year']}",
            "fiscal_year": ident["fiscal_year"], "period_end": f"{ident['fiscal_year']}-12-31",
            "filing_date": f"{ident['fiscal_year'] + 1}-02-20",
            "form_type": "annual_report", "document_kind": "annual_report",
            "provider": "cninfo", "provider_document_id": ident["provider_document_id"],
        }, ensure_ascii=False), encoding="utf-8")
    return tmp_path / "companies"


def _dayu_fixture(tmp_path: Path, body: bytes, ident: dict) -> Path:
    portfolio = tmp_path / "portfolio"
    group = portfolio / "Acme" / "filings" / "fil_x"
    group.mkdir(parents=True)
    (group / "fil_x.pdf").write_bytes(body)
    (group / "meta.json").write_text(json.dumps({
        "document_id": "fil_x", "ticker": ident["security_id"],
        "form_type": "annual_report", "fiscal_year": ident["fiscal_year"],
        "fiscal_period": "FY", "filing_date": f"{ident['fiscal_year'] + 1}-02-20",
        "source_provider": "cninfo", "source_id": ident["provider_document_id"],
        "source_url": f"https://provider.example/{ident['security_id']}/{ident['fiscal_year']}",
        "source_language": "zh", "source_title": f"Acme {ident['fiscal_year']}",
        "amended": False, "ingest_complete": True, "primary_document": "fil_x.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (portfolio / "Acme" / "meta.json").write_text(json.dumps(
        {"ticker": ident["security_id"], "market": ident["market"]},
        ensure_ascii=False), encoding="utf-8")
    return portfolio


def _dropbox_fixture(tmp_path: Path, body: bytes, ident: dict) -> Path:
    dropbox = tmp_path / "Dropbox" / "Stock" / "Acme"
    dropbox.mkdir(parents=True)
    (dropbox / f"Acme_{ident['fiscal_year']}_annual.pdf").write_bytes(body)
    (dropbox / f"Acme_{ident['fiscal_year']}_annual.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0",
        "canonical_entity_id": f"ent-{ident['security_id']}",
        "display_name": "Acme", "market": ident["market"],
        "security_id": ident["security_id"], "document_kind": "annual_report",
        "fiscal_year": ident["fiscal_year"], "period_end": f"{ident['fiscal_year']}-12-31",
        "filing_date": f"{ident['fiscal_year'] + 1}-02-20",
        "form_type": "annual_report", "provider": "cninfo",
        "provider_document_id": ident["provider_document_id"],
        "source_url": f"https://provider.example/{ident['security_id']}/{ident['fiscal_year']}",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path / "Dropbox" / "Stock"


def _single_root_catalog(tmp_path: Path, root_kind: str, root_path: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    kind_to_spec = {
        "company_raw": RootSpec("company_raw", root_path, "company_raw",
                                priority=10, adapter_id="company_raw_v1",
                                read_only=False, reusable_for_filing=True,
                                canonical_write_target="companies"),
        "dayu_portfolio": RootSpec("dayu_portfolio", root_path, "dayu_portfolio",
                                   priority=10, adapter_id="dayu_filing_v1",
                                   read_only=True, reusable_for_filing=True),
        "directory": RootSpec("dropbox_stock", root_path, "directory",
                              priority=10, adapter_id="sidecar_filing_v1",
                              read_only=True, reusable_for_filing=True),
    }
    # entity inference needs company_names from a company_raw root; always
    # include a company_raw root (with an Acme dir) so entity gates pass,
    # but restrict reusable_root_kinds to the target kind only so only the
    # target root is reusable
    if root_kind == "company_raw":
        # company_raw IS the target; its fixture already has the Acme dir
        roots = (kind_to_spec["company_raw"],)
    else:
        # add a separate company_raw root for entity inference only
        companies = tmp_path / "companies" / "Acme" / "raw"
        companies.mkdir(parents=True, exist_ok=True)
        company_root = RootSpec("company_raw", tmp_path / "companies", "company_raw",
                                adapter_id="company_raw_v1", read_only=False,
                                reusable_for_filing=True,
                                canonical_write_target="companies")
        roots = (company_root, kind_to_spec[root_kind])
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".catalogs" / root_kind,
            reusable_root_kinds=(root_kind,),
            roots=roots,
        )
    )
    catalog.scan()
    return catalog


def _resolve(catalog, ident, entity="Acme"):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(SourceRequest(
        entity=entity, market=ident["market"],
        security_id=ident["security_id"],
        document_kind="annual_report", form_type="annual_report",
        fiscal_year=ident["fiscal_year"],
        provider_document_id=ident["provider_document_id"],
        as_of_date="2026-08-10", mode="exact",
    ))


def _contract(handle: dict) -> dict:
    return {f: handle.get(f) for f in CONTRACT_FIELDS}


# --- same request, consistent contract across the three roots -----------------


def test_fc604_cn_consistent_across_three_roots(tmp_path):
    """CN identity resolves to the same contract on companies/dayu/Dropbox;
    only the canonical path (provenance) differs."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = _identity("CN", "601899", "1225023658", 2025)
    body = b"%PDF-1.4 acme-cn-2025"
    catalogs = {
        "company_raw": _single_root_catalog(tmp_path / "co", "company_raw",
                                            _companies_fixture(tmp_path / "co", body, ident)),
        "dayu_portfolio": _single_root_catalog(tmp_path / "dy", "dayu_portfolio",
                                               _dayu_fixture(tmp_path / "dy", body, ident)),
        "directory": _single_root_catalog(tmp_path / "db", "directory",
                                          _dropbox_fixture(tmp_path / "db", body, ident)),
    }
    contracts = {}
    paths = {}
    for kind, catalog in catalogs.items():
        result = _resolve(catalog, ident)
        assert result.status is ResolutionStatus.REUSED_EXACT, (
            f"{kind}: {result.status.value} ({result.reason}) "
            f"trace={list(result.debug_trace)[:3]}")
        handle = result.matches[0].to_dict()
        contracts[kind] = _contract(handle)
        paths[kind] = handle["canonical_path"]
    # contract identical across all three roots
    assert contracts["company_raw"] == contracts["dayu_portfolio"] == contracts["directory"], (
        f"contract drift: {contracts}")
    # provenance differs (each root serves its own canonical path)
    assert len(set(paths.values())) == 3, f"canonical paths not distinct: {paths}"
    assert "companies" in paths["company_raw"].replace("\\", "/")
    assert "portfolio" in paths["dayu_portfolio"].replace("\\", "/")
    assert "Dropbox" in paths["directory"].replace("\\", "/")


def test_fc604_us_consistent_across_three_roots(tmp_path):
    """US identity resolves to the same contract on companies/dayu/Dropbox."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = _identity("US", "AAPL", "0000320193-25-000079", 2025)
    body = b"%PDF-1.4 acme-us-2025"
    contracts = {}
    paths = {}
    for kind, builder in (("company_raw", _companies_fixture),
                          ("dayu_portfolio", _dayu_fixture),
                          ("directory", _dropbox_fixture)):
        base = tmp_path / kind
        root_path = builder(base, body, ident)
        catalog = _single_root_catalog(base, kind, root_path)
        result = _resolve(catalog, ident)
        assert result.status is ResolutionStatus.REUSED_EXACT
        handle = result.matches[0].to_dict()
        contracts[kind] = _contract(handle)
        paths[kind] = handle["canonical_path"]
    assert contracts["company_raw"] == contracts["dayu_portfolio"] == contracts["directory"]
    assert len(set(paths.values())) == 3


# --- architecture gate: no root-specific business branch in the resolver --------


def test_fc604_no_root_specific_branch_in_resolver():
    """The resolver must carry NO conditional that selects behavior by
    root_id or root_kind (any such branch is a root-specific business
    branch).  Only config-driven reusable_root_kinds allowances are
    permitted."""
    resolver_path = (Path(__file__).resolve().parents[2]
                     / "src" / "company_wiki" / "source_catalog" / "resolver.py")
    tree = ast.parse(resolver_path.read_text(encoding="utf-8"))
    root_specific_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            left = node.left
            comparators = node.comparators
            operands = [left, *comparators]
            # detect `root_id == "dropbox_stock"` / `root.kind == "company_raw"`
            for op in operands:
                if isinstance(op, ast.Constant) and isinstance(op.value, str) \
                        and op.value in ("dropbox_stock", "company_raw", "dayu_portfolio"):
                    root_specific_calls.append((resolver_path.name, node.lineno, op.value))
    assert not root_specific_calls, (
        f"root-specific business branch in resolver: {root_specific_calls}")


def test_fc604_dropbox_configured_not_missing_on_canary(tmp_path):
    """Phase 5 exit gate (regression): a Dropbox-only catalog with a canary
    resolves REUSED_EXACT, never the old MISSING — the consistency gate
    depends on every root being a usable source."""
    from company_wiki.source_catalog import ResolutionStatus

    ident = _identity("CN", "601899", "1225023658", 2025)
    body = b"%PDF-1.4 dropbox-canary"
    catalog = _single_root_catalog(tmp_path / "db", "directory",
                                   _dropbox_fixture(tmp_path / "db", body, ident))
    result = _resolve(catalog, ident)
    assert result.status is ResolutionStatus.REUSED_EXACT
    handle = result.matches[0].to_dict()
    assert handle["capture_ready"] is True
    assert handle["content_sha256"] == hashlib.sha256(body).hexdigest()
