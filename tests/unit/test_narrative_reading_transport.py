"""Reading strategies cross the existing formal boundary without copying evidence."""

from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_contracts import (
    NarrativeBundle, NarrativeContractError, NarrativeSelectResult,
    NarrativeSummaryResult, SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import (
    NarrativeModelRequest, NarrativeModelResponse, decode_model_draft,
)
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.models import canonical_json
from support.narrative_model_request_fixture import selection
from unit.test_official_json_model_subject import selection as official_selection


def reading_context(selected):
    ids = [span.span_id for span in selected.evidence_spans]
    return {
        "schema_version": "du-production-reading/1",
        "reading_policy_version": "du-sent-policy/1+" + "f" * 64,
        "reading_policies": [{
            "profile_id": "cn-prospectus", "profile_version": "cn-prospectus/v2+local",
            "family": "prospectus", "summary_focus": "Read business progress in context.",
            "policy_components": [{"kind": "family", "id": "cn_ipo", "version": "1.0.0",
                                   "content_digest": "a" * 64}],
            "reading_questions": ["What changed in the business?"],
            "context_requirements": [{"when": "always_for_assertion", "slots": ["subject"],
                                      "missing_behavior": "unknown", "reason": "Keep attribution."}],
            "family_policy": {"id": "cn_ipo", "design_status": "verified", "spec_status": "verified",
                              "evidence_status": "verified", "integration_status": "integrated", "gaps": []},
            "negative_hints": ["administrative material"], "semantic_units": ["business_progress"],
            "section_priorities": [{"section_role": "business", "priority": 1}],
        }],
        "business_facets": [{
            "id": "overseas", "version": "1.0.0", "content_digest": "b" * 64,
            "selection_basis": [{"unit_id": ids[0], "matched_signals": ["overseas"]}],
            "business_questions": ["What is the actual overseas progress?"],
            "summary_focus": "Preserve qualification and shipment stages.",
            "required_context": ["subject", "period"], "absence_rules": ["Unknown is not absent."],
            "confusion_checks": [{"risk": "Qualification is not a shipment.",
                                  "required_context_slots": ["stage", "period"]}],
            "applicable_mechanisms": [],
        }],
        "constraints": ["Use only the supplied original excerpts."],
        "groups": [{"group_id": "first", "kind": "business_progress", "section_role": "business",
                    "evidence_ids": ids[:2]},
                   {"group_id": "second", "kind": "project", "section_role": "business",
                    "evidence_ids": ids[1:]}] if len(ids) > 1 else [],
        "unread": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": [],
                   "deferred_unit_ids": [], "unassigned_unit_ids": [], "structure_complete": True},
        "deferred": [{"package_id": "not-sent", "reason": "CHAR_BUDGET"}],
        "layout_coverage": {"complete": False, "geometry_available": False},
    }


def with_reading(selected=None):
    selected = selected or selection(3)
    wire = selected.to_dict()
    wire["reading_context"] = reading_context(selected)
    return NarrativeSelectResult.from_dict(wire)


def summary(selected):
    span = selected.evidence_spans[0]
    return NarrativeSummaryResult.from_dict({
        "schema_version": "narrative-summary-result/2.0", "source_ref": selected.source_ref.to_dict(),
        "language": "zh", "translate": False, "status": "completed",
        "draft": {"source_id": selected.source_ref.source_id,
                  "source_sha256": selected.source_ref.content_sha256, "language": "zh",
                  "claims": [{"claim_id": "c", "text": span.raw_text, "evidence_ids": [span.span_id],
                              "claim_type": "company_statement", "modality": "actual", "needs_review": False}],
                  "status": "draft"},
        "model": {"adapter_id": "fixture", "model_id": "configured-flash", "prompt_version": "1.7.0",
                  "response_sha256": "c" * 64}, "prompt_review": selected.prompt_review.to_dict(),
    })


def test_old_select_and_model_wire_are_identical_without_reading_context():
    selected = selection(3)
    assert "reading_context" not in selected.to_dict()
    assert "reading_strategy" not in json.loads(NarrativeModelRequest.from_selection(selected).data_json)


def test_reading_context_roundtrips_and_is_detached_from_mutable_input_and_output():
    base = selection(3)
    wire = base.to_dict()
    context = reading_context(base)
    wire["reading_context"] = context
    selected = NarrativeSelectResult.from_dict(wire)
    expected = deepcopy(context)
    context["constraints"].append("mutated input")
    output = selected.to_dict()
    assert output["reading_context"] == expected
    output["reading_context"]["constraints"].append("mutated output")
    assert selected.to_dict()["reading_context"] == expected


