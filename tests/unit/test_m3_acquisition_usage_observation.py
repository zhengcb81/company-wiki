"""M3-USAGE unit contracts for acquisition-observation/1 (CWP producer side).

Strict closed-shape validation, the null-vs-zero distinction, per-operation
counter isolation, and the typed never-started proof (pre-launch timeout
carrying provider_started=False, the only accepted zero-receipt trigger).
The old acquisition_usage/1.0 and acquisition-failure/1 shapes are pinned by
the existing suites (test_acquisition_failure_diagnostic,
test_acquisition_usage_recovery, test_adapter_process_budget) and are not
re-tested here.
"""
from __future__ import annotations

import pytest

from company_wiki.source_catalog.acquisition_observation import (
    ACQUISITION_OBSERVATION_SCHEMA,
    observation_from_budget,
    observation_from_result,
    published_acquisition_observation,
    validated_http_observation,
    validated_observation,
)
from company_wiki.source_catalog.download_budget import AcquisitionBudget


def observation(**overrides):
    value = {
        "schema_version": ACQUISITION_OBSERVATION_SCHEMA,
        "usage_scope": "operation",
        "outcome": "downloaded_new",
        "provider_started": True,
        "usage_complete": True,
        "wire_body_bytes": 10,
        "wire_usage_complete": True,
        "entity_body_bytes": 40,
        "http_exchanges": 3,
        "http_exchanges_complete": True,
        "cost_usd": "0.01",
        "http_observation": {"status_code": 200, "mime_type": "application/pdf",
                             "content_encoding": "gzip", "wire_content_length": 10},
    }
    value.update(overrides)
    return value


def budget_with_usage(**limits):
    limits.setdefault("max_response_bytes", 1000)
    limits.setdefault("max_seconds", 60.0)
    limits.setdefault("max_cost_usd", "1")
    return AcquisitionBudget.from_limits(**limits)


class TestValidatedObservation:
    def test_accepts_the_published_shape(self):
        assert validated_observation(observation()) == observation()

    @pytest.mark.parametrize("mutate", [
        lambda v: v.pop("cost_usd"),
        lambda v: v.update(extra=1),
        lambda v: v.update(schema_version="acquisition-observation/2"),
        lambda v: v.update(usage_scope="invocation"),
        lambda v: v.update(outcome="invented"),
        lambda v: v.update(provider_started="yes"),
        lambda v: v.update(usage_complete=1),
        lambda v: v.update(wire_body_bytes=-1),
        lambda v: v.update(wire_body_bytes=True),
        lambda v: v.update(entity_body_bytes="40"),
        lambda v: v.update(http_exchanges=2.5),
        lambda v: v.update(http_exchanges_complete="maybe"),
    ])
    def test_any_deviation_drops_the_whole_value(self, mutate):
        value = observation()
        mutate(value)
        assert validated_observation(value) is None

    @pytest.mark.parametrize("cost", ["NaN", "Infinity", "-Infinity", "-0.5", "abc", 0.5, True])
    def test_unknown_or_invalid_cost_is_rejected_not_zeroed(self, cost):
        assert validated_observation(observation(cost_usd=cost)) is None

    def test_null_cost_is_a_valid_unknown(self):
        assert validated_observation(observation(cost_usd=None))["cost_usd"] is None

    def test_null_flags_are_valid_unknowns(self):
        validated = validated_observation(observation(provider_started=None,
                                                      usage_complete=None,
                                                      wire_usage_complete=None,
                                                      http_exchanges_complete=None))
        assert validated["provider_started"] is None
        assert validated["usage_complete"] is None

    def test_http_observation_is_four_closed_keys(self):
        assert validated_observation(observation(http_observation={
            "status_code": 200, "mime_type": "text/plain",
            "content_encoding": "identity", "wire_content_length": 5,
            "etag": "secret-token"})) is None
        assert validated_http_observation({"status_code": 200, "mime_type": "text/plain",
                                           "content_encoding": "identity",
                                           "wire_content_length": None}) is not None

    def test_http_observation_rejects_unbounded_text(self):
        assert validated_http_observation({"status_code": 200, "mime_type": "x" * 129,
                                           "content_encoding": "identity",
                                           "wire_content_length": None}) is None

    def test_field_names_carry_no_physical_location_token(self):
        for key in observation():
            assert not any(part in key for part in ("path", "location", "root", "bundle"))


