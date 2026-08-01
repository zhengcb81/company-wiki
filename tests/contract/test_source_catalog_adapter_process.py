"""Hermetic JSON process bridge contract for external downloader projects."""

from __future__ import annotations

import json
from pathlib import Path
import sys


_FAKE_ADAPTER = r"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("discover", "fetch"))
parser.add_argument("--staging-dir")
args = parser.parse_args()
payload = json.loads(sys.stdin.read())
identity = {"name": "fake-json", "version": "1.0.0"}
if args.action == "discover":
    assert payload["security_id"] == "600000"
    response = {
        "schema_version": "1.0",
        "status": "ok",
        "adapter": identity,
        "candidates": [{
            "candidate_id": "fake:2025",
            "provider": "cninfo",
            "provider_document_id": "2025",
            "market": "CN",
            "entity": payload["security_id"],
            "title": "示例公司2025年年度报告",
            "source_url": "https://example.invalid/report.pdf",
            "document_kind": "annual_report",
            "form_type": "annual_report",
            "filing_date": "2026-03-20",
            "fiscal_year": 2025,
            "fiscal_period": "FY",
            "language": "zh-CN",
            "amended": False,
            "transport_token": "opaque-value"
        }]
    }
else:
    raw = json.loads(payload["adapter_payload_json"])
    assert raw["transport_token"] == "opaque-value"
    path = Path(args.staging_dir) / "report.pdf"
    body = b"%PDF-1.7\njson bridge bytes"
    path.write_bytes(body)
    response = {
        "schema_version": "1.0",
        "status": "ok",
        "adapter": identity,
        "receipt": {
            "candidate_id": payload["candidate_id"],
            "provider": payload["provider"],
            "provider_document_id": payload["provider_document_id"],
            "source_url": payload["source_url"],
            "staged_path": str(path),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "byte_size": len(body),
            "mime_type": "application/pdf",
            "retrieved_at": "2026-07-18T12:00:00Z",
            "http_status": 200,
            "adapter_name": identity["name"],
            "adapter_version": identity["version"],
            "etag": None,
            "last_modified": None
        }
    }
sys.stdout.write(json.dumps(response, ensure_ascii=False))
"""


def test_json_command_adapter_preserves_opaque_candidate_and_stages(tmp_path: Path):
    from company_wiki.source_catalog import JsonCommandAdapter, SourceRequest

    project = tmp_path / "adapter"
    project.mkdir()
    script = project / "fake_adapter.py"
    script.write_text(_FAKE_ADAPTER, encoding="utf-8")
    adapter = JsonCommandAdapter(
        name="fake-json",
        version="1.0.0",
        command=(sys.executable, str(script)),
        project_root=project,
        timeout_seconds=30,
    )
    request = SourceRequest(
        entity="示例公司",
        security_id="600000",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )

    candidates = adapter.discover(request)
    receipt = adapter.fetch(candidates[0], tmp_path / "staging")

    assert len(candidates) == 1
    assert candidates[0].entity == "示例公司"
    raw = json.loads(candidates[0].adapter_payload_json or "{}")
    assert raw["entity"] == "600000"
    assert raw["transport_token"] == "opaque-value"
    assert Path(receipt.staged_path).is_file()
    assert receipt.adapter_name == adapter.name


def test_acquisition_config_builds_market_adapters_and_cli_is_read_only_by_default(
    tmp_path: Path,
):
    from company_wiki.source_catalog import load_acquisition_config
    from company_wiki.source_catalog.cli import _parser

    project = tmp_path / "project"
    project.mkdir()
    for name in ("cn", "hk", "us"):
        (project / name).mkdir()
    config_path = project / "source_acquisition.yaml"
    config_path.write_text(
        """schema_version: \"1.1\"
