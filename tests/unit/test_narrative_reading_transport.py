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


def public_select_wire(package, document):
    base = selection(4)
    payload = base.to_dict()
    payload["source_ref"].update(
        source_id=package.source_id,
        content_sha256=package.source_sha256,
    )
    event = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0",
        "source_ref": payload["source_ref"],
        "source_metadata": payload["source_metadata"],
        "expected_read_policy_sha256": payload["expected_read_policy_sha256"],
    })
    parsed = SimpleNamespace(
        page_count=document.page_count,
        pages_read=document.pages_read,
        line_count=0,
        table_scan_pages=(),
        deferred_table_pages=(),
    )
    work = SimpleNamespace(
        parsed=parsed,
        package=package,
        material=None,
        parser_identity=("narrative-parser", "0.1.0"),
    )
    return NarrativeSelectHandler._result_dict(
        event, base.prompt_review, work, selector_version="0.9.0"
    )


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


def test_reading_context_group_identity_preserves_semantics_and_deduplicates_exact_rows(monkeypatch):
    from company_wiki.source_catalog import narrative_reading

    base = selection(3)
    unit_ids = [
        f"urn:company-wiki:narrative-unit:sha256:{index:064x}"
        for index in range(1, len(base.evidence_spans) + 1)
    ]
    selected_span_ids = {
        unit_id: span.span_id
        for unit_id, span in zip(unit_ids, base.evidence_spans, strict=True)
    }
    monkeypatch.setattr(
        narrative_reading,
        "_sent_policies",
        lambda pipeline, entries: ([], [], "du-sent-policy/1+" + "f" * 64),
    )
    monkeypatch.setattr(
        narrative_reading,
        "_unread",
        lambda structure, observation: {
            "native_scan": "complete",
            "opaque_pages": [],
            "deferred_pages": [],
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
            "structure_complete": True,
        },
    )
    pipeline = {
        "observation": {"units": [{"unit_id": uid, "role": "management"} for uid in unit_ids]},
        "selected_span_ids": selected_span_ids,
        "structure": {},
        "layout_hints": {},
    }
    shared = {
        "member_unit_ids": unit_ids,
        "required_context_unit_ids": [],
        "truncated": False,
    }
    eligible = [
        {"package_id": "risk-1", "kind": "risk", "section_role": "operating_metrics",
         **shared, "anchor_unit_ids": [unit_ids[0]],
         "citation_support_views": [[unit_ids[0]]]},
        {"package_id": "native-1", "kind": "native_continuity", "section_role": "unknown",
         **shared, "anchor_unit_ids": [unit_ids[1]],
         "citation_support_views": [[unit_ids[1]]]},
        {"package_id": "risk-duplicate", "kind": "risk", "section_role": "operating_metrics",
         **shared, "anchor_unit_ids": [unit_ids[0]],
         "citation_support_views": [[unit_ids[0]]]},
        {"package_id": "risk-other-role", "kind": "risk", "section_role": "business",
         **shared, "anchor_unit_ids": [unit_ids[0]],
         "citation_support_views": [[unit_ids[0]]]},
        {"package_id": "risk-other-view", "kind": "risk", "section_role": "operating_metrics",
         **shared, "anchor_unit_ids": [unit_ids[0]],
         "citation_support_views": [[unit_ids[0], unit_ids[1]]]},
    ]

    context = narrative_reading._context(
        pipeline, SimpleNamespace(evidence_spans=base.evidence_spans), eligible
    )
    groups = context["groups"]
    assert len(groups) == 4
    assert len({group["group_id"] for group in groups}) == 4
    assert {group["kind"] for group in groups} == {"risk", "native_continuity"}

    wire = base.to_dict()
    full_context = reading_context(base)
    full_context["schema_version"] = "du-production-reading/2"
    full_context["groups"] = groups
    wire["reading_context"] = full_context
    selected = NarrativeSelectResult.from_dict(wire)
    request = NarrativeModelRequest.from_selection(selected)
    assert len(json.loads(request.data_json)["evidence_groups"]) == 4


