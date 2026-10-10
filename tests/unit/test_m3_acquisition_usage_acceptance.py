"""Acceptance counterexamples: optional diagnostics must never mask a cause."""
from __future__ import annotations

import pytest

from company_wiki.source_catalog.acquisition_observation import validated_observation as validate


def _observation(**changes):
    value = {
        "schema_version": "acquisition-observation/1", "usage_scope": "operation",
        "outcome": "failed", "provider_started": True, "usage_complete": True,
        "wire_body_bytes": 10, "wire_usage_complete": True, "entity_body_bytes": 20,
        "http_exchanges": 1, "http_exchanges_complete": True, "cost_usd": None,
        "http_observation": None,
    }
    value.update(changes)
    return value


@pytest.mark.parametrize("outcome", [[], {}])
def test_unhashable_outcome_is_dropped_without_masking_primary_error(outcome):
    assert validate(_observation(outcome=outcome)) is None


def test_exchange_count_is_integer_across_all_three_responsibility_layers():
    assert validate(_observation(http_exchanges=None)) is None
    assert validate(_observation(http_exchanges=0, http_exchanges_complete=None)) is not None


from company_wiki.source_catalog import dayu_sdk_cli as dayu  # noqa: E402
from company_wiki.source_catalog.adapter_process import AdapterProcessError, JsonCommandAdapter  # noqa: E402
from company_wiki.source_catalog.acquisition_observation import observation_from_budget  # noqa: E402
from company_wiki.source_catalog.download_budget import AcquisitionBudget  # noqa: E402
from company_wiki.source_catalog.bounded_http import ProviderBudgetStop, usage_receipt  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402


def _budget():
    return AcquisitionBudget.from_limits(max_response_bytes=10000, max_seconds=20, max_cost_usd="1")


def _reply(*, observed=None, include=True):
    reply = {"acquisition_usage": {"schema_version": "1.0", "response_bytes": 20, "cost_usd": "0"},
             "http_wire_bytes": 10, "http_exchanges": 1, "http_observation": None}
    if include:
        reply["acquisition_cost_observed"] = observed
    return reply


@pytest.mark.parametrize("known_first", [True, False])
def test_known_and_unknown_cost_preserve_observed_lower_bound_in_either_order(known_first):
    budget = _budget()
    known = _reply(include=False)
    known["acquisition_usage"]["cost_usd"] = "0.03"
    unknown = _reply(observed=False)
    for reply in ([known, unknown] if known_first else [unknown, known]):
        JsonCommandAdapter._charge_bounded_usage(reply, budget)
    value = observation_from_budget(budget, outcome="downloaded_new")
    assert value["cost_usd"] == "0.03"
    assert value["usage_complete"] is False
    assert budget.usage_complete is True  # Optional fee observation never blocks original acquisition.
    assert value["entity_body_bytes"] == 40 and value["wire_body_bytes"] == 20
    assert value["http_exchanges"] == 2


@pytest.mark.parametrize("marker", [False, None, [], {}, "yes", 1])
def test_unobserved_or_malformed_fee_marker_is_unknown_without_a_new_gate(marker):
    budget = _budget()
    JsonCommandAdapter._charge_bounded_usage(_reply(observed=marker), budget)
    assert observation_from_budget(budget, outcome="downloaded_new")["cost_usd"] is None
    assert budget.response_bytes_used == 20
    budget.ensure_open()


@pytest.mark.parametrize("fee", ["0", "0.03"])
def test_legacy_fee_counter_is_not_full_fee_certainty(fee):
    budget = _budget()
    reply = _reply(include=False)
    reply["acquisition_usage"]["cost_usd"] = fee
    JsonCommandAdapter._charge_bounded_usage(reply, budget)
    value = observation_from_budget(budget, outcome="downloaded_new")
    if fee == "0":
        assert value["cost_usd"] is None
    else:
        assert value["cost_usd"] == fee
        assert value["usage_complete"] is False  # Reported legacy positive lower bound.
    assert str(budget.cost_usd_used) == fee  # Preserve original 1.0 accounting.
    budget.ensure_open()


@pytest.mark.parametrize("fee", ["0", "0.03"])
def test_explicit_fee_proof_is_complete_including_explicit_free(fee):
    budget = _budget()
    reply = _reply(observed=True)
    reply["acquisition_usage"]["cost_usd"] = fee
    JsonCommandAdapter._charge_bounded_usage(reply, budget)
    value = observation_from_budget(budget, outcome="downloaded_new")
    assert value["cost_usd"] == fee
    assert value["usage_complete"] is True


