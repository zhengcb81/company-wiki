"""A question is context for an answer, never authority for a company fact."""
from copy import deepcopy
import json

import pytest

from company_wiki.automation import narrative_model as model
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import (
    NarrativeContractError, NarrativeSelectResult, _claim_from_dict,
    subject_draft_from_dict, subject_draft_to_dict,
)
from company_wiki.document_understanding.orchestration import build_dependency_packages
from company_wiki.document_understanding.structure.qa import QaDraft
from company_wiki.source_catalog.narrative_evidence import (
    SummaryValidationError, project_summary_claim_quality, validate_summary_claim,
)
from company_wiki.source_contract import EvidenceSpan
from company_wiki.automation.narrative_output_language import observe_summary_language
from unit.test_narrative_output_language_binding import EN
from unit.test_narrative_source_owned_model_boundary import official_reading


V3 = "reading-model-input/3"


def qa_wire():
    wire = official_reading().to_dict()
    context = wire["reading_context"]
    context["schema_version"] = "du-production-reading/2"
    question, answer, second = [row["span_id"] for row in wire["evidence_spans"]]
    first, other = context["groups"]
    first["kind"] = "qa_exchange"
    first["citation_views"] = [
        {"support_evidence_ids": [answer], "context_evidence_ids": [question]},
        {"support_evidence_ids": [question], "context_evidence_ids": [answer]},
    ]
    other["citation_views"] = [{"support_evidence_ids": [second], "context_evidence_ids": []}]
    return wire


def selected_qa():
    return NarrativeSelectResult.from_dict(qa_wire())


def reply(selected, *, support="e2", kind="company_statement", modality="actual", extra=None):
    request = model.NarrativeModelRequest.from_selection(selected, reading_projection_version=V3)
    data = json.loads(request.data_json)
    columns = data["citation_unit_columns"]
    assert columns == ["id", "evidence_ids", "support_evidence_ids"]
    unit = next(dict(zip(columns, row, strict=True)) for row in data["citation_units"]
                if row[2] == [support])
    text = next(row[1] for row in data["evidence"] if row[0] == support)
    claim = {"claim_id": "answer", "text": text,
             "citation_unit_ids": [unit["id"]], "claim_type": kind, "modality": modality,
             **(extra or {})}
    response = model.NarrativeModelResponse("offline", "fixture", request.prompt_version,
        canonical_json({"claims": [claim]}).encode())
    return model.decode_model_draft(response, selected=selected, reading_projection_version=V3)


def test_native_qa_package_preserves_both_explicit_support_views():
    semantic = QaDraft("qa", ["q", "a"], ["q"], ["a"]).as_wire()
    result = build_dependency_packages({"sections": [], "semantic_units": [semantic]})
    assert result["packages"][0]["citation_support_views"] == [["a"], ["q"]]
    assert semantic["anchor_unit_ids"] == ["a"]
    assert semantic["required_context_unit_ids"] == ["q"]


def test_management_answer_has_support_and_complete_question_context():
    selected = selected_qa()
    draft = reply(selected)
    claim = draft["claims"][0]
    assert claim["evidence_ids"] == [selected.evidence_spans[1].span_id]
    assert claim["context_evidence_ids"] == [selected.evidence_spans[0].span_id]
    assert claim["claim_type"] == "company_statement"
    assert claim["modality"] == "actual"
    assert draft["status"] == "draft"
    assert subject_draft_to_dict(subject_draft_from_dict(draft)) == draft


def test_question_view_has_question_role_and_keeps_answer_context():
    selected = selected_qa()
    draft = reply(selected, support="e1", kind="analyst_question", modality="question")
    claim = draft["claims"][0]
    assert claim["evidence_ids"] == [selected.evidence_spans[0].span_id]
    assert claim["context_evidence_ids"] == [selected.evidence_spans[1].span_id]


@pytest.mark.parametrize("support,kind,modality", [
    ("e1", "company_statement", "actual"),
    ("e2", "analyst_question", "question"),
    ("e1", "analyst_question", "actual"),
])
def test_context_never_promotes_question_or_changes_its_role(support, kind, modality):
    with pytest.raises(NarrativeContractError):
        reply(selected_qa(), support=support, kind=kind, modality=modality)


def test_same_full_exchange_has_distinct_answer_and_question_aliases():
    selected = selected_qa()
    data = json.loads(model.NarrativeModelRequest.from_selection(selected,
        reading_projection_version=V3).data_json)
    views = [row for row in data["citation_units"] if row[1] == ["e1", "e2"]]
    assert len(views) == 2 and views[0][0] != views[1][0]
    assert {tuple(row[2]) for row in views} == {("e1",), ("e2",)}
    assert len(data["evidence"]) == len(selected.evidence_spans)