def test_public_reading_transport_preserves_bounded_native_page_proofs_without_sending_them_to_model():
    base = selection(3)
    wire = base.to_dict()
    context = reading_context(base)
    context["schema_version"] = "du-production-reading/2"
    ids = [span.span_id for span in base.evidence_spans]
    proof_units = [
        f"urn:company-wiki:narrative-unit:sha256:{index:064x}"
        for index in (101, 102, 103)
    ]
    context["groups"] = [{
        "group_id": "urn:company-wiki:reading-group:sha256:" + "a" * 64,
        "kind": "native_continuity",
        "section_role": "business",
        "evidence_ids": ids[:2],
        "citation_views": [{"support_evidence_ids": ids[:1], "context_evidence_ids": ids[1:2]}],
        "source_proof_unit_ids": [proof_units[0], proof_units[2]],
        "source_proof_target_unit_ids": [proof_units[1]],
        "source_proofs": [{
            "basis": "observed_adjacent_page_flow",
            "left": proof_units[0], "right": proof_units[1],
            "left_page": 1, "right_page": 2,
            "left_ordinal": 1, "right_ordinal": 2,
            "column": 0, "coordinate_frame": "pdf_page",
            "furniture_unit_ids": [proof_units[2]],
        }],
    }]
    wire["reading_context"] = context

    selected = NarrativeSelectResult.from_dict(wire)
    request = NarrativeModelRequest.from_selection(selected)

    assert selected.to_dict()["reading_context"]["groups"][0]["source_proofs"] == context["groups"][0]["source_proofs"]
    assert "source_proofs" not in request.data_json
    assert "source_proof_unit_ids" not in request.data_json
    assert "source_proof_target_unit_ids" not in request.data_json


def test_public_reading_transport_rejects_native_proof_with_an_unbound_endpoint():
    base = selection(3)
    wire = base.to_dict()
    context = reading_context(base)
    context["schema_version"] = "du-production-reading/2"
    ids = [span.span_id for span in base.evidence_spans]
    left = f"urn:company-wiki:narrative-unit:sha256:{201:064x}"
    right = f"urn:company-wiki:narrative-unit:sha256:{202:064x}"
    target = f"urn:company-wiki:narrative-unit:sha256:{203:064x}"
    context["groups"] = [{
        "group_id": "urn:company-wiki:reading-group:sha256:" + "b" * 64,
        "kind": "native_continuity",
        "section_role": "business",
        "evidence_ids": ids[:2],
        "citation_views": [{"support_evidence_ids": ids[:1], "context_evidence_ids": ids[1:2]}],
        "source_proof_unit_ids": [left],
        "source_proof_target_unit_ids": [target],
        "source_proofs": [{
            "basis": "observed_adjacent_page_flow",
            "left": left, "right": right,
            "left_page": 1, "right_page": 2,
            "left_ordinal": 1, "right_ordinal": 2,
            "column": 0, "coordinate_frame": "pdf_page",
            "furniture_unit_ids": [],
        }],
    }]
    wire["reading_context"] = context

    with pytest.raises(NarrativeContractError, match="proof endpoints are invalid"):
        NarrativeSelectResult.from_dict(wire)


