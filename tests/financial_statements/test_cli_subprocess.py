"""Neutral RED: real CLI subprocess FF→CWP-style flow over frozen fixtures.

The CLI runs as ``python -m company_wiki.source_catalog.financial_statements.cli``
in a real subprocess with a fixture HTTP root: the provider reads frozen real
responses from disk (offline replay of the exact wire bytes), then canonical
storage, two-table publish and public query all execute in-process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityRecord,
)
from company_wiki.source_catalog.service import SourceCatalog

from . import fixtures

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUEST = {
    "schema_version": "financial-statements-request/1",
    "company_query": "中微公司",
    "market": "CN",
    "statements": ["income_statement"],
    "report_types": ["annual", "semi_annual", "q1", "q3"],
    "period_end_from": "2016-01-01",
    "period_end_to": "2026-06-30",
    "knowledge_mode": "current_snapshot",
    "as_of_date": "2026-10-25",
    "intent": "fetch_if_missing",
    "acquisition_limits": {
        "max_bytes": 8000000,
        "timeout_seconds": 60,
        "max_cost_usd": "0.00",
    },
}


@pytest.fixture()
def wiki_root(tmp_path) -> Path:
    project = tmp_path / "wiki"
    companies = project / "companies"
    companies.mkdir(parents=True)
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    )
    SourceCatalog(config).scan()
    SecurityMasterStore(config.catalog_dir / "security_master").write_market(
        "CN",
        (
            SecurityRecord(
                canonical_name="中微公司",
                market="CN",
                exchange="SSE",
                ticker="688012",
                security_id="688012",
                aliases=("中微",),
                active=True,
                source_name="cninfo",
                source_url="https://www.cninfo.com.cn/",
                source_record_id="9900033375",
                identifiers={},
            ),
        ),
        retrieved_at="2026-10-25T00:00:00Z",
        sources=("cninfo",),
    )
    (project / "config").mkdir(exist_ok=True)
    (project / "config" / "source_catalog.yaml").write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: '${PROJECT_ROOT}/.source_catalog'\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    kind: company_raw\n"
        "    path: companies\n",
        encoding="utf-8",
    )
    return project


@pytest.fixture()
def fixture_root(tmp_path) -> Path:
    root = tmp_path / "fixtures"
    root.mkdir()
    entries = []
    for page in range(1, 5):
        name = f"sh688012-lrb-type0-page{page}-num10.json.gz"
        entries.append(
            {
                "url": (
                    "https://quotes.sina.cn/cn/api/openapi.php/"
                    "CompanyFinanceService.getFinanceReport2022"
                    f"?paperCode=sh688012&source=lrb&type=0&page={page}&num=10"
                ),
                "file": name,
            }
        )
    for entry in entries:
        (root / entry["file"]).write_bytes(fixtures.fixture_path(entry["file"]).read_bytes())
    (root / "manifest.json").write_text(
        json.dumps({"fixtures": entries}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return root


def _run(wiki_root: Path, fixture_root: Path, request: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.financial_statements.cli",
            "--wiki-root",
            str(wiki_root),
            "--fixture-root",
            str(fixture_root),
        ],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=120,
    )


def _raw_file_count(wiki_root: Path) -> int:
    lake = wiki_root / "companies" / "中微公司" / "raw" / "financial_statements"
    return len(list(lake.glob("*.json"))) if lake.is_dir() else 0


class TestCliSubprocess:
    def test_full_offline_flow_and_exact_coverage(self, wiki_root, fixture_root):
        proc = _run(wiki_root, fixture_root, REQUEST)
        assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")[-2000:]
        response = json.loads(proc.stdout.decode("utf-8"))
        assert response["schema_version"] == "financial-statements-response/1"
        assert response["status"] == "complete"
        statement = response["statements"][0]
        assert statement["coverage"]["observed_periods"] == 36
        assert statement["coverage"]["pages"] == 4
        assert statement["usage"]["http_requests"] == 5
        assert statement["usage"]["cost_usd"] == "0.00"
        report = next(
            r for r in statement["reports"] if r["period_end"] == "2026-06-30"
        )
        total = next(
            r for r in report["rows"] if r["provider_field"] == "BIZTOTINCO"
        )
        assert total["value_decimal"] == "6691287327.670000"
        assert total["json_pointer"] == (
            "/result/data/report_list/20260630/data/0/item_value"
        )
        assert report["source_ref"]["content_sha256"]
        # public output never leaks physical paths
        assert str(wiki_root) not in proc.stdout.decode("utf-8", errors="replace")
        assert _raw_file_count(wiki_root) == 4

    def test_second_run_zero_http_and_no_new_artifacts(self, wiki_root, fixture_root):
        first = json.loads(_run(wiki_root, fixture_root, REQUEST).stdout.decode("utf-8"))
        before = _raw_file_count(wiki_root)
        manifest = fixture_root / "manifest.json"
        manifest.unlink()  # any later HTTP attempt now fails loudly
        second_proc = _run(wiki_root, fixture_root, REQUEST)
        assert second_proc.returncode == 0
        second = json.loads(second_proc.stdout.decode("utf-8"))
        assert second["statements"][0]["usage"]["http_requests"] == 0
        assert _raw_file_count(wiki_root) == before
        first_ids = {r["statement_version_id"] for r in first["statements"][0]["reports"]}
        second_ids = {r["statement_version_id"] for r in second["statements"][0]["reports"]}
        assert first_ids == second_ids

    def test_bad_request_exits_two_with_error_envelope(self, wiki_root, fixture_root):
        bad = dict(REQUEST, statements=["bogus"])
        proc = _run(wiki_root, fixture_root, bad)
        assert proc.returncode == 2
        payload = json.loads(proc.stdout.decode("utf-8"))
        assert payload["status"] == "request_error"

    def test_identity_failure_is_not_found(self, wiki_root, fixture_root):
        request = dict(REQUEST, company_query="不存在的公司xyzq")
        proc = _run(wiki_root, fixture_root, request)
        assert proc.returncode == 0
        payload = json.loads(proc.stdout.decode("utf-8"))
        assert payload["status"] == "not_found"