@pytest.mark.parametrize("change", ["extra", "short_hash", "empty_ref", "unknown_ref", "duplicate_ref",
                                    "duplicate_group", "raw_text", "synthetic_example", "path", "oversized",
                                    "nested_too_deep", "invalid_unread", "invalid_finite"])
def test_malformed_or_unbounded_strategy_refuses_before_model(change, tmp_path):
    base = selection(3)
    wire = base.to_dict()
    context = reading_context(base)
    if change == "extra":
        context["unexpected"] = True
    elif change == "short_hash":
        context["reading_policy_version"] = "du-sent-policy/1+" + "f" * 16
    elif change == "empty_ref":
        context["groups"][0]["evidence_ids"] = []
    elif change == "unknown_ref":
        context["groups"][0]["evidence_ids"] = ["not-selected"]
    elif change == "duplicate_ref":
        context["groups"][0]["evidence_ids"] *= 2
    elif change == "duplicate_group":
        context["groups"][1]["group_id"] = context["groups"][0]["group_id"]
    elif change == "raw_text":
        context["reading_policies"][0]["raw_text"] = "duplicated original"
    elif change == "synthetic_example":
        context["business_facets"][0]["confusion_checks"][0]["wrong_assertion"] = "Synthetic wrong claim."
    elif change == "path":
        context["layout_coverage"]["local_path"] = str(tmp_path / "material.pdf")
    elif change == "oversized":
        context["constraints"] = ["x" * 200_000]
    elif change == "nested_too_deep":
        value = "deep"
        for _ in range(20):
            value = {"nested": value}
        context["layout_coverage"] = value
    elif change == "invalid_unread":
        context["unread"]["opaque_pages"] = [True]
    else:
        context["layout_coverage"]["ratio"] = float("nan")
    wire["reading_context"] = context
    with pytest.raises(NarrativeContractError):
        NarrativeSelectResult.from_dict(wire)


def test_shared_groups_send_original_text_once_and_restore_each_exact_group():
    selected = with_reading()
    before = selected.to_dict()
    request = NarrativeModelRequest.from_selection(selected)
    data = json.loads(request.data_json)
    assert data["evidence_groups"] == [["g1", ["e1", "e2"]], ["g2", ["e2", "e3"]]]
    assert [row[1] for row in data["evidence"]] == [span.raw_text for span in selected.evidence_spans]
    strategy = data["reading_strategy"]
    assert strategy["reading_policies"] == before["reading_context"]["reading_policies"]
    assert strategy["business_facets"] == before["reading_context"]["business_facets"]
    assert strategy["groups"] == [
        {"id": "g1", "kind": "business_progress", "section_role": "business"},
        {"id": "g2", "kind": "project", "section_role": "business"},
    ]
    assert "raw_text" not in canonical_json(strategy)
    assert selected.to_dict() == before
    response = {"draft": {"source_id": selected.source_ref.source_id,
        "source_sha256": selected.source_ref.content_sha256, "language": "zh", "claims": [
        {"claim_id": "c", "text": "公司新产品进展。", "evidence_ids": ["e2", "e3"],
         "evidence_group_ids": ["g2"], "claim_type": "company_statement", "modality": "actual"}]}}
    draft = decode_model_draft(NarrativeModelResponse("fixture", "configured-flash", request.prompt_version,
                                                    canonical_json(response).encode()), selected=selected)
    assert draft["claims"][0]["evidence_ids"] == [span.span_id for span in selected.evidence_spans[1:]]
    response["draft"]["claims"][0]["evidence_ids"] = ["e2"]
    with pytest.raises(NarrativeContractError, match="group coverage is incomplete"):
        decode_model_draft(NarrativeModelResponse("fixture", "configured-flash", request.prompt_version,
                           canonical_json(response).encode()), selected=selected)


def test_strategy_and_group_changes_alter_actual_model_request_fingerprint():
    selected = with_reading()
    request = NarrativeModelRequest.from_selection(selected)
    for field in ("constraints", "groups"):
        wire = selected.to_dict()
        if field == "constraints":
            wire["reading_context"][field].append("Keep conditional qualifiers.")
        else:
            wire["reading_context"][field].pop()
        assert NarrativeModelRequest.from_selection(NarrativeSelectResult.from_dict(wire)).input_sha256 != request.input_sha256


