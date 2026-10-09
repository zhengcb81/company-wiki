"""Returned failure paths share the same operation-level DTO as thrown errors."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.adapter_process import AdapterProcessError
from company_wiki.source_catalog.error_taxonomy import structured_error
from company_wiki.source_catalog.source_operation import project_operation_result
from test_close_gap_fc801 import _binding, _request, _txn
from test_single_intent_latest_acquisition import BoundedAdapter, _budget, _service


def _error():
    error = AdapterProcessError("provider failure")
    error.error_code = "provider_failed"
    error.retryable = False
    error.provider_started = True
    error.acquisition_usage_complete = True
    return error


def test_latest_provider_failure_return_retains_machine_cause_and_shared_usage(tmp_path):
    class FailedDiscovery(BoundedAdapter):
        def discover_bounded(self, request, budget):
            budget.record_reported_usage(response_bytes=17, cost_usd="0")
            raise _error()
    txn, service = _service(tmp_path, FailedDiscovery())
    try:
        result = service.ensure(replace(_request(), mode="latest_as_of", fiscal_year=None), budget=_budget())
        value = result.to_dict()
        dto = value["acquisition_failure"]
        assert value["status"] == "gap"
        assert dto["code"] == "provider_failed" and dto["provider_started"] is True
        assert dto["acquisition_usage"]["response_bytes"] == 17 and dto["usage_complete"] is True
        projected = project_operation_result({"source_ensure": value}, operation="ensure", reader=SimpleNamespace())
        assert projected["status"] == "gap" and projected["acquisition_failure"] == dto
    finally:
        txn.catalog.close()


def test_close_gap_return_failure_retains_diagnostic_without_changing_status(tmp_path):
    class FailedFetch(BoundedAdapter):
        def fetch_bounded(self, candidate, stage, budget):
            budget.consume_response_bytes(11)
            raise _error()
    txn = _txn(tmp_path, FailedFetch())
    try:
        result = txn.execute(_binding("0"*64, policy_hash="a"*64), _request(), budget=_budget())
        value = result.to_dict()
        assert value["status"] == "failed" and value["fetch_events"] == 0
        assert value["acquisition_failure"]["acquisition_usage"]["response_bytes"] == 7 + 11
        assert value["acquisition_failure"]["code"] == "provider_failed"
    finally:
        txn.catalog.close()


def test_normal_metadata_gap_and_success_do_not_invent_failure(tmp_path):
    txn, service = _service(tmp_path, BoundedAdapter())
    try:
        req = replace(_request(), mode="latest_as_of", fiscal_year=None, allow_download=False)
        gap = service.ensure(req, budget=_budget()).to_dict()
        assert gap["status"] == "gap" and "acquisition_failure" not in gap
        assert "acquisition_failure" not in gap["acquisition"]
        result = service.ensure(replace(req, allow_download=True), budget=_budget()).to_dict()
        assert result["status"] == "imported" and "acquisition_failure" not in result
    finally:
        txn.catalog.close()


def test_actual_discovery_and_three_fetch_attempts_are_one_operation_total(tmp_path):
    class ThreeFailures(BoundedAdapter):
        def fetch_bounded(self, candidate, stage, budget):
            self.fetch_calls += 1
            budget.record_reported_usage(response_bytes=self.fetch_calls * 5, cost_usd="0.01")
            error = _error()
            error.retryable = True
            raise error
    adapter = ThreeFailures()
    txn, service = _service(tmp_path, adapter)
    b = _budget()
    b.max_cost_usd = Decimal("1")
    try:
        with pytest.raises(AdapterProcessError) as caught:
            service.ensure(replace(_request(), allow_download=True), budget=b)
        dto = structured_error(caught.value)["acquisition_failure"]
        assert adapter.discover_calls == 1 and adapter.fetch_calls == 3
        assert dto["acquisition_usage"] == {"schema_version": "1.0", "response_bytes": 7+5+10+15, "cost_usd": "0.03"}
        assert dto["provider_started"] is True and dto["usage_complete"] is True
        assert not list(txn.coordinator.staging_root.rglob("*.pdf"))
    finally:
        txn.catalog.close()


def test_post_ensure_envelope_failure_retains_already_accounted_provider_usage(tmp_path, monkeypatch):
    import company_wiki.source_catalog.cli as cli
    import company_wiki.source_catalog.resolver as resolver
    from company_wiki.source_catalog.acquisition_failure import attach_acquisition_failure
    txn, service = _service(tmp_path, BoundedAdapter())
    args = cli._parser().parse_args(["ensure", "--entity", "ACME", "--document-kind", "annual_report",
        "--as-of-date", "2026-10-09", "--allow-download", "--max-download-bytes", "5000000",
        "--max-download-seconds", "20", "--max-download-cost-usd", "0"])
    config_path = tmp_path / "acquisition.yaml"
    config_path.write_text("fixture", encoding="utf-8")
    args.acquisition_config = config_path
    monkeypatch.setattr(cli, "load_acquisition_config", lambda *a, **k: SimpleNamespace(
        build_registry=lambda: txn.coordinator.adapters, staging_root=txn.coordinator.staging_root))
    monkeypatch.setattr(resolver, "build_resolution_envelope", lambda *a, **k: (_ for _ in ()).throw(OSError("after import")))
    try:
        with pytest.raises(OSError) as caught:
            cli._run_ensure_command(args, txn.catalog.config, txn.catalog.config.project_root,
                                    lambda: txn.catalog, lambda **k: (replace(_request(), allow_download=True), None))
        attach_acquisition_failure(caught.value, budget=args._acquisition_budget,
                                   code="acquisition_validation_failed")
        dto = structured_error(caught.value)["acquisition_failure"]
        assert dto["provider_started"] is True and dto["usage_complete"] is True
        assert dto["acquisition_usage"]["response_bytes"] == 7+len(b"%PDF-2025")
        assert len(list(txn.catalog.config.roots[0].path.rglob("*.pdf"))) == 1
    finally:
        txn.catalog.close()


def test_actual_writer_failure_has_correct_responsibility_code_and_keeps_usage(tmp_path, monkeypatch):
    txn, service = _service(tmp_path, BoundedAdapter())
    original = OSError("writer operation failed")
    def fail(*a, **k):
        raise original
    monkeypatch.setattr(txn.writer, "import_staged", fail)
    try:
        with pytest.raises(OSError) as caught:
            service.ensure(replace(_request(), allow_download=True), budget=_budget())
        dto = structured_error(caught.value)["acquisition_failure"]
        assert dto["code"] == "canonical_import_failed"
        assert dto["provider_started"] is True and dto["usage_complete"] is True
        assert dto["acquisition_usage"]["response_bytes"] == 7+len(b"%PDF-2025")
        assert not list(txn.coordinator.staging_root.rglob("*.pdf"))
    finally:
        txn.catalog.close()


def test_budget_failure_inside_writer_is_not_relabelled_as_import_defect(tmp_path, monkeypatch):
    from company_wiki.source_catalog.download_budget import AcquisitionBudgetExceeded
    txn, service = _service(tmp_path, BoundedAdapter())
    def budget_stop(*a, **k):
        raise AcquisitionBudgetExceeded("deadline during local import")
    monkeypatch.setattr(txn.writer, "import_staged", budget_stop)
    try:
        with pytest.raises(AcquisitionBudgetExceeded) as caught:
            service.ensure(replace(_request(), allow_download=True), budget=_budget())
        dto = structured_error(caught.value)["acquisition_failure"]
        assert dto["code"] == "acquisition_budget_exceeded"
        assert dto["provider_started"] is True and dto["usage_complete"] is True
        assert dto["acquisition_usage"]["response_bytes"] == 7+len(b"%PDF-2025")
    finally:
        txn.catalog.close()
