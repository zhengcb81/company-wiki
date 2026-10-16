"""Actual work boundaries of the shared source view, not budget-counter mirrors."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from company_wiki.document_understanding import layout_bridge
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.profiles import get_profile, route_document
from company_wiki.document_understanding.profiles import observation as routing
from company_wiki.document_understanding.profiles.registry import resolve_reading_profile
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.source_catalog import narrative_reading
from company_wiki.source_catalog.narrative_document import DocumentStructure


def source():
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "opaque", "source_sha256": "passed-through"},
        "metadata": {"mime_type": "text/html", "language": "en"},
        "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
        "units": [{"unit_id": "form", "ordinal": 0, "locator": "native:0", "page": None,
                   "text": "FORM 10-Q", "kind": "heading", "role": "company_filing",
                   "hints": {"heading_level": 1}, "layout": {}}],
    }


class NoIteration(list):
    def __iter__(self):
        raise AssertionError("zero enhancement budget must not enumerate the document")


def test_route_and_policy_reuse_actual_unit_preparation():
    original = source()
    prepared = routing.parse_observation(original)
    with patch.object(routing, "_parse_units", side_effect=AssertionError("prepared twice")):
        route = route_document(prepared)
        policy = resolve_reading_profile(get_profile(route["profile_id"]), prepared, route)
    assert route["family"] == "quarterly"
    assert policy["form_type"] == "10-Q"
    assert prepared.units[0].text == "FORM 10-Q"


def test_prepared_limits_can_tighten_without_reconstructing_units():
    prepared = routing.parse_observation(source())
    with patch.object(routing, "_parse_units", side_effect=AssertionError("prepared twice")):
        bounded = routing.parse_observation(prepared, {"max_probe_units": 0})
    assert bounded.units is prepared.units
    assert bounded.probes == ()
    assert bounded.probe_limited


def test_zero_shared_layout_budget_does_not_touch_units():
    observation = source()
    observation["units"] = NoIteration(observation["units"])
    budget = WorkBudget(0)
    enriched, hints = layout_bridge.apply_layout_hints(observation, work_budget=budget)
    assert enriched is observation
    assert hints["unit_hints"] == []
    assert hints["coverage"]["complete"] is False
    assert any(d["code"] == "WORK_BUDGET_EXCEEDED" for d in hints["diagnostics"])


def test_zero_binding_budget_has_no_deepcopy_or_exception_tail_scan():
    structure = {"source_ref": source()["source_ref"], "sections": NoIteration([{}]),
                 "semantic_units": NoIteration([{}]), "coverage": {"complete": True},
                 "diagnostics": []}
    with patch.object(layout_bridge, "deepcopy", side_effect=AssertionError("whole document copied")):
        result = layout_bridge.bind_layout_context(
            structure, {"source_ref": source()["source_ref"]}, work_budget=WorkBudget(0))
    assert result["coverage"]["complete"] is False
    assert structure["coverage"]["complete"] is True
    assert result["diagnostics"][-1]["unit_ids"] == []


def test_shared_layout_passes_same_budget_into_geometry(monkeypatch):
    original = layout_bridge.derive_layout_hints
    budgets = []

    def observe(payload, **kwargs):
        budgets.append(kwargs.get("work_budget"))
        return original(payload, **kwargs)

    monkeypatch.setattr(layout_bridge, "derive_layout_hints", observe)
    budget = WorkBudget(100_000)
    layout_bridge.apply_layout_hints(source(), work_budget=budget)
    assert budgets == [budget]
    assert budget.used > 0


def test_standalone_layout_returns_independent_nested_view():
    observation = source()
    before = deepcopy(observation)
    enriched, _ = layout_bridge.apply_layout_hints(observation)
    enriched["units"][0]["hints"]["private_test_value"] = [1]
    assert observation == before


@pytest.mark.parametrize("raw", [{"max_probe_units": -1}, {"max_probe_chars": True}])
def test_prepared_view_retains_real_limit_errors(raw):
    with pytest.raises(routing.ObservationError):
        routing.parse_observation(routing.parse_observation(source()), raw)


def test_composed_route_prepares_units_once():
    original = routing._parse_units
    calls = []

    def track(raw):
        calls.append(len(raw))
        return original(raw)

    with patch.object(routing, "_parse_units", side_effect=track):
        understand_units([], source_id="opaque", source_sha256="opaque")
    assert calls == [0]


def test_pipeline_zero_budget_does_not_iterate_parser_units():
    result = understand_units(NoIteration([object()]), source_id="opaque", source_sha256="opaque",
                              work_budget=WorkBudget(0))
    assert result["analysis_status"] == "deferred"
    assert result["observation"]["units"] == []
    assert result["structure"]["coverage"]["complete"] is False
    assert result["work"]["source_unit_count"] == 1


def test_production_zero_budget_stops_before_grouping_and_classifying():
    parsed = DocumentStructure(source_id="opaque", source_sha256="opaque", language="en",
                               units=NoIteration([object()]), line_count=1)
    with patch.object(narrative_reading, "_understand", side_effect=AssertionError("read source")):
        result = narrative_reading.select_reading_evidence(
            parsed, title="Annual report", work_budget=WorkBudget(0))
    assert result.status == "needs_review"
    assert result.source_units == 1
    assert result.evidence_spans == ()
    assert result.coverage_complete is False


def test_standalone_zero_binding_never_mutates_original_semantics():
    structure = {"source_ref": source()["source_ref"], "sections": [],
                 "semantic_units": [{"completeness": "complete", "member_unit_ids": ["form"]}],
                 "coverage": {"complete": True, "limits": {"max_work_units": 0}}, "diagnostics": []}
    before = deepcopy(structure)
    result = layout_bridge.bind_layout_context(structure, {"source_ref": source()["source_ref"]})
    assert structure == before
    assert result["semantic_units"][0]["completeness"] == "partial"


def test_shared_binding_zero_budget_does_not_copy_old_diagnostics():
    structure = {"source_ref": source()["source_ref"], "sections": [], "semantic_units": [],
                 "coverage": {"complete": True}, "diagnostics": NoIteration([{}] * 1000)}
    result = layout_bridge.bind_layout_context(
        structure, {"source_ref": source()["source_ref"]}, work_budget=WorkBudget(0))
    assert len(result["diagnostics"]) == 1
    assert result["coverage"]["complete"] is False


def test_policy_does_not_silently_expand_prepared_probe_limits():
    prepared = routing.parse_observation(source(), {"max_probe_units": 1, "max_probe_chars": 1})
    route = route_document(prepared)
    policy = resolve_reading_profile(get_profile(route["profile_id"]), prepared, route)
    assert policy["policy_probe"]["probed_chars"] <= 1
