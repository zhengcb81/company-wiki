"""Local task presentation is a source binding, never a semantic truth proof."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.models import canonical_json
from support.narrative_model_request_fixture import selection
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_source_owned_model_boundary import official_reading


def view(selected):
    return compile_scoped_model_view(selected, max_claims=20)


def definitions(data):
    return data["shared_fragments"] + [part for task in data["tasks"]
                                        for part in task["parts"] if "text" in part]


def test_real_original_prose_is_defined_once_and_next_to_local_tasks():
    p = Path(__file__).parents[1] / "fixtures/narrative_claim_grounding/cn_h1_unit3.json.gz"
    case = json.loads(gzip.decompress(p.read_bytes()))
    selected = NarrativeSelectResult.from_dict(case["selected"])
    result = view(selected)
    data = result.to_model_dict()
    rows = definitions(data)
    # Adjacent single-view tasks of one page and section are merged up to the
    # claim budget, so the model receives 40 local tasks instead of 64 while
    # every selected span is still defined exactly once.
    assert len(data["tasks"]) == 40 and len(rows) == len(selected.evidence_spans) == 96
    assert len({row["source_key"] for row in rows}) == 96
    by_key = {row["source_key"]: row for row in rows}
    assert [by_key["s" + str(i)]["text"] for i in range(1, 97)] == [row.raw_text for row in selected.evidence_spans]
    assert any("text" in part for task in data["tasks"] for part in task["parts"])
    assert data["scope"] == "selected_source_tasks_only"
    assert "u_" not in json.dumps(data)  # hashes stay in program binding, not prose citations
    assert all(row.span_id not in json.dumps(data) for row in selected.evidence_spans)
    assert selected.to_dict() == case["selected"]


def test_shared_overlap_is_a_graph_not_duplicated_text_or_recursive_expansion():
    selected = with_reading()
    result = view(selected)
    data = result.to_model_dict()
    assert len(definitions(data)) == 3
    assert len(data["shared_fragments"]) == 1
    assert [len(row["parts"]) for row in data["tasks"]] == [2, 2]
    bound = result.resolve_basis("t1", ["p2"])
    assert bound.support_ids == tuple(row.span_id for row in selected.evidence_spans[:2])
    assert selected.evidence_spans[2].span_id not in bound.support_ids
    assert bound.basis_ids == (selected.evidence_spans[1].span_id,)


def test_qa_context_is_visible_once_but_cannot_be_selected_as_factual_basis():
    selected = official_reading()
    result = view(selected)
    data = result.to_model_dict()
    assert len(definitions(data)) == len(selected.evidence_spans)
    # This fixture's source context is v1; upgrade only through the source
    # contract to its genuine existing role views for this presentation probe.
    wire = selected.to_dict()
    ids = wire["reading_context"]["groups"][0]["evidence_ids"]
    wire["reading_context"]["schema_version"] = "du-production-reading/2"
    for group in wire["reading_context"]["groups"]:
        group["citation_views"] = [{"support_evidence_ids": group["evidence_ids"], "context_evidence_ids": []}]
    wire["reading_context"]["groups"][0]["citation_views"] = [
        {"support_evidence_ids": ids[1:], "context_evidence_ids": ids[:1]},
        {"support_evidence_ids": ids[:1], "context_evidence_ids": ids[1:]},
    ]
    selected = NarrativeSelectResult.from_dict(wire)
    result = view(selected)
    data = result.to_model_dict()
    task = data["tasks"][0]
    assert task["context_parts"] and task["support_parts"]
    assert len(definitions(data)) == len(selected.evidence_spans)
    with pytest.raises(ValueError):
        result.resolve_basis(task["key"], [task["context_parts"][0]])
    bound = result.resolve_basis(task["key"], task["support_parts"])
    assert bound.context_ids == tuple(ids[:1])
    assert bound.support_ids == tuple(ids[1:])


@pytest.mark.parametrize("task,parts", [("absent", ["p1"]), ("t1", []), ("t1", ["p1", "p1"]),
                                       ("t1", ["t2:p1"]), ("t1", ["p999"]), ("t1", "p1")])
def test_unknown_cross_task_duplicate_or_malformed_basis_is_not_repaired(task, parts):
    with pytest.raises(ValueError):
        view(with_reading()).resolve_basis(task, parts)


def test_binding_digest_covers_exact_source_and_task_map_not_a_second_text_store():
    selected = with_reading()
    first = view(selected)
    assert first.binding_sha256 == view(selected).binding_sha256
    assert first.binding_sha256 != view(selection(2)).binding_sha256
    assert all(row.raw_text not in json.dumps(first.to_binding(), ensure_ascii=False)
               for row in selected.evidence_spans)
    data = first.to_model_dict()
    data["tasks"].clear()
    assert len(first.to_model_dict()["tasks"]) == 2


def test_correct_task_key_and_legal_basis_still_do_not_prove_wrong_summary_text():
    selected = selection(1)
    bound = view(selected).resolve_basis("t1", ["p1"])
    wrong_text = "An unrelated product generated USD 99 billion in 2035."
    assert wrong_text not in selected.evidence_spans[0].raw_text
    # The compiler has no paraphrase input or generic entailment predicate.
    # A valid source binding therefore stays explicitly unreviewed.
    assert bound.semantic_status == "not_evaluated"
    assert bound.support_ids == (selected.evidence_spans[0].span_id,)


def test_model_presentation_does_not_mutate_source_reading_intent():
    selected = with_reading()
    before = deepcopy(selected.to_dict())
    view(selected).to_model_dict()
    assert selected.to_dict() == before


@pytest.mark.parametrize("selected", [with_reading(), official_reading()], ids=["raw", "official"])
def test_compact_defaults_losslessly_preserve_every_source_role_flag_and_task_view(selected):
    result = view(selected)
    data = result.to_model_dict()
    defaults = data["fragment_defaults"]
    by_source_key = {row["source_key"]: {**defaults, **row} for row in definitions(data)}
    for i, original in enumerate(selected.evidence_spans, 1):
        actual = by_source_key["s" + str(i)]
        assert actual["text"] == original.raw_text
        assert actual["source_role"] == original.structured_value.get("source_role", "unknown")
        assert actual["quality_flags"] == list(original.quality_flags)
    binding = result.to_binding()
    for original, task in zip(result.plan.tasks, data["tasks"], strict=True):
        actual = {**data["task_defaults"], **task}
        local = binding["task_parts"][task["key"]]
        support = list(local) if actual["support_parts"] == "all_parts" else actual["support_parts"]
        assert tuple(local[key] for key in support) == original.support_ids
        assert tuple(local[key] for key in actual["context_parts"]) == original.context_ids
        assert actual["kind"] == original.kind and actual["section_role"] == original.section_role
        assert actual["topics"] == list(original.topics)


def test_actual_material_view_does_not_grow_beyond_old_cross_table_representation():
    p = Path(__file__).parents[1] / "fixtures/narrative_claim_grounding/cn_h1_unit3.json.gz"
    case = json.loads(gzip.decompress(p.read_bytes()))
    old = json.loads(case["request"]["data_json"])
    old_material = {key: old[key] for key in ("default_source_role", "default_quality_flags",
        "evidence_columns", "evidence", "citation_unit_columns", "citation_units")}
    old_material["strategy_groups"] = old["reading_strategy"]["groups"]
    actual = view(NarrativeSelectResult.from_dict(case["selected"])).to_model_dict()
    # Material representation only: this does not measure full prompt tokens,
    # API latency or summary quality and must not be reported as those gains.
    assert len(canonical_json(actual).encode()) <= len(canonical_json(old_material).encode())
