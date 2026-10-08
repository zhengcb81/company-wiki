"""Provider proof and operation accounting at the CWP public failure boundary."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.adapter_process import AdapterProcessError, JsonCommandAdapter
from company_wiki.source_catalog.download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
from company_wiki.source_catalog.error_taxonomy import structured_error
from company_wiki.source_catalog.resolver import SourceRequest


def budget(cap=100):
    return AcquisitionBudget.from_limits(max_response_bytes=cap, max_seconds=20, max_cost_usd="1")


def usage(count=7, cost="0.01"):
    return {"schema_version": "1.0", "response_bytes": count, "cost_usd": cost}


def request():
    return SourceRequest(entity="Fixture", market="US", security_id="FIXTURE", document_kind="annual_report",
                         fiscal_year=2025, as_of_date="2026-10-09", allow_download=True)


def adapter(tmp_path):
    return JsonCommandAdapter(name="proof", version="1.0.0", command=(sys.executable, "unused.py"),
                              project_root=tmp_path, supports_acquisition_budget=True)


def final(code="upstream_unavailable", count=7, identity=None, cost="0.01"):
    return json.dumps({"schema_version": "1.0", "status": "failed",
                       "adapter": identity or {"name": "proof", "version": "1.0.0"},
                       "error": {"code": code, "retryable": True, "message": "secret-key /private/path?token=bad",
                                 "acquisition_usage": usage(count, cost)}})


def checkpoint(count=7, cost="0.01", identity=None):
    return json.dumps({"schema_version": "1.0", "status": "progress",
                       "adapter": identity or {"name": "proof", "version": "1.0.0"},
                       "acquisition_usage": usage(count, cost)}) + "\n"


def publish(exc, shared_budget):
    from company_wiki.source_catalog.acquisition_failure import attach_acquisition_failure
    attach_acquisition_failure(exc, budget=shared_budget)
    return structured_error(exc)["acquisition_failure"]


def test_legacy_generic_failure_remains_exactly_four_fields():
    assert structured_error(sqlite3.OperationalError("database is locked")) == {
        "status": "failed", "error_type": "catalog_busy", "error": "database is locked", "retryable": True}
    # Invocation metadata alone is not proof of operation accounting.
    error = AdapterProcessError("failed")
    error.error_code = "provider_failed"
    error.acquisition_usage = usage()
    assert set(structured_error(error)) == {"status", "error_type", "error", "retryable"}


def test_valid_final_failure_publishes_safe_machine_proof_and_operation_total(tmp_path, monkeypatch):
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", final()))
    b = budget()
    b.record_reported_usage(response_bytes=13, cost_usd="0.02")
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto == {"schema_version": "acquisition-failure/1", "code": "upstream_unavailable", "retryable": True,
                   "provider_started": True, "usage_complete": True, "usage_scope": "operation",
                   "acquisition_usage": usage(20, "0.03")}
    assert "secret" not in json.dumps(dto)


@pytest.mark.parametrize("code", ["evil-secret?token=raw", {"evil": "raw"}, ["evil"]])
def test_unknown_adapter_code_never_leaks_body(tmp_path, monkeypatch, code):
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", final(code=code)))
    b = budget()
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["code"] == "adapter_process_failed"
    assert dto["provider_started"] is True
    assert "evil" not in json.dumps(dto) and "raw" not in json.dumps(dto)


@pytest.mark.parametrize("kind", ["timeout", "output"])
def test_multiple_checkpoints_are_one_invocation_lower_bound(tmp_path, monkeypatch, kind):
    from company_wiki._bounded_process import OutputLimitExceeded
    detail = checkpoint(3) + checkpoint(7) + checkpoint(8, cost="NaN") + '{"unfinished":'
    def fail(*a, **k):
        if kind == "timeout":
            raise subprocess.TimeoutExpired(a[0], 1, stderr=detail)
        error = OutputLimitExceeded("safe output cap")
        error.stderr = detail
        raise error
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process", fail)
    b = budget()
    b.record_reported_usage(response_bytes=13, cost_usd="0.02")
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["code"] == ("adapter_timeout" if kind == "timeout" else "adapter_output_limit")
    assert dto["provider_started"] is True and dto["usage_complete"] is False
    assert dto["acquisition_usage"] == usage(20, "0.03")
    assert b.usage_complete is False and caught.value.retryable is False


@pytest.mark.parametrize("kind,complete", [("timeout", False), ("oserror", None)])
def test_no_target_execution_evidence_stays_unknown_not_zero(tmp_path, monkeypatch, kind, complete):
    def fail(*a, **k):
        if kind == "timeout":
            raise subprocess.TimeoutExpired(a[0], 1, stderr="")
        raise OSError("may be cleanup after target execution")
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process", fail)
    b = budget()
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["provider_started"] is None and dto["usage_complete"] is complete
    assert dto["acquisition_usage"] is None
    assert caught.value.retryable is False and b.usage_complete is False


@pytest.mark.parametrize("status", ["failed", "progress"])
def test_wrong_target_identity_and_version_never_prove_execution(tmp_path, monkeypatch, status):
    identity = {"name": "proof", "version": "OTHER"}
    detail = final(identity=identity) if status == "failed" else checkpoint(identity=identity)
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", detail))
    b = budget()
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["provider_started"] is None and dto["acquisition_usage"] is None
    assert dto["usage_complete"] is None


@pytest.mark.parametrize("invalid", [True, -1, 1.25])
def test_bad_usage_does_not_publish_false_complete_zero(tmp_path, monkeypatch, invalid):
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", final(count=invalid)))
    b = budget()
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["provider_started"] is True
    assert dto["usage_complete"] is None and dto["acquisition_usage"] is None
    assert b.response_bytes_used == 0 and b.usage_complete is False
    assert dto["retryable"] is True  # Adapter fact; unknown charge still blocks automatic retry.


def test_budget_overage_keeps_real_both_dimensions(tmp_path, monkeypatch):
    response = {"schema_version": "1.0", "status": "ok", "adapter": {"name": "proof", "version": "1.0.0"},
                "acquisition_usage": usage(101, "2"), "candidates": []}
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, json.dumps(response), ""))
    b = budget()
    with pytest.raises(AcquisitionBudgetExceeded) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["code"] == "acquisition_budget_exceeded"
    assert dto["provider_started"] is True and dto["usage_complete"] is True
    assert dto["acquisition_usage"] == usage(101, "2")


def test_local_pre_target_failure_is_proven_zero_but_never_erases_prior_execution(tmp_path):
    b = budget()
    b.deadline_monotonic = 1
    with pytest.raises(AcquisitionBudgetExceeded) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["provider_started"] is False and dto["usage_complete"] is True
    assert dto["acquisition_usage"] == usage(0, "0")
    b.record_reported_usage(response_bytes=5, cost_usd="0.01")
    dto = publish(caught.value, b)
    assert dto["provider_started"] is True and dto["acquisition_usage"] == usage(5, "0.01")


def test_real_pre_target_barrier_failure_proves_false(tmp_path, monkeypatch):
    from company_wiki._bounded_process import TransportError
    def fail(*a, **k):
        error = TransportError("barrier rejected before release")
        error.provider_started = False
        raise error
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process", fail)
    b = budget()
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["provider_started"] is False and dto["usage_complete"] is True
    assert dto["acquisition_usage"] == usage(0, "0")


def test_shared_budget_aggregates_discovery_and_multiple_fetch_failures(tmp_path, monkeypatch):
    details = iter([final(count=5, cost="0.01"), final(count=9, cost="0.02"), final(count=11, cost="0.03")])
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", next(details)))
    b = budget()
    for _ in range(3):
        with pytest.raises(AdapterProcessError) as caught:
            adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["acquisition_usage"] == usage(25, "0.06")
    assert dto["usage_complete"] is True and b.usage_complete is True


def test_after_provider_failure_journal_error_does_not_replace_original(tmp_path):
    from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
    original = AdapterProcessError("original provider failure")
    original.error_code = "provider_failed"
    original.provider_started = True
    original.acquisition_usage_complete = True
    b = budget()
    b.record_reported_usage(response_bytes=7, cost_usd="0.01")
    def fail(*a, **k):
        raise original
    def journal_fail(**kwargs):
        raise OSError("secondary journal fault")
    service = object.__new__(SourceAcquisitionService)
    service.coordinator = SimpleNamespace(select=fail)
    service.journal = SimpleNamespace(record=journal_fail)
    with pytest.raises(AdapterProcessError) as caught:
        service.ensure(request(), budget=b)
    assert caught.value is original
    assert structured_error(caught.value)["acquisition_failure"]["acquisition_usage"] == usage()
    assert any("journal" in note for note in getattr(original, "__notes__", []))


def test_after_provider_success_completion_error_retains_operation_accounting(tmp_path, monkeypatch):
    from company_wiki.source_catalog.acquisition import AcquisitionStatus
    from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
    b = budget()
    b.record_reported_usage(response_bytes=7, cost_usd="0.01")
    selected = SimpleNamespace(status=AcquisitionStatus.SELECTED, candidate=SimpleNamespace(
        provider="sec", provider_document_id="one", market="US", document_kind="annual_report"), receipt=None)
    service = object.__new__(SourceAcquisitionService)
    service.coordinator = SimpleNamespace(select=lambda *a, **k: selected,
        catalog=SimpleNamespace(config=SimpleNamespace(catalog_dir=tmp_path)), cleanup_target=lambda *a: None)
    service.journal = SimpleNamespace(record=lambda **k: None)
    monkeypatch.setattr("company_wiki.source_catalog.acquisition_service.acquisition_target_sha256", lambda *a: "fixture")
    monkeypatch.setattr(service, "_stage_with_retry", lambda *a, **k: selected)
    original = RuntimeError("import failed after provider")
    def import_fail(*a, **k):
        raise original
    monkeypatch.setattr(service, "_finish", import_fail)
    with pytest.raises(RuntimeError) as caught:
        service.ensure(request(), budget=b)
    assert caught.value is original
    dto = structured_error(original)["acquisition_failure"]
    assert dto["code"] == "acquisition_validation_failed"
    assert dto["provider_started"] is True and dto["usage_complete"] is True
    assert dto["acquisition_usage"] == usage()


def test_cleanup_error_after_retry_does_not_hide_provider_cause(tmp_path):
    from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
    original = AdapterProcessError("retryable provider cause")
    original.error_code = "provider_failed"
    original.retryable = True
    def fail(*a, **k):
        raise original
    def cleanup(*a, **k):
        raise OSError("cleanup fault")
    service = object.__new__(SourceAcquisitionService)
    service.coordinator = SimpleNamespace(stage_selected=fail, cleanup_target=cleanup)
    with pytest.raises(AdapterProcessError) as caught:
        service._stage_with_retry(request(), SimpleNamespace(candidate="one"), budget=budget())
    assert caught.value is original


def test_owned_windows_barrier_proves_no_target_launch(tmp_path, monkeypatch):
    import company_wiki._bounded_process as transport
    if transport.os.name != "nt":
        pytest.skip("Windows pre-target bootstrap barrier")
    marker = tmp_path / "must-not-exist"
    monkeypatch.setattr(transport, "_assign_windows_job", lambda *a: (_ for _ in ()).throw(OSError("barrier")))
    with pytest.raises(transport.TransportError) as caught:
        transport.run_bounded([sys.executable, "-B", "-c", f"from pathlib import Path;Path({str(marker)!r}).write_text('ran')"],
                              timeout_seconds=5, cwd=str(tmp_path))
    assert caught.value.provider_started is False
    assert not marker.exists()


def test_timeout_preflight_proves_target_not_launched():
    from company_wiki._bounded_process import run_json_process
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        run_json_process([sys.executable, "unused.py"], input="", cwd=Path.cwd(), env={}, timeout_seconds=0)
    assert caught.value.provider_started is False


def test_owned_cleanup_secondary_error_preserves_primary_timeout_and_checkpoint(tmp_path, monkeypatch):
    import company_wiki._bounded_process as transport
    actual_cleanup = transport._cleanup
    def cleanup(*a):
        actual_cleanup(*a)
        raise OSError("cleanup failed after child ran")
    monkeypatch.setattr(transport, "_cleanup", cleanup)
    code = "import sys,time;sys.stderr.write(" + repr(checkpoint()) + ");sys.stderr.flush();time.sleep(3)"
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        transport.run_json_process([sys.executable, "-B", "-c", code], input="", cwd=tmp_path,
                                   env=None, timeout_seconds=0.7)
    assert b'"status": "progress"' in caught.value.stderr
    assert caught.value.provider_started is None
    assert any("cleanup" in note for note in getattr(caught.value.__cause__, "__notes__", []))


@pytest.mark.parametrize("success", [False, True])
def test_scratch_cleanup_after_verified_final_keeps_original_cause_and_usage(tmp_path, monkeypatch, success):
    class BrokenCleanup:
        name = str(tmp_path)
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self.name
        def __exit__(self, *a):
            raise OSError("scratch cleanup after final")
        def cleanup(self):
            raise OSError("scratch cleanup after final")
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.TemporaryDirectory", BrokenCleanup)
    result = {"schema_version": "1.0", "status": "ok", "adapter": {"name": "proof", "version": "1.0.0"},
              "acquisition_usage": usage(), "candidates": []}
    monkeypatch.setattr("company_wiki.source_catalog.adapter_process.run_json_process", lambda *a, **k:
        subprocess.CompletedProcess(a[0], 0 if success else 1, json.dumps(result) if success else "", "" if success else final()))
    b = budget()
    with pytest.raises(AdapterProcessError) as caught:
        adapter(tmp_path).discover_bounded(request(), b)
    dto = publish(caught.value, b)
    assert dto["code"] == ("adapter_process_failed" if success else "upstream_unavailable")
    assert dto["provider_started"] is True and dto["usage_complete"] is True
    assert dto["acquisition_usage"] == usage()


def test_barrier_cleanup_failure_does_not_erase_proven_pre_target_failure(tmp_path, monkeypatch):
    import company_wiki._bounded_process as transport
    if transport.os.name != "nt":
        pytest.skip("Windows bootstrap barrier")
    actual_close = transport._close_pipes
    def close(*a):
        actual_close(*a)
        raise OSError("secondary close fault")
    monkeypatch.setattr(transport, "_close_pipes", close)
    monkeypatch.setattr(transport, "_assign_windows_job", lambda *a: (_ for _ in ()).throw(OSError("primary barrier")))
    with pytest.raises(transport.TransportError) as caught:
        transport.run_bounded([sys.executable, "-B", "-c", "print('must not run')"], timeout_seconds=5, cwd=str(tmp_path))
    assert caught.value.provider_started is False
    assert any("cleanup" in note for note in caught.value.__notes__)


@pytest.mark.parametrize("count,started,expected_usage", [(23, True, usage(23, "0.04")), (0, None, None)])
def test_restored_existing_budget_does_not_publish_false_final_zero(count, started, expected_usage):
    deadline = budget().deadline_monotonic
    b = AcquisitionBudget(max_response_bytes=100, max_cost_usd="1", deadline_monotonic=deadline,
                          response_bytes_used=count, cost_usd_used="0.04" if count else "0", usage_complete=False)
    error = AcquisitionBudgetExceeded("incomplete restored accounting")
    dto = publish(error, b)
    assert dto["provider_started"] is started and dto["usage_complete"] is False
    assert dto["acquisition_usage"] == expected_usage


@pytest.mark.parametrize("observed", [False, None])
def test_exception_execution_proof_cannot_be_erased_by_unobserved_operation_budget(observed):
    b = budget()
    if observed is None:
        b.observe_provider(started=None, complete=None)
    error = AdapterProcessError("target ran but invocation not operation-accounted")
    error.provider_started = True
    error.acquisition_usage = usage(77, "0.5")
    error.acquisition_usage_complete = True
    dto = publish(error, b)
    assert dto["provider_started"] is True
    assert dto["usage_complete"] is None
    assert dto["acquisition_usage"] is None  # Invocation numbers cannot masquerade as operation totals.
