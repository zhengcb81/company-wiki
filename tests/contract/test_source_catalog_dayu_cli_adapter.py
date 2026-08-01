"""Contracts for calling Dayu's existing CLI without modifying Dayu code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest


_FAKE_DAYU_CLI = r'''
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
if not args or args[0] != "download":
    raise SystemExit(31)

def value(name: str) -> str:
    index = args.index(name)
    return args[index + 1]

base = Path(value("--base"))
ticker = value("--ticker")
market = os.environ["FAKE_DAYU_MARKET"]
record = Path(os.environ["FAKE_DAYU_RECORD"])
record.write_text(json.dumps(args, ensure_ascii=False), encoding="utf-8")
if os.environ.get("FAKE_DAYU_FAIL") == "1":
    (base / "partial").mkdir(parents=True)
    raise SystemExit(17)
filing = base / "portfolio" / ticker / "filings" / ("fil_hk_123" if market == "HK" else "fil_0000123456-26-000007")
filing.mkdir(parents=True)
if market == "HK":
    source = filing / "fil_hk_123.pdf"
    source.write_bytes(b"%PDF-1.7\nHK annual report")
    digest = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
    meta = {
        "document_id": "fil_hk_123",
        "ticker": ticker,
        "form_type": "FY",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "filing_date": "2026-03-28",
        "ingest_complete": True,
        "is_deleted": False,
        "source_provider": "hkexnews",
        "source_id": "12345678",
        "source_url": "https://www1.hkexnews.hk/report.pdf",
        "source_language": "zh",
        "source_title": "2025年度报告",
        "amended": False,
        "files": [{
            "name": source.name,
            "source": "original",
            "size": source.stat().st_size,
            "sha256": digest,
            "content_type": "application/pdf",
        }],
    }
else:
    source = filing / "issuer-20251231.htm"
    source.write_text("<html><body>US annual report</body></html>", encoding="utf-8")
    digest = __import__("hashlib").sha256(source.read_bytes()).hexdigest()
    meta = {
        "document_id": "fil_0000123456-26-000007",
        "accession_number": "0000123456-26-000007",
        "ticker": ticker,
        "company_id": "123456",
        "form_type": "10-K",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "report_date": "2025-12-31",
        "filing_date": "2026-02-20",
        "ingest_complete": True,
        "is_deleted": False,
        "primary_document": source.name,
        "amended": False,
        "files": [{
            "name": source.name,
            "size": source.stat().st_size,
            "sha256": digest,
            "content_type": "text/html",
            "source_url": "https://www.sec.gov/Archives/edgar/data/123456/000012345626000007/issuer-20251231.htm",
        }],
    }
(filing / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
print("下载结果\n- status: ok")
'''


def _adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, market: str):
    from company_wiki.source_catalog import DayuCliDownloadAdapter

    script = tmp_path / "fake_dayu.py"
    script.write_text(_FAKE_DAYU_CLI, encoding="utf-8")
    config = tmp_path / "dayu-config"
    config.mkdir()
    workspace_parent = tmp_path / "dayu-workspaces"
    record = tmp_path / "invocation.json"
    monkeypatch.setenv("FAKE_DAYU_MARKET", market)
    monkeypatch.setenv("FAKE_DAYU_RECORD", str(record))
    adapter = DayuCliDownloadAdapter(
        name="dayu-hkex-cli" if market == "HK" else "dayu-sec-cli",
        version="1.0.0",
        market=market,
        command=(sys.executable, str(script)),
        project_root=tmp_path,
        config_root=config,
        workspace_parent=workspace_parent,
        timeout_seconds=30,
    )
    return adapter, record, workspace_parent


@pytest.mark.parametrize(
    ("market", "security_id", "expected_provider", "expected_form", "mime_type"),
    [
        ("HK", "0700", "hkexnews", "FY", "application/pdf"),
        ("US", "ACME", "sec", "10-K", "text/html"),
    ],
)
def test_dayu_cli_adapter_uses_isolated_workspace_and_stages_primary_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    market: str,
    security_id: str,
    expected_provider: str,
    expected_form: str,
    mime_type: str,
):
    from company_wiki.source_catalog import SourceRequest

    adapter, record, workspace_parent = _adapter(tmp_path, monkeypatch, market=market)
    request = SourceRequest(
        entity="示例公司",
        market=market,
        security_id=security_id,
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )

    candidates = adapter.discover(request)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.provider == expected_provider
    assert candidate.form_type == expected_form
    assert candidate.fiscal_year == 2025
    invocation = json.loads(record.read_text(encoding="utf-8"))
    assert invocation[:3] == ["download", "--ticker", security_id]
    assert invocation[invocation.index("--start") + 1] == "2025-01-01"
    assert invocation[invocation.index("--end") + 1] == "2026-07-18"
    assert "--base" in invocation and "--config" in invocation and "--quiet" in invocation
    assert expected_form in invocation[invocation.index("--forms") + 1 :]

    receipt = adapter.fetch(candidate, tmp_path / "company-wiki-staging")

    staged = Path(receipt.staged_path)
    assert staged.is_file()
    assert receipt.mime_type == mime_type
    assert receipt.content_sha256 == hashlib.sha256(staged.read_bytes()).hexdigest()
    assert list(workspace_parent.glob("dayu-*")) == []


def test_dayu_cli_failure_removes_isolated_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from company_wiki.source_catalog import DayuCliAdapterError, SourceRequest

    adapter, _record, workspace_parent = _adapter(tmp_path, monkeypatch, market="HK")
    monkeypatch.setenv("FAKE_DAYU_FAIL", "1")
    request = SourceRequest(
        entity="示例公司",
        market="HK",
        security_id="0700",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )

    with pytest.raises(DayuCliAdapterError, match="exited 17"):
        adapter.discover(request)

    assert list(workspace_parent.glob("dayu-*")) == []


def test_acquisition_config_builds_dayu_cli_adapters_without_dayu_private_module(
    tmp_path: Path,
):
    from company_wiki.source_catalog import DayuCliDownloadAdapter, load_acquisition_config

    project = tmp_path / "project"
    project.mkdir()
    for name in ("cn", "dayu"):
        (project / name).mkdir()
    (project / "dayu-config").mkdir()
    config_path = project / "source_acquisition.yaml"
    config_path.write_text(
        """schema_version: "1.1"
