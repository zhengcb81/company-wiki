"""Whole-source admission follows source order and ranking carries exact scopes."""
from copy import deepcopy
import json

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_extractive import (
    build_extractive_request, compile_extractive_plan, decode_extractive_result,
)
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan
from unit.test_narrative_extractive_runtime import selected


def source_with_discovered_groups(order, *, priority_page=None, unknown_page=None,
                                  unknown_hint_page=None):
    original = selected(3, text_suffix="A" * 750)
    wire = original.to_dict()
    spans = []
    for span in original.evidence_spans:
        page = span.coordinates.page_number
        value = dict(span.structured_value)
        if page != unknown_hint_page:
            value.update(reading_priority=0 if page == priority_page else 2,
                         reading_value_band="description", reading_score=0)
        coords = EvidenceCoordinates(page_number=None if page == unknown_page else page,
                                     paragraph_index=0)
        spans.append(EvidenceSpan.create(
            source_id=span.source_id, coordinates=coords, raw_text=span.raw_text,
            structured_value=value, parser_name=span.parser_name,
            parser_version=span.parser_version, parse_status=span.parse_status,
            quality_flags=span.quality_flags,
        ))
    wire["evidence_spans"] = [span.to_dict() for span in spans]
    wire["reading_context"]["groups"] = [
        {"group_id": f"discovered-{page}", "kind": "business_progress",
         "section_role": "business", "evidence_ids": [spans[page - 1].span_id]}
        for page in order
    ]
    return NarrativeSelectResult.from_dict(wire)


@pytest.mark.parametrize("order", [(3, 1, 2), (2, 3, 1)])
def test_equal_priority_byte_allocation_uses_source_not_group_discovery_order(order):
    source = source_with_discovered_groups(order)
    before = deepcopy(source.to_dict())
    plan = compile_extractive_plan(source, max_draft_bytes=1800)
    assert len(plan.draft["claims"]) == 1
    assert plan.draft["claims"][0]["text"] == source.evidence_spans[0].raw_text
    assert source.to_dict() == before


@pytest.mark.parametrize("option", [{"priority_page": 3}, {"unknown_page": 3},
                                   {"unknown_hint_page": 3}])
def test_source_tie_order_never_overrules_hint_or_unknown_coordinate_slots(option):
    source = source_with_discovered_groups((3, 1, 2), **option)
    plan = compile_extractive_plan(source, max_draft_bytes=1800)
    assert len(plan.draft["claims"]) == 1
    assert plan.draft["claims"][0]["text"] == source.evidence_spans[2].raw_text


def test_compact_rank_rows_reconstruct_complete_support_context_roles_and_text():
    source = selected(3)
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire["reading_context"]["schema_version"] = "du-production-reading/2"
    wire["reading_context"]["groups"] = [
        {"group_id": "qa-one", "kind": "business_progress", "section_role": "business",
         "evidence_ids": ids[:2], "citation_views": [
             {"support_evidence_ids": ids[1:2], "context_evidence_ids": ids[:1]}]},
        {"group_id": "qa-two", "kind": "business_progress", "section_role": "business",
         "evidence_ids": [ids[0], ids[2]], "citation_views": [
             {"support_evidence_ids": ids[2:], "context_evidence_ids": ids[:1]}]},
    ]
    source = NarrativeSelectResult.from_dict(wire)
    before = deepcopy(source.to_dict())
    request = build_extractive_request(source)
    material = json.loads(request.data_json)["material"]
    assert material["schema_version"] == "source-extractive-ranking-view/1"
    assert material["fragment_columns"] == ["source_key", "text", "source_role", "quality_flags"]
    assert material["task_columns"] == ["key", "support", "context", "reading_hint_index"]
    assert len(material["fragments"]) == 3  # Shared question/context is not copied twice.
    for index, row in enumerate(material["fragments"]):
        span = source.evidence_spans[index]
        assert row == [f"s{index + 1}", span.raw_text,
                       span.structured_value["source_role"], list(span.quality_flags)]
    assert [row[1:3] for row in material["tasks"]] == [[[1], [0]], [[2], [0]]]
    assert source.to_dict() == before
    assert request.input_sha256 == build_extractive_request(source).input_sha256


def test_model_only_receives_cards_that_can_reach_the_canonical_draft():
    source = selected(96, text_suffix="Complete original passage." * 20)
    plan = compile_extractive_plan(source)
    admitted = {row["task"] for row in plan.execution["tasks"]
                if row["source_disposition"] == "admitted"}
    assert len(admitted) == 96  # No implicit 56 KiB representation permission.
    assert len(canonical_json(plan.draft).encode('utf-8')) > 56 * 1024
    assert [claim['text'] for claim in plan.draft['claims']] == [
        span.raw_text for span in source.evidence_spans
    ]
    envelope = json.loads(build_extractive_request(source).data_json)
    material = envelope["material"]
    assert material["schema_version"] == "source-extractive-ranking-view/1"
    assert {row[0] for row in material["tasks"]} == admitted
    assert envelope["output_plan"]["available_task_count"] == len(admitted)
    assert all(isinstance(index, int) and not isinstance(index, bool) and index >= 0
               for row in material["tasks"] for index in row[1] + row[2])
    assert source.selection.status == 'partial'
    assert source.selection.omitted_candidate_count == 20
    assert envelope['output_plan']['coverage'] == 'selected_source_tasks_only'


