"""SR-CWP: the public discover-incremental / read-incremental CLI entries.

Discovery runs a real child-process adapter through the production
``json_command_v1`` wire; reading composes the configured batch entry with a
loopback model for the summary tier.  No production configuration, no paid
API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from support.narrative_batch_fixtures import KEY, loopback_model_server  # noqa: F401
from support.sr_cwp_fixtures import sr_cwp_readable_catalog


REPO = Path(__file__).resolve().parents[2]
ADAPTER_CLI = REPO / "tests" / "support" / "sr_cwp_adapter_cli.py"


def _invoke(command, state, request, extra_args=()):
    return subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli", command,
         "--config", str(state.config_path),
         "--acquisition-config", str(state.root / "config" / "acquisition.json"),
         *extra_args],
        input=json.dumps(request, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONUTF8="1"),
        cwd=str(state.root),
    )


def _write_acquisition_config(root: Path) -> Path:
    """A fixture acquisition config driving the local child-process adapter."""
    command = [sys.executable, "-B", str(ADAPTER_CLI),
               "--name", "fixture-provider", "--version", "1.0.0"]
    config = {
        "schema_version": "1.1",
        "staging_root": str(root / "staging"),
        "timeout_seconds": 60,
        "adapters": {
            "cn": {"name": "fixture-provider", "version": "1.0.0",
                   "interface": "json_command_v1", "project_root": str(root),
                   "config_root": None, "command": command,
                   "supports_acquisition_budget": True},
            "hk": {"name": "fixture-provider", "version": "1.0.0",
                   "interface": "dayu_sdk_bounded_v1", "project_root": str(root),
                   "config_root": None, "command": command,
                   "supports_acquisition_budget": True},
            "us": {"name": "fixture-provider", "version": "1.0.0",
                   "interface": "dayu_sdk_bounded_v1", "project_root": str(root),
                   "config_root": None, "command": command,
                   "supports_acquisition_budget": True},
        },
    }
    path = root / "config" / "acquisition.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_discovery_via_the_public_cli_returns_the_wire_receipt(sr_cwp_readable_catalog):
    """A real child-process adapter answers a complete discovery request."""
    state = sr_cwp_readable_catalog
    _write_acquisition_config(state.root)
    request = {
        "schema_version": "cwp-incremental-discovery-request/1",
        "request_id": "cli-discovery-1",
        "identity": {"entity": "Acme", "security_id": "600001",
                     "identity_scope": None, "issuer_link_id": None},
        "source_market": "CN",
        "document_kinds": ["annual_report"],
        "since_date": "2026-04-01", "as_of_date": "2026-05-31",
        "cursor": None,
        "limits": {"max_candidates": 20, "max_pages": 8, "max_requests": 8,
                   "max_seconds": 120},
    }
    process = _invoke("discover-incremental", state, request)
    assert process.returncode == 0, process.stderr
    receipt = json.loads(process.stdout)
    assert receipt["schema_version"] == "cwp-incremental-discovery/1"
    assert receipt["coverage"] == "complete"
    assert receipt["next_cursor"] is None
    ids = [c["provider_document_id"] for c in receipt["candidates"]]
    assert ids == ["annual-report.pdf", "annual-report-revised.pdf"]
    # The registered original carries its exact reuse ref; the revised
    # accession stays missing locally.
    registered, revised = receipt["candidates"]
    assert registered["existing_source_ref"]["content_sha256"] == (
        state.refs["annual-report.pdf"].content_sha256
    )
    assert revised["existing_source_ref"] is None
    assert "https://provider.invalid" not in json.dumps(receipt)
    assert "usage" in receipt and "candidates" in receipt["usage"]


def test_read_level_local_via_the_public_entry_is_zero_model(sr_cwp_readable_catalog):
    """The composed read entry returns the same receipt as the service."""
    state = sr_cwp_readable_catalog
    ref = state.refs["call-transcript.txt"]
    request = {
        "schema_version": "cwp-incremental-read-request/1",
        "run_id": "cli-read-1", "reading_level": "local",
        "sources": [ref.to_dict()], "limits": None,
    }
    process = _invoke("read-incremental", state, request)
    assert process.returncode == 0, process.stderr
    receipt = json.loads(process.stdout)
    assert receipt["schema_version"] == "cwp-incremental-read/1"
    assert receipt["run_id"] == "cli-read-1"
    item, = receipt["items"]
    assert item["state"] == "read"
    assert receipt["usage"]["model_requests"] == 0
    assert item["result_ref"]["source_ref"]["content_sha256"] == ref.content_sha256


def test_read_entry_second_call_reuses_and_reports_it(sr_cwp_readable_catalog):
    """Re-running the same request reuses the persisted product."""
    state = sr_cwp_readable_catalog
    ref = state.refs["call-transcript.txt"]
    request = {
        "schema_version": "cwp-incremental-read-request/1",
        "run_id": "cli-read-2", "reading_level": "local",
        "sources": [ref.to_dict()], "limits": None,
    }
    first = _invoke("read-incremental", state, request)
    assert first.returncode == 0, first.stderr
    first_item, = json.loads(first.stdout)["items"]
    assert first_item["reused"] is False

    second = _invoke("read-incremental", state, request)
    assert second.returncode == 0, second.stderr
    second_item, = json.loads(second.stdout)["items"]
    assert second_item["reused"] is True
    assert second_item["result_ref"] == first_item["result_ref"]


def test_summary_level_generates_through_the_configured_batch_and_reuses(
    sr_cwp_readable_catalog, tmp_path_factory, loopback_model_server, monkeypatch,
):
    """A4 summary tier: loopback generation once, then reuse with zero calls."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    state = sr_cwp_readable_catalog
    ref = state.refs["call-transcript.txt"]
    automation_db = state.root / "automation.db"
    work_dir = state.root / "reading-run-work"
    llm_config = state.root / "llm.yaml"
    endpoint = loopback_model_server.endpoint.removesuffix("/chat/completions")
    llm_config.write_text(
        "llm:\n  provider: deepseek\n  model: stub-model\n"
        f"  base_url: {endpoint}\n  max_tokens: 8192\n  temperature: 0.7\n",
        encoding="utf-8",
    )
    batch_config = state.root / "summary-batch.json"
    batch_config.write_text(json.dumps({
        "profile": "P2", "max_seconds": 120, "max_tokens": 200000,
        "max_cost_usd": "2",
        "pricing": {"version": "fixture-price/1",
                    "input_micro_usd_per_million_tokens": 1000000,
                    "output_micro_usd_per_million_tokens": 2000000},
    }), encoding="utf-8")
    request = {
        "schema_version": "cwp-incremental-read-request/1",
        "run_id": "cli-summary-1", "reading_level": "summary",
        "sources": [ref.to_dict()], "limits": None,
    }
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONUTF8="1")
    first = _invoke(
        "read-incremental", state, request,
        extra_args=["--llm-config", str(llm_config),
                    "--allow-local-model-http",
                    "--summary-batch-config", str(batch_config),
                    "--automation-db", str(automation_db),
                    "--work-dir", str(work_dir)],
    )
    assert first.returncode == 0, first.stderr
    first_receipt = json.loads(first.stdout)
    first_item, = first_receipt["items"]
    assert first_item["state"] == "summarized"
    assert first_item["result_ref"]["artifact_role"] == "narrative_bundle"
    assert first_item["reused"] is False
    assert len(loopback_model_server.requests) == 1

    second = _invoke(
        "read-incremental", state, request,
        extra_args=["--llm-config", str(llm_config),
                    "--allow-local-model-http",
                    "--summary-batch-config", str(batch_config),
                    "--automation-db", str(automation_db),
                    "--work-dir", str(work_dir)],
    )
    assert second.returncode == 0, second.stderr
    second_item, = json.loads(second.stdout)["items"]
    assert second_item["state"] == "summarized"
    assert second_item["reused"] is True
    assert second_item["result_ref"] == first_item["result_ref"]
    # The second read is bundle-first: no additional model request.
    assert len(loopback_model_server.requests) == 1
    assert KEY not in first.stdout + first.stderr + second.stdout + second.stderr


def test_cli_rejects_an_unknown_request_schema(sr_cwp_readable_catalog):
    """The public entry refuses anything that is not its wire contract."""
    state = sr_cwp_readable_catalog
    acquisition = _write_acquisition_config(state.root)
    process = _invoke("discover-incremental", state, {"schema_version": "unknown/1"})
    assert process.returncode == 2
    assert "cwp-incremental-error/1" in process.stderr
    assert process.stdout.strip() == ""
    assert acquisition.exists()