@pytest.mark.parametrize("kind", ["success", "failure", "progress"])
def test_parent_preserves_optional_fee_evidence_at_every_response_boundary(kind, tmp_path):
    adapter = JsonCommandAdapter(name="fixture", version="1.0.0", command=["python"],
                                 project_root=tmp_path, supports_acquisition_budget=True)
    reply = {"schema_version": "1.0", "status": "ok", "adapter": {"name": "fixture", "version": "1.0.0"},
             **_reply(observed=False)}
    budget = _budget()
    if kind == "success":
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(reply), stderr="")
        response = adapter._decode_response(completed, "discover")
        JsonCommandAdapter._charge_bounded_usage(response, budget)
    else:
        reply["status"] = "failed" if kind == "failure" else "progress"
        if kind == "failure":
            reply["error"] = {"code": "upstream_unavailable", "retryable": False,
                              "acquisition_usage": reply.pop("acquisition_usage")}
            completed = subprocess.CompletedProcess([], 1, stdout="", stderr=json.dumps(reply))
            with pytest.raises(AdapterProcessError) as caught:
                adapter._decode_response(completed, "discover")
            error = caught.value
        else:
            error = AdapterProcessError("primary timeout")
            adapter._attach_usage_checkpoint(error, json.dumps(reply))
        JsonCommandAdapter._charge_failure_usage(error, budget)
    assert observation_from_budget(budget, outcome="failed")["cost_usd"] is None
    assert budget.response_bytes_used == 20


@pytest.mark.parametrize("failed, reported", [(False, False), (True, False), (False, True)])
def test_owned_sdk_cli_publishes_actual_fee_proof_in_final_and_checkpoint(failed, reported, tmp_path, monkeypatch, capsys):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("CWP_ADAPTER_SCRATCH_ROOT", str(scratch))
    monkeypatch.setattr(tempfile, "tempdir", tempfile.tempdir)
    for name in ("TMP", "TEMP", "TMPDIR"):
        monkeypatch.setenv(name, str(tmp_path))
    monkeypatch.setattr(dayu.sys, "stdin", io.StringIO(json.dumps({"acquisition_budget": {
        "schema_version": "1.0", "max_response_bytes": 10000, "timeout_seconds": 20, "max_cost_usd": "1"}})))

    def operation(_action, _payload, budget, _scratch, _staging, _identity, checkpoint):
        budget.consume_http_bytes(wire_bytes=10, response_bytes=20)
        budget.record_http_exchange()
        if reported:
            budget.consume_cost_usd("0")  # A real explicit fee report, distinct from initial zero.
        checkpoint(usage_receipt(budget))
        if failed:
            raise ProviderBudgetStop("upstream_unavailable", "primary controlled failure")
        return {"candidates": []}

    monkeypatch.setattr(dayu, "_hk_operation", operation)
    result = dayu.main(["--market", "HK", "--adapter-name", "fixture", "--adapter-version", "1.0.0",
                        "--provider-state-root", str(tmp_path / "state"), "discover"])
    captured = capsys.readouterr()
    assert result == (1 if failed else 0)
    final = json.loads(captured.err.splitlines()[-1] if failed else captured.out)
    assert final["acquisition_cost_observed"] is reported
    checkpoints = [json.loads(line) for line in captured.err.splitlines() if json.loads(line)["status"] == "progress"]
    assert checkpoints[-1]["acquisition_cost_observed"] is reported
    old_usage = final["error"]["acquisition_usage"] if failed else final["acquisition_usage"]
    assert set(old_usage) == {"schema_version", "response_bytes", "cost_usd"}
    assert old_usage["cost_usd"] == "0"  # Keep old 1.0 counter contract byte-for-byte.


def test_empty_http_response_itself_proves_provider_started_without_fee_inference():
    budget = _budget()
    budget.record_http_exchange({"status_code": 204, "mime_type": "application/json",
                                 "content_encoding": "identity", "wire_content_length": 0})
    value = observation_from_budget(budget, outcome="missing")
    assert value["provider_started"] is True
    assert value["http_exchanges"] == 1
    assert value["entity_body_bytes"] == 0 and value["wire_body_bytes"] == 0
    assert value["cost_usd"] is None


def test_lower_bound_completeness_does_not_discard_new_observed_responses():
    budget = _budget()
    budget.http_exchanges_complete = False
    budget.record_http_exchange({"status_code": 200, "mime_type": "application/json",
                                 "content_encoding": "identity", "wire_content_length": 0})
    value = observation_from_budget(budget, outcome="failed")
    assert value["http_exchanges"] == 1
    assert value["http_exchanges_complete"] is False
    assert value["http_observation"]["status_code"] == 200