def test_projection_accepts_reading_context_but_group_cannot_cross_original_parents():
    selected = official_selection()
    wire = selected.to_dict()
    context = reading_context(selected)
    context["groups"] = context["groups"][:1]
    wire["reading_context"] = context
    parsed = NarrativeSelectResult.from_dict(wire)
    assert "reading_strategy" in json.loads(NarrativeModelRequest.from_selection(parsed).data_json)
    context["groups"][0]["evidence_ids"] = [selected.evidence_spans[0].span_id, selected.evidence_spans[2].span_id]
    with pytest.raises(NarrativeContractError, match="parent"):
        NarrativeSelectResult.from_dict(wire)


def test_select_result_builder_passes_context_without_running_another_reading_engine():
    selected = with_reading()
    payload = SourceRevisionEventPayload.from_dict({"schema_version": "source-revision-event/2.0",
        "source_ref": selected.source_ref.to_dict(), "expected_read_policy_sha256": selected.expected_read_policy_sha256,
        "source_metadata": selected.source_metadata.to_dict()})
    package = SimpleNamespace(status="partial", coverage_complete=True, source_units=23,
        candidate_count=23, evidence_spans=selected.evidence_spans, omitted_candidate_count=20,
        dropped_financial_count=10, reading_context=selected.to_dict()["reading_context"], reading_dependencies=None)
    parsed = SimpleNamespace(page_count=3, pages_read=3, line_count=0, table_scan_pages=(), deferred_table_pages=())
    work = SimpleNamespace(parsed=parsed, package=package, material=None, parser_identity=("synthetic-parser", "1.0.0"))
    wire = NarrativeSelectHandler._result_dict(payload, selected.prompt_review, work, selector_version="0.9.0")
    assert NarrativeSelectResult.from_dict(wire).to_dict()["reading_context"] == package.reading_context


def test_verified_bundle_preserves_reading_strategy_for_artifact_cache_recovery():
    selected = with_reading()
    summarized = summary(selected)
    bundle = NarrativeVerifyHandler._bundle(selected, summarized, selected.prompt_review)
    wire = bundle.to_dict()
    assert wire["reading_context"] == selected.to_dict()["reading_context"]
    recovered = NarrativeBundle.from_dict(wire)
    recovered.validate_against(selected, summarized)
    wire["reading_context"]["constraints"].append("Altered after publication.")
    with pytest.raises(NarrativeContractError, match="selection"):
        NarrativeBundle.from_dict(wire).validate_against(selected, summarized)
    assert recovered.to_dict()["reading_context"] == selected.to_dict()["reading_context"]


def test_null_optional_strategy_is_omitted_for_legacy_wire():
    selected = selection()
    wire = selected.to_dict()
    wire["reading_context"] = None
    assert "reading_context" not in NarrativeSelectResult.from_dict(wire).to_dict()
    assert replace(selected, reading_context=None).to_dict() == selected.to_dict()


def test_actual_shared_engine_context_passes_formal_transport_at_48k_shared_budget(monkeypatch):
    from unit.document_understanding_selection.test_reading_production_selection import (
        _document, _package, _patch_reading, _select, _shared_projects, _unit,
    )

    _, footnote, first, second = _shared_projects()
    header = _unit("Unit and reporting period: " + "auxiliary qualification context " * 900)
    document = _document(header, footnote, first, second)
    _patch_reading(monkeypatch, document,
        packages=[_package("alpha", first, context=(header, footnote), kind="project"),
                  _package("beta", second, context=(header, footnote), kind="project")],
        priorities={first.unit_id: 1, second.unit_id: 1})
    package = _select(document, limit=4)
    base = selection(4)
    payload = base.to_dict()
    payload["source_ref"].update(source_id=package.source_id, content_sha256=package.source_sha256)
    event = SourceRevisionEventPayload.from_dict({"schema_version": "source-revision-event/2.0",
        "source_ref": payload["source_ref"], "source_metadata": payload["source_metadata"],
        "expected_read_policy_sha256": payload["expected_read_policy_sha256"]})
    work = SimpleNamespace(parsed=document, package=package, material=None,
                           parser_identity=("narrative-parser", "0.1.0"))
    wire = NarrativeSelectHandler._result_dict(event, base.prompt_review, work, selector_version="0.9.0")
    selected = NarrativeSelectResult.from_dict(wire)
    data = json.loads(NarrativeModelRequest.from_selection(selected).data_json)
    assert len(data["evidence"]) == 4 and len(data["evidence_groups"]) == 2
    assert [row[1] for row in data["evidence"]] == [unit.raw_text for unit in document.units]
    assert sum(len(row[1]) for row in data["evidence"]) < 48000
    assert data["reading_strategy"]["reading_policy_version"].startswith("du-sent-policy/1+")
    assert len(data["reading_strategy"]["reading_policy_version"].split("+")[1]) == 64
    assert data["reading_strategy"]["reading_policies"] == package.reading_context["reading_policies"]
    assert "wrong_assertion" not in canonical_json(data)