staging_root: \"${PROJECT_ROOT}/.source_catalog/staging\"
timeout_seconds: 30
adapters:
  cn: {name: cn-adapter, version: 1.0.0, interface: json_command_v1, project_root: \"${PROJECT_ROOT}/cn\", config_root: null, command: [\"${PYTHON_EXECUTABLE}\", \"-m\", \"cn.cli\"]}
  hk: {name: hk-adapter, version: 1.0.0, interface: dayu_cli_v1, project_root: \"${PROJECT_ROOT}/hk\", config_root: \"${PROJECT_ROOT}/hk\", command: [\"${PYTHON_EXECUTABLE}\", \"-m\", \"dayu.cli\"]}
  us: {name: us-adapter, version: 1.0.0, interface: dayu_cli_v1, project_root: \"${PROJECT_ROOT}/us\", config_root: \"${PROJECT_ROOT}/us\", command: [\"${PYTHON_EXECUTABLE}\", \"-m\", \"dayu.cli\"]}
""",
        encoding="utf-8",
    )

    config = load_acquisition_config(config_path, project_root=project)
    registry = config.build_registry()
    args = _parser().parse_args(
        [
            "ensure",
            "--entity",
            "示例公司",
            "--document-kind",
            "annual_report",
            "--as-of-date",
            "2026-07-18",
        ]
    )

    assert registry.cn.name == "cn-adapter"
    assert registry.hk.name == "hk-adapter"
    assert registry.us.name == "us-adapter"
    assert registry.hk.__class__.__name__ == "DayuCliDownloadAdapter"
    assert registry.us.__class__.__name__ == "DayuCliDownloadAdapter"
    assert config.staging_root == project / ".source_catalog" / "staging"
    assert args.allow_download is False


# ---------------------------------------------------------------------------
# CW-2.27D / Phase 3 — AdapterProcessError typed error_code/retryable parsing
# Standardised 1.0 error-JSON shape emitted by adapter CLIs:
#   {"schema_version": "1.0", "status": "failed",
#    "adapter": {"name": ..., "version": ...},
#    "error": {"code": ..., "type": ..., "message": ..., "retryable": bool}}
# Legacy / unknown stderr must degrade safely to ``adapter_process_failed``.
# ---------------------------------------------------------------------------

_FAILED_ADAPTER_PREFIX = r"""
import json, sys
def _emit_error(code, retryable):
    payload = {
        "schema_version": "1.0",
        "status": "failed",
        "adapter": {"name": "stockinfo-cninfo", "version": "1.1.0"},
        "error": {
            "code": code,
            "type": "AdapterError",
            "message": "boom",
            "retryable": retryable,
        },
    }
    sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.exit(1)
_payload = json.loads(sys.stdin.read())
"""


_TYPED_ERROR_ADAPTER = (
    _FAILED_ADAPTER_PREFIX
    + r"""
_emit_error("upstream_unavailable", True)
"""
)


_NONJSON_ERROR_ADAPTER = r"""
import sys, json
sys.stderr.write("Traceback (most recent call last):\n  File ...\nRuntimeError: legacy error\n")
sys.exit(1)
"""


def _write_adapter(project: Path, name: str, source: str) -> Path:
    project.mkdir(parents=True, exist_ok=True)
    script = project / name
    script.write_text(source, encoding="utf-8")
    return script


def test_adapter_process_error_exposes_typed_error_code_and_retryable(tmp_path: Path):
    from company_wiki.source_catalog import JsonCommandAdapter, SourceRequest

    project = tmp_path / "adapter"
    script = _write_adapter(project, "typed_error.py", _TYPED_ERROR_ADAPTER)
    adapter = JsonCommandAdapter(
        name="stockinfo-cninfo",
        version="1.1.0",
        command=(sys.executable, str(script)),
        project_root=project,
        timeout_seconds=30,
    )
    request = SourceRequest(
        entity="示例公司",
        security_id="002594",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2024,
        as_of_date="2026-07-25",
        allow_download=True,
    )
    try:
        adapter.discover(request)
    except Exception as exc:
        captured = exc
    else:
        raise AssertionError("adapter.discover should have raised AdapterProcessError")

    from company_wiki.source_catalog.adapter_process import AdapterProcessError

    assert isinstance(captured, AdapterProcessError)
    assert captured.error_code == "upstream_unavailable"
    assert captured.retryable is True
    assert captured.adapter_version == "1.1.0"


def test_adapter_process_error_degrades_safely_for_legacy_nonjson_stderr(
    tmp_path: Path,
):
    from company_wiki.source_catalog import JsonCommandAdapter, SourceRequest
    from company_wiki.source_catalog.adapter_process import AdapterProcessError

    project = tmp_path / "adapter"
    script = _write_adapter(project, "legacy_error.py", _NONJSON_ERROR_ADAPTER)
    adapter = JsonCommandAdapter(
        name="stockinfo-cninfo",
        version="1.1.0",
        command=(sys.executable, str(script)),
        project_root=project,
        timeout_seconds=30,
    )
    request = SourceRequest(
        entity="示例公司",
        security_id="002594",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2024,
        as_of_date="2026-07-25",
        allow_download=True,
    )

    try:
        adapter.discover(request)
    except AdapterProcessError as exc:
        assert exc.error_code == "adapter_process_failed"
        assert exc.retryable is None
        assert exc.adapter_version is None
    else:
        raise AssertionError("expected AdapterProcessError on legacy stderr")