def test_reading_context_unread_samples_are_bounded_and_keep_full_counts(monkeypatch):
    from company_wiki.source_catalog import narrative_reading

    base = selection(3)
    unit_ids = [
        f"urn:company-wiki:narrative-unit:sha256:{index:064x}"
        for index in range(1, len(base.evidence_spans) + 1)
    ]
    unread = {
        "native_scan": "partial",
        "opaque_pages": list(range(1, 141)),
        "deferred_pages": list(range(1, 141)),
        "deferred_unit_ids": unit_ids * 47,
        "unassigned_unit_ids": unit_ids * 47,
        "structure_complete": False,
    }
    monkeypatch.setattr(
        narrative_reading,
        "_sent_policies",
        lambda pipeline, entries: ([], [], "du-sent-policy/1+" + "f" * 64),
    )
    monkeypatch.setattr(narrative_reading, "_unread", lambda structure, observation: unread)
    pipeline = {
        "observation": {"units": [{"unit_id": uid, "role": "management"} for uid in unit_ids]},
        "selected_span_ids": {
            uid: span.span_id for uid, span in zip(unit_ids, base.evidence_spans, strict=True)
        },
        "structure": {},
        "layout_hints": {},
    }

    context = narrative_reading._context(
        pipeline, SimpleNamespace(evidence_spans=base.evidence_spans), []
    )
    assert len(context["unread"]["opaque_pages"]) == 32
    assert len(context["unread"]["deferred_pages"]) == 32
    assert len(context["unread"]["deferred_unit_ids"]) == 32
    assert len(context["unread"]["unassigned_unit_ids"]) == 32
    assert context["unread"]["counts"] == {
        "opaque_pages": 140,
        "deferred_pages": 140,
        "deferred_unit_ids": len(unit_ids) * 47,
        "unassigned_unit_ids": len(unit_ids) * 47,
    }
    assert context["unread"]["limited"] is True


def test_deferred_diagnostics_keep_reference_rows_first_and_bound_samples():
    from company_wiki.source_catalog.narrative_reading import _sample_deferred

    references = [{"package_id": f"reference-{index}", "reason": "REFERENCE_UNRESOLVED"}
                  for index in range(40)]
    selected = [{"package_id": f"selector-{index}", "reason": "SELECTION_BUDGET"}
                for index in range(30)]
    other = [{"package_id": f"other-{index}", "reason": "OTHER"} for index in range(30)]

    sample, count, limited = _sample_deferred(references, selected, other)

    assert count == 100
    assert limited is True
    assert sample[0] == references[0]
    assert any(row["reason"] == "SELECTION_BUDGET" for row in sample)
    assert any(row["reason"] == "OTHER" for row in sample)
    assert len(sample) == 32


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


