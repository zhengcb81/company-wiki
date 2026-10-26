"""Regressions for the second independent recheck (W19-R10/R11/R12/R13/R14)."""

from __future__ import annotations

import json

import httpx
import pytest

from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.financial_statements import contracts
from company_wiki.source_catalog.financial_statements.service import (
    FinancialStatementsService,
)
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityRecord,
)

from .test_service_contracts import (
    _recorder,
    _request_payload,
    _service,
    _zhongwei_lrb,
)


@pytest.fixture()
def statements_catalog(tmp_path):
    """Fresh catalog + CN security master, same shape as the service tests."""
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.service import SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    )
    SourceCatalog(config).scan()
    from company_wiki.source_catalog.security_identity import SecurityMasterStore

    SecurityMasterStore(config.catalog_dir / "security_master").write_market(
        "CN",
        (
            SecurityRecord(
                canonical_name="中微公司", market="CN", exchange="SSE",
                ticker="688012", security_id="688012", aliases=("中微",),
                active=True, source_name="cninfo",
                source_url="https://www.cninfo.com.cn/",
                source_record_id="9900033375", identifiers={},
            ),
        ),
        retrieved_at="2026-10-25T00:00:00Z",
        sources=("cninfo",),
    )
    yield SourceCatalog(config)

NULL_PAGE_BYTES = b'{"result":{"status":{"code":0},"data":null}}'


class TestFetchEnvelopeDirections:
    """W19-R10: honest refetch for every widened-range variant."""

    def test_t2b_unbounded_from_after_narrow_fetch_refetches(self, statements_catalog):
        narrow = _request_payload(period_end_from="2024-01-01")
        first = _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(narrow)
        )
        assert first["statements"][0]["coverage"]["observed_periods"] == 10
        unbounded = _request_payload()
        unbounded.pop("period_end_from")
        second = _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(unbounded)
        )
        assert second["statements"][0]["usage"]["http_requests"] == 5
        assert second["statements"][0]["coverage"]["observed_periods"] == 36

    def test_t2c_all_history_after_narrow_fetch_refetches(self, statements_catalog):
        _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(
                _request_payload(period_end_from="2024-01-01")
            )
        )
        payload = _request_payload(all_history=True)
        payload.pop("period_end_from")
        second = _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(payload)
        )
        assert second["statements"][0]["usage"]["http_requests"] == 5
        assert second["statements"][0]["coverage"]["observed_periods"] == 36
        third = FinancialStatementsService(
            catalog=statements_catalog, writer=CanonicalSourceWriter(statements_catalog), provider=None,
        ).handle_request(contracts.StatementsRequest.from_payload(payload))
        assert third["statements"][0]["usage"]["http_requests"] == 0
        assert third["statements"][0]["coverage"]["observed_periods"] == 36

    @staticmethod
    def _mutated_handler():
        """Provider page 1 gains an extra newer period (2026-09-30)."""

        pages = _zhongwei_lrb()  # {page_number: bytes}

        def handler(request: httpx.Request) -> httpx.Response:
            page = int(request.url.params.get("page", "1"))
            if page == 1:
                enriched = json.loads(pages[1].decode("utf-8"))
                report_list = enriched["result"]["data"]["report_list"]
                entry = json.loads(
                    json.dumps(report_list["20260630"], ensure_ascii=False)
                )
                report_list["20260930"] = entry
                enriched["result"]["data"]["report_count"] = str(
                    int(enriched["result"]["data"]["report_count"]) + 1
                )
                return httpx.Response(
                    200,
                    content=json.dumps(enriched, ensure_ascii=False).encode("utf-8"),
                )
            if page in pages:
                return httpx.Response(200, content=pages[page])
            return httpx.Response(200, content=NULL_PAGE_BYTES)

        return handler

    def test_t3b_newer_provider_period_after_exhaustion_refetches(self, statements_catalog):
        _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(_request_payload())
        )
        second = _service(statements_catalog, self._mutated_handler()).handle_request(
            contracts.StatementsRequest.from_payload(
                _request_payload(period_end_to="2026-12-31")
            )
        )
        assert second["statements"][0]["usage"]["http_requests"] > 0
        assert second["statements"][0]["coverage"]["last_period_end"] == "2026-09-30"
        assert second["statements"][0]["coverage"]["observed_periods"] == 37

    def test_t3b_repeat_identical_after_mutation_is_zero_http(self, statements_catalog):
        self.test_t3b_newer_provider_period_after_exhaustion_refetches(statements_catalog)
        quiet = FinancialStatementsService(
            catalog=statements_catalog, writer=CanonicalSourceWriter(statements_catalog), provider=None,
        ).handle_request(
            contracts.StatementsRequest.from_payload(
                _request_payload(period_end_to="2026-12-31")
            )
        )
        assert quiet["statements"][0]["usage"]["http_requests"] == 0
        assert quiet["statements"][0]["coverage"]["observed_periods"] == 37


