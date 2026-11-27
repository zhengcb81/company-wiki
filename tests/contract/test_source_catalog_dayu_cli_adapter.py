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
import subprocess
import sys
import time

args = sys.argv[1:]
if not args or args[0] != "download":
    raise SystemExit(31)

def value(name: str) -> str:
    index = args.index(name)
    return args[index + 1]

base = Path(value("--base"))
ticker = value("--ticker")
fixture = json.loads((Path(value("--config")) / "fake.json").read_text(encoding="utf-8"))
market = fixture["market"]
record = Path(fixture["record"])
if fixture.get("chatter"):
    sys.stdout.buffer.write(b"x" * 524288)
    sys.stdout.buffer.flush()
    sys.stderr.buffer.write(b"y" * 524288 + b"\n")
    sys.stderr.buffer.flush()
if fixture.get("environment"):
    Path(fixture["environment"]).write_text(
        json.dumps({key: key in os.environ for key in ("RESEARCH_FEEDBACK_DIR", "UNRELATED_API_KEY", "SEC_USER_AGENT")}),
        encoding="utf-8",
    )
record.write_text(json.dumps(args, ensure_ascii=False), encoding="utf-8")
if fixture.get("fail"):
    print("Authorization: Bearer p0-secret-synthetic", file=sys.stderr)
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
if fixture.get("pausing_pid"):
    worker = subprocess.Popen(
        [sys.executable, "-B", "-c", "import time; time.sleep(15)"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    Path(fixture["pausing_pid"]).write_text(str(worker.pid), encoding="ascii")
if fixture.get("partial_then_complete"):
    completed_original = source.read_bytes()
    source.write_bytes(completed_original[:8])
    meta["ingest_complete"] = False
(filing / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
if fixture.get("partial_then_complete"):
    time.sleep(1)
    complete = source.with_suffix(".complete")
    complete.write_bytes(completed_original)
    complete.replace(source)
if fixture.get("pausing_pid"):
    time.sleep(15)
print("下载结果\n- status: ok")
'''


def _adapter(tmp_path: Path, *, market: str, timeout: float = 30, **fixture):
    from company_wiki.source_catalog import DayuCliDownloadAdapter

    script = tmp_path / "fake_dayu.py"
    script.write_text(_FAKE_DAYU_CLI, encoding="utf-8")
    config = tmp_path / "dayu-config"
    config.mkdir()
    workspace_parent = tmp_path / "dayu-workspaces"
    record = tmp_path / "invocation.json"
    (config / "fake.json").write_text(json.dumps({"market": market, "record": str(record), **fixture}), encoding="utf-8")
    adapter = DayuCliDownloadAdapter(
        name="dayu-hkex-cli" if market == "HK" else "dayu-sec-cli",
        version="1.0.0",
        market=market,
        command=(sys.executable, str(script)),
        project_root=tmp_path,
        config_root=config,
        workspace_parent=workspace_parent,
        timeout_seconds=timeout,
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

    adapter, record, workspace_parent = _adapter(tmp_path, market=market)
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

    adapter, _record, workspace_parent = _adapter(tmp_path, market="HK", fail=True)
    request = SourceRequest(
        entity="示例公司",
        market="HK",
        security_id="0700",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )

    with pytest.raises(DayuCliAdapterError, match="exited 17") as caught:
        adapter.discover(request)
    assert "p0-secret-synthetic" not in str(caught.value)

    assert list(workspace_parent.glob("dayu-*")) == []


def test_bounded_acquisition_rejects_dayu_before_starting_external_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Dayu's current CLI cannot enforce response-byte budgets, so bounded
    requests must fail before the external process performs network I/O."""
    from decimal import Decimal
    import time

    from company_wiki.source_catalog import (
        AcquisitionBudget,
        AcquisitionCoordinator,
        AcquisitionError,
        AdapterRegistry,
        CatalogConfig,
        RootSpec,
        SourceCatalog,
        SourceRequest,
    )

    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
    )
    catalog.scan()
    adapter, record, _workspace_parent = _adapter(tmp_path, market="HK")
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
        staging_root=tmp_path / "staging",
    )
    request = SourceRequest(
        entity="示例公司",
        market="HK",
        security_id="0700",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )
    budget = AcquisitionBudget(
        max_response_bytes=1024,
        deadline_monotonic=time.monotonic() + 30,
        max_cost_usd=Decimal("0.00"),
    )

    with pytest.raises(AcquisitionError, match="bounded acquisition"):
        coordinator.resolve_or_stage(request, budget=budget)

    assert not record.exists(), "unsupported bounded request must not launch Dayu"
    assert not (tmp_path / "staging").exists()


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


def test_dayu_drains_both_pipes_before_candidate_and_passes_only_supported_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    from company_wiki.source_catalog import SourceRequest

    observed = tmp_path / "child-environment.json"
    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", "do-not-inherit-p0")
    monkeypatch.setenv("UNRELATED_API_KEY", "p0-secret-synthetic")
    monkeypatch.setenv("SEC_USER_AGENT", "P0 acceptance synthetic")
    adapter, _, workspace_parent = _adapter(
        tmp_path, market="HK", timeout=2.5, chatter=True, environment=str(observed),
    )
    request = SourceRequest(
        entity="示例公司", market="HK", security_id="0700", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", allow_download=True,
    )
    try:
        assert len(adapter.discover(request)) == 1
        assert json.loads(observed.read_text(encoding="utf-8")) == {
            "RESEARCH_FEEDBACK_DIR": False, "UNRELATED_API_KEY": False, "SEC_USER_AGENT": True,
        }
    finally:
        adapter.close()
    assert list(workspace_parent.glob("dayu-*")) == []


def test_ready_dayu_original_stops_post_processing_tree_before_deadline(tmp_path: Path):
    import time
    from company_wiki._process_tree import pid_is_alive
    from company_wiki.source_catalog import SourceRequest

    pid_path = tmp_path / "post-processing-pid"
    adapter, _, workspaces = _adapter(
        tmp_path, market="HK", timeout=8, pausing_pid=str(pid_path),
    )
    request = SourceRequest(
        entity="Example", market="HK", security_id="0700", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", allow_download=True,
    )
    started = time.monotonic()
    try:
        candidates = adapter.discover(request)
        assert time.monotonic() - started < adapter.timeout_seconds
        assert len(candidates) == 1
        pid = int(pid_path.read_text(encoding="ascii"))
        end = time.monotonic() + 2
        while pid_is_alive(pid) and time.monotonic() < end:
            time.sleep(0.01)
        assert not pid_is_alive(pid)
        assert adapter.fetch(candidates[0], tmp_path / "staged").mime_type == "application/pdf"
    finally:
        adapter.close()
    assert not list(workspaces.glob("dayu-*"))


def test_early_stop_waits_for_the_declared_original_bytes(tmp_path: Path):
    from company_wiki.source_catalog import SourceRequest

    adapter, _, workspaces = _adapter(
        tmp_path, market="HK", timeout=8, partial_then_complete=True,
        pausing_pid=str(tmp_path / "post-processing-pid"),
    )
    request = SourceRequest(
        entity="Example", market="HK", security_id="0700", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", allow_download=True,
    )
    try:
        candidate, = adapter.discover(request)
        receipt = adapter.fetch(candidate, tmp_path / "staged")
        assert Path(receipt.staged_path).read_bytes() == b"%PDF-1.7\nHK annual report"
    finally:
        adapter.close()
    assert not list(workspaces.glob("dayu-*"))
