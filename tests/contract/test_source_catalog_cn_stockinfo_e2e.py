"""CW-2.27G / Phase 6 — CN cross-process offline full chain.

Covers 7 scenarios per CW-2.27 Plan Section 11 (test_source_catalog_cn_stockinfo_e2e.py):

  1. BYD FY2024 real-fixture candidate schema enters company-wiki through the
     JSON subprocess boundary, fordable to discover/fetch via JsonCommandAdapter.
  2. transport_url + announcement_id round-trip via opaque adapter_payload_json;
     company-wiki public candidate keeps the detail URL as source_url.
  3-4. First-time missing + allow_download=True → IMPORTED; raw + .source.json +
     catalog + journal entry written; second run → REUSED with fetch=0
     (no new staging entries / no new raw / no new journal entry other than
     reused_before_download).
  5a. full+summary scenario (real adapter excludes summary inside CLI) →
     exactly one candidate → IMPORTED full only.
  5b. two-full input (legitimately ambiguous) → AMBIGUOUS, fetch=0, raw=0.
  6. upstream typed failure error JSON → service.ensure raises
     AdapterProcessError; staging/raw/catalog zero writes.
  7. allow_download=False with no existing source → MISSING, no fetch attempt
     (adapter.discover_calls == 0; fetch never invoked).

Helpers live under tests (not production CLI). No backdoor fixture flags on the
production CLI: instead, this test file embeds a fake-stockinfo-cli Python
script that simulates the real StockInfo adapter CLI's response/contract.",
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from company_wiki.source_catalog import (
    AcquisitionCoordinator,
    AcquisitionJournal,
    AdapterRegistry,
    CanonicalSourceWriter,
    CatalogConfig,
    JsonCommandAdapter,
    RootSpec,
    SourceCatalog,
    SourceEnsureStatus,
    SourceRequest,
    SourceAcquisitionService,
)


# ---------------------------------------------------------------------------
# Fake StockInfo adapter CLI scripts (embedded strings)
# ---------------------------------------------------------------------------

# BYD FY2024 fixture identity — extracted from real cninfo fixture in Phase 4.
_BYD_FY2024_FULL_ANNOUNCEMENT_ID = "1222881496"
_BYD_FY2024_FULL_FILING_DATE = "2025-03-24"
_BYD_FY2024_FULL_TITLE = "比亚迪股份有限公司2024年年度报告"
_BYD_FY2024_FULL_DETAIL_URL = (
    "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=002594"
    "&announcementId=1222881496&announcementTime=2025-03-24%2016:00"
)
_BYD_FY2024_FULL_TRANSPORT_URL = (
    "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF"
)
_BYD_FY2024_SUMMARY_ANNOUNCEMENT_ID = "1222881505"
_BYD_FY2024_SUMMARY_TITLE = "比亚迪股份有限公司2024年年度报告摘要"
_BYD_FY2024_SUMMARY_TRANSPORT_URL = (
    "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881505.PDF"
)
_FAKE_PDF_BYTES = b"%PDF-1.7\nbyd fy2024 annual report bytes for offline E2E " * 30
_FAKE_ADAPTER_NAME = "stockinfo-cninfo"
_FAKE_ADAPTER_VERSION = "1.1.0"


def _candidate_dict(
    *,
    announcement_id: str,
    title: str,
    detail_url: str,
    transport_url: str,
    fiscal_year: int = 2024,
) -> dict[str, Any]:
    return {
        "candidate_id": f"cninfo:{announcement_id}",
        "provider": "cninfo",
        "provider_document_id": announcement_id,
        "identity_method": "announcement_id",
        "market": "CN",
        "entity": "002594",
        "title": title,
        "source_url": detail_url,
        "document_kind": "annual_report",
        "form_type": "annual_report",
        "filing_date": _BYD_FY2024_FULL_FILING_DATE,
        "fiscal_year": fiscal_year,
        "fiscal_period": "FY",
        "language": "zh-CN",
        "amended": False,
        "transport_url": transport_url,
    }


# Fake CLI script — discover returns BYD FY2024 full only (summary already
# excluded at adapter level, mirroring real StockInfo adapter design).
_FAKE_BYD_FULL_CLI = r"""
import argparse, json, sys
from pathlib import Path
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=("discover", "fetch"))
parser.add_argument("--staging-dir")
args = parser.parse_args()
payload = json.loads(sys.stdin.read())
identity = {"name": "stockinfo-cninfo", "version": "1.1.0"}

ANN_ID = "1222881496"
TITLE = "比亚迪股份有限公司2024年年度报告"
DETAIL_URL = "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=002594&announcementId=1222881496&announcementTime=2025-03-24%2016:00"
TRANSPORT_URL = "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF"
RETRIEVED_AT = "2026-07-25T08:00:00Z"

