"""A computation limit cannot invent the end of an explicit source note."""
from dataclasses import replace

import pytest

from company_wiki.document_understanding.structure.contract import ObservationUnit
from company_wiki.document_understanding.structure.layout import Ordering
from company_wiki.document_understanding.structure.source_scopes import build_source_marked_scopes
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
from company_wiki.source_catalog.narrative_native_materials import prepare_native_materials

from .fixtures import Row, inherited_heading_ids, observation, run_pipeline, source


@pytest.mark.parametrize("count,boundary", [(27, "heading"), (73, "new_note")])
def test_note_limit_preserves_entire_unexamined_suffix_until_real_boundary(count, boundary):
    box = (72., 80., 528., 700.)
    rows = [Row("intro", "備註三十一：丙方的设备交付及服务义务：", block=0, box=box)]
    rows.extend(Row(f"b{i}", f"“{i+1}、公司已交付检测设备，丙方应保留原始验收记录。”",
                    block=0, box=box) for i in range(count))
    if boundary == "new_note":
        rows.extend((Row("next_intro", "备注３１：丙方的新设备服务范围：", block=0, box=box),
                     Row("next_body", "“1、公司已交付另一类新设备。”", block=0, box=box)))
    rows.extend((Row("healthy", "一、另一项业务进展", block=1, box=(72., 710., 528., 730.)),
                 Row("healthy_body", "公司已交付独立的新设备。", block=2, box=(72., 740., 528., 760.))))
    parsed, owned = source(tuple(rows))
    result, contexts = run_pipeline(parsed)
    packages, _facts, continuity, blocked = prepare_native_materials(
        parsed, result, work_budget=WorkBudget(16_000_000), _native_contexts=contexts)
    suffix = {owned[f"b{i}"].unit_id for i in range(23, count)}
    assert suffix <= blocked
    limit_diagnostics = [d for d in result["structure"]["diagnostics"]
                         if d["code"] == "SOURCE_SCOPE_LIMIT_REACHED"]
    assert all(len(d["unit_ids"]) <= 24 for d in limit_diagnostics)
    assert {uid for d in limit_diagnostics for uid in d["unit_ids"]} == suffix
    assert all(not suffix.intersection(p["anchor_unit_ids"]) for p in packages)
    assert continuity["complete"] is False
    assert owned["healthy_body"].unit_id not in blocked
    assert any(owned["healthy_body"].unit_id in p["anchor_unit_ids"] for p in packages)
    if boundary == "new_note":
        assert owned["next_body"].unit_id not in blocked
        context = inherited_heading_ids(result, owned["next_body"])
        assert owned["next_intro"].unit_id in context and owned["intro"].unit_id not in context
        assert any(owned["next_body"].unit_id in p["anchor_unit_ids"] for p in packages)


@pytest.mark.parametrize("fault", ["page_gap", "missing_proof"])
def test_unproven_relation_keeps_following_targets_unknown_until_heading(fault):
    rows = (Row("intro", "备注８：丙方的服务范围：", box=(72., 650., 528., 678.)),
            Row("previous", "“1、公司已交付检测设备。”", box=(72., 730., 528., 758.)),
            Row("failed", "“2、公司已交付第二类设备。”", page=3 if fault == "page_gap" else 1),
            Row("suffix", "“3、公司已交付第三类设备。”", page=3 if fault == "page_gap" else 1),
            Row("healthy", "一、业务进展", page=3 if fault == "page_gap" else 1),
            Row("healthy_body", "公司已交付独立的设备。", page=3 if fault == "page_gap" else 1))
    parsed, owned = source(rows)
    if fault == "missing_proof":
        failed = owned["failed"]
        reading = failed.metadata["reading_layout"]
        failed = replace(failed, metadata={**failed.metadata,
            "reading_layout": {**reading, "layout": {**reading["layout"], "column": 1}}})
        parsed = replace(parsed, units=tuple(failed if u == owned["failed"] else u for u in parsed.units))
    result, contexts = run_pipeline(parsed)
    packages, _facts, continuity, blocked = prepare_native_materials(
        parsed, result, work_budget=WorkBudget(16_000_000), _native_contexts=contexts)
    suffix = {owned["failed"].unit_id, owned["suffix"].unit_id}
    assert suffix <= blocked
    assert all(not suffix.intersection(p["anchor_unit_ids"]) for p in packages)
    assert continuity["complete"] is False
    assert owned["healthy_body"].unit_id not in blocked


def test_failure_tail_scanning_is_charged_and_cannot_publish_after_budget_exhaustion():
    parsed, _owned = source((Row("intro", "备注8：服务范围："),
                            *(Row(f"b{i}", f"{i+1}、公司已交付设备。") for i in range(40))))
    wire = observation(parsed)
    units = tuple(ObservationUnit(item, i) for i, item in enumerate(wire["units"]))
    ordering = Ordering(units, frozenset(), frozenset(), frozenset(), ())
    # Enough work to reach the original 24-unit cap, not the whole suffix.
    prefix_cost = 1 + len(units) + sum(1 + len(u.text) for u in units[:25])
    budget = WorkBudget(prefix_cost)
    with pytest.raises(WorkBudgetExceeded):
        build_source_marked_scopes(ordering, native_context=None,
            limits={"max_group_members": 64}, work_budget=budget)
    assert budget.used <= prefix_cost and budget.exhausted
