"""Local source budgets expose owner measurements without changing decisions."""
from dataclasses import asdict
import json

import pytest

from company_wiki.source_catalog.local_inventory import LocalPrepareLimits, LocalReadBudget
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.source_reader import SourceReadError
from unit.test_local_source_boundaries import cn_lake, cn_request, original_with_text, NAME


def report(budget, reason="budget_exceeded"):
    value = budget.observation(reason=reason)
    assert value["schema_version"] == "local-read-budget/1"
    assert value["operation"] == "local_read_budget"
    assert value["usage_scope"] == "local_original_verification"
    assert value["limits"] == asdict(budget.limits)
    assert isinstance(value["consumed"]["elapsed_seconds"], (int, float))
    assert value["consumed"]["elapsed_seconds"] >= 0
    return value


def test_candidate_exhaustion_reports_the_owner_bound_and_accepted_count():
    budget = LocalReadBudget(LocalPrepareLimits(max_candidates=1))
    assert budget.take_candidate() == ""
    assert budget.take_candidate() == "budget_exceeded"
    value = report(budget)
    assert value["triggered_bound"] == "max_candidates"
    assert value["consumed"]["candidates"] == 1
    assert value["consumed"]["charged_read_bytes"] == 0


def test_read_charge_reports_a_rejected_tail_separately_from_accepted_bytes():
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=3))
    assert budget.charge(2) == ""
    assert budget.charge(2) == "budget_exceeded"
    value = report(budget)
    assert value["triggered_bound"] == "max_bytes"
    assert value["consumed"]["charged_read_bytes"] == 2
    assert value["consumed"]["observed_charge_bytes"] == 4


def test_metadata_preflight_does_not_invent_actual_read_bytes(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_bytes(b'{"x": 1}')
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=1))
    with pytest.raises(SourceReadError, match="budget_exceeded"):
        budget.read_metadata_observation(path, root=tmp_path)
    value = report(budget)
    assert value["triggered_bound"] == "max_bytes"
    assert value["phase"] == "metadata_read"
    assert value["consumed"]["charged_read_bytes"] == 0
    assert value["consumed"]["observed_charge_bytes"] == 0
    assert str(tmp_path) not in json.dumps(value)


@pytest.mark.parametrize("action,limit,reason,counter", [
    ("observe_group", "max_discovery_groups", "local_source_group_limit", "discovery_groups"),
    ("observe_entry", "max_discovery_entries", "local_discovery_entry_limit", "discovery_entries"),
])
def test_discovery_limit_records_the_attempted_entry(action, limit, reason, counter):
    budget = LocalReadBudget(LocalPrepareLimits(**{limit: 1}))
    getattr(budget, action)()
    with pytest.raises(SourceReadError, match=reason):
        getattr(budget, action)()
    value = report(budget, reason)
    assert value["triggered_bound"] == limit
    assert value["consumed"][counter] == 2


def test_deadline_and_cancellation_are_distinct_and_do_not_claim_bytes(monkeypatch):
    from company_wiki.source_catalog import local_inventory
    clock = [100.0]
    monkeypatch.setattr(local_inventory.time, "monotonic", lambda: clock[0])
    budget = LocalReadBudget(LocalPrepareLimits(timeout_seconds=1))
    clock[0] = 102.0
    with pytest.raises(SourceReadError, match="local_prepare_deadline"):
        budget.check()
    value = report(budget, "local_prepare_deadline")
    assert value["triggered_bound"] == "timeout_seconds"
    assert value["consumed"]["elapsed_seconds"] == 2
    other = LocalReadBudget(LocalPrepareLimits())
    other.cancel()
    with pytest.raises(SourceReadError, match="cancelled"):
        other.check()
    assert report(other, "cancelled")["triggered_bound"] == "cancelled"


def test_real_prepare_failure_keeps_originals_and_the_actual_budget_operation(tmp_path):
    catalog, raw = cn_lake(tmp_path)
    try:
        folder = raw / NAME
        folder.mkdir()
        original = original_with_text(NAME + "\n2026年半年度报告\n证券代码：600999")
        path = folder / "2026.pdf"
        path.write_bytes(original.data)
        value = prepare_local_source(catalog, cn_request(), limits=LocalPrepareLimits(max_bytes=1))
        assert value["status"] == "unavailable" and value["reason"] == "budget_exceeded", value
        assert value["blocks_download"] and value["download_events"] == 0
        assert value["source_ref"] is None
        assert set(value) == {"schema_version", "status", "reason", "source_ref", "blocks_download",
                              "operations", "diagnostics", "download_events"}
        rows = [row for row in value["operations"] if row.get("operation") == "local_read_budget"]
        assert len(rows) == 1, value
        snapshot = rows[0]
        assert snapshot["limits"]["max_bytes"] == 1
        assert snapshot["consumed"]["charged_read_bytes"] == 0
        assert snapshot["consumed"]["observed_charge_bytes"] == 0
        assert path.read_bytes() == original.data
        assert str(tmp_path) not in json.dumps(value)
    finally:
        catalog.close()


def test_real_later_budget_failure_keeps_an_earlier_scope_diagnostic(tmp_path):
    from dataclasses import replace
    catalog, raw = cn_lake(tmp_path)
    try:
        folder = raw / NAME
        folder.mkdir()
        older = original_with_text(NAME + "\n2024年半年度报告\n证券代码：600999")
        old_path = folder / "2024.pdf"
        old_path.write_bytes(older.data)
        assert prepare_local_source(catalog, replace(cn_request(), fiscal_year=2024))["status"] == "ready"
        newer = original_with_text(NAME + "\n2026年半年度报告\n证券代码：600999")
        new_path = folder / "2026.pdf"
        new_path.write_bytes(newer.data)
        result = prepare_local_source(catalog, cn_request(), limits=LocalPrepareLimits(max_bytes=1))
        assert result["status"] == "unavailable" and result["reason"] == "budget_exceeded"
        assert any(row["reason"] == "trusted_scope_not_relevant" for row in result["diagnostics"]), result
        assert len([row for row in result["operations"] if row.get("operation") == "local_read_budget"]) == 1
        assert old_path.read_bytes() == older.data and new_path.read_bytes() == newer.data
    finally:
        catalog.close()


def test_orchestration_failure_keeps_completed_owner_operations_and_diagnostics(tmp_path, monkeypatch):
    from company_wiki.source_catalog import local_reconcile
    operation = {"operation": "source_facts_restored", "status": "completed", "source_id": "first-source"}
    diagnostic = {"document_id": "other-document", "reason": "trusted_scope_not_relevant"}

    def bounded_owner(_catalog, _request, **kwargs):
        progress = kwargs["_progress"]
        progress.operations.append(operation)
        progress.diagnostics.append(diagnostic)
        raise SourceReadError("unavailable", "budget_exceeded")

    monkeypatch.setattr(local_reconcile, "_prepare_local_source", bounded_owner)
    catalog, _raw = cn_lake(tmp_path)
    try:
        result = prepare_local_source(catalog, cn_request())
        assert result["operations"][0] == operation
        assert result["diagnostics"] == [diagnostic]
        assert result["reason"] == "budget_exceeded" and result["blocks_download"]
        assert result["operations"][-1]["triggered_bound"] is None
        assert result["operations"][-1]["consumed"]["charged_read_bytes"] == 0
    finally:
        catalog.close()
