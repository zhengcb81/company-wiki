"""Opt-in FF source candidates must come from a DB-only CWP query."""


from __future__ import annotations


import hashlib


import json


import os


from pathlib import Path


import subprocess






import pytest






SHA = hashlib.sha256(b"isolated metadata-only source").hexdigest()


DOCUMENT = "urn:company-wiki:document:sha256:" + SHA


SOURCE = "urn:company-wiki:source:sha256:" + SHA


def _wiki(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    config = root / "config"
    config.mkdir(parents=True)
    (config / "source_catalog.yaml").write_text("schema_version: '1.0'\n", encoding="utf-8")
    return root


def _request() -> dict:
    return {
        "schema_version": "1.1", "company_query": "AMD", "market": "US",
        "document_kind": "annual_report", "fiscal_year": 2025,
        "as_of_date": "2026-07-18",
    }


def _v2_request(*, intent: str = "fetch_if_missing") -> dict:
    return {
        **_request(),
        "schema_version": "2.0",
        "filing_intent": intent,
        "acquisition_limits": {
            "max_bytes": 5_000_000,
            "timeout_seconds": 60,
            "max_cost_usd": "1.00",
        },
    }


def _identity() -> dict:
    return {
        "schema_version": "1.0", "status": "resolved", "reason": "exact ticker",
        "resolved": {
            "canonical_name": "Advanced Micro Devices, Inc.",
            "market": "US", "exchange": "NASDAQ", "ticker": "AMD",
            "security_id": "AMD", "match_basis": "ticker",
            "matched_value": "AMD", "source_name": "SEC",
            "source_url": "https://www.sec.gov/files/company_tickers.json",
            "source_record_id": "urn:company-wiki:security:US:AMD",
            "verified": True, "active": True,
        },
    }


def _ref() -> dict:
    return {
        "schema_version": "2.0", "document_id": DOCUMENT,
        "source_id": SOURCE, "content_sha256": SHA, "byte_size": 42,
        "mime_type": "application/pdf",
    }


def _candidate() -> dict:
    return {
        "source_ref": _ref(), "document_id": DOCUMENT,
        "source_id": SOURCE, "title": "AMD 2025 annual report",
        "document_kind": "annual_report", "fiscal_year": 2025,
        "fiscal_period": None, "period_end": "2025-12-31",
        "form_type": "10-K", "published_date": "2026-02-20",
        "https_url": "https://www.sec.gov/Archives/amd/2025",
        "snapshot_sha256": SHA, "byte_size": 42,
        "mime_type": "application/pdf",
        "retrieved_at": "2026-02-21T00:00:00Z",
        "collector_name": "filesystem-catalog-company_raw",
        "collector_version": "1.0.0", "provider": "sec",
        "provider_document_id": "amd-2025-10k",
        "capture_ready": True, "capture_provenance": "indexed_location_manifest",
        "prompt_injection_status": "not_detected",
    }


def _query(status: str = "found", candidate: dict | None = None) -> dict:
    return {
        "schema_version": "2.0", "status": status,
        "reason": "one_local_match" if status == "found" else "no_local_match",
        "request_id": "urn:company-wiki:source-request:sha256:" + "a" * 64,
        "matches": [_ref()] if status == "found" else [],
        "candidates": [candidate or _candidate()] if status == "found" else [],
        "source_read_policy_sha256": "b" * 64,
    }


def _completed(payload: dict, rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], rc, json.dumps(payload), "")


def test_real_db_only_reuse_accepts_configured_root_with_legacy_labels_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    cwp_root_text = os.environ.get("CWP_V2_CODE_ROOT")
    if not cwp_root_text:
        pytest.skip("set CWP_V2_CODE_ROOT to the isolated CWP checkout")
    cwp_root = Path(cwp_root_text).resolve(strict=True)
    cwp_src = cwp_root / "src"
    monkeypatch.syspath_prepend(str(cwp_src))
    monkeypatch.setenv(
        "PYTHONPATH", str(cwp_src) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    from e2e_support import isolated_wiki
    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.policy_2x import export_policy_2x
    from company_wiki.source_catalog.prompt_injection import record_prompt_injection_review

    monkeypatch.setattr(isolated_wiki, "PRODUCTION_WIKI", cwp_root)
    wiki = isolated_wiki.IsolatedWiki(tmp_path / "wiki")
    text = wiki.config_path.read_text(encoding="utf-8")
    assert "    priority: 10\n" in text
    wiki.config_path.write_text(
        text.replace(
            "    priority: 10\n",
            "    priority: 10\n    reusable_for_filing: false\n",
        ) + "reusable_root_kinds: [directory]\n", encoding="utf-8",
    )
    source = wiki.seed_market("US")
    body = source.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    wiki.scan()
    catalog = SourceCatalog(load_catalog_config(wiki.config_path))
    try:
        row = catalog.store.fetchone(
            "SELECT d.document_id FROM documents d JOIN sources s "
            "ON s.source_id=d.primary_source_id WHERE s.content_sha256=?",
            (digest,),
        )
        assert row is not None
        policy_hash, _ = export_policy_2x(catalog.config)
        with catalog.store.transaction() as connection:
            record_prompt_injection_review(
                connection, str(row["document_id"]), status="not_detected",
                reviewer="ff-v2-e2e", evidence_sha256=digest,
                source_sha256=digest, policy_hash=policy_hash,
                evidence_payload=body, now="2026-09-27T00:00:00Z",
            )
    finally:
        catalog.close()
    rc, stdout, stderr = wiki.run_fetch({
        "schema_version": "1.1", "company_query": "Apple Inc.",
        "market": "US", "document_kind": "annual_report",
        "fiscal_year": 2025, "as_of_date": "2026-09-27",
    }, extra_args=["--source-ref-v2"])
    assert rc == 0, stderr + stdout
    response = json.loads(stdout)
    assert response["status"] == "capture_ready"
    assert response["handle"]["source_ref"]["content_sha256"] == digest
    assert response["handle"]["download_events"] == response["downloads"] == 0
    assert response["handle"]["prompt_injection_status"] == "not_detected"
    assert wiki.journal_outcomes() == []


def _operation_v2(
    *,
    operation: str = "ensure",
    status: str = "completed",
    outcome: str = "reused_after_discovery",
    download_events: int = 0,
    gap_plan: dict | None = None,
    policy_hash: str | None = "b" * 64,
) -> dict:
    return {
        "operation_schema_version": "1.0",
        "operation": operation,
        "status": status,
        "request_id": "urn:req:operation-v2",
        "outcome": outcome,
        "download_events": download_events,
        "policy_hash": policy_hash,
        "source_ref": _ref() if status == "completed" else None,
        "candidate": _candidate() if status == "completed" else None,
        "gap_plan": gap_plan,
    }


def _latest_request() -> dict:
    return {
        "schema_version": "1.2",
        "company_query": "AMD",
        "market": "US",
        "document_kind": "annual_report",
        "mode": "latest_as_of",
        "as_of_date": "2026-09-27",
    }
