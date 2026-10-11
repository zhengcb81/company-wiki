"""Own-line, guarded author worktree setup; no provider/network/config writes."""
from pathlib import Path
import json

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
assert TREE.resolve().name == 'cwp-acquisition-scope-root'
PLAN = TREE / '.planning/w06-cross-period-acquisition'
design = '''
## 作者实施细则（2026-10-11；隔离 TREE；实现前决定）

1. 新 canonical_scope.py 是本来源层事实/相关性边界：SourceScope、ScopeRelation（MATCH/NOT_RELEVANT/UNKNOWN）、qualified_source_scope、scope_relatedness；合法 steady source-facts 绑定 document/source/SHA，正常 canonical provider 入库与原文 DEI 的 evidence locator 分开。仅 scan acquisition JSON 永不资格升级。
2. writer 验过 request/candidate/receipt/实际字节后，在现有有限单组 registration 的 coalesced 事务内通过内部 on_registered 回调写既有 source-facts projection；同连接构建，提交后才 query_ref。_prepare_source_fact_write 增同连接读 port。provider 声明不得覆盖现有相反事实；重入/物理去重不重复原件或改首份 sidecar。无新表、schema、许可、手填 assertion。
3. 历史成功 acquisition journal 仅资格升级 request_id 哈希绑定的显式 scope；重算 attempt_id/request_id，版本 SHA/provider/accession/URL/candidate ID 一致。一个 local 操作最多读一次有界 journal，不升级旧 journal 未绑定的 publication/title/candidate period。无可靠旧记录为 UNKNOWN。旧 path 不是可信条件，根迁移仍按版本定位。
4. local_reconcile 在源责任层判断 relevance 后，可信非目标不调用字节/事实恢复、不重查 identity master、不恢复 retired。目标继续完整 SHA/MIME/as-of/status 和 SEC 实际 DEI。UNKNOWN 不视为可下载的空湖；给具体诊断。已有正常 source-facts 的非 SEC 目标身份按已验事实使用，不读另一身份库。
5. AcquisitionResult.local_preparation 为有限 pathless 诊断（status/reason/blocks_download/具名原因）；操作 DTO 同步可选字段。缺期 not_found 与本地 blocked/unavailable 区分；预算的 provider_started=false 沿既有 observation 保持，不推断已调用。
6. TDD A 文件 tests/contract/test_canonical_acquisition_scope.py：public service cold→same期reuse0→跨年度三市场、同年Q2→Q3、半年度旧2024→2025，各真实小 PDF/独立湖；旧原件 SHA 保持、新期再次reuse0。先跑前五行为 RED（不是缺模块假 RED）。然后加 scope unit 与 scan 假来源、历史 request 改写、目标篡改、未知 publication、retired、原子失败与 dedup 冲突控制。
7. B 一次集中执行本新增+canonical writer+local relevance/discovery+operation v2+scope responsibility+latest acquisition+acquisition usage 相关测试与 lint；发现具体失败才补范围，不跑3314或41matrix/LLM。C 留 ROOT 原41矩阵、FF消费接口与非作者最终验收。

环境：最小子进程 env，假 HOME/TEMP，dotenv disabled，pytest 网络 guard；unique 短 scratch 全合成并结束恢复不存在。已发现默认 sandbox 外部 git status 异常，escalated 同命令正常；一次测试路径不存在已更正，是探索输入错误不是代码缺陷。原件、配置、密钥、母 PWF、FF/ET/Dayu/IQS/Port工具均不写。

Next Step：运行 public writer 行为 RED 并封存，然后按本决定实现。无 commit/install/merge/push；最终 freeze SHA+handoff 后 STOP ROOT。
'''
with (PLAN / 'task_plan.md').open('a', encoding='utf-8') as f: f.write(design)
with (PLAN / 'findings.md').open('a', encoding='utf-8') as f: f.write('\n## 来源事实资格设计\n独立 scope_origin_design 已只读确认：scan acquisition/r4_provenance 无 writer origin；journal 只绑定 request scope，不绑定完整 candidate/sidecar。采用已有 source-facts 表和同事务内部 hook，事实证据明确 provider import vs primary-DEI；禁止以缺 correction assertion 判无正常来源事实。\n')
with (PLAN / 'progress.md').open('a', encoding='utf-8') as f: f.write('\n## 作者线启动\n已读三份 PWF，确定函数边界、事务、历史迁移、DTO 诊断和 TDD；无产品修改、真实调用或费用。A 行为 RED 待执行。\n')

