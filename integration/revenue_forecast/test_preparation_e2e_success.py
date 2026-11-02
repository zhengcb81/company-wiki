"""WU-1201 C2: full-chain success path — fixture catalog hit.

Builds a temp company-wiki root (config + catalog with one active document),
spawns the REAL source_preparation chain with --company-wiki-config, and
asserts a RevenueSourceRecord is produced (no fabricated handles).
"""
import datetime as _dt
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT


def _fixture_wiki_root(tmp: Path) -> Path:
    """A temp company-wiki root with an indexed active annual report."""
    # RF-E2E-ADAPT: the review receipt is written through CW's fail-closed
    # writer (state_domain + payload/dual binding, the promoted 5d72529
    # contract) — same call shape as CW tests/unit/test_prompt_injection_guard.
    sys.path.insert(0, str(ROOT.parent / "company-wiki" / "src"))
    from company_wiki.source_catalog.prompt_injection import (
        record_prompt_injection_review,
    )
    from company_wiki.source_catalog.prompt_injection_guard import RULESET_HASH

    catalog = tmp / ".source_catalog" / "catalog.sqlite3"
    catalog.parent.mkdir(parents=True)
    companies = tmp / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    companies.mkdir(parents=True)
    import hashlib

    pdf_body = b"%PDF-1.4 acme" * 10
    (companies / "2025_Acme_annual.pdf").write_bytes(pdf_body)
    PDF_SIZE = len(pdf_body)
    PDF_SHA = hashlib.sha256(pdf_body).hexdigest()
    con = sqlite3.connect(catalog)
    con.execute("CREATE TABLE roots (root_id TEXT, path TEXT, kind TEXT, "
                "priority INTEGER, last_scan_run TEXT, last_scanned_at TEXT)")
    con.execute("INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', "
                "10, '', '')", (str(tmp / "companies"),))
    con.execute("CREATE TABLE sources (source_id TEXT PRIMARY KEY, "
                "content_sha256 TEXT, byte_size INTEGER, mime_type TEXT, "
                "first_seen_at TEXT)")
    con.execute("CREATE TABLE documents (document_id TEXT PRIMARY KEY, "
                "primary_source_id TEXT, title TEXT, source_status TEXT, "
                "source_type TEXT, document_kind TEXT, published_date TEXT, "
                "metadata_priority INTEGER, metadata_json TEXT, "
                "first_seen_at TEXT, last_seen_at TEXT)")
    con.execute("CREATE TABLE locations (location_id TEXT PRIMARY KEY, "
                "root_id TEXT, relative_path TEXT, absolute_path TEXT, "
                "source_id TEXT, document_id TEXT, role TEXT, "
                "location_status TEXT, observed_size INTEGER, "
                "observed_mtime_ns INTEGER, last_seen_run TEXT, "
                "manifest_json TEXT, metadata_json TEXT, error TEXT)")
    con.execute("CREATE TABLE artifacts (artifact_id TEXT, document_id TEXT, "
                "artifact_role TEXT, source_id TEXT, path TEXT, "
                "content_sha256 TEXT, byte_size INTEGER, mime_type TEXT, "
                "generator_name TEXT, generator_version TEXT, status TEXT, "
                "error TEXT, schema_version TEXT, source_sha256 TEXT, "
                "created_at TEXT)")
    con.execute("CREATE TABLE entities (entity_id TEXT PRIMARY KEY, name TEXT, "
                "entity_kind TEXT)")
    con.execute("CREATE TABLE document_entities (document_id TEXT, entity_id "
                "TEXT, confidence REAL, method TEXT)")
    con.execute("INSERT INTO entities VALUES ('ent-acme', 'Acme', 'company')")
    con.execute("INSERT INTO document_entities VALUES ('d1', 'ent-acme', 1.0, "
                "'fixture')")
    # ZR-203: the read-only resolve path reads these tables directly (no
    # store initialization on the read path) — the fixture must carry the
    # full read schema instead of relying on implicit DDL.
    con.execute("CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, "
                "value TEXT NOT NULL)")
    con.execute("INSERT INTO catalog_meta VALUES ('schema_version', '1.2.0')")
    con.execute("CREATE TABLE remediation_proposals (proposal_id TEXT PRIMARY KEY, "
                "source_id TEXT, status TEXT, proposed_by TEXT, created_at TEXT)")
    con.execute("CREATE TABLE producer_events (event_id TEXT PRIMARY KEY, "
                "document_id TEXT, artifact_role TEXT, producer_name TEXT, "
                "producer_version TEXT, event_type TEXT, created_at TEXT)")
    con.execute("CREATE TABLE source_metadata_assertions (assertion_id TEXT "
                "PRIMARY KEY, source_id TEXT, document_id TEXT, "
                "content_sha256 TEXT, evidence_basis TEXT, evidence_json "
                "TEXT, decision TEXT, created_at TEXT, created_by TEXT, "
                "schema_version TEXT, adapter_id TEXT, adapter_version TEXT, "
                "normalization_status TEXT, visibility_state TEXT, "
                "fiscal_year INTEGER, fiscal_period TEXT, document_kind TEXT, "
                "form_type TEXT, provider TEXT, provider_document_id TEXT, "
                "source_url TEXT, security_id TEXT, market TEXT)")
    con.execute("INSERT INTO sources VALUES ('s1', ?, 100, "
                "'application/pdf', '2026-01-01')", (PDF_SHA,))
    doc_meta = json.dumps({"acquisition": {
        "form_type": "annual_report", "fiscal_year": 2025,
        "source_url": "https://example-filing.com/acme/2025",
        "provider": "example-filing", "market": "US",
        "security_id": "SEC-US"}})
    con.execute("INSERT INTO documents VALUES ('d1', 's1', 'Acme 2025', "
                "'active', 'file', 'annual_report', '2026-04-15', 10, ?, "
                "'2026-01-01', '2026-01-01')", (doc_meta,))
    # FC-905: the chain blocks unreviewed sources — the fixture document
    # carries a review receipt so the E2E chain passes the policy gate.
    # RF-E2E-ADAPT: written via CW's writer (state_domain stamped, evidence
    # payload bound to the reviewed source bytes) — a hand-shaped pre-5d72529
    # dict is fail-closed as not_reviewed by the reader's state_domain gate.
    record_prompt_injection_review(
        con, "d1", status="not_detected", reviewer="fixture-reviewer",
        evidence_sha256=PDF_SHA, now="2026-01-01T00:00:00Z",
        source_sha256=PDF_SHA, policy_hash=RULESET_HASH,
        evidence_payload=pdf_body,
    )
    con.execute("INSERT INTO locations VALUES ('l1', 'company_raw', "
                "'2025_Acme_annual.pdf', ?, 's1', 'd1', 'original_primary', 'active', "
                "100, 0, '2026-01-01', ?, ?, NULL)",
                (str(companies / "2025_Acme_annual.pdf"),
                 json.dumps({"content_sha256": PDF_SHA,
                             "retrieved_at": "2026-04-15T00:00:00Z",
                             "collector_name": "fixture",
                             "collector_version": "1.0.0",
                             "mime_type": "application/pdf",
                             "byte_size": PDF_SIZE}),
                 json.dumps({"acquisition": {}}),))
    con.commit()
    con.close()
    # security_master snapshots (identity anchor for the chain)
    master = tmp / ".source_catalog" / "security_master"
    master.mkdir(parents=True, exist_ok=True)
    for market in ("CN", "US", "HK"):
        (master / f"{market.lower()}.json").write_text(json.dumps({
            "schema_version": "1.0", "market": market,
            "retrieved_at": "2026-01-01", "sources": ["fixture"],
            "record_count": 1,
            "records": [{
                "schema_version": "1.0", "canonical_name": "Acme Corp",
                "market": market, "exchange": "TEST", "ticker": "ACME",
                "security_id": f"SEC-{market}", "aliases": [],
                "active": True, "source_name": "fixture",
                "source_url": "https://x", "source_record_id": f"rec-{market}",
                "identifiers": {},
            }],
        }), encoding="utf-8")
    (tmp / "config").mkdir()
    (tmp / "config" / "source_catalog.yaml").write_text(
        "\n".join([
            "schema_version: '1.0'",
            "catalog_dir: " + str(tmp / ".source_catalog"),
            "roots:",
            "  - root_id: company_raw",
            "    path: " + str(tmp / "companies"),
            "    kind: company_raw",
        ]),
        encoding="utf-8",
    )
    return tmp


