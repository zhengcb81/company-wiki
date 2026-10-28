"""Source readability and source-owned summary support are different contracts."""

from copy import deepcopy

import pytest

from company_wiki.automation.narrative_contracts import (
    NarrativeContractError,
    NarrativeSelectResult,
)
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.document_understanding.source_cards import (
    source_cards,
    source_task_admission,
)
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from unit.test_narrative_extractive_runtime import selected
from unit.test_scoped_source_admission import envelope, decode, clause
from company_wiki.automation import narrative_model
from company_wiki.automation.narrative_model_runtime import (
    build_model_request,
    decode_model_draft,
)


def current_wire(uses=("context_only", "support")):
    wire = selected(len(uses)).to_dict()
    ctx = wire["reading_context"]
    ctx.update(
        schema_version="du-production-reading/4",
        deferred=[],
        deferred_count=0,
        deferred_limited=False,
        selection_diagnostics=[],
    )
    ids = [span["span_id"] for span in wire["evidence_spans"]]
    ctx["groups"] = [
        {
            "group_id": f"original-scope-{index}",
            "kind": "paragraph_event",
            "section_role": "business",
            "evidence_ids": [sid],
            "citation_views": [
                {
                    "support_evidence_ids": [sid],
                    "context_evidence_ids": [],
                    "reading_support_use": use,
                    "reading_support_reason": "source_scope_assessed",
                }
            ],
        }
        for index, (sid, use) in enumerate(zip(ids, uses, strict=True))
    ]
    empty = {"count": 0, "limited": False, "samples": []}
    ctx["selection_trace"] = {
        "schema_version": "selection-trace/1",
        "source_unit_count": len(ids),
        "admission": {
            **empty,
            "admitted_count": 0,
            "rejected_count": 0,
            "rejection_counts": {},
        },
        "eligible_packages": dict(empty),
        "withheld": dict(empty),
        "selected": {"count": len(ids), "limited": True, "samples": []},
    }
    return wire


@pytest.mark.parametrize("use", ["context_only", "unresolved"])
def test_readable_source_is_preserved_but_does_not_consume_a_generation_slot(use):
    source = NarrativeSelectResult.from_dict(current_wire((use, "support")))
    before = deepcopy(source.to_dict())
    plan = build_summary_task_plan(
        source.evidence_spans, reading_context=source.reading_context, max_claims=20
    )
    cards = tuple(
        source_cards(plan, {span.span_id: span for span in source.evidence_spans})
    )
    assert all(card.available and card.text for card in cards)
    admission = source_task_admission(cards)
    assert admission["t1"] == {"status": "unavailable", "reason": "source_" + use}
    assert admission["t2"]["status"] == "admitted"
    assert [task["key"] for task in envelope(source)["material"]["tasks"]] == ["t2"]
    assert len(plan.tasks) == 2
    assert source.to_dict() == before
    assert plan.to_binding()["schema_version"] == "source-summary-task-plan/2"


def test_current_annotation_cannot_be_omitted_forged_or_smuggled_as_a_path(tmp_path):
    for mutate in ("missing", "wrong_use", "long_reason", "path_reason"):
        wire = current_wire()
        view = wire["reading_context"]["groups"][0]["citation_views"][0]
        if mutate == "missing":
            view.pop("reading_support_use")
        elif mutate == "wrong_use":
            view["reading_support_use"] = "approved"
        elif mutate == "long_reason":
            view["reading_support_reason"] = "a" * 81
        elif mutate == "path_reason":
            view["reading_support_reason"] = str(tmp_path.anchor) + "secret/location"
        with pytest.raises(NarrativeContractError):
            NarrativeSelectResult.from_dict(wire)


def test_support_use_is_carried_per_view_instead_of_borrowed_from_context():
    wire = current_wire(("support", "support"))
    ids = [span["span_id"] for span in wire["evidence_spans"]]
    group = wire["reading_context"]["groups"][0]
    group["evidence_ids"] = ids
    group["citation_views"][0]["context_evidence_ids"] = ids[1:]
    group["citation_views"].append(
        {
            "support_evidence_ids": ids[1:],
            "context_evidence_ids": ids[:1],
            "reading_support_use": "context_only",
            "reading_support_reason": "format_context",
        }
    )
    wire["reading_context"]["groups"] = [group]
    source = NarrativeSelectResult.from_dict(wire)
    view = compile_scoped_model_view(source, max_claims=20)
    assert [task.key for task in view.model_tasks] == ["t1"]
    assert view.plan.tasks[0].support_ids == (ids[0],)
    assert view.plan.tasks[1].support_use == "context_only"


def test_uncertain_model_wording_cannot_resurrect_context_only_support():
    source = NarrativeSelectResult.from_dict(current_wire())
    invalid = clause(source, 0)
    invalid["modality"] = "uncertain"
    draft = decode(source, {"t1": [invalid], "t2": [clause(source, 1)]})
    assert len(draft["claims"]) == 1
    assert draft["claims"][0]["evidence_ids"] == [source.evidence_spans[1].span_id]


def test_legacy_source_cards_remain_readable_with_their_old_binding():
    source = selected(2)
    plan = build_summary_task_plan(
        source.evidence_spans, reading_context=source.reading_context, max_claims=20
    )
    assert plan.to_binding()["schema_version"] == "source-summary-task-plan/1"
    assert "support_use" not in plan.to_binding()["tasks"][0]
    assert all(
        card.available
        for card in source_cards(
            plan, {span.span_id: span for span in source.evidence_spans}
        )
    )


def test_current_ungrouped_source_does_not_invent_a_complete_support_assessment():
    wire = current_wire()
    wire["reading_context"]["groups"].pop()
    source = NarrativeSelectResult.from_dict(wire)
    view = compile_scoped_model_view(source, max_claims=20)
    assert view.plan.tasks[-1].support_use == "unresolved"
    assert view.plan.tasks[-1].support_reason == "source_use_unassessed"
    assert [task.key for task in view.model_tasks] == []


@pytest.mark.parametrize(
    "version",
    [None, "reading-model-input/1", "reading-model-input/2", "reading-model-input/3"],
)
def test_renderer_without_scoped_support_use_cannot_silently_accept_new_context(
    version,
):
    source = NarrativeSelectResult.from_dict(current_wire())
    with pytest.raises(
        narrative_model.ModelResponseError, match="SUPPORT_USE_UNSUPPORTED"
    ):
        build_model_request(source, reading_projection_version=version)
    with pytest.raises(
        narrative_model.ModelResponseError, match="SUPPORT_USE_UNSUPPORTED"
    ):
        narrative_model.NarrativeModelRequest.from_selection(
            source, reading_projection_version=version
        )
    boundary = narrative_model.resolve_model_boundary(version)
    response = narrative_model.NarrativeModelResponse(
        "offline", "configured", boundary.prompt_version, b"{}"
    )
    with pytest.raises(
        narrative_model.ModelResponseError, match="SUPPORT_USE_UNSUPPORTED"
    ):
        decode_model_draft(
            response, selected=source, reading_projection_version=version
        )


def test_extractive_program_draft_honors_the_same_support_use_as_its_request():
    from company_wiki.automation.narrative_model_extractive import (
        compile_extractive_plan,
    )

    source = NarrativeSelectResult.from_dict(current_wire())
    result = compile_extractive_plan(source)
    assert [claim["evidence_ids"] for claim in result.draft["claims"]] == [
        [source.evidence_spans[1].span_id]
    ]
    assert result.execution["tasks"][0]["source_disposition"] == "unsupported"
    assert result.execution["tasks"][0]["reason"] == "source_context_only"
