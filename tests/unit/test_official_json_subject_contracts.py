"""New projection semantics never masquerade as the old single-source DTOs."""

from copy import deepcopy
import json

import pytest

from company_wiki.automation.narrative_official_json import (
    VerifiedProjectionView,
    select_verified_projection,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult,
    NarrativeSummaryResult,
    NarrativeBundle,
    NarrativeContractError,
)
from unit.test_official_json_narrative_adapter import source_export


def selection():
    projection, export = source_export()
    view = VerifiedProjectionView(json.dumps(export, ensure_ascii=False))
    package = select_verified_projection(view, title="Business development Q&A")
    parser_span = view.evidence_spans[0]
    return {
        "schema_version": "narrative-select-result/3.0",
        "subject_binding": view.subject.to_dict(),
        "source_metadata": {
            "source_class": "official_json",
            "title": "Business development Q&A",
            "document_kind": "investor_relations",
            "language": view.language,
        },
        "parser": {
            "name": parser_span.parser_name,
            "version": parser_span.parser_version,
        },
        "selector": {"name": "narrative-selector", "version": "1.0.0"},
        "selection": {
            "status": package.status,
            "coverage_complete": package.coverage_complete,
            "source_units": package.source_units,
            "candidate_count": package.candidate_count,
            "selected_count": len(package.evidence_spans),
            "omitted_candidate_count": package.omitted_candidate_count,
            "dropped_financial_count": package.dropped_financial_count,
            "pages_total": 1,
            "pages_read": 1,
            "lines_total": len(view.evidence_spans),
            "tables_total": 0,
            "tables_scanned": 0,
        },
        "evidence_spans": [span.to_dict() for span in package.evidence_spans],
        "prompt_review": {
            "status": "not_reviewed",
            "source_sha256": None,
            "evidence_sha256": None,
            "policy_hash": None,
            "reviewed_at": None,
        },
        "summary_scope": "selected_evidence_only",
    }


def summary(selected=None):
    selected = selection() if selected is None else selected
    answer = next(
        span
        for span in selected["evidence_spans"]
        if span["structured_value"]["source_role"] in {"management", "company_filing"}
    )
    s = selected["subject_binding"]
    return {
        "schema_version": "narrative-summary-result/3.0",
        "subject_binding": deepcopy(s),
        "language": selected["source_metadata"]["language"],
        "translate": False,
        "status": "completed",
        "draft": {
            "subject_id": s["item_key"],
            "subject_sha256": s["subject_sha256"],
            "language": selected["source_metadata"]["language"],
            "status": "draft",
            "claims": [
                {
                    "claim_id": "business-update",
                    "text": "新产品客户验证完成，计划四季度批量交付。",
                    "evidence_ids": [answer["span_id"]],
                    "claim_type": "company_statement",
                    "modality": "planned",
                    "needs_review": False,
                }
            ],
        },
        "model": {
            "adapter_id": "synthetic-local-model",
            "model_id": "synthetic-local",
            "prompt_version": "official-json/1.0.0",
            "response_sha256": "a" * 64,
        },
        "prompt_review": deepcopy(selected["prompt_review"]),
    }


def bundle(selected=None, summarized=None):
    selected = selection() if selected is None else selected
    summarized = summary(selected) if summarized is None else summarized
    return {
        "schema_version": "narrative-bundle/3.0",
        "subject_binding": deepcopy(selected["subject_binding"]),
        "source_metadata": deepcopy(selected["source_metadata"]),
        "quality_status": "verified",
        "selection": deepcopy(selected["selection"]),
        "evidence_spans": deepcopy(selected["evidence_spans"]),
        "summary": {
            key: deepcopy(summarized[key])
            for key in ("status", "translate", "draft", "model")
        },
        "prompt_review": deepcopy(selected["prompt_review"]),
        "versions": {
            "parser": selected["parser"]["version"],
            "selector": selected["selector"]["version"],
            "material": None,
            "model": "synthetic-local",
            "prompt": "official-json/1.0.0",
            "bundle_producer": "1.0.0",
        },
        "replay": {"required": True, "locator_count": len(selected["evidence_spans"])},
    }