class TestBudgetProjection:
    def test_no_budget_means_no_observation(self):
        assert observation_from_budget(None, outcome="failed") is None

    def test_unknown_outcome_is_not_projected(self):
        assert observation_from_budget(budget_with_usage(), outcome="invented") is None

    def test_zero_cap_is_not_a_zero_fee(self):
        budget = budget_with_usage(max_cost_usd="0")
        budget.consume_http_bytes(wire_bytes=7, response_bytes=100)
        projected = observation_from_budget(budget, outcome="downloaded_new")
        assert projected["cost_usd"] is None  # byte metering never proves a fee
        assert projected["entity_body_bytes"] == 100

    def test_provider_stated_zero_fee_is_an_observed_zero(self):
        budget = budget_with_usage()
        budget.record_reported_usage(response_bytes=0, cost_usd="0")
        assert observation_from_budget(budget, outcome="downloaded_new")["cost_usd"] == "0"

    def test_synthetic_receipt_never_marks_the_fee_observed(self):
        budget = budget_with_usage()
        budget.record_reported_usage(response_bytes=0, cost_usd="0", cost_observed=False)
        assert observation_from_budget(budget, outcome="failed")["cost_usd"] is None

    def test_lower_bound_flags_survive_projection(self):
        budget = budget_with_usage()
        budget.consume_http_bytes(wire_bytes=10, response_bytes=40)
        budget.observe_provider(started=True, complete=False)
        projected = observation_from_budget(budget, outcome="failed")
        assert projected["usage_complete"] is False
        assert projected["provider_started"] is True

    def test_operations_never_mix(self):
        first = budget_with_usage()
        first.record_reported_usage(response_bytes=11, cost_usd="0.01", wire_bytes=5,
                                    http_exchanges=1)
        second = budget_with_usage()
        second.record_reported_usage(response_bytes=97, cost_usd="0.07", wire_bytes=97,
                                     http_exchanges=3)
        a = observation_from_budget(first, outcome="downloaded_new")
        b = observation_from_budget(second, outcome="gap_plan")
        assert (a["entity_body_bytes"], a["cost_usd"], a["http_exchanges"]) == (11, "0.01", 1)
        assert (b["entity_body_bytes"], b["cost_usd"], b["http_exchanges"]) == (97, "0.07", 3)

    def test_exchange_counting_stashes_last_observation(self):
        budget = budget_with_usage()
        budget.record_http_exchange({"status_code": 200, "mime_type": "text/plain",
                                     "content_encoding": "identity",
                                     "wire_content_length": 5})
        assert budget.http_exchanges_used == 1
        projected = observation_from_budget(budget, outcome="downloaded_new")
        assert projected["http_observation"]["status_code"] == 200

    def test_legacy_receipt_without_exchange_count_is_unmeasured_not_zero_final(self):
        budget = budget_with_usage()
        budget.record_reported_usage(response_bytes=10, cost_usd="0")
        projected = observation_from_budget(budget, outcome="downloaded_new")
        assert projected["http_exchanges"] == 0
        assert projected["http_exchanges_complete"] is None


class TestResultProjection:
    def test_reads_the_defined_producer_shapes(self):
        published = observation()
        assert observation_from_result({"acquisition_observation": published}) == published
        assert observation_from_result({"source_ensure": {"acquisition_observation": published}}) == published
        assert observation_from_result({"close_gap": {"acquisition": {"acquisition_observation": published}}}) == published

    def test_garbage_never_publishes(self):
        assert observation_from_result({"acquisition_observation": "text"}) is None
        assert observation_from_result(["list"]) is None
        assert observation_from_result({"nested": {"acquisition_observation": observation()}}) is None

    def test_exception_attribute_is_published_only_when_valid(self):
        exc = RuntimeError("boom")
        assert published_acquisition_observation(exc) is None
        exc.acquisition_observation = observation()
        assert published_acquisition_observation(exc)["outcome"] == "downloaded_new"
        exc.acquisition_observation = {"schema_version": "acquisition-observation/1"}
        assert published_acquisition_observation(exc) is None


class TestNeverStartedProof:
    @staticmethod
    def _preflight_timeout(*_args, **_kwargs):
        import subprocess
        # Exactly what run_json_process emits when the deadline expires before
        # the child starts (see test_timeout_preflight_proves_target_not_launched).
        error = subprocess.TimeoutExpired("adapter", 1)
        error.provider_started = False
        raise error

    def test_preflight_timeout_is_a_typed_never_started_zero(self, monkeypatch, tmp_path):
        from company_wiki.source_catalog import adapter_process
        from company_wiki.source_catalog.adapter_process import AdapterProcessError, JsonCommandAdapter

        monkeypatch.setattr(adapter_process, "run_json_process", self._preflight_timeout)
        project = tmp_path / "proj"
        project.mkdir()
        adapter = JsonCommandAdapter(
            name="m3-unit", version="1.0.0", command=["python", "-c", "pass"],
            project_root=project, supports_acquisition_budget=True)
        budget = budget_with_usage()
        request = adapter_process.SourceRequest(
            entity="Fixture", market="US", security_id="FIXTURE",
            document_kind="annual_report", as_of_date="2026-10-10", mode="exact",
            fiscal_year=2025)
        with pytest.raises(AdapterProcessError) as caught:
            adapter.discover_bounded(request, budget)
        exc = caught.value
        assert exc.provider_started is False
        assert exc.synthetic_zero_receipt is True
        assert exc.http_exchanges == 0
        # The synthetic zero proves byte counts only: no fee observed, no
        # exchanges observed, and no usage was charged as reported usage.
        assert budget.cost_reported is False
        assert budget.http_exchanges_used == 0
        projected = observation_from_budget(budget, outcome="failed")
        assert projected["provider_started"] is False
        assert projected["usage_complete"] is True
        assert projected["http_exchanges"] == 0
        assert projected["cost_usd"] is None

    def test_synthetic_zero_never_clears_an_earlier_fee_receipt(self, monkeypatch, tmp_path):
        from company_wiki.source_catalog import adapter_process
        from company_wiki.source_catalog.adapter_process import AdapterProcessError, JsonCommandAdapter

        monkeypatch.setattr(adapter_process, "run_json_process", self._preflight_timeout)
        project = tmp_path / "proj"
        project.mkdir()
        adapter = JsonCommandAdapter(
            name="m3-unit", version="1.0.0", command=["python", "-c", "pass"],
            project_root=project, supports_acquisition_budget=True)
        budget = budget_with_usage()
        budget.record_reported_usage(response_bytes=45, cost_usd="0.0003", wire_bytes=45,
                                     http_exchanges=1)
        request = adapter_process.SourceRequest(
            entity="Fixture", market="US", security_id="FIXTURE",
            document_kind="annual_report", as_of_date="2026-10-10", mode="exact",
            fiscal_year=2025)
        with pytest.raises(AdapterProcessError):
            adapter.discover_bounded(request, budget)
        projected = observation_from_budget(budget, outcome="failed")
        assert projected["cost_usd"] == "0.0003"  # earlier receipt survives
        assert projected["http_exchanges"] == 1
        assert projected["entity_body_bytes"] == 45
