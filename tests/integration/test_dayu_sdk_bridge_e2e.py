"""Opt-in real Dayu SDK, synthetic HTTP: discovery -> staging -> CWP -> reuse.

DAYU_SDK_ROOT selects the external read-only checkout/venv. This is an offline
interface test, not evidence of official live availability or a real filing.
All scratch is owned and cleaned; Dayu code and its caches remain unchanged.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from company_wiki.source_catalog.adapter_process import JsonCommandAdapter
from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.resolver import SourceRequest


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


_HOOK = r'''
import httpx, json, os
from pathlib import Path

html = b"""<html><body><ix:nonNumeric name="dei:DocumentFiscalYearFocus">2025</ix:nonNumeric>
<ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">FY</ix:nonNumeric>
<ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-06-30</ix:nonNumeric>
<ix:nonNumeric name="dei:EntityCentralIndexKey">0000000123</ix:nonNumeric>
<p>Fixture business description for an offline SDK contract.</p></body></html>"""
pdf = b'%PDF-1.7\n' + b'offline fixture ' * 200

def provider(request):
    path = request.url.path
    body = b''
    if path.endswith('company_tickers.json'):
        value = {'0': {'ticker':'FIXTURE', 'cik_str':123, 'title':'Fixture US Company'}}
    elif path.endswith('CIK0000000123.json'):
        value = {'cik':123, 'name':'Fixture US Company', 'fiscalYearEnd':'0630',
                 'filings':{'recent':{'form':['10-K'], 'filingDate':['2025-07-31'],
                 'reportDate':['2025-06-30'], 'accessionNumber':['0000000123-25-000001'],
                 'primaryDocument':['fixture.htm']}, 'files':[]}}
    elif path.endswith('activestock_sehk_c.json') and not path.endswith('inactivestock_sehk_c.json'):
        value = {'stockInfo':[{'stockCode':'00700','stockId':'123','stockName':'Fixture HK Company'}]}
    elif path.endswith('inactivestock_sehk_c.json'):
        value = {'stockInfo':[]}
    elif path.endswith('titleSearchServlet.do'):
        value = {'result':json.dumps([{'NEWS_ID':'HK-FIXTURE','TITLE':'2025年年度報告',
                 'FILE_LINK':'/listedco/listconews/sehk/2026/0420/fixture.pdf',
                 'STOCK_CODE':'00700','DATE_TIME':'20/04/2026 17:00','FILE_TYPE':'PDF'}])}
    elif path.endswith('fixture.htm'):
        value = None; body = html
    elif path.endswith('fixture.pdf'):
        value = None; body = pdf if request.method != 'HEAD' else b''
    else:
        raise AssertionError('Unexpected offline provider request path')
    if value is not None:
        body = json.dumps(value,ensure_ascii=False).encode('utf-8')
    with Path(os.environ['CWP_SDK_TEST_CALLS']).open('a',encoding='utf-8') as stream:
        stream.write(json.dumps({'method':request.method,'path':path,'body_bytes':len(body)})+'\n')
    return httpx.Response(200, headers={'content-length':str(len(pdf) if request.method=='HEAD' else len(body)),
                          'content-type':'application/json' if value is not None else 'application/octet-stream'},
                          stream=httpx.ByteStream(body))

# Keep these as classes: unrelated SDK imports subclass HTTPX transports.
# Replacing a class with a lambda breaks their import before any HTTP request.
class FixtureHTTPTransport(httpx.HTTPTransport):
    def __init__(self,*a,**kw): self.mock = httpx.MockTransport(provider)
    def handle_request(self,request): return self.mock.handle_request(request)
    def close(self): self.mock.close()
class FixtureAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    def __init__(self,*a,**kw): self.mock = httpx.MockTransport(provider)
    async def handle_async_request(self,request): return await self.mock.handle_async_request(request)
    async def aclose(self): await self.mock.aclose()
httpx.HTTPTransport = FixtureHTTPTransport
httpx.AsyncHTTPTransport = FixtureAsyncHTTPTransport
'''


def _sdk_snapshot(root):
    return {str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in (root / "dayu").rglob("*") if path.is_file()}


@pytest.mark.parametrize("market,security", [("US", "FIXTURE"), ("HK", "0700.HK")])
def test_actual_sdk_discovery_is_metadata_only_fetch_once_and_external_tree_unchanged(
    tmp_path, monkeypatch, market, security,
):
    configured = os.environ.get("DAYU_SDK_ROOT")
    if not configured:
        pytest.skip("opt-in: set DAYU_SDK_ROOT to the external read-only SDK checkout")
    sdk = Path(configured).resolve(strict=True)
    python = sdk / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    before = _sdk_snapshot(sdk)
    hook = tmp_path / "hook"
    hook.mkdir()
    (hook / "sitecustomize.py").write_text(_HOOK, encoding="utf-8")
    calls = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PYTHONPATH", str(hook) + os.pathsep + str(ROOT / "src"))
    monkeypatch.setenv("CWP_SDK_TEST_CALLS", str(calls))
    monkeypatch.setenv("SEC_USER_AGENT", "offline-fixture SDK contract; no real requests")
    adapter = JsonCommandAdapter(name="sdk-fixture", version="1.0.0",
        command=(str(python), "-B", str(ROOT / "tools/dayu_sdk_bridge.py"),
                 "--market", market, "--adapter-name", "sdk-fixture", "--adapter-version", "1.0.0",
                 "--provider-state-root", str(tmp_path / "provider-state")),
        project_root=sdk, supports_acquisition_budget=True, timeout_seconds=20)
    budget = AcquisitionBudget.from_limits(max_response_bytes=65536, max_seconds=30, max_cost_usd="0")
    request = SourceRequest(entity="Fixture " + market, market=market, security_id=security,
                            document_kind="annual_report", fiscal_year=2025,
                            as_of_date="2026-10-08", allow_download=True)
    candidates = adapter.discover_bounded(request, budget)
    discovered = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
    assert len(candidates) == 1
    assert not any(row["method"] == "GET" and row["path"].endswith((".pdf", ".htm")) for row in discovered)
    receipt = adapter.fetch_bounded(candidates[0], tmp_path / "staging", budget)
    fetched = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
    originals = [row for row in fetched if row["method"] == "GET" and row["path"].endswith((".pdf", ".htm"))]
    assert len(originals) == 1
    assert Path(receipt.staged_path).stat().st_size == receipt.byte_size
    assert budget.response_bytes_used == sum(row["body_bytes"] for row in fetched)
    assert budget.cost_usd_used == 0
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog, SourceResolver
    from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
    project = tmp_path / "wiki"
    companies = project / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(CatalogConfig(project_root=project,
        catalog_dir=project / ".source_catalog", roots=(RootSpec("company_raw", companies,
        "company_raw", read_only=False, reusable_for_filing=True, canonical_write_target="companies"),)))
    try:
        writer = CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging")
        imported = writer.import_staged(request, candidates[0], receipt, budget=budget)
        assert Path(imported.canonical_path).is_file()
        ref = writer.source_ref_for_import(request, candidates[0], receipt.content_sha256)
        assert ref.content_sha256 == receipt.content_sha256
        assert not Path(receipt.staged_path).exists()
        resolved = SourceResolver(catalog).resolve(request)
        assert len(resolved.matches) == 1
        assert resolved.matches[0].source_id == ref.source_id
        assert calls.read_text(encoding="utf-8") == "\n".join(json.dumps(row) for row in fetched) + "\n"
    finally:
        catalog.close()
    assert _sdk_snapshot(sdk) == before
    assert not tuple((tmp_path / "staging").glob("*.part"))
