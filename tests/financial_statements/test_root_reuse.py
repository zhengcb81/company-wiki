"""Integration: an original moved to another configured root stays readable.

The public reference (document_id/source_id/content_sha256) and the published
statement values survive a canonical-root relocation: after the move and a
rescan, the reader resolves the same bytes and the values do not change.
"""

from __future__ import annotations

import json
import shutil

import httpx

from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.financial_statements import contracts
from company_wiki.source_catalog.financial_statements.repository import (
    FinancialStatementRepository,
)
from company_wiki.source_catalog.financial_statements.service import (
    FinancialStatementsService,
)
from company_wiki.source_catalog.financial_statements.sina_provider import (
    SinaStatementsProvider,
)
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityRecord,
)
from company_wiki.source_catalog.service import SourceCatalog

from . import fixtures


def _write_master(config: CatalogConfig) -> None:
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


def _config(project, companies) -> CatalogConfig:
    return CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    )


def _service(catalog, handler) -> FinancialStatementsService:
    def factory(budget):
        return httpx.Client(
            transport=BudgetedHTTPTransport(httpx.MockTransport(handler), budget)
        )

    return FinancialStatementsService(
        catalog=catalog,
        writer=CanonicalSourceWriter(catalog),
        provider=SinaStatementsProvider(http_client_factory=factory),
    )


def _handler():
    def handle(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        body = fixtures.fixture_bytes(
            f"sh688012-lrb-type0-page{page}-num10.json.gz"
        )
        if page > 4:
            body = b'{"result":{"status":{"code":0},"data":null}}'
        return httpx.Response(200, content=body)

    return handle


def _request_payload() -> dict:
    return {
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
            "max_bytes": 8000000, "timeout_seconds": 60, "max_cost_usd": "0.00",
        },
    }


def test_moved_original_resolves_through_same_reference(tmp_path):
    project = tmp_path / "project"
    lake_a = project / "companies"
    lake_a.mkdir(parents=True)
    config = _config(project, lake_a)
    SourceCatalog(config).scan()
    _write_master(config)
    catalog = SourceCatalog(config)

    first = _service(catalog, _handler()).handle_request(
        contracts.StatementsRequest.from_payload(_request_payload())
    )
    assert first["status"] == "complete"
    report = next(
        r for r in first["statements"][0]["reports"] if r["period_end"] == "2026-06-30"
    )
    reference = report["source_ref"]
    value_pointer = report["rows"][0]["json_pointer"]
    version_id = report["statement_version_id"]

    # Relocate the canonical lake to another configured root and rescan.
    lake_b = tmp_path / "relocated-companies"
    shutil.move(str(lake_a), str(lake_b))
    config_b = _config(project, lake_b)
    catalog_b = SourceCatalog(config_b)
    catalog_b.scan()

    from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

    reader = SourceVersionReader(catalog_b)
    ref = SourceRef(
        document_id=reference["document_id"],
        source_id=reference["source_id"],
        content_sha256=reference["content_sha256"],
        byte_size=reference["byte_size"],
        mime_type=reference["mime_type"],
    )
    ref = reader.query_ref(
        ref.document_id, ref.source_id, ref.content_sha256
    )
    assert ref.content_sha256 == reference["content_sha256"]

    # The published values are unchanged by the relocation.
    repository = FinancialStatementRepository(catalog_b.store)
    rows = repository.query_statement_rows(
        security_id="688012", statement_type="income_statement",
        period_end_from="2026-06-30", period_end_to="2026-06-30",
    )
    assert rows["versions"][0]["statement_version_id"] == version_id
    assert rows["versions"][0]["rows"][0]["json_pointer"] == value_pointer

    # And the pointer still resolves inside the relocated original bytes.
    original = json.loads(reader.open_version(ref).data.decode("utf-8"))
    node = original
    for segment in value_pointer.lstrip("/").split("/"):
        segment = int(segment) if isinstance(node, list) else segment
        node = node[segment]
    assert node == "6691287327.670000"
