"""Existing physical owner proves flow; structure must own the note scope."""
from dataclasses import replace

import pytest

from company_wiki.resource_budget import WorkBudget
from .fixtures import Row, inherited_heading_ids, run_pipeline, source


def cross_page_source(fault=None):
    next_page = 3 if fault == "page_gap" else 2
    parsed, owned = source((
        Row("intro", "备注19：乙方关于股份处置范围的承诺：", box=(72., 650., 528., 678.)),
        Row("previous", "“1、乙方将在规定范围内履行披露义务。", box=(72., 730., 528., 758.)),
        Row("next", "2、本公司承诺，股份处置前将事先通报。", page=next_page,
            box=(72., 70., 528., 98.)),
    ))
    if fault == "column_conflict":
        unit = owned["next"]
        reading = unit.metadata["reading_layout"]
        metadata = {**unit.metadata, "reading_layout": {
            **reading, "layout": {**reading["layout"], "column": 1},
        }}
        changed = replace(unit, metadata=metadata)
        parsed = replace(parsed, units=tuple(changed if candidate == unit else candidate
                                            for candidate in parsed.units))
        owned["next"] = changed
    return parsed, owned


def test_complete_clause_page_neighbour_is_not_an_unfinished_sentence_requirement():
    parsed, owned = cross_page_source()
    result, contexts = run_pipeline(parsed)
    proof = contexts[parsed.source_id].page_neighbour(
        owned["previous"].unit_id, owned["next"].unit_id, furniture_unit_ids=frozenset())
    assert proof is not None, "synthetic native source metadata must actually prove physical adjacency"
    assert proof["basis"] == "observed_adjacent_page_flow"
    assert proof["left"] == owned["previous"].unit_id and proof["right"] == owned["next"].unit_id
    assert proof["left_page"] == 1 and proof["right_page"] == 2
    assert proof["column"] == 0
    assert result["structure"]["coverage"]["complete"] is True


def test_proven_cross_page_clause_keeps_its_own_note_intro_and_dependency_proof():
    parsed, owned = cross_page_source()
    result, contexts = run_pipeline(parsed)
    proof = contexts[parsed.source_id].page_neighbour(
        owned["previous"].unit_id, owned["next"].unit_id, furniture_unit_ids=frozenset())
    assert proof is not None  # test the real producer, not a fabricated proof dict
    context = inherited_heading_ids(result, owned["next"])
    assert owned["intro"].unit_id in context, "本公司 keeps its original source introduction"
    semantics = result["structure"]["semantic_units"]
    target = owned["next"].unit_id
    declared_context = {uid for semantic in semantics
                        for uid in semantic.get("required_context_by_unit_id", {}).get(target, ())}
    declared_proofs = [row for semantic in semantics
                       for row in semantic.get("native_source_proofs_by_unit_id", {}).get(target, ())]
    assert owned["intro"].unit_id in declared_context
    assert proof in declared_proofs


@pytest.mark.parametrize("fault", ["deferred", "page_gap", "column_conflict"])
def test_unproven_cross_page_scope_cannot_silently_be_a_complete_smaller_context(fault):
    parsed, owned = cross_page_source(fault)
    result, contexts = run_pipeline(parsed, deferred_pages=(2,) if fault == "deferred" else ())
    assert contexts[parsed.source_id].page_neighbour(
        owned["previous"].unit_id, owned["next"].unit_id, furniture_unit_ids=frozenset()) is None
    assert owned["intro"].unit_id not in inherited_heading_ids(result, owned["next"])
    assert result["structure"]["coverage"]["complete"] is False, "unproved note relation must remain partial"


def test_zero_work_budget_stops_before_scope_indexing_without_mutating_source():
    parsed, _owned = cross_page_source()
    budget = WorkBudget(0)
    result, contexts = run_pipeline(parsed, budget=budget)
    assert budget.used == 0 and budget.exhausted
    assert result["analysis_status"] == "deferred"
    assert result["structure"]["coverage"]["complete"] is False
    assert contexts == {}
