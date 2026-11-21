"""Isolated fixtures for the scheduled-refresh source and reading surfaces.

Nothing here touches production configuration, a real provider or a paid
model.  The provider is a local stand-in that declares its own coverage, and
the originals are real bytes registered through the real catalog writer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.acquisition import DiscoveryPage, DownloadCandidate
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader

PROVIDER = "fixture"
MARKET = "CN"
SECURITY_ID = "600001"
ENTITY = "Acme"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class FixturePage:
    """One provider page the stand-in returns."""

    candidates: tuple[DownloadCandidate, ...]
    next_cursor: str | None = None
    coverage: str = "complete"
    covered_from: str | None = None
    covered_to: str | None = None
    reason_codes: tuple[str, ...] = ()


class FixtureDiscoveryAdapter:
    """A bounded provider stand-in that declares its own page coverage.

    It implements the same adapter surface the production adapters use —
    including the bounded discovery pair — so the discovery owner is
    exercised through the real routing, capability gate and validation.
    """

    name = "fixture-provider"
    version = "1.0.0"
    supports_acquisition_budget = True

    def __init__(self, *, pages: list[FixturePage], market: str = MARKET) -> None:
        self._pages = list(pages)
        self._market = market
        self.requests: list[dict] = []
        self.fetches: list[str] = []

    def discover(self, request):
        return self.discover_page(request).candidates

    def discover_bounded(self, request, budget):
        return self.discover_page(request).candidates

    def discover_page(self, request, *, since_date=None) -> DiscoveryPage:
        self.requests.append(request.to_dict())
        cursor = getattr(request, "cursor", None)
        index = 0 if cursor is None else int(cursor)
        if index >= len(self._pages):
            return DiscoveryPage((), coverage="complete", covered_to=request.as_of_date)
        page = self._pages[index]
        return DiscoveryPage(
            candidates=page.candidates,
            coverage=page.coverage,
            next_cursor=page.next_cursor,
            reason_codes=page.reason_codes,
            covered_from=page.covered_from,
            covered_to=page.covered_to,
        )

    def discover_page_bounded(self, request, budget, *, since_date=None) -> DiscoveryPage:
        return self.discover_page(request, since_date=since_date)

    def fetch(self, candidate, staging_dir):  # pragma: no cover - never called here
        raise AssertionError("discovery must not fetch original bytes")

    def fetch_bounded(self, candidate, staging_dir, budget):  # pragma: no cover
        raise AssertionError("discovery must not fetch original bytes")


def candidate(
    *,
    provider_document_id: str,
    document_kind: str,
    filing_date: str,
    fiscal_year: int = 2026,
    fiscal_period: str | None = "FY",
    amended: bool = False,
    title: str = "Acme filing",
    market: str = MARKET,
    entity: str = ENTITY,
    security_id: str = SECURITY_ID,
) -> DownloadCandidate:
    """One provider document identity, as the provider actually reports it."""
    return DownloadCandidate(
        candidate_id=f"{PROVIDER}:{provider_document_id}",
        provider=PROVIDER,
        provider_document_id=provider_document_id,
        market=market,
        entity=entity,
        title=title,
        source_url=f"https://provider.invalid/{provider_document_id}",
        document_kind=document_kind,
        filing_date=filing_date,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        amended=amended,
        security_id=security_id,
    )


#: Two real originals registered through the real catalog writer.  The first is
#: already registered, so the refresh must reuse it and download nothing.
REGISTERED_ANNUAL = (
    "Acme 2025 annual report\n"
    "The company expanded overseas capacity and launched a new product line.\n"
).encode("utf-8")

REGISTERED_IR = (
    "Acme investor relations announcement\n"
    "Acme completed the customer certification of a new product and started "
    "batch delivery in the second quarter.\n"
).encode("utf-8")


def build_catalog(root: Path, *, documents=(
    ("annual-report.txt", REGISTERED_ANNUAL, "annual_report", "FY", None),
    ("ir-announcement.txt", REGISTERED_IR, "investor_relations", None, None),
), sidecar_overrides=None):
    """Register real originals and return the catalog plus their exact refs."""
    company_root = root / "companies" / ENTITY / "raw"
    company_root.mkdir(parents=True, exist_ok=True)
    for name, data, kind, period, title in documents:
        (company_root / name).write_bytes(data)
        sidecar = {
            "schema_version": "1.0", "canonical_entity_id": "ent-acme",
            "display_name": ENTITY, "market": MARKET, "security_id": SECURITY_ID,
            "document_kind": kind, "fiscal_year": 2026,
            "fiscal_period": period or "Q1", "period_end": "2026-03-31",
            "filing_date": "2026-05-01", "provider": PROVIDER,
            "provider_document_id": name, "content_sha256": sha256(data),
            "source_url": "https://fixtures.invalid/" + name,
            "source_title": title or name, "retrieved_at": "2026-05-02T00:00:00Z",
            "collector_name": "sr_cwp_fixture", "collector_version": "1.0.0",
        }
        sidecar.update((sidecar_overrides or {}).get(name, {}))
        (company_root / (name + ".source.json")).write_text(
            json.dumps(sidecar), encoding="utf-8"
        )
    # The public CLI derives the project root from <root>/config/<file>,
    # matching the production layout convention.
    config_dir = root / "config"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "catalog.json"
    config_path.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw",
            "adapter_id": "company_raw_v1", "read_only": True,
            "reusable_for_filing": True,
        }],
    }), encoding="utf-8")
    catalog = SourceCatalog(load_catalog_config(config_path, project_root=root))
    catalog.scan()
    reader = SourceVersionReader(catalog)
    refs = {}
    for name, data, _kind, _period, _title in documents:
        row = catalog.reader.fetchone(
            "SELECT d.document_id, d.primary_source_id AS source_id FROM documents d "
            "JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?",
            (sha256(data),),
        )
        assert row is not None
        ref = reader.query_ref(row["document_id"], row["source_id"], sha256(data))
        refs[name] = ref
    return SimpleNamespace(
        root=root, config_path=config_path, catalog=catalog, reader=reader, refs=refs
    )


@pytest.fixture
def sr_cwp_catalog(tmp_path):
    """A registered catalog with two real originals; always closed."""
    state = build_catalog(tmp_path)
    try:
        yield state
    finally:
        state.catalog.close()


#: A transcript TXT whose body carries a proven speaker turn, an
#: annual-report PDF with business content, and a PDF template without any.
TRANSCRIPT_BODY = (
    "Full Conference Call Transcript\n"
    "CEO: We launched a new product and expanded overseas capacity.\n"
).encode("utf-8")

TEMPLATE_PDF_TEXT = "This policy describes meeting administration procedures."
ANNUAL_PDF_TEXT = (
    "Company launched a new product and expanded overseas capacity for customers."
)


def _pdf_bytes(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    try:
        document.new_page().insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def readable_documents():
    """Real parseable originals: transcript TXT, business PDF, template PDF.

    The template carries a real IR-policy title: the reading route classifies
    administrative policies by title, and only then may an empty selection
    become a named skip instead of a reviewable gap.
    """
    return [
        ("call-transcript.txt", TRANSCRIPT_BODY, "investor_call_transcript", "Q1",
         "Acme 2026 Q1 earnings call"),
        ("annual-report.pdf", _pdf_bytes(ANNUAL_PDF_TEXT), "annual_report", "FY",
         "Acme annual report 2025"),
        ("ir-policy-template.pdf", _pdf_bytes(TEMPLATE_PDF_TEXT), "ir_policy", None,
         "Acme投资者关系管理办法（2025年8月）.pdf"),
    ]


def build_readable_catalog(root: Path):
    """Register parseable originals through the real catalog writer."""
    return build_catalog(root, documents=readable_documents())


@pytest.fixture
def sr_cwp_readable_catalog(tmp_path):
    """A registered catalog with parseable originals; always closed."""
    state = build_readable_catalog(tmp_path)
    try:
        yield state
    finally:
        state.catalog.close()