def test_actual_shared_engine_budget_diagnostics_survive_public_result_roundtrip(monkeypatch):
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
    package = _select(document, limit=3)
    budget_row = package.reading_context["selection_diagnostics"][0]
    assert {key: value for key, value in budget_row.items() if key not in {"targets", "targets_limited"}} == {
        "code": "budget_full", "count": 1, "phase": "selection",
        "external_model_cost": False, "dimension": "selection_spans", "used": 3, "limit": 3,
    }
    assert len(budget_row["targets"]) == 1 and budget_row["targets_limited"] is False
    assert budget_row["targets"][0]["used"] + budget_row["targets"][0]["requested"] > budget_row["targets"][0]["limit"]

    base = selection(4)
    payload = base.to_dict()
    payload["source_ref"].update(source_id=package.source_id, content_sha256=package.source_sha256)
    event = SourceRevisionEventPayload.from_dict({"schema_version": "source-revision-event/2.0",
        "source_ref": payload["source_ref"], "source_metadata": payload["source_metadata"],
        "expected_read_policy_sha256": payload["expected_read_policy_sha256"]})
    work = SimpleNamespace(parsed=document, package=package, material=None,
                           parser_identity=("narrative-parser", "0.1.0"))
    wire = NarrativeSelectHandler._result_dict(event, base.prompt_review, work, selector_version="0.9.0")
    restored = NarrativeSelectResult.from_dict(wire)
    restored_context = restored.to_dict()["reading_context"]
    assert restored_context["selection_diagnostics"] == package.reading_context["selection_diagnostics"]
    assert restored_context["selection_trace"]["selected"]["samples"]
    assert all(row["span_id"] in {span.span_id for span in package.evidence_spans}
               for row in restored_context["selection_trace"]["selected"]["samples"])
    trace = restored_context["selection_trace"]
    invalid_counts = (len(package.evidence_spans) - 1, trace["source_unit_count"] + 1)
    for invalid_count in invalid_counts:
        malformed_trace = deepcopy(wire)
        selected_trace = malformed_trace["reading_context"]["selection_trace"]["selected"]
        selected_trace["count"] = invalid_count
        if invalid_count < len(package.evidence_spans):
            selected_trace["samples"] = []
        selected_trace["limited"] = invalid_count > len(selected_trace["samples"])
        with pytest.raises(NarrativeContractError, match="selected count"):
            NarrativeSelectResult.from_dict(malformed_trace)
    model_strategy = json.loads(NarrativeModelRequest.from_selection(
        restored, reading_projection_version="reading-model-input/1").data_json)["reading_strategy"]
    assert "selection_diagnostics" not in model_strategy
    assert "selection_trace" not in model_strategy

    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_reading import _document_work_diagnostic

    work_wire = deepcopy(wire)
    work_wire["reading_context"]["selection_diagnostics"] = [
        _document_work_diagnostic(WorkBudget(3, used=1, exhausted=True, phase="candidate_scan"))
    ]
    work_result = NarrativeSelectResult.from_dict(work_wire)
    assert work_result.to_dict()["reading_context"]["selection_diagnostics"] == work_wire["reading_context"]["selection_diagnostics"]
    unsafe_detail = deepcopy(work_wire)
    unsafe_detail["reading_context"]["selection_diagnostics"][0]["detail"] = "source: C:/private/report.pdf"
    with pytest.raises(NarrativeContractError, match="fixed safe message"):
        NarrativeSelectResult.from_dict(unsafe_detail)

    zero_limit_wire = deepcopy(wire)
    zero_limit_wire["reading_context"]["selection_diagnostics"] = [
        _document_work_diagnostic(WorkBudget(0, exhausted=True, phase="document"))
    ]
    zero_limit_result = NarrativeSelectResult.from_dict(zero_limit_wire)
    assert zero_limit_result.to_dict()["reading_context"]["selection_diagnostics"][0]["limit"] == 0

    malformed = deepcopy(wire)
    malformed["reading_context"]["selection_diagnostics"][0]["unreviewed_field"] = "ignored"
    with pytest.raises(NarrativeContractError, match="unknown fields"):
        NarrativeSelectResult.from_dict(malformed)
    malformed = deepcopy(wire)
    malformed["reading_context"]["selection_diagnostics"][0]["dimension"] = []
    with pytest.raises(NarrativeContractError, match="dimension"):
        NarrativeSelectResult.from_dict(malformed)
    malformed = deepcopy(wire)
    malformed["reading_context"]["selection_diagnostics"][0]["count"] = 0
    with pytest.raises(NarrativeContractError, match="count"):
        NarrativeSelectResult.from_dict(malformed)
    malformed = deepcopy(wire)
    malformed["reading_context"]["selection_diagnostics"][0]["dimension"] = "selection_characters"
    with pytest.raises(NarrativeContractError, match="code and dimension"):
        NarrativeSelectResult.from_dict(malformed)
    malformed = deepcopy(wire)
    malformed["reading_context"]["selection_diagnostics"][0]["used"] = 4
    with pytest.raises(NarrativeContractError, match="exceeds limit"):
        NarrativeSelectResult.from_dict(malformed)


def test_zero_character_budget_diagnostics_survive_public_result_roundtrip(monkeypatch):
    from unit.document_understanding_selection.test_reading_production_selection import (
        _document, _package, _patch_reading, _shared_projects,
    )
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence

    _, _, first, second = _shared_projects()
    document = _document(first, second)
    _patch_reading(monkeypatch, document, packages=[
        _package("first-project", first, kind="project"),
        _package("second-project", second, kind="project"),
    ])
    package = select_reading_evidence(document, title="Annual report", max_chars=0)
    diagnostic = next(row for row in package.selection_diagnostics
                      if row["code"] == "character_budget")
    assert diagnostic["used"] == diagnostic["limit"] == 0
    assert diagnostic["targets"] and all(row["limit"] == 0 for row in diagnostic["targets"])

    restored = NarrativeSelectResult.from_dict(public_select_wire(package, document))
    assert restored.to_dict()["reading_context"]["selection_diagnostics"] == list(
        package.reading_context["selection_diagnostics"]
    )