def test_selected_native_fields_bind_projection_and_each_real_parent():
    raw = selection()
    selected = NarrativeSelectResult.from_dict(raw)
    assert selected.to_dict() == raw
    assert selected.subject.item_key == raw["subject_binding"]["item_key"]
    assert selected.item_key == selected.subject.item_key
    assert selected.source_ref.to_dict() == selected.subject.anchor_ref
    assert selected.expected_read_policy_sha256 is None
    assert {
        span.structured_value["source_role"] for span in selected.evidence_spans
    } == {"management", "investor_question"}
    assert "source_ref" not in selected.to_dict()


def test_summary_draft_uses_explicit_subject_identity_and_shared_claim_validation():
    raw = selection()
    selected = NarrativeSelectResult.from_dict(raw)
    output = summary(raw)
    summarized = NarrativeSummaryResult.from_dict(output)
    summarized.validate_against(selected)
    assert summarized.to_dict() == output
    assert summarized.subject == selected.subject
    assert summarized.draft.subject_id == selected.item_key
    assert not hasattr(summarized.draft, "source_id")


def test_bundle_round_trip_binds_whole_subject_and_dependencies():
    raw = selection()
    summarized = summary(raw)
    output = bundle(raw, summarized)
    selected = NarrativeSelectResult.from_dict(raw)
    summary_value = NarrativeSummaryResult.from_dict(summarized)
    result = NarrativeBundle.from_dict(output)
    result.validate_against(selected, summary_value)
    assert result.to_dict() == output and result.subject == selected.subject
    assert "source_ref" not in result.to_dict()


@pytest.mark.parametrize(
    "bad", ["parent", "projection", "fake_ref", "transcript", "language"]
)
def test_bad_selected_identity_is_refused_as_contract_consistency(bad):
    raw = selection()
    if bad == "parent":
        raw["evidence_spans"][0]["source_id"] = (
            "urn:company-wiki:source:sha256:" + "f" * 64
        )
    elif bad == "projection":
        raw["evidence_spans"][0]["structured_value"]["projection_id"] = "urn:wrong"
    elif bad == "fake_ref":
        raw["source_ref"] = raw["subject_binding"]["parent_source_refs"][0]
    elif bad == "transcript":
        raw["source_metadata"]["source_class"] = "transcript"
    else:
        raw["source_metadata"]["language"] = "invalid"
    with pytest.raises(ValueError):
        NarrativeSelectResult.from_dict(raw)


@pytest.mark.parametrize(
    "bad", ["raw_header", "wrong_subject", "wrong_language", "question_as_statement"]
)
def test_wrong_summary_header_or_role_cannot_be_accepted(bad):
    raw = selection()
    selected = NarrativeSelectResult.from_dict(raw)
    output = summary(raw)
    if bad == "raw_header":
        output["draft"]["source_id"] = output["draft"].pop("subject_id")
        output["draft"]["source_sha256"] = output["draft"].pop("subject_sha256")
    elif bad == "wrong_subject":
        output["draft"]["subject_id"] = "urn:wrong"
    elif bad == "wrong_language":
        output["draft"]["language"] = "en"
    else:
        question = next(
            span
            for span in raw["evidence_spans"]
            if span["structured_value"]["source_role"] == "investor_question"
        )
        output["draft"]["claims"][0]["evidence_ids"] = [question["span_id"]]
    with pytest.raises(NarrativeContractError):
        NarrativeSummaryResult.from_dict(output).validate_against(selected)


@pytest.mark.parametrize(
    "schema,parser",
    [
        ("narrative-select-result/2.0", NarrativeSelectResult),
        ("narrative-summary-result/2.0", NarrativeSummaryResult),
        ("narrative-bundle/2.0", NarrativeBundle),
    ],
)
def test_projection_fields_never_accepted_under_old_version(schema, parser):
    raw = (
        selection()
        if parser is NarrativeSelectResult
        else summary()
        if parser is NarrativeSummaryResult
        else bundle()
    )
    raw["schema_version"] = schema
    with pytest.raises(NarrativeContractError):
        parser.from_dict(raw)
