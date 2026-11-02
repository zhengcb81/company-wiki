"""R1 cross-process companion failure retention and source-clock compatibility."""


from __future__ import annotations

import os




import json


from pathlib import Path


import subprocess


import sys




import pytest


sys.path.insert(0, str(Path(os.environ["RF_CODE_ROOT"]) / "scripts"))




import source_preparation as prep






def companion():
    return {
        "status": "not_run",
        "reason": "filing_failed_before_companion_dispatch",
        "retryable": False,
        "intent": "fetch_if_missing",
        "provider": "fmp",
        "fiscal_year": 2026,
        "fiscal_quarter": 2,
        "acquisition_limits": {
            "max_bytes": 100000,
            "timeout_seconds": 10,
            "max_cost_usd": "0",
        },
        "provider_started": False,
        "provider_requests": 0,
        "provider_response_bytes": 0,
        "provider_usage_complete": True,
    }


def failed():
    return {
        "schema_version": "2.0",
        "status": "upstream_error",
        "request_period": {
            "mode": "exact",
            "fiscal_year": 2026,
            "fiscal_period": "H1",
            "as_of_date": "2026-10-21",
        },
        "filing": {
            "status": "upstream_error",
            "reason": "company-wiki ensure unavailable",
            "retryable": False,
            "producer_exit_code": 2,
            "upstream_cause": {
                "schema_version": "filing-upstream-cause/1",
                "operation": "ensure",
                "code": "local_candidate_limit",
                "provider_started": False,
                "usage_complete": True,
                "retry_scope": "none",
            },
        },
        "transcript": companion(),
        "calls": 2,
        "downloads": 0,
    }


def proof():
    return {
        "schema_version": "source-availability-evidence/1",
        "source_sha256": "a" * 64,
        "available_by": "2026-10-21",
        "basis": "current_verified_open",
        "evidence_ref": "source-verified-open:sha256:fixture",
        "locator": "/read_at + /content_sha256",
    }


def test_real_cwp_ff_rf_cold_catalog_offline_contract(tmp_path):
    """Opt-in exact three-checkout CLI chain, with synthetic state only."""
    import os

    cwp_text = os.environ.get("CWP_V2_CODE_ROOT")
    ff_text = os.environ.get("W02_FF_CODE_ROOT")
    if not cwp_text or not ff_text:
        pytest.skip("set CWP_V2_CODE_ROOT and W02_FF_CODE_ROOT for cross-repo contract")
    cwp = Path(cwp_text).resolve(strict=True)
    ff = Path(ff_text).resolve(strict=True)
    wiki = tmp_path / "isolated-wiki"
    (wiki / "companies").mkdir(parents=True)
    (wiki / "config").mkdir()
    (wiki / "config" / "source_catalog.yaml").write_text(
        'schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nroots:\n'
        '  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n',
        encoding="utf-8",
    )
    master = wiki / ".source_catalog" / "security_master"
    master.mkdir(parents=True)
    record = {
        "schema_version": "1.0",
        "canonical_name": "騰訊控股",
        "market": "HK",
        "exchange": "HKEX",
        "ticker": "00700",
        "security_id": "00700",
        "aliases": ["TENCENT"],
        "identifiers": {"org_id": "w02-hk-1"},
        "active": True,
        "source_name": "hkexnews",
        "source_record_id": "w02-hk-1",
        "source_url": "https://www.hkex.com.hk/",
    }
    (master / "hk.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "market": "HK",
                "retrieved_at": "2026-10-21T00:00:00Z",
                "sources": [record["source_url"]],
                "record_count": 1,
                "records": [record],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    connection = wiki / "connection.json"
    connection.write_text(
        json.dumps({"schema_version": "1.0", "company_wiki_root": str(wiki)}),
        encoding="utf-8",
    )
    request = {
        "schema_version": "2.0",
        "company_query": "00700",
        "market": "HK",
        "document_kind": "semi_annual_report",
        "fiscal_year": 2026,
        "fiscal_period": "H1",
        "as_of_date": "2026-10-21",
        "filing_intent": "reuse_only",
        "companion_transcript": {
            "intent": "reuse_only",
            "fiscal_year": 2026,
            "fiscal_quarter": 2,
            "provider": "fmp",
        },
    }
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(cwp / "src"),
    }
    result = subprocess.run(
        [
            sys.executable,
            str(Path(prep.__file__)),
            "--result-envelope",
            "--company-wiki-catalog-config",
            str(wiki / "config" / "source_catalog.yaml"),
            "--company-wiki-config",
            str(connection),
            "--filing-fetch-root",
            str(ff),
            "--timeout-seconds",
            "30",
        ],
        input=json.dumps(request),
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=50,
    )
    assert result.returncode == 3, result.stdout + result.stderr
    error = json.loads(result.stderr)
    assert error["upstream_cause"]["code"] in {
        "catalog_unavailable",
        "reader_unavailable",
    }
    assert error["producer_exit_code"] == 2
    assert error["upstream_cause"]["provider_started"] is False
    assert error["companion_observation"]["status"] == "not_run"
    assert error["companion_observation"]["fiscal_quarter"] == 2
    assert error["companion_observation"]["provider_requests"] == 0
    assert error["filing_fetch_result"]["transcript"] == error["companion_observation"]
    assert not list((wiki / "companies").rglob("*.pdf"))
    assert not (wiki / ".source_catalog" / "acquisition_attempts.jsonl").exists()


def normal_gap():
    value = failed()
    value.update(status="gap", calls=3)
    value["filing"] = {
        "status": "gap",
        "reason": "metadata_only_gap_plan",
        "gap_hash": "e" * 64,
        "download_events": 0,
    }
    value["transcript"] = {
        "status": "not_applicable",
        "reason": "filing_not_capture_ready",
        "retryable": False,
    }
    return value