def test_zero_document_work_budget_stops_safely_at_public_result_boundary():
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence
    from unit.document_understanding_selection.test_reading_production_selection import (
        _document, _unit,
    )

    document = _document(_unit("Business activity was described in this filing."))
    package = select_reading_evidence(
        document, title="Annual report", work_budget=WorkBudget(0)
    )
    assert package.status == "needs_review"
    assert package.selection_diagnostics[0]["dimension"] == "document_work"
    assert package.selection_diagnostics[0]["limit"] == 0

    wire = public_select_wire(package, document)
    assert wire["schema_version"] == "narrative-select-result/2.1"
    result = NarrativeSelectResult.from_dict(wire)
    assert result.selection.status == "needs_review"
    assert result.evidence_spans == ()
    assert [dict(row) for row in result.selection_diagnostics] == list(package.selection_diagnostics)


def test_group_closure_limit_has_correct_dimension_through_public_result(monkeypatch):
    from unit.document_understanding_selection.test_reading_production_selection import (
        _document, _package, _patch_reading, _select, _shared_projects, _unit,
    )

    _, footnote, first, second = _shared_projects()
    header = _unit("Unit and reporting period: project qualification context")
    document = _document(header, footnote, first, second)
    _patch_reading(
        monkeypatch, document,
        packages=[
            _package("alpha", first, context=(header, footnote), kind="project"),
            _package("beta", second, context=(header, footnote), kind="project"),
        ],
        priorities={first.unit_id: 1, second.unit_id: 1},
    )
    package = _select(document, limit=1)
    rows = package.reading_context["selection_diagnostics"]
    group_row = next(row for row in rows if row["code"] == "group_exceeds_limit")
    assert group_row["dimension"] == "selection_spans"
    assert group_row["limit"] == package.selection_limit
    assert group_row["max_closure_size"] > group_row["limit"]
    assert group_row["targets"] and all(
        row["closure_size"] > row["limit"] for row in group_row["targets"]
    )

    result = NarrativeSelectResult.from_dict(public_select_wire(package, document))
    public = result.to_dict()
    assert public["reading_context"]["selection_diagnostics"] == rows
    context = public["reading_context"]
    assert context["schema_version"] == "du-production-reading/3"
    trace = context["selection_trace"]
    assert trace["schema_version"] == "selection-trace/1"
    assert trace["selected"]["count"] == len(package.evidence_spans)
    assert trace["selected"]["samples"] == []
    assert trace["admission"]["count"] >= 1
    assert trace["admission"]["count"] >= trace["admission"]["admitted_count"]
    assert trace["admission"]["count"] >= trace["admission"]["rejected_count"]
    assert all(row["selected_span_id"] is None or row["selected_span_id"] in {
        span.span_id for span in package.evidence_spans
    } for row in trace["admission"]["samples"])
    assert not package.evidence_spans
    forged_selected = deepcopy(public)
    forged_trace = forged_selected["reading_context"]["selection_trace"]["selected"]
    forged_trace.update(count=1, limited=True)
    with pytest.raises(NarrativeContractError, match="selected count"):
        NarrativeSelectResult.from_dict(forged_selected)
    legacy_strategy = json.loads(NarrativeModelRequest.from_selection(result).data_json)["reading_strategy"]
    assert "selection_trace" not in legacy_strategy
    assert "selection_diagnostics" not in legacy_strategy