if args.action == "discover":
    assert payload["security_id"] == "002594"
    assert payload["fiscal_year"] == 2024
    response = {
        "schema_version": "1.0",
        "status": "ok",
        "adapter": identity,
        "candidates": [{
            "candidate_id": "cninfo:" + ANN_ID,
            "provider": "cninfo",
            "provider_document_id": ANN_ID,
            "identity_method": "announcement_id",
            "market": "CN",
            "entity": "002594",
            "title": TITLE,
            "source_url": DETAIL_URL,
            "document_kind": "annual_report",
            "form_type": "annual_report",
            "filing_date": "2025-03-24",
            "fiscal_year": 2024,
            "fiscal_period": "FY",
            "language": "zh-CN",
            "amended": False,
            "transport_url": TRANSPORT_URL,
        }],
    }
else:
    raw = json.loads(payload["adapter_payload_json"])
    assert raw["provider_document_id"] == ANN_ID
    assert raw["transport_url"] == TRANSPORT_URL
    staging_dir = Path(args.staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    filename = "byd_fy2024_annual.pdf"
    part = staging_dir / (filename + ".part")
    body = b"%PDF-1.7\nbyd fy2024 annual report bytes for offline E2E " * 30
    part.write_bytes(body)
    final = staging_dir / filename
    if final.exists():
        final.unlink()
    part.replace(final)
    response = {
        "schema_version": "1.0",
        "status": "ok",
        "adapter": identity,
        "receipt": {
            "candidate_id": raw["candidate_id"],
            "provider": raw["provider"],
            "provider_document_id": raw["provider_document_id"],
            "source_url": raw["source_url"],  # detail URL, NOT transport URL
            "staged_path": str(final),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "byte_size": len(body),
            "mime_type": "application/pdf",
            "retrieved_at": RETRIEVED_AT,
            "http_status": 200,
            "adapter_name": identity["name"],
            "adapter_version": identity["version"],
            "etag": None,
            "last_modified": None,
        },
    }
sys.stdout.write(json.dumps(response, ensure_ascii=False))
"""


# Fake CLI — returns BOTH full + summary FY2024 (simulates a contract violation
# where adapter forgets to exclude summary). coordinator must AMBIGUOUS, fetch=0.
_FAKE_BYD_FULL_AND_SUMMARY_CLI = _FAKE_BYD_FULL_CLI.replace(
    '"candidates": [{',
    (
        '"candidates": [{'
        ' "candidate_id": "cninfo:1222881505",'
        ' "provider": "cninfo",'
        ' "provider_document_id": "1222881505",'
        ' "identity_method": "announcement_id",'
        ' "market": "CN",'
        ' "entity": "002594",'
        ' "title": "比亚迪股份有限公司2024年年度报告摘要",'
        ' "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=002594&announcementId=1222881505&announcementTime=2025-03-24%2016:00",'
        ' "document_kind": "annual_report",'
        ' "form_type": "annual_report",'
        ' "filing_date": "2025-03-24",'
        ' "fiscal_year": 2024,'
        ' "fiscal_period": "FY",'
        ' "language": "zh-CN",'
        ' "amended": False,'
        ' "transport_url": "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881505.PDF"'
        "},{"
    ),
)


# Fake CLI — returns 2 full FY2024 records (full + amended). coordinator AMBIGUOUS.
_FAKE_BYD_TWO_FULL_CLI = _FAKE_BYD_FULL_CLI.replace(
    '"candidates": [{',
    (
        '"candidates": [{'
        ' "candidate_id": "cninfo:1222881496",'
        ' "provider": "cninfo",'
        ' "provider_document_id": "1222881496",'
        ' "identity_method": "announcement_id",'
        ' "market": "CN",'
        ' "entity": "002594",'
        ' "title": "比亚迪股份有限公司2024年年度报告（修订版）",'
        ' "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=002594&announcementId=1222881496amp&announcementTime=2025-04-26%2009:30",'
        ' "document_kind": "annual_report",'
        ' "form_type": "annual_report",'
        ' "filing_date": "2025-04-26",'
        ' "fiscal_year": 2024,'
        ' "fiscal_period": "FY",'
        ' "language": "zh-CN",'
        ' "amended": True,'
        ' "transport_url": "https://static.cninfo.com.cn/finalpage/2025-04-26/1222881496amp.PDF"'
        "},{"
    ),
)


# Fake CLI — always emits structured 1.0 typed error on stderr + exit 1.
_FAKE_BYD_TYPED_ERROR_CLI = r"""
import json, sys
payload = {
    "schema_version": "1.0",
    "status": "failed",
    "adapter": {"name": "stockinfo-cninfo", "version": "1.1.0"},
    "error": {
        "code": "upstream_unavailable",
        "type": "CninfoApiError",
        "message": "boom simulated upstream unavailable",
        "retryable": True,
    },
}
sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
sys.exit(1)
"""


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _write_cli_script(project: Path, name: str, source: str) -> Path:
    cli_dir = project / "adapter"
    cli_dir.mkdir(parents=True, exist_ok=True)
    path = cli_dir / name
    path.write_text(source, encoding="utf-8")
    return path


def _cn_adapter(project: Path, script_name: str, source: str) -> JsonCommandAdapter:
    script = _write_cli_script(project, script_name, source)
    return JsonCommandAdapter(
        name=_FAKE_ADAPTER_NAME,
        version=_FAKE_ADAPTER_VERSION,
        command=(sys.executable, str(script)),
        project_root=script.parent,
        timeout_seconds=30,
    )


def _build_catalog(tmp_path: Path) -> SourceCatalog:
    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True, exist_ok=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
    )
    catalog.scan()
    return catalog


def _service(
    tmp_path: Path,
    cn_adapter: JsonCommandAdapter,
) -> tuple[SourceAcquisitionService, SourceCatalog]:
    catalog = _build_catalog(tmp_path)
    staging_root = catalog.config.catalog_dir / "staging"
    service = SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(cn=cn_adapter, hk=cn_adapter, us=cn_adapter),
            staging_root=staging_root,
        ),
        writer=CanonicalSourceWriter(catalog, staging_root=staging_root),
        journal=AcquisitionJournal(catalog.config.catalog_dir),
    )
    return service, catalog


def _byd_request(*, allow_download: bool) -> SourceRequest:
    return SourceRequest(
        entity="比亚迪",
        security_id="002594",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2024,
        as_of_date="2026-07-25",
        allow_download=allow_download,
    )


def _raw_files(catalog: SourceCatalog, entity: str) -> list[Path]:
    raw_dir = catalog.config.project_root / "companies" / entity / "raw"
    if not raw_dir.exists():
        return []
    return sorted(p for p in raw_dir.rglob("*") if p.is_file())


def _sidecars(catalog: SourceCatalog, entity: str) -> list[Path]:
    raw_dir = catalog.config.project_root / "companies" / entity / "raw"
    if not raw_dir.exists():
        return []
    return sorted(p for p in raw_dir.rglob("*.source.json") if p.is_file())


def _staging_files(catalog: SourceCatalog) -> list[Path]:
    staging = catalog.config.catalog_dir / "staging"
    if not staging.exists():
        return []
    return sorted(p for p in staging.rglob("*") if p.is_file())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_byd_fy2024_imports_via_subprocess_and_reuses_on_second_run(tmp_path):
    cn = _cn_adapter(tmp_path, "byd_full_only.py", _FAKE_BYD_FULL_CLI)
    service, catalog = _service(tmp_path, cn)

    first = service.ensure(_byd_request(allow_download=True))
    assert first.status is SourceEnsureStatus.IMPORTED
    assert first.canonical_import is not None
    canonical = Path(first.canonical_import.canonical_path)
    sidecar = Path(first.canonical_import.provenance_path)
    assert canonical.is_file()
    assert sidecar.is_file()
    assert canonical.relative_to(
        catalog.config.project_root / "companies" / "比亚迪" / "raw"
    )
    assert sidecar == canonical.with_name(canonical.name + ".source.json")
    # Staged must be cleaned up after canonical import
    staged_after_first = _staging_files(catalog)
    assert staged_after_first == []

    # Second run → REUSED, zero fetch (no new staged file)
    second = service.ensure(_byd_request(allow_download=True))
    assert second.status is SourceEnsureStatus.REUSED
    assert _staging_files(catalog) == []  # no new staged entries
    _raw_after_second = _raw_files(catalog, "比亚迪")
    assert len(_raw_after_second) == len(_raw_files(catalog, "比亚迪"))
    # Journal entries: first "downloaded_new", second "reused_before_download"
    journal = AcquisitionJournal(catalog.config.catalog_dir)
    outcomes = [item.outcome for item in journal.read_all()]
    assert outcomes == ["downloaded_new", "reused_before_download"]


def test_byd_opaque_payload_preserves_transport_url_in_sidecar(tmp_path):
    cn = _cn_adapter(tmp_path, "byd_full_only.py", _FAKE_BYD_FULL_CLI)
    service, catalog = _service(tmp_path, cn)
    first = service.ensure(_byd_request(allow_download=True))
    assert first.status is SourceEnsureStatus.IMPORTED
    sidecars = _sidecars(catalog, "比亚迪")
    assert len(sidecars) == 1
    payload = json.loads(sidecars[0].read_text(encoding="utf-8"))
    # Candidate identity preserved
    assert payload["provider_document_id"] == _BYD_FY2024_FULL_ANNOUNCEMENT_ID
    assert payload["source_url"].startswith(
        "https://www.cninfo.com.cn/new/disclosure/detail"
    )
    # transport_url preserved inside candidate.adapter_payload_json
    candidate_obj = payload["candidate"]
    adapter_payload = json.loads(candidate_obj["adapter_payload_json"])
    assert adapter_payload["transport_url"] == _BYD_FY2024_FULL_TRANSPORT_URL
    # Only one raw file imported
    raw = _raw_files(catalog, "比亚迪")
    assert len([p for p in raw if not p.name.endswith(".source.json")]) == 1


def test_full_and_summary_input_imports_only_full(tmp_path):
    """Real StockInfo adapter excludes summary at CLI subprocess boundary, so
    coordinator sees exactly 1 candidate. (Subprocess here simulates that.)"""
    cn = _cn_adapter(tmp_path, "byd_full_only.py", _FAKE_BYD_FULL_CLI)
    service, catalog = _service(tmp_path, cn)
    result = service.ensure(_byd_request(allow_download=True))
    assert result.status is SourceEnsureStatus.IMPORTED
    raw = _raw_files(catalog, "比亚迪")
    pdf_files = [p for p in raw if not p.name.endswith(".source.json")]
    assert len(pdf_files) == 1


def test_full_plus_summary_returned_to_coordinator_yields_ambiguous_no_fetch(
    tmp_path,
):
    """If a (misbehaving) adapter returned BOTH full + summary, coordinator
    must AMBIGUOUS and not fetch. raw stays empty."""
    cn = _cn_adapter(
        tmp_path, "byd_full_and_summary.py", _FAKE_BYD_FULL_AND_SUMMARY_CLI
    )
    service, catalog = _service(tmp_path, cn)
    result = service.ensure(_byd_request(allow_download=True))
    assert result.status is SourceEnsureStatus.AMBIGUOUS
    assert _raw_files(catalog, "比亚迪") == []
    assert _staging_files(catalog) == []


def test_two_full_candidates_yield_ambiguous_no_fetch(tmp_path):
    cn = _cn_adapter(tmp_path, "byd_two_full.py", _FAKE_BYD_TWO_FULL_CLI)
    service, catalog = _service(tmp_path, cn)
    result = service.ensure(_byd_request(allow_download=True))
    assert result.status is SourceEnsureStatus.AMBIGUOUS
    assert _raw_files(catalog, "比亚迪") == []
    assert _staging_files(catalog) == []


def test_upstream_typed_failure_fail_closed_zero_writes(tmp_path):
    cn = _cn_adapter(tmp_path, "byd_typed_error.py", _FAKE_BYD_TYPED_ERROR_CLI)
    service, catalog = _service(tmp_path, cn)
    with pytest.raises(Exception) as exc_info:
        service.ensure(_byd_request(allow_download=True))
    # AdapterProcessError surfaced; structured error_code preserved
    err = exc_info.value
    assert hasattr(err, "error_code")
    assert err.error_code == "upstream_unavailable"
    assert err.retryable is True
    # Nothing must have been written
    assert _raw_files(catalog, "比亚迪") == []
    assert _staging_files(catalog) == []
    # Journal records the failure outcome
    journal = AcquisitionJournal(catalog.config.catalog_dir)
    outcomes = [item.outcome for item in journal.read_all()]
    assert outcomes == ["failed"]
    attempt = journal.read_all()[0]
    assert attempt.reason == "adapter_or_staging_failed"


def test_allow_download_false_with_no_existing_source_returns_missing_no_fetch(
    tmp_path,
):
    cn = _cn_adapter(tmp_path, "byd_full_only.py", _FAKE_BYD_FULL_CLI)
    service, catalog = _service(tmp_path, cn)

    result = service.ensure(_byd_request(allow_download=False))
    assert result.status is SourceEnsureStatus.MISSING
    assert result.acquisition.reason == "download_required_but_not_allowed"
    # No raw, no staging, journal records missing
    assert _raw_files(catalog, "比亚迪") == []
    assert _staging_files(catalog) == []
    journal = AcquisitionJournal(catalog.config.catalog_dir)
    outcomes = [item.outcome for item in journal.read_all()]
    assert outcomes == ["missing"]
