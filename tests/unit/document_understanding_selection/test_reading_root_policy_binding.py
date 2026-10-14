"""Preserve observed forms through strategy binding and causal cache scopes.

Cover and body fragments are established source excerpt fixtures; no company-specific
route, provider call, parser rerun or replacement metadata claim participates.
"""

from copy import deepcopy

import pytest

from company_wiki.document_understanding import understand_units
from company_wiki.document_understanding.profiles import (
    get_profile,
    resolve_reading_profile,
    route_document,
)
from fixtures.document_understanding_profiles.builders import (
    SEC_10K_BODY,
    SEC_10K_COVER,
    SEC_10Q_BODY,
    SEC_10Q_COVER,
    SEC_20F_BODY,
    SEC_20F_COVER,
    observation,
    unit,
)


CASES = [
    ("10-K", "sec_10k", "annual", SEC_10K_COVER, SEC_10K_BODY),
    ("10-Q", "sec_10q", "quarterly", SEC_10Q_COVER, SEC_10Q_BODY),
    ("20-F", "sec_20f", "annual", SEC_20F_COVER, SEC_20F_BODY),
]


def _units(cover, body):
    return [
        unit(f"native-{index}", index, text, kind="heading" if index < len(cover) else "paragraph", page=1)
        for index, text in enumerate([*cover, *body])
    ]


def _pipeline(cover, body):
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    sid = source_id_for_sha256("a" * 64)
    native = [
        _make_unit(source_id=sid, parser_version="1.0.0",
                   coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
                   raw_text=text, unit_kind="html_paragraph", source_role="company_filing",
                   language="en", metadata={})
        for index, text in enumerate([*cover, *body])
    ]
    return understand_units(native, source_id=sid, source_sha256="a" * 64,
                            declared_kind="unknown", mime_type="text/html", language="en",
                            metadata={"form_type": "unknown"})


@pytest.mark.parametrize("form,policy,family,cover,body", CASES)
@pytest.mark.parametrize("metadata_form", [None, "unknown"])
def test_root_route_retains_original_detected_sec_form(form, policy, family, cover, body, metadata_form):
    original = observation(_units(cover, body), form_type=metadata_form, mime_type="text/html")
    before = deepcopy(original)
    route = route_document(original)
    assert route["profile_id"] == policy and route["family"] == family
    assert route.get("form_type") == form, "do not drop the already-detected source-owned form"
    assert original == before, "resolving a form does not replace the source metadata claim"


@pytest.mark.parametrize("form,policy,family,cover,body", CASES)
def test_policy_consumes_actual_route_form_instead_of_unknown_metadata(form, policy, family, cover, body):
    original = observation(_units(cover, body), form_type="unknown", mime_type="text/html")
    route = route_document(original)
    # Isolate the resolver seam: this is the actual value the existing router detected,
    # not a new classification, subtype heuristic or another parser invocation.
    routed_form = {**route, "form_type": form}
    resolved = resolve_reading_profile(get_profile(route["profile_id"]), original, routed_form)
    assert resolved["family_policy"]["id"] == policy
    assert resolved["family"] == family
    assert any(component["id"] == policy for component in resolved["policy_components"])
    assert all(component["kind"] != "fallback" for component in resolved["policy_components"])


@pytest.mark.parametrize("form,policy,family,cover,body", CASES)
def test_pipeline_binds_actual_sec_policy_to_original_units(form, policy, family, cover, body):
    pipeline = _pipeline(cover, body)
    assert pipeline["route"].get("form_type") == form
    assert pipeline["profile"]["family_policy"]["id"] == policy
    assert pipeline["observation"]["metadata"]["form_type"] == "unknown"
    assert pipeline["reading_plan"]["unit_profiles"]
    assert all(view["family_policy"]["id"] == policy
               for view in pipeline["reading_plan"]["unit_profiles"].values())


@pytest.mark.parametrize("form,policy,family,cover,body", CASES)
def test_actual_sec_form_reaches_reading_scope_and_dependency_eligibility(form, policy, family, cover, body):
    from company_wiki.document_understanding.decision_inventory import build_decision_trace

    pipeline = _pipeline(cover, body)
    assert pipeline["profile"].get("form_type") == form
    assert all(view.get("form_type") == form
               for view in pipeline["reading_plan"]["unit_profiles"].values())
    trace = build_decision_trace(pipeline)
    assert trace["inventory_complete"]
    assert trace["scopes"][0]["form_type"] == form
    candidates = [row for row in trace["candidates"] if row["candidate_id"].startswith("family|")]
    assert next(row for row in candidates if row["candidate_id"].endswith("|" + policy))["eligible"]
    if family == "annual":
        other = "sec_20f" if policy == "sec_10k" else "sec_10k"
        assert not next(row for row in candidates if row["candidate_id"].endswith("|" + other))["eligible"]