def test_trace_separates_semantic_reject_defer_and_budget_omission(monkeypatch):
    from unit.document_understanding_selection.test_reading_production_selection import (
        _document, _package, _patch_reading, _select, _unit,
    )

    bare_number = _unit("2025 300 400", page=1)
    first = _unit("Our water treatment project entered customer qualification.", page=2)
    second = _unit("Our recycling service expanded into a second operating region.", page=3)
    missing_reference = _unit("These products have not obtained customer certification.", page=4)
    document = _document(bare_number, first, second, missing_reference)
    _patch_reading(
        monkeypatch, document,
        packages=[
            _package("bare-number", bare_number),
            _package("first-project", first),
            _package("second-project", second),
            _package("missing-reference", missing_reference, kind="project"),
        ],
        priorities={first.unit_id: 1, second.unit_id: 2, missing_reference.unit_id: 3},
    )
    package = _select(document, limit=1)
    trace = package.reading_context["selection_trace"]
    assert trace["admission"]["rejection_counts"]
    assert trace["admission"]["rejected_count"] >= 1
    assert any(row["reason"] == "REFERENCE_UNRESOLVED" for row in trace["withheld"]["samples"]), trace["withheld"]
    budget = next(row for row in package.selection_diagnostics if row["code"] == "budget_full")
    selected_ids = {row["unit_id"] for row in trace["selected"]["samples"]}
    omitted_ids = {
        item_id for target in budget["targets"] for item_id in target["item_ids"]
    } | {target["item_id"] for target in budget["targets"]}
    assert omitted_ids - selected_ids

    restored = NarrativeSelectResult.from_dict(public_select_wire(package, document))
    model = json.loads(NarrativeModelRequest.from_selection(restored).data_json)
    sent_text = {row[1] for row in model["evidence"]}
    assert sent_text == {span.raw_text for span in package.evidence_spans}
    assert "selection_trace" not in model["reading_strategy"]

    inconsistent_admission = public_select_wire(package, document)
    admission = inconsistent_admission["reading_context"]["selection_trace"]["admission"]
    admission.update(admitted_count=0, rejected_count=admission["count"],
                     rejection_counts={"FORGED_REJECTION": admission["count"]})
    with pytest.raises(NarrativeContractError, match="sample exceeds aggregate"):
        NarrativeSelectResult.from_dict(inconsistent_admission)


def test_selection_trace_schema_rejects_raw_text_and_false_sample_counts():
    selected = with_reading()
    wire = selected.to_dict()
    context = wire["reading_context"]
    context["schema_version"] = "du-production-reading/3"
    context["deferred"] = []
    context["deferred_count"] = 0
    context["deferred_limited"] = False
    context["selection_diagnostics"] = []
    for group in context["groups"]:
        group["citation_views"] = [{
            "support_evidence_ids": group["evidence_ids"][:1],
            "context_evidence_ids": group["evidence_ids"][1:],
        }]
    context["selection_trace"] = {
        "schema_version": "selection-trace/1",
        "source_unit_count": 1,
        "admission": {
            "count": 1,
            "admitted_count": 1,
            "rejected_count": 0,
            "limited": False,
            "rejection_counts": {},
            "samples": [{
                "unit_id": "not-an-id", "package_ref": "not-a-ref", "status": "admitted",
                "reason": None, "fact_purpose": "operating", "fact_reasons": [],
                "fact_reason_count": 0, "fact_reasons_limited": False,
                "required_unit_ids": [], "required_unit_count": 0,
                "required_unit_ids_limited": False, "priority": 1, "selected_span_id": None,
            }],
        },
        "eligible_packages": {"count": 0, "limited": False, "samples": []},
        "withheld": {"count": 0, "limited": False, "samples": []},
        "selected": {"count": 0, "limited": False, "samples": []},
    }
    with pytest.raises(NarrativeContractError, match="unit ID"):
        NarrativeSelectResult.from_dict(wire)

    trace = context["selection_trace"]
    trace["admission"]["samples"][0]["unit_id"] = "urn:company-wiki:narrative-unit:sha256:" + "1" * 64
    trace["admission"]["samples"][0]["package_ref"] = "urn:company-wiki:reading-package:sha256:" + "a" * 64
    trace["admission"]["count"] = 0
    trace["admission"]["admitted_count"] = 0
    with pytest.raises(NarrativeContractError, match="sample count"):
        NarrativeSelectResult.from_dict(wire)