class TestReplayOwnershipAndShape:
    """W19-R11/R13/R14: replay stays inside one security, proper envelope."""

    def _committed_report(self, statements_catalog):
        first = _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(_request_payload())
        )
        return next(
            r for r in first["statements"][0]["reports"]
            if r["period_end"] == "2026-06-30"
        )

    def test_r11_cross_entity_replay_refused(self, statements_catalog):
        # write_market replaces the whole CN snapshot: keep 中微 (needed by
        # the fetch) and add 美的 in one snapshot.
        SecurityMasterStore(
            statements_catalog.config.catalog_dir / "security_master"
        ).write_market(
            "CN",
            (
                SecurityRecord(
                    canonical_name="中微公司", market="CN", exchange="SSE",
                    ticker="688012", security_id="688012", aliases=("中微",),
                    active=True, source_name="cninfo",
                    source_url="https://www.cninfo.com.cn/",
                    source_record_id="9900033375", identifiers={},
                ),
                SecurityRecord(
                    canonical_name="美的集团", market="CN", exchange="SZSE",
                    ticker="000333", security_id="000333", aliases=(),
                    active=True, source_name="cninfo",
                    source_url="https://www.cninfo.com.cn/",
                    source_record_id="m", identifiers={},
                ),
            ),
            retrieved_at="2026-10-25T00:00:00Z",
            sources=("cninfo",),
        )
        report = self._committed_report(statements_catalog)
        service = FinancialStatementsService(
            catalog=statements_catalog, writer=CanonicalSourceWriter(statements_catalog), provider=None,
        )
        with pytest.raises(ValueError, match="different security"):
            service.replay_source(
                request=contracts.StatementsRequest.from_payload(
                    _request_payload(company_query="美的集团")
                ),
                source_id=report["source_ref"]["source_id"],
            )
        # and nothing was published under the wrong security
        rows = statements_catalog.store.fetchall(
            "SELECT security_id FROM financial_statement_values v "
            "JOIN financial_statement_versions ver "
            "ON v.statement_version_id=ver.statement_version_id "
            "WHERE ver.security_id='000333'"
        )
        assert rows == []

    def test_r14_replay_envelope_carries_statements(self, statements_catalog):
        report = self._committed_report(statements_catalog)
        service = FinancialStatementsService(
            catalog=statements_catalog, writer=CanonicalSourceWriter(statements_catalog), provider=None,
        )
        replay = service.replay_source(
            request=contracts.StatementsRequest.from_payload(_request_payload()),
            source_id=report["source_ref"]["source_id"],
        )
        assert replay["status"] == "complete"
        assert replay["company_identity"]["security_id"] == "688012"
        statement = replay["statements"][0]
        assert statement["statement_type"] == "income_statement"
        assert statement["usage"]["http_requests"] == 0
        assert statement["new_version_ids"] == []
        assert len(statement["reused_version_ids"]) == 10

    def test_r13_cli_replay_works_with_reuse_only_intent(self, tmp_path):
        import subprocess
        import sys
        import os
        from pathlib import Path

        from company_wiki.source_catalog.models import CatalogConfig, RootSpec
        from company_wiki.source_catalog.service import SourceCatalog

        repo_root = Path(__file__).resolve().parents[2]
        project = tmp_path / "wiki"
        companies = project / "companies"
        companies.mkdir(parents=True)
        config = CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
        SourceCatalog(config).scan()
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
        SecurityMasterStore(config.catalog_dir / "security_master").write_market(
            "CN",
            (
                SecurityRecord(
                    canonical_name="中微公司", market="CN", exchange="SSE",
                    ticker="688012", security_id="688012", aliases=("中微",),
                    active=True, source_name="cninfo",
                    source_url="https://www.cninfo.com.cn/",
                    source_record_id="9900033375", identifiers={},
                ),
            ),
            retrieved_at="2026-10-25T00:00:00Z",
            sources=("cninfo",),
        )
        # in-process fetch to commit one page
        from company_wiki.source_catalog.financial_statements.service import (
            FinancialStatementsService as Service,
        )
        from company_wiki.source_catalog.financial_statements.sina_provider import (
            SinaStatementsProvider,
        )
        from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport
        from .test_service_contracts import _zhongwei_lrb

        pages = _zhongwei_lrb()

        def factory(budget):
            return httpx.Client(
                transport=BudgetedHTTPTransport(
                    httpx.MockTransport(_recorder(pages)), budget
                )
            )

        cw_catalog = SourceCatalog(config)
        Service(
            catalog=cw_catalog,
            writer=CanonicalSourceWriter(cw_catalog),
            provider=SinaStatementsProvider(http_client_factory=factory),
        ).handle_request(
            contracts.StatementsRequest.from_payload(_request_payload())
        )
        source_id = cw_catalog.store.fetchone(
            "SELECT source_id FROM financial_statement_versions LIMIT 1"
        )["source_id"]

        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get(
            "PYTHONPATH", ""
        )
        env["PYTHONUTF8"] = "1"
        request = _request_payload(intent="reuse_only", acquisition_limits=None)
        proc = subprocess.run(
            [
                sys.executable, "-m",
                "company_wiki.source_catalog.financial_statements.cli",
                "--wiki-root", str(project),
                "--replay-source", source_id,
            ],
            input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(repo_root), env=env, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
        payload = json.loads(proc.stdout.decode("utf-8"))
        assert payload["status"] == "complete"
        assert payload["statements"][0]["statement_type"] == "income_statement"


class TestContinuationContract:
    """W19-R12: continuation semantics."""

    def test_continuation_not_for_reuse_only(self):
        payload = _request_payload(intent="reuse_only", acquisition_limits=None)
        payload["continuation"] = "fsv-abc:5"
        with pytest.raises(contracts.RequestValidationError):
            contracts.StatementsRequest.from_payload(payload)

    def test_manual_continuation_does_not_blank_other_statements(self, statements_catalog):
        # Seed all three statements through the multi-statement fixture chain.
        from . import fixtures as research_fixtures

        def three_table_handler(request: httpx.Request) -> httpx.Response:
            source = request.url.params.get("source")
            page = int(request.url.params.get("page", "1"))
            if page <= 4:
                body = research_fixtures.fixture_bytes(
                    f"sh688012-{source}-type0-page{page}-num10.json.gz"
                )
            else:
                body = NULL_PAGE_BYTES
            return httpx.Response(200, content=body)

        full = _request_payload(
            statements=["income_statement", "balance_sheet", "cash_flow"]
        )
        seeded = _service(statements_catalog, three_table_handler).handle_request(
            contracts.StatementsRequest.from_payload(full)
        )
        by_type_seeded = {s["statement_type"]: s for s in seeded["statements"]}
        assert by_type_seeded["balance_sheet"]["coverage"]["observed_periods"] == 33
        report = next(
            r for r in by_type_seeded["income_statement"]["reports"]
            if r["period_end"] == "2026-06-30"
        )
        token = f"{report['statement_version_id']}:5"
        service = FinancialStatementsService(
            catalog=statements_catalog, writer=CanonicalSourceWriter(statements_catalog), provider=None,
        )
        paged = service.handle_request(
            contracts.StatementsRequest.from_payload(
                _request_payload(
                    statements=["income_statement", "balance_sheet", "cash_flow"],
                    continuation=token,
                )
            )
        )
        by_type = {s["statement_type"]: s for s in paged["statements"]}
        income_rows = by_type["income_statement"]["reports"][0]["rows"]
        assert income_rows and all(row["row_ordinal"] > 5 for row in income_rows)
        # the token's statement pages; the others are served whole, not blanked
        assert len(by_type["balance_sheet"]["reports"]) == 33
        assert len(by_type["cash_flow"]["reports"]) == 36


class TestR15UnboundedToDirection:
    """W19-R15: a request without period_end_to wants the newest data."""

    def test_omitted_to_refetches_newer_provider_period(self, statements_catalog):
        import httpx

        from company_wiki.source_catalog.financial_statements import contracts

        with_to = _request_payload()
        _service(statements_catalog, _recorder(_zhongwei_lrb())).handle_request(
            contracts.StatementsRequest.from_payload(with_to)
        )
        # provider gains 2026-09-30; request omits period_end_to
        mutated = json.loads(_zhongwei_lrb()[1].decode("utf-8"))
        del mutated

        def handler(request: httpx.Request) -> httpx.Response:
            pages = _zhongwei_lrb()
            page = int(request.url.params.get("page", "1"))
            if page == 1:
                enriched = json.loads(pages[1].decode("utf-8"))
                report_list = enriched["result"]["data"]["report_list"]
                entry = json.loads(
                    json.dumps(report_list["20260630"], ensure_ascii=False)
                )
                report_list["20260930"] = entry
                enriched["result"]["data"]["report_count"] = str(
                    int(enriched["result"]["data"]["report_count"]) + 1
                )
                return httpx.Response(
                    200,
                    content=json.dumps(enriched, ensure_ascii=False).encode("utf-8"),
                )
            if page in pages:
                return httpx.Response(200, content=pages[page])
            return httpx.Response(200, content=NULL_PAGE_BYTES)

        no_to = _request_payload()
        no_to.pop("period_end_to")
        second = _service(statements_catalog, handler).handle_request(
            contracts.StatementsRequest.from_payload(no_to)
        )
        assert second["statements"][0]["usage"]["http_requests"] > 0
        assert second["statements"][0]["coverage"]["last_period_end"] == "2026-09-30"
        # repeated identical unbounded-to request: exhausted unbounded envelope
        quiet = FinancialStatementsService(
            catalog=statements_catalog,
            writer=CanonicalSourceWriter(statements_catalog),
            provider=None,
        ).handle_request(contracts.StatementsRequest.from_payload(no_to))
        assert quiet["statements"][0]["usage"]["http_requests"] == 0
        assert quiet["statements"][0]["coverage"]["observed_periods"] == 37
