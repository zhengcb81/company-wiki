"""Neutral RED: request contract validation and service orchestration."""

from __future__ import annotations

import httpx
import pytest

from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.financial_statements import contracts
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


def _request_payload(**overrides) -> dict:
    payload = {
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
    payload.update(overrides)
    return payload


class TestRequestContract:
    def test_valid_request_parses(self):
        request = contracts.StatementsRequest.from_payload(_request_payload())
        assert request.statements == ("income_statement",)
        assert request.intent == "fetch_if_missing"
        assert request.acquisition_limits.max_bytes == 8000000

    def test_reuse_only_needs_no_limits(self):
        payload = _request_payload(
            intent="reuse_only", acquisition_limits=None
        )
        request = contracts.StatementsRequest.from_payload(payload)
        assert request.acquisition_limits is None

    @pytest.mark.parametrize(
        "overrides",
        [
            {"schema_version": "financial-statements-request/2"},
            {"market": "US"},
            {"statements": []},
            {"statements": ["bogus_statement"]},
            {"report_types": ["annual", "bogus"]},
            {"company_query": "  "},
            {"intent": "always_download"},
            {"knowledge_mode": "future"},
            {"as_of_date": "2026-13-99"},
            {"period_end_from": "2026-06-30", "period_end_to": "2016-01-01"},
            {"all_history": True},  # all_history conflicts with period_end_from
            {
                "intent": "refresh",
                "acquisition_limits": None,
            },  # fetching intents require limits
            {
                "acquisition_limits": {
                    "max_bytes": 0,
                    "timeout_seconds": 60,
                    "max_cost_usd": "0.00",
                }
            },
            {
                "acquisition_limits": {
                    "max_bytes": 10,
                    "timeout_seconds": -1,
                    "max_cost_usd": "0.00",
                }
            },
            {
                "acquisition_limits": {
                    "max_bytes": 10,
                    "timeout_seconds": 5,
                    "max_cost_usd": "-1.00",
                }
            },
        ],
    )
    def test_invalid_requests_are_rejected(self, overrides):
        with pytest.raises(contracts.RequestValidationError):
            contracts.StatementsRequest.from_payload(_request_payload(**overrides))

    def test_all_history_without_from_is_valid(self):
        payload = _request_payload(all_history=True)
        payload.pop("period_end_from")
        request = contracts.StatementsRequest.from_payload(payload)
        assert request.all_history is True

    def test_public_echo_contains_no_secrets_or_paths(self):
        request = contracts.StatementsRequest.from_payload(_request_payload())
        echoed = request.to_public_dict()
        assert "acquisition_limits" in echoed
        assert echoed["schema_version"] == contracts.STATEMENTS_REQUEST_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# service orchestration against frozen fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def catalog(tmp_path):
    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(
            RootSpec(
                "company_raw",
                companies,
                "company_raw",
                priority=10,
                adapter_id="company_raw_v1",
            ),
        ),
    )
    made = SourceCatalog(config)
    made.scan()
    store = SecurityMasterStore(config.catalog_dir / "security_master")
    store.write_market(
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
    return made


def _provider(handler):
    def factory(budget):
        return httpx.Client(
            transport=BudgetedHTTPTransport(httpx.MockTransport(handler), budget)
        )

    return SinaStatementsProvider(http_client_factory=factory)


def _recorder(pages: dict[int, bytes]):
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        page = int(request.url.params.get("page", "1"))
        body = pages.get(page)
        if body is None:
            return httpx.Response(
                200, json={"result": {"status": {"code": 0}, "data": None}}
            )
        return httpx.Response(200, content=body)

    handler.requests = requested
    return handler


def _zhongwei_lrb() -> dict[int, bytes]:
    return {
        page: fixtures.fixture_bytes(
            f"sh688012-lrb-type0-page{page}-num10.json.gz"
        )
        for page in range(1, 5)
    }


def _service(catalog, handler) -> FinancialStatementsService:
    return FinancialStatementsService(
        catalog=catalog,
        writer=CanonicalSourceWriter(catalog),
        provider=_provider(handler),
    )


class TestServiceOrchestration:
    def test_fetch_if_missing_then_reuse_without_http(self, catalog):
        handler = _recorder(_zhongwei_lrb())
        service = _service(catalog, handler)
        first = service.handle_request(
            contracts.StatementsRequest.from_payload(_request_payload())
        )
        assert first["schema_version"] == "financial-statements-response/1"
        assert first["status"] == "complete"
        statement = first["statements"][0]
        assert statement["statement_type"] == "income_statement"
        assert statement["status"] == "complete"
        assert statement["provider"] == "sina_finance"
        assert statement["coverage"]["observed_periods"] == 36
        assert statement["coverage"]["first_period_end"] == "2016-12-31"
        assert statement["coverage"]["last_period_end"] == "2026-06-30"
        assert statement["usage"]["http_requests"] == 5
        assert statement["usage"]["cost_usd"] == "0.00"
        # canonical originals committed exactly once per unique page
        originals = list(
            (catalog.config.roots[0].path / "中微公司" / "raw" / "financial_statements").glob("*.json")
        )
        assert len(originals) == 4
        # reports carry verifiable source refs and locators
        report = next(
            r for r in statement["reports"] if r["period_end"] == "2026-06-30"
        )
        assert report["source_ref"]["content_sha256"]
        assert report["source_locator"].startswith("/result/data/report_list/")
        anomaly = next(
            r for r in statement["reports"] if r["period_end"] == "2023-12-31"
        )
        assert anomaly["provider_publish_date"] == "20250418"

        # second identical request: zero HTTP, zero new originals/versions.
        # Provider is force-removed: any fetch attempt makes the run fail.
        file_count_before = len(originals)
        service2 = FinancialStatementsService(
            catalog=catalog,
            writer=CanonicalSourceWriter(catalog),
            provider=None,
        )
        second = service2.handle_request(
            contracts.StatementsRequest.from_payload(_request_payload())
        )
        assert second["status"] == "complete"
        assert second["statements"][0]["usage"]["http_requests"] == 0
        assert second["statements"][0]["coverage"]["observed_periods"] == 36
        originals_after = list(
            (catalog.config.roots[0].path / "中微公司" / "raw" / "financial_statements").glob("*.json")
        )
        assert len(originals_after) == file_count_before
        # identical business versions are reused, not duplicated
        first_ids = {
            r["statement_version_id"] for r in first["statements"][0]["reports"]
        }
        second_ids = {
            r["statement_version_id"] for r in second["statements"][0]["reports"]
        }
        assert first_ids == second_ids

    def test_reuse_only_without_local_data_is_not_found(self, catalog):
        service = FinancialStatementsService(
            catalog=catalog,
            writer=CanonicalSourceWriter(catalog),
            provider=None,
        )
        response = service.handle_request(
            contracts.StatementsRequest.from_payload(
                _request_payload(intent="reuse_only", acquisition_limits=None)
            )
        )
        assert response["status"] == "not_found"
        assert response["statements"][0]["status"] == "not_found"

    def test_unknown_company_is_not_found_with_reason(self, catalog):
        service = FinancialStatementsService(
            catalog=catalog,
            writer=CanonicalSourceWriter(catalog),
            provider=None,
        )
        response = service.handle_request(
            contracts.StatementsRequest.from_payload(
                company_query="完全不存在的公司xyzq"
            )
        )
        assert response["status"] == "not_found"

    def test_partial_when_one_statement_fails(self, catalog):
        def handler(request: httpx.Request) -> httpx.Response:
            source = request.url.params.get("source")
            if source == "fzb":
                return httpx.Response(403, text="forbidden")
            page = int(request.url.params.get("page", "1"))
            body = {
                page: fixtures.fixture_bytes(
                    f"sh688012-{'lrb' if source == 'lrb' else 'llb'}-type0-page{page}-num10.json.gz"
                )
                for page in (1, 2, 3, 4)
            }.get(page)
            if body is None:
                return httpx.Response(
                    200, json={"result": {"status": {"code": 0}, "data": None}}
                )
            return httpx.Response(200, content=body)

        service = _service(catalog, handler)
        payload = _request_payload(
            statements=["income_statement", "balance_sheet", "cash_flow"]
        )
        response = service.handle_request(
            contracts.StatementsRequest.from_payload(payload)
        )
        assert response["status"] == "partial"
        by_type = {s["statement_type"]: s for s in response["statements"]}
        assert by_type["income_statement"]["status"] == "complete"
        assert by_type["balance_sheet"]["status"] == "unavailable"
        assert by_type["balance_sheet"].get("error_code") == "forbidden"
        assert by_type["cash_flow"]["status"] == "complete"

    def test_point_in_time_before_capture_is_refused(self, catalog):
        handler = _recorder(_zhongwei_lrb())
        service = _service(catalog, handler)
        service.handle_request(
            contracts.StatementsRequest.from_payload(_request_payload())
        )
        strict = service.handle_request(
            contracts.StatementsRequest.from_payload(
                knowledge_mode="point_in_time", as_of_date="2024-01-01"
            )
        )
        statement = strict["statements"][0]
        assert statement["point_in_time_quality"] == "historical_asof_unverifiable"
        # data may be described, but must not be claimed as verified PIT
        assert statement["status"] != "complete" or all(
            r.get("pit_verified") is not True for r in statement["reports"]
        )

    def test_period_range_limits_selected_reports(self, catalog):
        handler = _recorder(_zhongwei_lrb())
        service = _service(catalog, handler)
        response = service.handle_request(
            contracts.StatementsRequest.from_payload(
                period_end_from="2025-01-01", period_end_to="2026-06-30"
            )
        )
        periods = [r["period_end"] for r in response["statements"][0]["reports"]]
        assert periods
        assert all("2025-01-01" <= p <= "2026-06-30" for p in periods)
