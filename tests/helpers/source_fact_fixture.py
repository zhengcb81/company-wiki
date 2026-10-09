"""Bounded owned-source fixtures for source facts and request relevance."""

import hashlib
import json

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.official_source_flow import import_official_source
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityRecord,
)


def lake(root, *, portfolio=False):
    raw = root / "companies"
    raw.mkdir()
    roots = [RootSpec("company_raw", raw, "company_raw")]
    if portfolio:
        provider = root / "portfolio"
        provider.mkdir()
        roots.append(
            RootSpec(
                "provider",
                provider,
                "dayu_portfolio",
                read_only=True,
                reusable_for_filing=True,
            )
        )
    cat = SourceCatalog(
        CatalogConfig(
            project_root=root, catalog_dir=root / "catalog", roots=tuple(roots)
        )
    )
    cat.store  # initialize an empty owned catalog before read-only discovery
    SecurityMasterStore(cat.config.catalog_dir / "security_master").write_market(
        "US",
        (
            SecurityRecord(
                "Acme",
                "US",
                "NASDAQ",
                "ACME",
                "ACME",
                ("Acme Corp",),
                True,
                "sec",
                "https://www.sec.gov/files/company_tickers.json",
                "12345",
                {"cik": "12345"},
            ),
        ),
        retrieved_at="2026-10-09T00:00:00Z",
        sources=("sec",),
    )
    return cat


def html(
    *,
    year=2026,
    period="FY",
    form="10-K",
    end="2026-06-30",
    transform="",
    cik="12345",
    title="10-K",
):
    return f'<html><head><title>{title}</title></head><body><ix:nonNumeric name="dei:EntityCentralIndexKey">{cik}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentFiscalYearFocus">{year}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">{period}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentPeriodEndDate" format="{transform}">{end}</ix:nonNumeric><ix:nonNumeric name="dei:DocumentType">{form}</ix:nonNumeric><p>Acme actual original.</p></body></html>'.encode()


def imported(
    cat, data, *, published=None, declared_year=None, title="fixture original", document_kind="annual_report", source_url=None
):
    sha = hashlib.sha256(data).hexdigest()
    request = {
        "schema_version": "official-source-import-request/1",
        "request_id": "fixture",
        "source": {
            "entity": "Acme",
            "market": "US",
            "security_id": "ACME",
            "document_kind": document_kind,
            "title": title,
            "publisher": "Acme",
            "source_url": source_url or "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/original.htm",
            "published_date": published,
            "filing_date": published,
            "fiscal_year": declared_year,
            "language": "en",
        },
        "content_sha256": sha,
        "mime_type": "text/html",
        "max_bytes": 4096,
        "capture_receipt": {
            "capture_method": "local_document",
            "tool_name": "fixture",
            "tool_call_id": "one",
            "captured_at": "2026-10-09T00:00:00Z",
            "content_sha256": sha,
            "response_bytes": len(data),
        },
    }
    result = import_official_source(cat, original=data, request=request)
    ref = SourceRef(**result["source_ref"])
    loc = cat.reader.exact_source_locations(ref.document_id, ref.source_id)[0]
    return ref, cat.config.roots[0].path / loc["relative_path"]


def evidence(ref, facts):
    return {
        key: {
            "value": value,
            "locator": "html:/html/head/title"
            if key == "title"
            else "primary-dei:/DocumentType",
            "content_sha256": ref.content_sha256,
            "observed_at": "2026-10-09T00:00:00Z",
        }
        for key, value in facts.items()
    }


def remove_capture_title(cat, ref):
    row = cat.reader.fetchone(
        "SELECT metadata_json FROM documents WHERE document_id=?", (ref.document_id,)
    )
    meta = json.loads(row["metadata_json"])
    meta["acquisition"]["source_title"] = None
    with cat.store.transaction() as conn:
        conn.execute(
            "UPDATE documents SET metadata_json=? WHERE document_id=?",
            (json.dumps(meta), ref.document_id),
        )
        # Model a pre-title-fact legacy capture in this owned fixture only.
        for assertion in conn.execute(
            "SELECT assertion_id,evidence_json FROM source_metadata_assertions WHERE source_id=?",
            (ref.source_id,),
        ).fetchall():
            proof = json.loads(assertion["evidence_json"])
            for key in ("source_fact_patch", "source_fact_evidence"):
                if isinstance(proof.get(key), dict):
                    proof[key].pop("title", None)
            conn.execute(
                "UPDATE source_metadata_assertions SET evidence_json=? WHERE assertion_id=?",
                (json.dumps(proof), assertion["assertion_id"]),
            )


def close(cat):
    cat.close()