@pytest.mark.parametrize("mutation, error", [
    ("parent_limit", "target limit differs"),
    ("max_closure", "maximum closure size is inconsistent"),
    ("sample_count", "target sample exceeds its count"),
    ("limited_flag", "target sample count is inconsistent"),
    ("raw_identifier", "target ID is invalid"),
    ("raw_locator", "target locator is invalid"),
    ("traversal_locator", "target locator is invalid"),
    ("path_style_locator", "target locator is invalid"),
])
def test_group_diagnostic_rejects_inconsistent_or_unbounded_samples(monkeypatch, mutation, error):
    from unit.document_understanding_selection.test_reading_production_selection import (
        _document, _package, _patch_reading, _select, _shared_projects, _unit,
    )

    _, footnote, first, second = _shared_projects()
    header = _unit("Unit and reporting period: project qualification context")
    document = _document(header, footnote, first, second)
    _patch_reading(
        monkeypatch, document,
        packages=[
            _package("alpha", first, context=(header, footnote), kind="project"),
            _package("beta", second, context=(header, footnote), kind="project"),
        ],
        priorities={first.unit_id: 1, second.unit_id: 1},
    )
    package = _select(document, limit=1)
    wire = public_select_wire(package, document)
    diagnostic = next(
        row for row in wire["reading_context"]["selection_diagnostics"]
        if row["code"] == "group_exceeds_limit"
    )
    target = diagnostic["targets"][0]
    if mutation == "parent_limit":
        target["limit"] += 1
    elif mutation == "max_closure":
        target["closure_size"] += 1
    elif mutation == "sample_count":
        diagnostic["targets"].append(deepcopy(target))
    elif mutation == "limited_flag":
        diagnostic["targets_limited"] = True
    elif mutation == "raw_identifier":
        target["item_id"] = "untrusted source text"
    elif mutation == "raw_locator":
        target["locator"] = "relative/source.pdf"
    elif mutation == "traversal_locator":
        target["locator"] = "loc:v1/../../private/source.pdf"
    elif mutation == "path_style_locator":
        target["locator"] = "loc:v1|relative/source.pdf"

    with pytest.raises(NarrativeContractError, match=error):
        NarrativeSelectResult.from_dict(wire)


def test_select_result_rejects_diagnostics_split_across_two_public_fields():
    selected = with_reading()
    wire = selected.to_dict()
    wire["selection_diagnostics"] = [{"code": "DECISION_DEPENDENCIES_UNAVAILABLE", "count": 1}]
    with pytest.raises(NarrativeContractError, match="cannot be split"):
        NarrativeSelectResult.from_dict(wire)


@pytest.mark.parametrize(("code", "limit", "closure_size"), [
    ("budget_full", 112, 1),
    ("character_budget", 105, 1),
    ("group_exceeds_limit", 112, 113),
])
def test_selection_diagnostic_target_rejects_used_above_limit(code, limit, closure_size):
    from company_wiki.automation.narrative_contracts import _selection_diagnostic_target

    target = {
        "item_id": "urn:company-wiki:narrative-unit:sha256:" + "a" * 64,
        "item_ids": [], "item_count": 1, "item_ids_limited": True,
        "group_id": None, "locator": "loc:v1/page:1",
        "used": limit + 1, "requested": 1, "limit": limit,
        "closure_size": closure_size,
    }
    with pytest.raises(NarrativeContractError, match="used exceeds its limit"):
        _selection_diagnostic_target(target, code=code)


def test_select_result_reader_keeps_previous_minor_schema_compatible():
    wire = selection(3).to_dict()
    assert wire["schema_version"] == "narrative-select-result/2.0"
    restored = NarrativeSelectResult.from_dict(wire)
    assert restored.to_dict()["schema_version"] == "narrative-select-result/2.0"


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
