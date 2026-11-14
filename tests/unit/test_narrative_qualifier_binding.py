"""Cited qualifiers must remain attached to claims across source spans.

These tests exercise the old and current source-backed decoders with offline
responses. Diagnostics describe known fidelity risks; they do not reject a
draft or claim a general semantic verdict.
"""

import json
import socket

import pytest

from company_wiki.automation import narrative_model_runtime
from company_wiki.automation.narrative_model import (
    NarrativeModelRequest,
    NarrativeModelResponse,
    decode_model_draft,
)
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_summary_assessment import (
    CLAUSE_SCOPE_ASSESSMENT_VERSION,
    assess_summary,
    claim_qualifier_diagnostics,
    validate_assessment_material,
)
from company_wiki.document_understanding.assertion_frames import source_assertion_frames
from support.fresh_summary_fixture import grouped_selection
from unit.test_narrative_reading_transport import reading_context


LEGACY = None
CURRENT = "reading-model-input/7"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("qualifier diagnostics must not call a model supplier")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def selected_source(texts, *, current=False):
    base = grouped_selection(texts, groups=tuple("same-scope" for _ in texts))
    if not current:
        return base

    payload = base.to_dict()
    context = reading_context(base)
    context["groups"] = [{
        "group_id": "same-scope",
        "kind": "business_progress",
        "section_role": "business",
        "evidence_ids": [span.span_id for span in base.evidence_spans],
    }]
    payload["reading_context"] = context
    return type(base).from_dict(payload)


