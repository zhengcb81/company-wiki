"""Source-owned summary tasks preserve existing scope; they do not rank prose."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import gzip
import json
from pathlib import Path

import pytest

from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256
from unit.document_understanding_selection.test_closed_group_support import SOURCE, context, span


def plan(rows, ctx=None, *, max_claims=20):
    return build_summary_task_plan(rows, reading_context=ctx, max_claims=max_claims)


def test_real_source_groups_become_tasks_without_a_second_selection():
    p = Path(__file__).parents[1] / "fixtures/narrative_claim_grounding/cn_h1_unit3.json.gz"
    case = json.loads(gzip.decompress(p.read_bytes()))
    selected = case["selected"]
    rows = tuple(EvidenceSpan.from_dict(row) for row in selected["evidence_spans"])
    before = deepcopy(selected)
    result = plan(rows, selected["reading_context"])
    assert len(result.tasks) == 64
    assert result.evidence_order == tuple(row.span_id for row in rows)
    assert {sid for task in result.tasks for sid in task.member_ids} == set(result.evidence_order)
    # The planner keeps references, not a second copy of 96 excerpts or a model
    # side product whitelist. Source order and current native scopes survive.
    assert not any(row.raw_text in json.dumps(result.to_binding(), ensure_ascii=False)
                   for row in rows if len(row.raw_text) > 20)
    assert selected == before
    assert result.coverage(())["not_emitted_task_keys"] == [task.key for task in result.tasks]


def test_overlapping_groups_never_expand_to_their_neighbor_closure():
    rows = [span("共同的原文标题", 0, heading=1), span("设备甲已验证。", 1), span("设备乙尚未投产。", 2)]
    ctx = context(rows, kind="background", groups=[rows[:2], [rows[0], rows[2]]])
    result = plan(rows, ctx)
    assert [task.member_ids for task in result.tasks] == [
        tuple(row.span_id for row in rows[:2]), (rows[0].span_id, rows[2].span_id)]
    assert result.tasks[0].support_ids == result.tasks[0].member_ids
    assert result.tasks[0].context_ids == ()


def test_qa_views_keep_factual_support_separate_from_shared_exchange_context():
    rows = [span("是否计划2027年投产？", 0, role="investor_question"),
            span("目前尚无投产时间表。", 1, role="management")]
    ctx = context(rows, kind="qa_pair")
    ctx["schema_version"] = "du-production-reading/2"
    ctx["groups"][0]["citation_views"] = [
        {"support_evidence_ids": [rows[1].span_id], "context_evidence_ids": [rows[0].span_id]},
        {"support_evidence_ids": [rows[0].span_id], "context_evidence_ids": [rows[1].span_id]},
    ]
    result = plan(rows, ctx)
    assert [task.support_ids for task in result.tasks] == [(rows[1].span_id,), (rows[0].span_id,)]
    assert [task.context_ids for task in result.tasks] == [(rows[0].span_id,), (rows[1].span_id,)]
    assert all(task.member_ids == tuple(row.span_id for row in rows) for task in result.tasks)
    assert [task.support_roles for task in result.tasks] == [("management",), ("investor_question",)]


def test_genuinely_ungrouped_material_only_becomes_standalone_tasks():
    rows = [span("设备甲已验证。", 0), span("设备乙尚未投产。", 1), span("海外业务已开展。", 2)]
    result = plan(rows, context(rows[:2], kind="background"))
    assert [len(task.member_ids) for task in result.tasks] == [2, 1]
    assert result.tasks[-1].member_ids == (rows[2].span_id,)


def test_source_intent_is_observed_metadata_and_never_an_inferred_fact():
    row = span("公司尚未披露订单金额。", 0)
    wire = row.to_dict()
    wire["structured_value"].update(topics=["new_business"], selection_reasons=["reading_plan"])
    actual = EvidenceSpan.create(source_id=row.source_id, coordinates=row.coordinates,
        raw_text=row.raw_text, structured_value=wire["structured_value"],
        parser_name=row.parser_name, parser_version=row.parser_version,
        parse_status=row.parse_status, quality_flags=row.quality_flags)
    result = plan([actual])
    assert result.tasks[0].topics == ("new_business",)
    assert result.tasks[0].selection_reasons == ("reading_plan",)
    assert result.tasks[0].kind == "standalone"
    assert result.tasks[0].section_role == "unknown"
    observation = result.coverage([result.tasks[0].key])
    assert observation["semantic_status"] == "not_evaluated"
    assert observation["scope"] == "selected_source_tasks_only"
    assert observation["source_task_coverage_complete"] is True


def test_local_key_reordering_changes_plan_not_immutable_source_identity():
    rows = [span("设备甲已验证。", 0), span("设备乙尚未投产。", 1)]
    first, second = plan(rows), plan(list(reversed(rows)))
    assert first.binding_sha256 != second.binding_sha256
    assert first.tasks[0].member_ids == second.tasks[1].member_ids
    assert first.tasks[0].key != second.tasks[1].key
    assert first.to_binding()["schema_version"] == "source-summary-task-plan/1"


def test_tasks_are_immutable_and_coverage_does_not_require_every_task_to_emit():
    rows = [span("设备甲已验证。", 0), span("设备乙尚未投产。", 1)]
    result = plan(rows, max_claims=1)
    assert len(result.tasks) == 2  # a claim limit never silently drops source tasks
    with pytest.raises(FrozenInstanceError):
        result.tasks[0].kind = "fabricated"
    coverage = result.coverage([result.tasks[0].key, result.tasks[0].key])
    assert coverage["emitted_task_count"] == 1
    assert coverage["not_emitted_task_keys"] == [result.tasks[1].key]
    assert coverage["semantic_status"] == "not_evaluated"


@pytest.mark.parametrize("change", ["duplicate_span", "unknown_member", "foreign_parent", "unknown_view", "overlapping_view"])
def test_plan_cannot_create_source_members_or_qa_views(change):
    rows = [span("设备甲已验证。", 0), span("设备乙尚未投产。", 1)]
    ctx = context(rows, kind="background")
    if change == "duplicate_span":
        rows.append(rows[0])
    elif change == "unknown_member":
        ctx["groups"][0]["evidence_ids"].append("absent")
    elif change == "foreign_parent":
        rows[1] = span("设备乙尚未投产。", 1, source=source_id_for_sha256("b" * 64))
        ctx = context(rows, kind="background")
    else:
        ctx["schema_version"] = "du-production-reading/2"
        ctx["groups"][0]["citation_views"] = [{
            "support_evidence_ids": ["absent"] if change == "unknown_view" else [rows[0].span_id],
            "context_evidence_ids": [rows[1].span_id] if change == "unknown_view" else [row.span_id for row in rows],
        }]
    with pytest.raises(ValueError):
        plan(rows, ctx)


def test_separate_official_parents_remain_separate_source_tasks():
    rows = [span("甲公司管理层回答。", 0, role="management"),
            span("乙公司管理层回答。", 1, role="management", source=source_id_for_sha256("b" * 64))]
    result = plan(rows)
    assert [task.source_id for task in result.tasks] == [SOURCE, rows[1].source_id]
    with pytest.raises(ValueError):
        result.coverage(["not-a-task"])


@pytest.mark.parametrize("field", ["kind", "section_role"])
def test_mutable_noncanonical_group_labels_cannot_enter_an_immutable_plan(field):
    rows = [span("公司新系列已经量产。", 0)]
    ctx = context(rows, kind="background")
    ctx["groups"][0][field] = ["mutable-label"]
    with pytest.raises(ValueError):
        plan(rows, ctx)


def test_unknown_json_role_projects_to_unknown_before_deduplicating_roles():
    rows = [span("角色来源尚不明确。", 0, role={"unexpected": "management"}),
            span("另一条记录角色也未分类。", 1, role=None)]
    result = plan(rows, context(rows, kind="background"))
    assert result.tasks[0].support_roles == ("unknown",)