test = '''"""Public canonical intake must not turn a trusted old period into a new-period veto."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import fitz
import pytest

from company_wiki.source_catalog.acquisition import (
    AcquisitionCoordinator, AdapterRegistry, DownloadCandidate, DownloadReceipt,
)
from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_operation import project_operation_result
from company_wiki.source_catalog.source_reader import SourceVersionReader


def pdf_bytes(label):
    with fitz.open() as pdf:
        pdf.new_page().insert_text((30, 40), label)
        return pdf.tobytes(no_new_id=True)


class PeriodAdapter:
    name = "scope-fixture"
    version = "1.0.0"

    def __init__(self):
        self.discoveries = self.fetches = 0

    def discover(self, request):
        self.discoveries += 1
        year = request.fiscal_year
        period = request.fiscal_period
        return (DownloadCandidate(
            candidate_id=f"c-{year}-{period}", provider="fixture",
            provider_document_id=f"{request.market}-{year}-{period}",
            market=request.market, entity=request.entity,
            title=f"{request.entity} {year} {period} business report",
            source_url=f"https://example.test/{request.market}/{year}/{period}.pdf",
            document_kind=request.document_kind, fiscal_year=year,
            fiscal_period=period, form_type=request.document_kind,
            filing_date=f"{year + 1}-03-01", language="en",
        ),)

    def fetch(self, candidate, staging_dir):
        self.fetches += 1
        staging_dir.mkdir(parents=True, exist_ok=True)
        staged = staging_dir / "original.pdf"
        data = pdf_bytes(f"{candidate.entity} {candidate.market} {candidate.fiscal_year} {candidate.fiscal_period}")
        staged.write_bytes(data)
        return DownloadReceipt(
            candidate_id=candidate.candidate_id, provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url, staged_path=str(staged),
            content_sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data),
            mime_type="application/pdf", retrieved_at="2026-01-01T00:00:00Z",
            http_status=200, adapter_name=self.name, adapter_version=self.version,
        )


@pytest.fixture
def lake(tmp_path):
    companies = tmp_path / "companies"
    companies.mkdir()
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", adapter_id="company_raw_v1"),),
    ))
    catalog.scan()
    try:
        yield catalog
    finally:
        catalog.close()


def request(market="CN", year=2024, period="FY", kind="annual_report"):
    return SourceRequest(entity="Acme", document_kind=kind, as_of_date="2026-12-31",
        market=market, security_id={"CN": "600000", "HK": "09999", "US": "ACME"}[market],
        fiscal_year=year, fiscal_period=period, allow_download=True)


def service(catalog, adapter):
    return SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(catalog,
            adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
            staging_root=catalog.config.project_root / "staging"),
        writer=CanonicalSourceWriter(catalog), journal=AcquisitionJournal(catalog.config.catalog_dir),
    )


def ensure(svc, req):
    return svc.ensure(req, budget=AcquisitionBudget.from_limits(
        max_response_bytes=200000, max_seconds=10, max_cost_usd="0"))


@pytest.mark.parametrize("market", ["CN", "HK", "US"])
def test_public_writer_old_annual_does_not_block_next_year(lake, market):
    adapter = PeriodAdapter()
    svc = service(lake, adapter)
    old = ensure(svc, request(market))
    assert old.status.value == "imported"
    old_ref = old.canonical_import.source_ref
    old_sha = hashlib.sha256(Path(old.canonical_import.canonical_path).read_bytes()).hexdigest()
    assert ensure(svc, request(market)).status.value == "reused"
    assert (adapter.discoveries, adapter.fetches) == (1, 1)
    newer = ensure(svc, request(market, 2025))
    assert newer.status.value == "imported", newer.to_dict()
    assert (adapter.discoveries, adapter.fetches) == (2, 2)
    assert newer.canonical_import.source_ref.content_sha256 != old_sha
    assert ensure(svc, request(market, 2025)).status.value == "reused"
    assert (adapter.discoveries, adapter.fetches) == (2, 2)
    checked = SourceVersionReader(lake).open_verified(old_ref, purpose="source_export")
    assert hashlib.sha256(checked).hexdigest() == old_sha


@pytest.mark.parametrize("kind,old_period,new_period,new_year", [
    ("quarterly_report", "Q2", "Q3", 2024),
    ("semi_annual_report", "H1", "H1", 2025),
])
def test_public_writer_nonannual_cross_period(lake, kind, old_period, new_period, new_year):
    adapter = PeriodAdapter()
    svc = service(lake, adapter)
    assert ensure(svc, request("HK", 2024, old_period, kind)).status.value == "imported"
    new = ensure(svc, request("HK", new_year, new_period, kind))
    assert new.status.value == "imported", new.to_dict()
    assert adapter.fetches == 2


def test_scan_shape_alone_cannot_claim_canonical_scope(lake):
    req = request()
    adapter = PeriodAdapter()
    candidate = adapter.discover(req)[0]
    staged = adapter.fetch(candidate, lake.config.project_root / "staging")
    destination = lake.config.roots[0].path / "Acme" / "old.pdf"
    destination.parent.mkdir()
    destination.write_bytes(Path(staged.staged_path).read_bytes())
    sidecar = dict(candidate.to_dict(), company_name=req.entity, security_id=req.security_id,
        content_sha256=staged.content_sha256, byte_size=staged.byte_size, mime_type=staged.mime_type,
        request=req.to_dict(), candidate=candidate.to_dict(), receipt=staged.to_dict(),
        request_id=req.request_id, capture_ready=True, created_by="canonical-writer")
    destination.with_name(destination.name + ".source.json").write_text(json.dumps(sidecar), encoding="utf-8")
    lake.scan()
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    result = prepare_local_source(lake, request(year=2025))
    assert result["blocks_download"] is True
    assert result["status"] in {"blocked", "unavailable"}


def test_local_unknown_diagnostic_survives_pathless_projection(lake):
    source = lake.config.roots[0].path / "Acme" / "2024_annual_report.pdf"
    source.parent.mkdir()
    source.write_bytes(pdf_bytes("Acme 2024 report"))
    lake.scan()
    adapter = PeriodAdapter()
    result = ensure(service(lake, adapter), request(year=2025))
    assert adapter.fetches == 0
    dto = project_operation_result(result.to_dict(), operation="ensure", catalog=lake)
    assert dto["status"] in {"blocked", "unavailable"}
    assert dto["local_preparation"]["blocks_download"] is True
    assert dto["local_preparation"]["reason"] == "verified_issuer_unavailable"
    assert dto["acquisition_observation"]["provider_started"] is False
'''
target = TREE / 'tests/contract/test_canonical_acquisition_scope.py'
assert not target.exists()
target.write_text(test, encoding='utf-8')
print(json.dumps({'plan_updated':3,'test':str(target),'production_changed':False}))