def decode_legacy(selected, claim_text, modality="actual"):
    ids = [span.span_id for span in selected.evidence_spans]
    request = NarrativeModelRequest.from_selection(selected, reading_projection_version=LEGACY)
    payload = {
        "draft": {
            "source_id": selected.source_ref.source_id,
            "source_sha256": selected.source_ref.content_sha256,
            "language": selected.source_metadata.language,
            "claims": [{
                "claim_id": "c1",
                "text": claim_text,
                "evidence_ids": ids,
                "claim_type": "company_statement",
                "modality": modality,
            }],
        }
    }
    response = NarrativeModelResponse(
        "offline", "fixture", request.prompt_version,
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    return decode_model_draft(response, selected=selected, reading_projection_version=LEGACY)


def decode_current(selected, claim_text, modality="actual"):
    request = narrative_model_runtime.build_model_request(
        selected, reading_projection_version=CURRENT,
    )
    request_text = json.dumps(json.loads(request.data_json), ensure_ascii=False)
    assert all(span.raw_text in request_text for span in selected.evidence_spans)
    view = compile_scoped_model_view(selected, max_claims=40)
    assert len(view.model_tasks) == 1
    task = view.model_tasks[0]
    assert set(task.support_ids) == {span.span_id for span in selected.evidence_spans}
    parts = [part for part, sid in view.to_binding()["task_parts"][task.key].items()
             if sid in task.support_ids]
    response = NarrativeModelResponse(
        "offline", "fixture", request.prompt_version,
        canonical_json({"drafts_by_task": {task.key: [{
            "text": claim_text,
            "basis_parts": parts,
            "modality": modality,
        }]}}).encode("utf-8"),
    )
    return narrative_model_runtime.decode_model_draft(
        response, selected=selected, reading_projection_version=CURRENT,
    )


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_real_condition_scope_loss_is_diagnostic_in_both_decoders(decoder):
    selected = selected_source((
        "公司计划在项目建成后为工厂提供产能保障。",
        "该安排仍须客户完成验收后方可投产。",
    ), current=decoder is decode_current)

    result = decoder(selected, "公司已为工厂提供产能保障。")

    assert result["status"] == "needs_review"
    assert result["claims"][0]["needs_review"] is True
    # The observation is advisory: valid source-bound output remains available.
    assert result["claims"][0]["evidence_ids"] == [span.span_id for span in selected.evidence_spans]


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_anaphoric_pending_condition_in_another_span_is_bound_to_matching_claim(decoder):
    selected = selected_source((
        "本安排包括为工厂提供产能保障。",
        "该安排仍须客户完成验收后方可投产。",
    ), current=decoder is decode_current)

    result = decoder(selected, "公司已为工厂提供产能保障。")

    assert result["status"] == "needs_review"
    assert result["claims"][0]["needs_review"] is True


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_english_anaphoric_condition_is_linked_without_company_vocabulary(decoder):
    selected = selected_source((
        "The arrangement includes providing capacity for the plant.",
        "This arrangement remains subject to customer acceptance before commissioning.",
    ), current=decoder is decode_current)

    result = decoder(selected, "The company has provided capacity for the plant.")

    assert result["status"] == "needs_review"
    assert result["claims"][0]["needs_review"] is True


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
@pytest.mark.parametrize(("source", "claim"), [
    ("本安排包括为工厂提供产能保障，该安排仍须客户完成验收后方可投产。",
     "公司已为工厂提供产能保障。"),
    ("The arrangement includes providing capacity for the plant, this arrangement remains subject to customer acceptance before commissioning.",
     "The company has provided capacity for the plant."),
])
def test_pending_condition_after_the_proposition_within_one_span_is_diagnostic(decoder, source, claim):
    selected = selected_source((source,), current=decoder is decode_current)

    if decoder is decode_current:
        request = narrative_model_runtime.build_model_request(selected, reading_projection_version=CURRENT)
        hints = json.loads(request.data_json)["material"]["source_frame_hints"]["sources"]
        assert hints == {"s1": [{"ordinal": 1, "condition_present": True}]}
    result = decoder(selected, claim)

    assert result["status"] == "needs_review"
    assert result["claims"][0]["needs_review"] is True
    assert result["claims"][0]["evidence_ids"] == [selected.evidence_spans[0].span_id]


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
@pytest.mark.parametrize(("source", "claim"), [
    ("批量投产仍须先通过客户验收后方可开展。", "公司已启动批量投产。"),
    ("Plant commissioning requires customer acceptance before production.",
     "The company has completed plant commissioning."),
])
def test_explicit_pending_requirement_qualifies_its_own_proposition(decoder, source, claim):
    selected = selected_source((source,), current=decoder is decode_current)

    result = decoder(selected, claim)

    assert result["status"] == "needs_review"
    assert result["claims"][0]["needs_review"] is True
    if decoder is decode_current:
        request = narrative_model_runtime.build_model_request(selected, reading_projection_version=CURRENT)
        hints = json.loads(request.data_json)["material"]["source_frame_hints"]["sources"]
        assert hints == {"s1": [{"ordinal": 0, "condition_present": True}]}


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_each_coordinated_prerequisite_remains_independently_required(decoder):
    first = "该安排仍须客户完成验收后方可投产"
    second = "且该安排还须监管部门批准后方可投产"
    selected = selected_source((
        f"本安排包括为工厂提供产能保障，{first}，{second}。",
    ), current=decoder is decode_current)

    base = f"公司计划为工厂提供产能保障，{first}"
    missing = decoder(selected, f"{base}。", modality="planned")
    preserved = decoder(selected, f"{base}，{second}。", modality="planned")

    assert missing["claims"][0]["needs_review"] is True
    assert preserved["claims"][0]["needs_review"] is False


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_pending_condition_tracks_nearest_proposition_instead_of_an_earlier_clause(decoder):
    selected = selected_source((
        "甲厂已经完成储能系统改造；本安排包括为乙厂提供运输服务。",
        "该安排仍须对方完成验收后方可开展。",
    ), current=decoder is decode_current)

    result = decoder(selected, "甲厂已经完成储能系统改造。")

    assert result["status"] == "draft"
    assert result["claims"][0]["needs_review"] is False


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
@pytest.mark.parametrize(("claim", "needs_review"), [
    ("计划为工厂提供产能保障，投产仍须客户完成验收。", False),
    ("已为工厂提供产能保障，投产不再需要客户完成验收。", True),
    ("计划为工厂提供产能保障，投产仍须供货商完成验收。", True),
])
def test_claim_must_preserve_the_pending_condition_not_just_repeat_its_terms(decoder, claim, needs_review):
    selected = selected_source((
        "本安排包括为工厂提供产能保障。该安排仍须客户完成验收后方可投产。",
    ), current=decoder is decode_current)

    result = decoder(selected, claim, modality="actual" if claim.startswith("已") else "planned")

    assert result["claims"][0]["needs_review"] is needs_review


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_claim_that_preserves_pending_condition_remains_clean(decoder):
    selected = selected_source((
        "本安排包括为工厂提供产能保障。",
        "该安排仍须客户完成验收后方可投产。",
    ), current=decoder is decode_current)

    result = decoder(
        selected,
        "公司计划为工厂提供产能保障；该安排仍须客户完成验收后方可投产。",
        modality="planned",
    )

    assert result["status"] == "draft"
    assert result["claims"][0]["needs_review"] is False


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_explicit_unrelated_subject_condition_does_not_attach_to_claim(decoder):
    selected = selected_source((
        "公司已为甲工厂提供产能保障。",
        "乙工厂仍须客户完成验收后方可投产。",
    ), current=decoder is decode_current)

    result = decoder(selected, "公司已为甲工厂提供产能保障。")

    assert result["status"] == "draft"
    assert result["claims"][0]["needs_review"] is False


@pytest.mark.parametrize("decoder", [decode_legacy, decode_current], ids=["legacy", "v7"])
def test_unconditional_completed_statement_remains_clean(decoder):
    selected = selected_source((
        "公司已完成客户验收，工厂现已投产并提供产能保障。",
    ), current=decoder is decode_current)

    result = decoder(selected, "公司已完成客户验收，工厂现已投产并提供产能保障。")

    assert result["status"] == "draft"
    assert result["claims"][0]["needs_review"] is False


def test_qualified_assessment_binds_context_condition_to_its_actual_span_and_roundtrips():
    base = selected_source((
        "公司计划在项目建成后为工厂提供产能保障。",
        "该安排仍须客户完成验收后方可投产。",
    ), current=True)
    view = compile_scoped_model_view(base, max_claims=40)
    task, = view.model_tasks
    claim = {
        "claim_id": "t1-1",
        "text": "公司已为工厂提供产能保障。",
        "evidence_ids": list(task.support_ids),
        "context_evidence_ids": list(task.context_ids),
        "claim_type": "company_statement",
        "modality": "actual",
        "needs_review": False,
    }

    report = assess_summary(base, [claim], plan_max_claims=40,
        requested_task_keys=[task.key], assessor_version=CLAUSE_SCOPE_ASSESSMENT_VERSION)

    assert report["validator"]["version"] == CLAUSE_SCOPE_ASSESSMENT_VERSION
    assert report["known_constraint_status"] == "diagnostics_found"
    assert any(row["rule_code"] == "possible_condition_scope_loss"
               and row["source_span_id"] == base.evidence_spans[1].span_id
               for row in report["diagnostics"])
    assert validate_assessment_material(
        report, base.evidence_spans, base.reading_context, [claim], plan_max_claims=40,
        assessor_version=CLAUSE_SCOPE_ASSESSMENT_VERSION,
    )["claims_sha256"] == report["claims_sha256"]


def test_cited_context_span_can_qualify_support_without_borrowing_uncited_material():
    selected = selected_source((
        "本安排包括为工厂提供产能保障。",
        "该安排仍须客户完成验收后方可投产。",
        "另一公司计划开发全新产品。",
    ))
    support, qualifier, unrelated = selected.evidence_spans

    rows = claim_qualifier_diagnostics(
        selected.evidence_spans, [support.span_id], [qualifier.span_id],
        "公司已为工厂提供产能保障。", "actual",
    )

    assert any(row["rule_code"] == "possible_condition_scope_loss"
               and row["source_span_id"] == qualifier.span_id for row in rows)
    assert all(row["source_span_id"] != unrelated.span_id for row in rows)


@pytest.mark.parametrize("source,expected", [
    ("公司计划在项目建成后为工厂提供产能保障。", True),
    ("The company plans to provide capacity after the facility is completed.", True),
    ("公司已为工厂提供产能保障。", False),
])
def test_source_owned_frame_observes_plan_modality_without_claiming_truth(source, expected):
    assert any(frame.future_marker for frame in source_assertion_frames(source)) is expected
