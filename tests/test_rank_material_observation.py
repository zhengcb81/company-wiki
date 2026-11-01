"""The benchmark observes transmitted whole scopes, not globally present text."""
from copy import deepcopy
import hashlib
import json

import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model_extractive import build_extractive_request
from tools.document_understanding_benchmark.phase_c_observer import (
    gold_admission_missing, gold_observation,
)
from unit.test_narrative_extractive_runtime import selected


def example():
    source = selected(3)
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire["reading_context"]["schema_version"] = "du-production-reading/2"
    wire["reading_context"]["groups"] = [
        {"group_id": "one", "kind": "business_progress", "section_role": "business",
         "evidence_ids": ids[:2], "citation_views": [
             {"support_evidence_ids": ids[1:2], "context_evidence_ids": ids[:1]}]},
        {"group_id": "two", "kind": "business_progress", "section_role": "business",
         "evidence_ids": [ids[0], ids[2]], "citation_views": [
             {"support_evidence_ids": ids[2:], "context_evidence_ids": ids[:1]}]},
    ]
    for group in wire["reading_context"]["groups"]:
        digest = hashlib.sha256(json.dumps(group["evidence_ids"], separators=(",", ":")).encode()).hexdigest()
        group["group_id"] = "urn:company-wiki:reading-group:sha256:" + digest
    source = NarrativeSelectResult.from_dict(wire)
    envelope = json.loads(build_extractive_request(source).data_json)
    gold = {"facts": [{"id": "business", "target_kind": "required_business",
        "any_support_sets": [[{"page": 2, "exact_quote": source.evidence_spans[1].raw_text}]]}]}
    return source, envelope, gold


def test_compiled_card_initial_request_is_not_mislabeled_as_a_repair():
    source, envelope, gold = example()
    before = deepcopy(source.to_dict())
    result = gold_observation(gold, source, envelope)
    assert result["sent_tasks"]["request_scope"] == "compiled_source_cards"
    assert result["sent_tasks"]["supported_count"] == 1
    assert gold_admission_missing(result, attempt_no=1) == []
    assert source.to_dict() == before


@pytest.mark.parametrize("fault", ["negative", "bool_index", "out_of_range", "duplicate_alias",
    "support_context_swap", "role", "missing_task", "hint_bool"])
def test_invalid_compact_scope_is_refused_before_source_gold_can_bless_it(fault):
    source, envelope, gold = example()
    material = envelope["material"]
    if fault == "negative":
        material["tasks"][0][1] = [-1]
    elif fault == "bool_index":
        material["tasks"][0][2] = [False]
    elif fault == "out_of_range":
        material["tasks"][0][1] = [len(material["fragments"])]
    elif fault == "duplicate_alias":
        material["fragments"][1][0] = material["fragments"][0][0]
    elif fault == "support_context_swap":
        material["tasks"][0][1], material["tasks"][0][2] = material["tasks"][0][2], material["tasks"][0][1]
    elif fault == "role":
        material["fragments"][1][2] = "investor_question"
    elif fault == "hint_bool":
        material["tasks"][0][3] = False
    else:
        # Even if gold only mentions the first task, another compiled card
        # cannot disappear by consistently changing the declared subset.
        material["tasks"].pop()
        material["available_task_count"] -= 1
        envelope["output_plan"]["admitted_task_keys"].pop()
        envelope["output_plan"]["available_task_count"] -= 1
    with pytest.raises(ValueError):
        gold_observation(gold, source, envelope)


@pytest.mark.parametrize("field,value", [("score", False), ("score", 0.0), ("priority", False)])
def test_hint_field_types_do_not_equate_boolean_or_float_to_source_integers(field, value):
    from unit.test_extractive_rank_material import source_with_discovered_groups
    from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
    from tools.document_understanding_benchmark.rank_material_observation import observed_rank_keys

    source = source_with_discovered_groups((1, 2, 3), priority_page=2)
    envelope = json.loads(build_extractive_request(source).data_json)
    view = compile_scoped_model_view(source, max_claims=len(source.evidence_spans) * 2)
    assert len(observed_rank_keys(source, envelope, view)) == 3
    hint = next(hint for hint in envelope["material"]["reading_hints"] if hint["priority"] == 0)
    hint[field] = value
    with pytest.raises(ValueError, match="PHASE_C_COMPACT_RANK_SCOPE_INVALID"):
        observed_rank_keys(source, envelope, view)