def test_old_route_without_form_field_retains_metadata_compatibility():
    original = observation(_units(SEC_10K_COVER, SEC_10K_BODY), form_type="10-K", mime_type="text/html")
    old_route = {key: value for key, value in route_document(original).items() if key != "form_type"}
    resolved = resolve_reading_profile(get_profile(old_route["profile_id"]), original, old_route)
    assert resolved["family_policy"]["id"] == "sec_10k"


@pytest.mark.parametrize("change,invalidates", [("instructions", False), ("eligibility", True)])
def test_actual_form_bounds_cache_dependencies_but_retains_losing_policy_matcher(monkeypatch, change, invalidates):
    from company_wiki.document_understanding.decision_inventory import build_decision_trace, current_decision_trace
    from company_wiki.document_understanding.profiles import registry

    frozen = build_decision_trace(_pipeline(SEC_10K_COVER, SEC_10K_BODY))
    changed = deepcopy(registry._CATALOG)
    other_form = next(row for row in changed["families"] if row["id"] == "sec_20f")
    if change == "instructions":
        other_form["reading_questions"].append("Changed only the other form's reading instruction.")
    else:
        other_form["applies_to"]["forms"].append("10-K")
    monkeypatch.setattr(registry, "_CATALOG", changed)
    assert (current_decision_trace(frozen) != frozen) is invalidates


@pytest.mark.parametrize("actual_form", [None, "unknown"])
def test_current_route_unknown_form_does_not_borrow_a_conflicting_metadata_identity(actual_form):
    original = observation([unit("body", 0, "A readable business description without an identified form.")],
                           form_type="20-F", mime_type="text/html")
    current_route = {"profile_id": "sec_10k", "regime": "sec", "family": "annual", "form_type": actual_form}
    resolved = resolve_reading_profile(get_profile("sec_10k"), original, current_route)
    assert resolved["family_policy"]["id"] is None
    assert resolved.get("form_type") in {None, "unknown"}


def test_observed_sec_form_outweighs_conflicting_metadata_in_policy_only():
    original = observation(_units(SEC_20F_COVER, SEC_20F_BODY), form_type="10-K", mime_type="text/html")
    before = deepcopy(original)
    route = route_document(original)
    assert route["profile_id"] == "sec_20f"
    resolved = resolve_reading_profile(get_profile(route["profile_id"]), original,
                                       {**route, "form_type": "20-F"})
    assert resolved["family_policy"]["id"] == "sec_20f", "route evidence must survive a false metadata claim"
    assert original == before


def test_generic_unidentified_document_does_not_gain_a_sec_form_or_policy():
    original = observation([unit("body", 0, "Our customers purchased the new product.")],
                           form_type="unknown", mime_type="text/html")
    route = route_document(original)
    resolved = resolve_reading_profile(get_profile(route["profile_id"]), original, route)
    assert route.get("form_type") in {None, "unknown"}
    assert route["profile_id"] == "generic"
    assert resolved["family_policy"]["id"] is None


def test_root_form_uses_existing_signal_pass_and_not_human_diagnostic_text(monkeypatch):
    from company_wiki.document_understanding import profiles
    from company_wiki.document_understanding.profiles import signals

    original_detect = profiles.detect_signals
    original_add = signals.SignalBag.add
    calls = []

    def observed_pass(parsed):
        bag = original_detect(parsed)
        calls.append(bag)
        return bag

    def changed_wording(bag, bucket, code, unit_ids, detail, **fields):
        if fields.get("form_type") is not None:
            detail = "Presentation wording changed; the source form did not."
        return original_add(bag, bucket, code, unit_ids, detail, **fields)

    monkeypatch.setattr(profiles, "detect_signals", observed_pass)
    monkeypatch.setattr(signals.SignalBag, "add", changed_wording)
    original = observation(_units(SEC_10K_COVER, SEC_10K_BODY), form_type="unknown", mime_type="text/html")
    route = route_document(original)
    assert len(calls) == 1
    assert any(signal.form_type == "10-K" for signal in calls[0].all)
    assert route.get("form_type") == "10-K"
    resolved = resolve_reading_profile(get_profile(route["profile_id"]), original, route)
    assert resolved["family_policy"]["id"] == "sec_10k"