staging_root: "${PROJECT_ROOT}/.source_catalog/staging"
timeout_seconds: 30
adapters:
  cn:
    name: cn-adapter
    version: 1.0.0
    interface: json_command_v1
    project_root: "${PROJECT_ROOT}/cn"
    config_root: null
    command: ["${PYTHON_EXECUTABLE}", "-m", "cn.cli"]
  hk:
    name: dayu-hkex-cli
    version: 1.0.0
    interface: dayu_cli_v1
    project_root: "${PROJECT_ROOT}/dayu"
    config_root: "${PROJECT_ROOT}/dayu-config"
    command: ["${PYTHON_EXECUTABLE}", "-m", "dayu.cli"]
  us:
    name: dayu-sec-cli
    version: 1.0.0
    interface: dayu_cli_v1
    project_root: "${PROJECT_ROOT}/dayu"
    config_root: "${PROJECT_ROOT}/dayu-config"
    command: ["${PYTHON_EXECUTABLE}", "-m", "dayu.cli"]
""",
        encoding="utf-8",
    )

    config = load_acquisition_config(config_path, project_root=project)
    registry = config.build_registry()

    assert isinstance(registry.hk, DayuCliDownloadAdapter)
    assert isinstance(registry.us, DayuCliDownloadAdapter)
    assert "company_wiki_adapter" not in " ".join(config.hk.command)
    assert "company_wiki_adapter" not in " ".join(config.us.command)