def test_context_depth_cap_applies_before_any_unbounded_path_walk():
    selected = selection(3)
    wire = selected.to_dict()
    wire["reading_context"] = reading_context(selected)
    nested = "untrusted"
    for _ in range(1500):
        nested = {"child": nested}
    wire["reading_context"]["layout_coverage"] = nested
    with pytest.raises(NarrativeContractError, match="structural bound"):
        NarrativeSelectResult.from_dict(wire)


def test_model_boundary_cannot_send_synthetic_examples_from_direct_dataclass_replacement():
    selected = with_reading()
    changed = selected.to_dict()["reading_context"]
    changed["business_facets"][0]["confusion_checks"][0]["wrong_assertion"] = "invented source fact"
    with pytest.raises(NarrativeContractError, match="forbidden"):
        NarrativeModelRequest.from_selection(replace(selected, reading_context=changed))


@pytest.mark.parametrize("mutation", [None, "count_too_small", "false_complete", "missing_count", "missing_limited"])
def test_unread_diagnostic_samples_preserve_full_counts_and_honest_limitation(mutation):
    selected = with_reading()
    wire = selected.to_dict()
    unread = wire["reading_context"]["unread"]
    unread.update(unassigned_unit_ids=["sample-only"],
        counts={"opaque_pages": 0, "deferred_pages": 0, "deferred_unit_ids": 0, "unassigned_unit_ids": 28000},
        limited=True)
    if mutation == "count_too_small":
        unread["counts"]["unassigned_unit_ids"] = 0
    elif mutation == "false_complete":
        unread["limited"] = False
    elif mutation == "missing_count":
        unread["counts"].pop("deferred_unit_ids")
    elif mutation == "missing_limited":
        unread.pop("limited")
    if mutation:
        with pytest.raises(NarrativeContractError):
            NarrativeSelectResult.from_dict(wire)
    else:
        restored = NarrativeSelectResult.from_dict(wire)
        strategy = json.loads(NarrativeModelRequest.from_selection(restored).data_json)["reading_strategy"]
        assert strategy["unread"] == unread
        assert len(strategy["unread"]["unassigned_unit_ids"]) == 1
        assert strategy["unread"]["counts"]["unassigned_unit_ids"] == 28000


def test_projection_verified_bundle_roundtrip_keeps_parent_scoped_reading_groups():
    base = official_selection()
    wire = base.to_dict()
    context = reading_context(base)
    context["groups"][1]["evidence_ids"] = [base.evidence_spans[2].span_id]
    wire["reading_context"] = context
    selected = NarrativeSelectResult.from_dict(wire)
    span = selected.evidence_spans[1]
    summarized = NarrativeSummaryResult.from_dict({
        "schema_version": "narrative-summary-result/3.0", "subject_binding": selected.subject.to_dict(),
        "language": "en", "translate": False, "status": "completed",
        "draft": {"subject_id": selected.subject.item_key, "subject_sha256": selected.subject.subject_sha256,
            "language": "en", "claims": [{"claim_id": "c", "text": span.raw_text,
                "evidence_ids": [span.span_id], "claim_type": "company_statement", "modality": "actual",
                "needs_review": False}], "status": "draft"},
        "model": {"adapter_id": "fixture", "model_id": "configured-flash",
            "prompt_version": "official-json/1.0.0", "response_sha256": "c" * 64},
        "prompt_review": selected.prompt_review.to_dict(),
    })
    bundle = NarrativeVerifyHandler._bundle(selected, summarized, selected.prompt_review)
    restored = NarrativeBundle.from_dict(bundle.to_dict())
    restored.validate_against(selected, summarized)
    assert restored.reading_context == selected.reading_context
    assert restored.to_dict()["reading_context"]["groups"] == context["groups"]