def test_full_chain_hits_fixture_record(tmp_path):
    """P5-RF: the real chain hits an EXISTING indexed filing on the v2 route
    and the record comes back with zero expensive calls."""
    from e2e_support.isolated_lake import IsolatedLake

    IsolatedLake(tmp_path, seed="prep-e2e").build()
    wiki = tmp_path / "lake" / "project"
    filing_config = wiki / "filing_config.json"
    filing_config.write_text(
        json.dumps({"schema_version": "1.0",
                    "company_wiki_root": str(wiki)}),
        encoding="utf-8",
    )
    request = {
        "schema_version": "1.2",
        "company_query": "紫金矿业",
        "market": "CN",
        "document_kind": "annual_report",
        "as_of_date": (_dt.date.today() + _dt.timedelta(days=7)).isoformat(),
        "fiscal_year": 2025,
    }
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "source_preparation.py"),
         "--company-wiki-config", str(filing_config),
         "--filing-fetch-root",
         str(Path.home() / "Projects" / "filing-fetch"),
         "--company-wiki-catalog-config",
         str(wiki / "config" / "source_catalog.yaml")],
        input=json.dumps(request), text=True, encoding="utf-8",
        capture_output=True, timeout=300, check=False,
    )
    # C2: the chain MUST succeed against the fixture (existing filing hit)
    assert proc.returncode == 0, f"chain failed: {proc.stderr}"
    record = json.loads(proc.stdout)
    assert record["source_type"] == "regulatory_filing"
    assert record["company_wiki_trace"]["read_receipt"]["document_id"]
    # PROCESS-E2E-01: hit-existing-filing => zero expensive calls
    receipt = record["reuse_receipt"]
    assert receipt["parser_calls"] is None
    assert receipt["llm_calls"] is None
    assert receipt["download_calls"] == 0
    assert receipt["outcome"] in ("reused_existing", "reused_exact")
