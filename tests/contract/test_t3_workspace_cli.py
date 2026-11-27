"""Native control and filing commands for the CWP-owned T3 isolation port."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


MODULE = "company_wiki.source_catalog.t3_workspace_cli"
REPO = Path(__file__).resolve().parents[2]
WINDOWLESS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_FAKE_CN = r'''
import argparse, hashlib, json
from pathlib import Path
import sys
parser = argparse.ArgumentParser()
parser.add_argument("action")
parser.add_argument("--staging-dir")
args = parser.parse_args()
request = json.load(sys.stdin)
identity = {"name": "fake-cn", "version": "1.0.0"}
provider_id = "t3-native-fixture-2024"
url = "https://www.cninfo.com.cn/t3-fixture-fy2024.pdf"
response = {"schema_version": "1.0", "status": "ok", "adapter": identity}
body = b"%PDF-1.4\\nOriginal annual capture fixture\\n%%EOF\\n"
response["acquisition_usage"] = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
if args.action == "discover":
    response["candidates"] = [{
        "candidate_id": provider_id, "provider": "cninfo", "provider_document_id": provider_id,
        "market": "CN", "security_id": "300750", "entity": request["entity"],
        "title": "宁德时代2024年年度报告", "source_url": url, "document_kind": "annual_report",
        "form_type": "FY", "filing_date": "2025-03-14", "fiscal_year": 2024,
        "fiscal_period": "FY", "amended": False, "language": "zh",
    }]
else:
    path = Path(args.staging_dir) / "annual.pdf"
    path.write_bytes(body)
    response["acquisition_usage"]["response_bytes"] = len(body)
    response["receipt"] = {
        "candidate_id": provider_id, "provider": "cninfo", "provider_document_id": provider_id,
        "source_url": url, "staged_path": str(path), "content_sha256": hashlib.sha256(body).hexdigest(),
        "byte_size": len(body), "mime_type": "application/pdf", "retrieved_at": "2025-03-15T00:00:00Z",
        "http_status": 200, "adapter_name": "fake-cn", "adapter_version": "1.0.0", "etag": None,
        "last_modified": None,
    }
print(json.dumps(response,ensure_ascii=True))
'''


def _call(command, payload, cwd, env):
    return subprocess.run(
        command, input=json.dumps(payload).encode() if payload is not None else b"",
        cwd=cwd, env=env, capture_output=True, creationflags=WINDOWLESS, timeout=25,
    )


@pytest.fixture
def deployment(tmp_path):
    owner = tmp_path / "deployed"
    identity = owner / "identity"
    identity.mkdir(parents=True)
    metadata = {
        "schema_version": "1.0", "market": "CN", "retrieved_at": "2026-01-01T00:00:00Z",
        "sources": ["https://www.cninfo.com.cn/"], "record_count": 1,
        "records": [{
            "schema_version": "1.0", "market": "CN", "security_id": "300750",
            "canonical_name": "宁德时代", "aliases": ["CATL"], "exchange": "SZSE",
            "source_name": "cninfo", "source_record_id": "fixture-300750", "ticker": "300750",
            "source_url": "https://www.cninfo.com.cn/", "active": True,
            "identifiers": {"org_id": "fixture-cn-300750"},
        }],
    }
    snapshots = identity / "cn.json"
    snapshots.write_text(json.dumps(metadata), encoding="utf-8")
    adapters = {
        market: {
            "name": f"fake-{market}", "version": "1.0.0", "interface": "json_command_v1",
            "project_root": str(owner), "config_root": None, "supports_acquisition_budget": True,
            "command": [sys.executable, "-B", "-c", "raise SystemExit(99)"],
        }
        for market in ("cn", "hk", "us")
    }
    fake = tmp_path / "fixture-provider.py"
    fake.write_text(_FAKE_CN, encoding="utf-8")
    adapters["cn"]["command"] = [sys.executable, "-B", str(fake)]
    for market in ("hk", "us"):
        adapters[market]["interface"] = "dayu_sdk_bounded_v1"
    acquisition = owner / "acquisition.yaml"
    acquisition.write_text(json.dumps({
        "schema_version": "1.1", "staging_root": str(owner / "must-remain-missing"),
        "timeout_seconds": 2, "adapters": adapters,
    }), encoding="utf-8")
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP", "TMPDIR"}
    }
    env.update(PYTHONPATH=str(REPO / "src"), PYTHONUTF8="1",
               USERPROFILE=str(owner), LOCALAPPDATA=str(owner),
               RESEARCH_FEEDBACK_DIR=str(owner / "unexpected-feedback"))
    workspaces = tmp_path / "workspaces"
    initial_bytes = {path: path.read_bytes() for path in (snapshots, acquisition)}
    command = [
        sys.executable, "-B", "-m", MODULE,
        "--workspace-root", str(workspaces), "--owner-root", str(owner),
        "--acquisition-config", str(acquisition), "--identity-cache", str(identity),
    ]
    yield command, owner, workspaces, env
    assert all(path.read_bytes() == data for path, data in initial_bytes.items())
    assert sorted(path.name for path in owner.iterdir()) == ["acquisition.yaml", "identity"]


def _request(operation, **extra):
    return {
        "schema_version": "cwp-t3-workspace-request/1",
        "operation": operation, "run_id": "one-native-run", "case_id": "corrupt_original", **extra,
    }


def test_native_workspace_create_observe_recover_and_close(deployment):
    command, owner, workspaces, env = deployment
    first = _call(command, _request("open"), owner, env)
    assert first.returncode == 0, first.stdout.decode() + first.stderr.decode()
    response = json.loads(first.stdout)
    assert response["schema_version"] == "cwp-t3-workspace/1"
    assert response["status"] == "opened"
    connection = response["connection"]
    workspace = Path(connection["cwd"])
    assert workspace.is_relative_to(workspaces)
    assert set(connection["commands"]) >= {"catalog", "query", "open"}
    workspace_id = response["workspace_id"]

    # A fresh process must recover the exact binding after a lost open reply.
    repeat = _call(command, _request("open"), owner, env)
    assert json.loads(repeat.stdout) == response
    checked = _call(
        command, _request("observe", workspace_id=workspace_id, checkpoint="corrupt"), owner, env,
    )
    assert checked.returncode == 0, checked.stderr.decode()
    receipt = json.loads(checked.stdout)
    assert receipt["facts"] == {
        "corrupt_original_unchanged": True, "downloaded_new": 0, "no_residue": True,
    }

    existing = _call(
        [*connection["commands"]["catalog"], "identify", "--query", "CATL", "--market", "CN"],
        None, workspace, env,
    )
    assert existing.returncode == 0, existing.stderr.decode()
    assert json.loads(existing.stdout)["resolved"]["security_id"] == "300750"
    blocked = _call(
        [*connection["commands"]["catalog"], "identify", "--query", "CATL",
         "--identity-cache-dir", str(owner / "identity")],
        None, workspace, env,
    )
    assert json.loads(blocked.stdout)["error_code"] == "workspace_config_override"
    ensured = _call(
        [*connection["commands"]["catalog"], "ensure", "--company-query", "CATL",
         "--document-kind", "annual_report", "--as-of-date", "2026-07-31",
         "--market", "CN", "--fiscal-year", "2024", "--allow-download",
         "--max-download-bytes", "8192", "--max-download-seconds", "25",
         "--max-download-cost-usd", "0"],
        None, workspace, env,
    )
    assert ensured.returncode != 0
    cause = json.loads(ensured.stderr or ensured.stdout)
    assert cause["acquisition_failure"]["provider_started"] is False
    after = _call(
        command, _request("observe", workspace_id=workspace_id, checkpoint="corrupt"), owner, env,
    )
    assert json.loads(after.stdout)["facts"] == receipt["facts"]
    rejected = _call(command, _request("close", workspace_id=workspace_id, run_id="different"), owner, env)
    assert json.loads(rejected.stdout)["status"] == "failed"
    assert workspace.is_dir()
    for ids in ({}, {"workspace_id": workspace_id}):
        closed = _call(command, _request("close", **ids), owner, env)
        assert json.loads(closed.stdout)["status"] == "closed"
        assert not workspace.exists()
    closed_again = _call(command, _request("open"), owner, env)
    assert json.loads(closed_again.stdout)["error_code"] == "workspace_closed"


def test_native_running_assurance_observes_exact_download_then_reuse(deployment):
    command, owner, _, env = deployment
    ids = {"run_id": "native-annual-run", "case_id": "cn_annual"}
    first = _call(command, _request("open", **ids), owner, env)
    assert first.returncode == 0, first.stdout.decode()
    response = json.loads(first.stdout)
    ids["workspace_id"] = response["workspace_id"]
    connection = response["connection"]
    workspace = Path(connection["cwd"])
    assert not (workspace / ".source_catalog/acquisition_attempts.jsonl").exists()
    ensure = [*connection["commands"]["catalog"], "ensure", "--company-query", "CATL",
              "--document-kind", "annual_report", "--as-of-date", "2026-07-31",
              "--market", "CN", "--fiscal-year", "2024", "--allow-download",
              "--max-download-bytes", "8192", "--max-download-seconds", "25",
              "--max-download-cost-usd", "0"]
    captures = []
    try:
        for checkpoint in ("first", "reused"):
            result = _call(ensure, None, workspace, env)
            assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
            observation = _call(command, _request("observe", checkpoint=checkpoint, **ids), owner, env)
            assert observation.returncode == 0, observation.stdout.decode()
            facts = json.loads(observation.stdout)["facts"]
            assert facts["downloaded_new"] == 1 and facts["no_residue"]
            assert facts["source_id"] and len(facts["sha256"]) == 64
            captures.append(facts)
        initial, reused = captures
        assert initial["provenance_complete"] and reused["reused_before_download"]
        assert (initial["source_id"], initial["sha256"], initial["mtime_ns"]) == (
            reused["source_id"], reused["sha256"], reused["mtime_ns"],
        )
    finally:
        closed = _call(command, _request("close", **ids), owner, env)
        assert json.loads(closed.stdout)["status"] == "closed"
        assert not workspace.exists()