@pytest.mark.parametrize("bad", ["unknown", "duplicate", "overlap", "missing", "empty_support", "foreign_parent"])
def test_invalid_or_incomplete_native_partition_rejects_before_model(bad):
    wire = qa_wire()
    view = wire["reading_context"]["groups"][0]["citation_views"][0]
    if bad == "unknown":
        view["context_evidence_ids"] = ["foreign"]
    elif bad == "duplicate":
        view["context_evidence_ids"] *= 2
    elif bad == "overlap":
        view["context_evidence_ids"] += view["support_evidence_ids"]
    elif bad == "missing":
        view["context_evidence_ids"] = []
    elif bad == "empty_support":
        view["support_evidence_ids"] = []
    else:
        view["context_evidence_ids"] = [wire["evidence_spans"][2]["span_id"]]
    with pytest.raises(NarrativeContractError):
        NarrativeSelectResult.from_dict(wire)


def test_old_context_cannot_silently_acquire_new_partition_fields():
    wire = qa_wire()
    wire["reading_context"]["schema_version"] = "du-production-reading/1"
    with pytest.raises(NarrativeContractError):
        NarrativeSelectResult.from_dict(wire)


def test_old_canonical_claim_has_no_new_empty_field():
    selected = official_reading()
    sid = selected.evidence_spans[1].span_id
    old = {"subject_id": selected.subject.item_key, "subject_sha256": selected.subject.subject_sha256,
        "language": "en", "status": "draft", "claims": [{"claim_id": "old", "text": "A business update.",
        "evidence_ids": [sid], "claim_type": "company_statement", "modality": "actual", "needs_review": False}]}
    typed = subject_draft_from_dict(old)
    assert getattr(typed.claims[0], "context_evidence_ids", None) == ()
    assert canonical_json(subject_draft_to_dict(typed)) == canonical_json(old)


def canonical_claim(*, context=None):
    selected = official_reading()
    refs = [span.span_id for span in selected.evidence_spans]
    return selected, _claim_from_dict({"claim_id": "typed", "text": "A business update.",
        "evidence_ids": [refs[1]], "context_evidence_ids": [refs[0]] if context is None else context,
        "claim_type": "company_statement", "modality": "actual", "needs_review": False})


@pytest.mark.parametrize("bad", ["unknown", "overlap", "duplicate", "foreign_parent"])
def test_canonical_context_does_not_bypass_source_and_membership_validation(bad):
    selected = official_reading()
    refs = [span.span_id for span in selected.evidence_spans]
    context = {"unknown": ["unknown"], "overlap": [refs[1]],
        "duplicate": [refs[0], refs[0]], "foreign_parent": [refs[2]]}[bad]
    with pytest.raises((NarrativeContractError, SummaryValidationError)):
        selected, claim = canonical_claim(context=context)
        validate_summary_claim(claim, {span.span_id: span for span in selected.evidence_spans}, "draft")


def test_context_role_is_preserved_without_becoming_factual_authority():
    selected, claim = canonical_claim()
    validate_summary_claim(claim, {span.span_id: span for span in selected.evidence_spans}, "draft")
    projected, _ = project_summary_claim_quality((claim,), evidence_spans=selected.evidence_spans)
    assert projected[0].claim_type == "company_statement" and not projected[0].needs_review
    assert selected.evidence_spans[0].structured_value["source_role"] == "investor_question"


def test_model_cannot_override_program_owned_context_binding():
    selected = selected_qa()
    with pytest.raises((NarrativeContractError, model.ModelResponseError)):
        reply(selected, extra={"context_evidence_ids": ["e3"]})


def test_partition_roundtrip_is_detached_from_mutable_input():
    wire = qa_wire()
    expected = deepcopy(wire["reading_context"])
    selected = NarrativeSelectResult.from_dict(wire)
    wire["reading_context"]["groups"][0]["citation_views"][0]["support_evidence_ids"].clear()
    assert selected.to_dict()["reading_context"] == expected


@pytest.mark.parametrize("translated", [False, True])
def test_chinese_question_context_cannot_authorize_translating_an_english_answer(translated):
    base = official_reading()
    question, answer = [EvidenceSpan.create(source_id=span.source_id,
        coordinates=span.coordinates, raw_text=text, structured_value=span.structured_value,
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=())
        for span, text in zip(base.evidence_spans[:2], [
            "请具体介绍公司海外产能扩张和商业化交付进度，包括新增客户的情况、新工厂投产及后续产品研发安排。",
            EN], strict=True)]
    text = ("公司扩大了生产能力并新增海外市场客户，新建工厂已经开始商业化交付，团队还在继续研发其他新产品。"
            if translated else EN)
    claim = _claim_from_dict({"claim_id": "answer", "text": text,
        "evidence_ids": [answer.span_id], "context_evidence_ids": [question.span_id],
        "claim_type": "company_statement", "modality": "actual", "needs_review": False})
    validate_summary_claim(claim, {span.span_id: span for span in (question, answer)}, "draft")
    observed = observe_summary_language((claim,), evidence_spans=(question, answer))
    assert observed.state == ("different" if translated else "compatible")