def source_with_unprocessed_scope():
    from unit.test_source_summary_capability import current_wire
    # A real unassessed source scope, rather than an implicit byte quota, is
    # unavailable to ranking. Its original task/quote remains in the source.
    return NarrativeSelectResult.from_dict(current_wire(('support',) * 95 + ('unresolved',)))


def test_rank_for_an_untransmitted_unresolved_task_is_not_an_actual_model_read():
    source = source_with_unprocessed_scope()
    plan = compile_extractive_plan(source)
    unprocessed = next(row['task'] for row in plan.execution['tasks']
                       if row['source_disposition'] == 'unsupported')
    request = build_extractive_request(source)
    transmitted = {row[0] for row in json.loads(request.data_json)['material']['tasks']}
    assert unprocessed not in transmitted and len(transmitted) == 95
    response = NarrativeModelResponse("offline", "configured", request.prompt_version,
        canonical_json({"decisions": [{"task": unprocessed, "priority": "high",
                                      "disposition": "consider"}]}).encode())
    decoded = decode_extractive_result(response, selected=source)
    assert decoded.execution["model_diagnostic"] == "RANK_INVALID"
    assert decoded.draft == plan.draft


def test_all_transmitted_ranks_do_not_hide_the_unprocessed_source_remainder():
    source = source_with_unprocessed_scope()
    before = source.to_dict()
    plan = compile_extractive_plan(source)
    tasks = [row for row in plan.execution["tasks"] if row["source_disposition"] == "admitted"]
    request = build_extractive_request(source)
    response = NarrativeModelResponse("offline", "configured", request.prompt_version,
        canonical_json({"decisions": [{"task": row["task"], "priority": "normal",
                                      "disposition": "consider"} for row in tasks]}).encode())
    decoded = decode_extractive_result(response, selected=source)
    assert decoded.execution["model_diagnostic"] == "RANK_INCOMPLETE"
    assert not decoded.execution["model_coverage_complete"]
    assert not decoded.execution['source_coverage_complete']
    assert len(decoded.draft['claims']) == len(tasks) == 95
    assert len(decoded.execution['tasks']) == 96
    assert all(row["model_disposition"] == "unprocessed" for row in decoded.execution["tasks"]
               if row["source_disposition"] == "unsupported")
    assert source.to_dict() == before
    assert source.selection.status == 'partial'


@pytest.mark.parametrize("use", ["context_only", "unresolved"])
def test_real_handler_keeps_non_support_source_without_failing_valid_summary(use):
    from company_wiki.automation.models import HandlerOutcome, _to_plain
    from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
    from company_wiki.automation.narrative_summary_execution import parse_summary_job_result
    from unit.test_narrative_summarize_handler import _context
    from unit.test_source_summary_capability import current_wire

    source = NarrativeSelectResult.from_dict(current_wire((use, "support")))
    calls = []

    class Model:
        def generate(self, request):
            calls.append(request)
            return NarrativeModelResponse("offline", "configured", request.prompt_version,
                b'{"decisions":[{"task":"t2","priority":"normal","disposition":"consider"}]}')

    result = NarrativeSummarizeHandler(model=Model(),
        reading_model_projection=lambda _: "reading-model-input/5")(_context(source))
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    assert len(calls) == 1
    summary = parse_summary_job_result(result.result, selected=source)
    assert len(summary.draft.claims) == 1
    assert summary.draft.claims[0].evidence_ids == (source.evidence_spans[1].span_id,)
    assert result.result["execution"]["tasks"][0]["reason"] == "source_" + use
    assert result.result["execution"]["tasks"][0]["model_disposition"] == "unprocessed"
    forged = _to_plain(result.result)
    claim = deepcopy(forged["summary"]["draft"]["claims"][0])
    claim.update(claim_id="t1-source", text=source.evidence_spans[0].raw_text,
                 evidence_ids=[source.evidence_spans[0].span_id])
    forged["summary"]["draft"]["claims"].insert(0, claim)
    forged["execution"]["tasks"][0].update(source_disposition="admitted", reason="source_card",
        claim_id="t1-source", model_disposition="consider", priority="normal")
    forged["execution"].update(source_coverage_complete=True, model_coverage_complete=True,
                              model_diagnostic=None)
    with pytest.raises(ValueError, match="execution availability differs"):
        parse_summary_job_result(forged, selected=source)
