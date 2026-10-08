"""Actual provider usage survives failure, overshoot and process timeout."""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog.adapter_process import AdapterProcessError, JsonCommandAdapter
from company_wiki.source_catalog.download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
from company_wiki.source_catalog.resolver import SourceRequest


def _budget():
    return AcquisitionBudget.from_limits(
        max_response_bytes=10, max_seconds=30, max_cost_usd="0.01"
    )


def _adapter(tmp_path: Path):
    return JsonCommandAdapter(
        name="recovery", version="1.0.0", command=(sys.executable, "unused.py"),
        project_root=tmp_path, supports_acquisition_budget=True,
    )


def _request():
    return SourceRequest(
        entity="Independent Fixture", market="US", security_id="FIXTURE",
        document_kind="annual_report", fiscal_year=2025,
        as_of_date="2026-10-08", allow_download=True,
    )


def _usage(count=7, cost="0.005"):
    return {"schema_version": "1.0", "response_bytes": count, "cost_usd": cost}


def _progress(version="1.0.0", count=7):
    return json.dumps({
        "schema_version": "1.0", "status": "progress",
        "adapter": {"name": "recovery", "version": version},
        "acquisition_usage": _usage(count),
    }) + "\n"


def test_actual_overage_preserves_both_usage_dimensions_and_stops_new_work():
    budget = _budget()
    with pytest.raises(AcquisitionBudgetExceeded, match="byte budget"):
        budget.record_reported_usage(response_bytes=11, cost_usd="0.02")
    assert budget.response_bytes_used == 11
    assert budget.cost_usd_used == Decimal("0.02")
    assert budget.remaining_response_bytes == 0
    assert budget.remaining_cost_usd == 0
    with pytest.raises(AcquisitionBudgetExceeded):
        budget.ensure_open()


def test_invalid_usage_is_validated_before_either_counter_changes(tmp_path: Path):
    budget = _budget()
    with pytest.raises(AdapterProcessError, match="invalid acquisition cost"):
        _adapter(tmp_path)._charge_bounded_usage(
            {"acquisition_usage": _usage(cost="NaN")}, budget
        )
    assert budget.response_bytes_used == 0
    assert budget.cost_usd_used == 0


def test_adapter_records_cost_even_when_byte_report_exceeds_limit(tmp_path: Path):
    budget = _budget()
    with pytest.raises(AcquisitionBudgetExceeded):
        _adapter(tmp_path)._charge_bounded_usage(
            {"acquisition_usage": _usage(count=11, cost="0.02")}, budget
        )
    assert (budget.response_bytes_used, budget.cost_usd_used) == (11, Decimal("0.02"))


@pytest.mark.parametrize("with_truncated_line", [False, True])
def test_timeout_preserves_last_complete_matching_progress(
    tmp_path: Path, monkeypatch, with_truncated_line: bool,
):
    partial = _progress(count=3) + _progress(count=7)
    if with_truncated_line:
        partial += '{"schema_version":"1.0","status":"progress","adapter":'

    def time_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1, stderr=partial.encode("utf-8"))

    monkeypatch.setattr(subprocess, "run", time_out)
    budget = _budget()
    with pytest.raises(AdapterProcessError) as error:
        _adapter(tmp_path).discover_bounded(_request(), budget)
    assert error.value.error_code == "adapter_timeout"
    assert error.value.acquisition_usage_complete is False
    assert error.value.retryable is False
    assert (budget.response_bytes_used, budget.cost_usd_used) == (7, Decimal("0.005"))
    with pytest.raises(AcquisitionBudgetExceeded, match="usage incomplete"):
        _adapter(tmp_path).discover_bounded(_request(), budget)


@pytest.mark.parametrize("status", ["failed", "progress"])
def test_failure_usage_with_wrong_adapter_version_is_not_trusted(
    tmp_path: Path, monkeypatch, status: str,
):
    if status == "progress":
        detail = _progress(version="OTHER")
    else:
        detail = json.dumps({
            "schema_version": "1.0", "status": "failed",
            "adapter": {"name": "recovery", "version": "OTHER"},
            "error": {"code": "network_failed", "retryable": True,
                      "acquisition_usage": _usage()},
        })

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 1, stdout="", stderr=detail))
    budget = _budget()
    with pytest.raises(AdapterProcessError) as error:
        _adapter(tmp_path).discover_bounded(_request(), budget)
    assert error.value.error_code == "adapter_process_failed"
    assert error.value.adapter_version is None
    assert budget.response_bytes_used == 0


def test_exhausted_bytes_blocks_new_provider_call_but_free_provider_cost_is_valid():
    budget = _budget()
    budget.consume_cost_usd("0.01")
    budget.ensure_open()
    budget.consume_response_bytes(10)
    budget.ensure_open()  # Local receipt validation/import may finish at the cap.
    with pytest.raises(AcquisitionBudgetExceeded, match="byte budget"):
        budget.ensure_new_request()


def test_failed_budget_can_be_restored_without_erasing_actual_overage():
    budget = AcquisitionBudget(
        max_response_bytes=10, deadline_monotonic=_budget().deadline_monotonic,
        max_cost_usd="0.01", response_bytes_used=11, cost_usd_used=Decimal("0.02"),
    )
    assert budget.remaining_response_bytes == 0
    with pytest.raises(AcquisitionBudgetExceeded):
        budget.ensure_open()


def test_real_subprocess_hard_timeout_recovers_checkpoint(tmp_path: Path):
    script = tmp_path / "checkpoint_child.py"
    script.write_text(
        "import sys, time\n"
        + "sys.stderr.write(" + repr(_progress(count=7)) + ")\n"
        + "sys.stderr.write('{\"unfinished\":'); sys.stderr.flush()\n"
        + "time.sleep(30)\n",
        encoding="utf-8",
    )
    adapter = JsonCommandAdapter(
        name="recovery", version="1.0.0", command=(sys.executable, "-B", str(script)),
        project_root=tmp_path, timeout_seconds=2, supports_acquisition_budget=True,
    )
    budget = _budget()
    with pytest.raises(AdapterProcessError) as error:
        adapter.discover_bounded(_request(), budget)
    assert error.value.error_code == "adapter_timeout"
    assert error.value.acquisition_usage_complete is False
    assert (budget.response_bytes_used, budget.cost_usd_used) == (7, Decimal("0.005"))
