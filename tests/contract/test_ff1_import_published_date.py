"""FF-1 B3: the ensure import writes published_date from the candidate's
filing_date DECLARATION through the existing source-facts mechanism.

Root cause being pinned here (2026-11-14 diagnosis, mdb-20260131): a prior
verified assertion recorded ``published_date: None`` (explicit unknown), and
``_record_validated_capture`` dropped every fact key already present in the
prior patch — so a later capture that DECLARED a filing date could never fill
the empty column.  An explicit unknown is an empty stored column, not a
correction: a declaring import fills it; a prior non-empty value still wins;
no value is guessed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    CanonicalSourceWriter,
    CatalogConfig,
    DownloadCandidate,
    DownloadReceipt,
    RootSpec,
    SourceCatalog,
    SourceRequest,
)

PAYLOAD = b"%PDF-1.4 ff1 b3 published-date declaration fixture"
SHA = hashlib.sha256(PAYLOAD).hexdigest()
DOCUMENT = "urn:company-wiki:document:sha256:" + SHA
SOURCE = "urn:company-wiki:source:sha256:" + SHA


def _catalog(tmp_path: Path) -> SourceCatalog:
    companies = tmp_path / "companies"
    companies.mkdir(parents=True, exist_ok=True)
    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10,
                         adapter_id="company_raw_v1", read_only=False,
                         reusable_for_filing=True, canonical_write_target="companies"),
            ),
        )
    )


def _staged(tmp_path: Path, *, filing_date: str | None, provider_id: str):
    staging = tmp_path / "staging" / "report.pdf"
    staging.parent.mkdir(parents=True, exist_ok=True)
    if not staging.exists():
        staging.write_bytes(PAYLOAD)
    request = SourceRequest(
        entity="Acme", security_id="600000", market="CN",
        document_kind="annual_report", fiscal_year=2025, fiscal_period="FY",
        as_of_date="2026-10-08", allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id=f"cninfo:{provider_id}",
        provider="cninfo",
        provider_document_id=provider_id,
        market="CN",
        entity="Acme",
        title="Acme 2025 Annual Report",
        source_url="https://static.cninfo.com.cn/finalpage/2026/report.pdf",
        document_kind="annual_report",
        form_type="annual_report",
        filing_date=filing_date,
        fiscal_year=2025,
        fiscal_period="FY",
        language="zh-CN",
        security_id="600000",
    )
    receipt = DownloadReceipt(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        provider_document_id=candidate.provider_document_id,
        source_url=candidate.source_url,
        staged_path=str(staging),
        content_sha256=SHA,
        byte_size=len(PAYLOAD),
        mime_type="application/pdf",
        retrieved_at="2026-10-09T12:00:00Z",
        http_status=200,
        adapter_name="fixture-adapter",
        adapter_version="1.0.0",
    )
    return request, candidate, receipt


def _document_row(catalog: SourceCatalog):
    return catalog.reader.exact_source_version(DOCUMENT)


def _latest_patch(catalog: SourceCatalog) -> dict:
    row = catalog.reader.fetchone(
        """SELECT evidence_json FROM source_metadata_assertions
           WHERE document_id=? AND decision='verified'
           ORDER BY created_at DESC LIMIT 1""",
        (DOCUMENT,),
    )
    assert row is not None
    evidence = json.loads(row["evidence_json"])
    patch = evidence.get("source_fact_patch") or {}
    return patch


def test_import_writes_published_date_from_the_declared_filing_date(tmp_path):
    catalog = _catalog(tmp_path)
    try:
        request, candidate, receipt = _staged(
            tmp_path, filing_date="2026-03-11", provider_id="declared-1",
        )
        CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging").import_staged(
            request, candidate, receipt,
        )

        row = _document_row(catalog)
        assert row is not None
        assert row["published_date"] == "2026-03-11"
        patch = _latest_patch(catalog)
        assert patch["published_date"] == "2026-03-11"
        # Declaration provenance rides the source-facts evidence.
        proof = json.loads(catalog.reader.fetchone(
            """SELECT evidence_json FROM source_metadata_assertions
               WHERE document_id=? AND decision='verified'
               ORDER BY created_at DESC LIMIT 1""",
            (DOCUMENT,),
        )["evidence_json"])["source_fact_evidence"]["published_date"]
        assert proof["value"] == "2026-03-11"
        assert proof["locator"] == "canonical-commit:/candidate/published_date"
        assert proof["extraction_method"] == "provider-metadata-import/1"
    finally:
        catalog.close()


def test_declared_import_fills_a_prior_explicit_unknown(tmp_path):
    """The 2026-11-10 regression: prior patch says None, capture declares."""
    catalog = _catalog(tmp_path)
    try:
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        # Import #1 without a filing-date declaration: honest unknown.
        request, candidate, receipt = _staged(
            tmp_path, filing_date=None, provider_id="undeclared-1",
        )
        CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging").import_staged(
            request, candidate, receipt,
        )
        assert _document_row(catalog)["published_date"] is None
        assert _latest_patch(catalog)["published_date"] is None

        # A later verified observation pins the explicit unknown (the shape
        # the 2026-11-08 batch wrote for the MDB rows).
        ref = SourceVersionReader(catalog).query_ref(DOCUMENT, SOURCE, SHA)
        catalog.record_source_facts(
            ref=ref,
            facts={"published_date": None},
            evidence={"published_date": {
                "locator": "fixture:explicit-publication", "value": None,
            }},
        )
        assert _latest_patch(catalog)["published_date"] is None

        # Re-acquisition of the same bytes whose candidate now DECLARES the
        # filing date: the empty column is filled, not skipped.
        request, candidate, receipt = _staged(
            tmp_path, filing_date="2026-03-11", provider_id="declared-2",
        )
        CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging").import_staged(
            request, candidate, receipt,
        )

        assert _document_row(catalog)["published_date"] == "2026-03-11"
        assert _latest_patch(catalog)["published_date"] == "2026-03-11"
    finally:
        catalog.close()


def test_prior_known_publication_date_still_wins(tmp_path):
    """A prior non-empty value stays authoritative (no silent replacement)."""
    catalog = _catalog(tmp_path)
    try:
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        request, candidate, receipt = _staged(
            tmp_path, filing_date="2026-03-11", provider_id="declared-1",
        )
        CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging").import_staged(
            request, candidate, receipt,
        )
        ref = SourceVersionReader(catalog).query_ref(DOCUMENT, SOURCE, SHA)
        catalog.record_source_facts(
            ref=ref,
            facts={"published_date": "2026-03-12"},
            evidence={"published_date": {
                "locator": "fixture:explicit-publication", "value": "2026-03-12",
            }},
        )
        assert _document_row(catalog)["published_date"] == "2026-03-12"

        request, candidate, receipt = _staged(
            tmp_path, filing_date="2026-03-11", provider_id="declared-3",
        )
        CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging").import_staged(
            request, candidate, receipt,
        )

        assert _document_row(catalog)["published_date"] == "2026-03-12"
        assert _latest_patch(catalog)["published_date"] == "2026-03-12"
    finally:
        catalog.close()
