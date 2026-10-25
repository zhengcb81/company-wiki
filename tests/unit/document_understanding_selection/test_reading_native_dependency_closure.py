"""Native target dependency port TDD; valid sources and actual public citations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult,
    PromptReviewValue,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import NarrativeModelRequest
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_operating_relations import (
    SourceOperatingSession,
    _specific_context_terms,
)
from company_wiki.source_contract import source_id_for_sha256
from unit.document_understanding_selection.test_reading_guidance_condition_scope import (
    _model,
    _spans_for,
)
from unit.document_understanding_selection.test_reading_native_list_ancestry import (
    _source,
)
from support.narrative_model_request_fixture import selection as select_result_fixture


def _case(*, parent_chars=None, furniture=False):
    parent = "(1) 产品业务实现收入12亿元。"
    if parent_chars is not None:
        parent = parent[:-1] + "业务描述" * ((parent_chars - len(parent)) // 4) + "。"
        parent += "原" * (parent_chars - len(parent))
    intro = "报告期内："
    boundary = "- 新产品收入占比超过30%。"
    target = "- 客户数量同比增长20%。"
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, parent, 1, (90, 640, 550, 672)),
        (1, intro, 1, (90, 640, 550, 672)),
        (1, boundary, 2, (110, 720, 550, 732)),
    ]
    if furniture:
        rows += [
            (1, "Neutral annual report", 3, (90, 780, 550, 792)),
            (2, "Neutral annual report", 0, (90, 12, 550, 24)),
        ]
    rows += [
        (2, target, 1 if furniture else 0, (110, 70, 550, 82)),
        (2, "(2) 其他业务实现收入9亿元。", 2 if furniture else 1, (90, 130, 550, 162)),
        (2, "报告期内：", 2 if furniture else 1, (90, 130, 550, 162)),
        (2, "- 公司已交付31台设备。", 3 if furniture else 2, (110, 190, 550, 202)),
    ]
    parsed = _source(rows)
    owned = {
        key: next(u for u in parsed.units if u.raw_text == text)
        for key, text in (
            ("parent", parent),
            ("intro", intro),
            ("boundary", boundary),
            ("target", target),
        )
    }
    return parsed, owned


def _select(parsed):
    budget = WorkBudget(16_000_000)
    result = reading.select_reading_evidence(
        parsed,
        title="中性年度报告",
        existing_kind="annual_report",
        max_selected=96,
        max_chars=48000,
        work_budget=budget,
    )
    assert 0 < budget.used < budget.max_work_units
    assert (
        len(result.evidence_spans) <= 96
        and sum(len(s.raw_text or "") for s in result.evidence_spans) <= 48000
    )
    return result


def _views_for_unit(selected, unit):
    span_ids = {span.span_id for span in _spans_for(selected, unit)}
    return [
        view
        for group in selected.reading_context["groups"]
        for view in group["citation_views"]
        if span_ids.intersection(view["support_evidence_ids"])
    ]


def test_adjacent_project_milestone_and_matching_capacity_are_mutual_context():
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "2025 年9 月，公司提前完成泰兴多肽产能建设；", 1, (90, 140, 550, 172)),
        (1, "公司多肽固相合成反应釜总体积已提升至超100,000L。", 1, (90, 140, 550, 172)),
    ]
    parsed = _source(rows)
    milestone = next(unit for unit in parsed.units if "提前完成泰兴多肽产能建设" in unit.raw_text)
    capacity = next(unit for unit in parsed.units if "反应釜总体积" in unit.raw_text)
    selected = _select(parsed)
    milestone_ids = {span.span_id for span in _spans_for(selected, milestone)}
    capacity_ids = {span.span_id for span in _spans_for(selected, capacity)}
    assert milestone_ids and capacity_ids
    milestone_views = _views_for_unit(selected, milestone)
    capacity_views = _views_for_unit(selected, capacity)
    assert milestone_views and capacity_views
    assert all(
        capacity_ids <= set(view["context_evidence_ids"])
        for view in milestone_views
    )
    assert all(
        not capacity_ids.intersection(view["support_evidence_ids"])
        for view in milestone_views
    )
    assert all(
        milestone_ids <= set(view["context_evidence_ids"])
        for view in capacity_views
    )
    assert all(
        not milestone_ids.intersection(view["support_evidence_ids"])
        for view in capacity_views
    )

    model_view, task_texts = _model(selected)
    milestone_tasks = [
        task for task in model_view.plan.tasks
        if milestone_ids.intersection(task.support_ids)
    ]
    capacity_tasks = [
        task for task in model_view.plan.tasks
        if capacity_ids.intersection(task.support_ids)
    ]
    assert milestone_tasks and capacity_tasks
    assert all(
        any(capacity.raw_text in text for text in task_texts[task.key])
        for task in milestone_tasks
    )
    assert all(
        any(milestone.raw_text in text for text in task_texts[task.key])
        for task in capacity_tasks
    )
    assert all(
        not capacity_ids.intersection(task.support_ids)
        for task in milestone_tasks
    )
    assert all(
        not milestone_ids.intersection(task.support_ids)
        for task in capacity_tasks
    )


def test_adjacent_project_facts_for_different_objects_stay_separate():
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "2025 年9 月，公司提前完成泰兴多肽产能建设；", 1, (90, 140, 550, 172)),
        (1, "公司抗体药物产线新增年产能10,000批。", 1, (90, 140, 550, 172)),
    ]
    parsed = _source(rows)
    milestone = next(unit for unit in parsed.units if "提前完成泰兴多肽产能建设" in unit.raw_text)
    capacity = next(unit for unit in parsed.units if "抗体药物产线" in unit.raw_text)
    selected = _select(parsed)
    milestone_ids = {span.span_id for span in _spans_for(selected, milestone)}
    capacity_ids = {span.span_id for span in _spans_for(selected, capacity)}
    assert milestone_ids and capacity_ids
    milestone_views = _views_for_unit(selected, milestone)
    capacity_views = _views_for_unit(selected, capacity)
    assert milestone_views and capacity_views
    assert all(
        not capacity_ids.intersection(view["context_evidence_ids"])
        for view in milestone_views
    )
    assert all(
        not milestone_ids.intersection(view["context_evidence_ids"])
        for view in capacity_views
    )


def test_adjacent_project_facts_do_not_match_only_on_generic_phase_number():
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "2025 年9 月，公司提前完成一期多肽产能建设；", 1, (90, 140, 550, 172)),
        (1, "公司一期抗体药物产线新增年产能10,000批。", 1, (90, 140, 550, 172)),
    ]
    parsed = _source(rows)
    milestone = next(unit for unit in parsed.units if "提前完成一期多肽产能建设" in unit.raw_text)
    capacity = next(unit for unit in parsed.units if "一期抗体药物产线" in unit.raw_text)
    selected = _select(parsed)
    milestone_ids = {span.span_id for span in _spans_for(selected, milestone)}
    capacity_ids = {span.span_id for span in _spans_for(selected, capacity)}
    milestone_views = _views_for_unit(selected, milestone)
    capacity_views = _views_for_unit(selected, capacity)
    assert milestone_ids and capacity_ids and milestone_views and capacity_views
    assert all(
        not capacity_ids.intersection(view["context_evidence_ids"])
        for view in milestone_views
    )
    assert all(
        not milestone_ids.intersection(view["context_evidence_ids"])
        for view in capacity_views
    )


def test_adjacent_project_facts_do_not_match_on_phase_prefix_or_generic_construction_terms():
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "2025 年9 月，公司提前完成第一期泰兴多肽产能建设；", 1, (90, 140, 550, 172)),
        (1, "第一期公司抗体药物产线新增年产能10,000批。", 1, (90, 140, 550, 172)),
    ]
    parsed = _source(rows)
    first = next(unit for unit in parsed.units if "完成第一期泰兴多肽产能建设" in unit.raw_text)
    second = next(unit for unit in parsed.units if "第一期公司抗体药物产线" in unit.raw_text)
    selected = _select(parsed)
    first_ids = {span.span_id for span in _spans_for(selected, first)}
    second_ids = {span.span_id for span in _spans_for(selected, second)}
    first_views = _views_for_unit(selected, first)
    second_views = _views_for_unit(selected, second)
    assert first_ids and second_ids and first_views and second_views
    assert all(
        not second_ids.intersection(view["context_evidence_ids"])
        for view in first_views
    )
    assert all(
        not first_ids.intersection(view["context_evidence_ids"])
        for view in second_views
    )


def test_specific_context_terms_remove_generic_phrases_before_cjk_bigrams():
    milestone = "公司完成第一期项目建设；"
    capacity = "第一期另一条产线完成建设。"

    assert "第一" not in _specific_context_terms(milestone)
    assert "一期" not in _specific_context_terms(milestone)
    assert not (_specific_context_terms(milestone) & _specific_context_terms(capacity))


def test_adjacent_project_context_does_not_spread_transitively_through_middle_fact():
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "2025 年9 月，公司完成泰兴多肽产能建设；", 1, (90, 140, 550, 172)),
        (1, "公司多肽抗体项目总体产能提升至10,000批。", 1, (90, 140, 550, 172)),
        (1, "2025 年10 月，公司完成苏州抗体产线建设。", 1, (90, 140, 550, 172)),
    ]
    parsed = _source(rows)
    first = next(unit for unit in parsed.units if "完成泰兴多肽产能建设" in unit.raw_text)
    middle = next(unit for unit in parsed.units if "多肽抗体项目总体产能" in unit.raw_text)
    last = next(unit for unit in parsed.units if "完成苏州抗体产线建设" in unit.raw_text)
    fact_session = SourceOperatingSession(
        {unit.unit_id: unit for unit in parsed.units}, work_budget=WorkBudget(16_000_000)
    )
    assert "project_execution_timeline" in fact_session.fact(first.unit_id).reasons
    assert "operating_quantity" in fact_session.fact(middle.unit_id).reasons
    assert "project_execution_timeline" in fact_session.fact(last.unit_id).reasons
    assert _specific_context_terms(first.raw_text) & _specific_context_terms(middle.raw_text)
    assert _specific_context_terms(middle.raw_text) & _specific_context_terms(last.raw_text)
    adjacency = [
        {"left": left.unit_id, "right": right.unit_id, "source_id": parsed.source_id,
         "basis": "source_body_adjacency", "left_page": 1, "right_page": 1}
        for left, right in ((first, middle), (middle, last))
    ]
    dependencies = fact_session.local_operating_context_dependencies(
        adjacency, section_ids={unit.unit_id: "operations" for unit in (first, middle, last)}
    )
    assert middle.unit_id in dependencies[first.unit_id]
    assert last.unit_id in dependencies[middle.unit_id]
    identity_components = {unit.unit_id: {unit.unit_id} for unit in (first, middle, last)}
    assert reading._package_local_context_members(
        (first.unit_id,), identity_components, dependencies
    ) == {middle.unit_id}
    selected = _select(parsed)
    first_ids = {span.span_id for span in _spans_for(selected, first)}
    middle_ids = {span.span_id for span in _spans_for(selected, middle)}
    last_ids = {span.span_id for span in _spans_for(selected, last)}
    first_views = _views_for_unit(selected, first)
    last_views = _views_for_unit(selected, last)
    assert first_ids and middle_ids and last_ids and first_views and last_views
    assert any(middle_ids.intersection(view["context_evidence_ids"]) for view in first_views)
    assert all(not last_ids.intersection(view["context_evidence_ids"]) for view in first_views)


@pytest.mark.parametrize(
    "boundary",
    ("missing_edge", "non_native_edge", "source_mismatch", "different_source",
     "different_page", "different_section", "different_role", "budget_exhausted"),
)
def test_project_context_requires_native_same_source_page_section_and_role(boundary):
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "2025 年9 月，公司提前完成泰兴多肽产能建设；", 1, (90, 140, 550, 172)),
        (1, "公司多肽固相合成反应釜总体积已提升至超100,000L。", 1, (90, 140, 550, 172)),
    ]
    parsed = _source(rows)
    milestone = next(unit for unit in parsed.units if "提前完成泰兴多肽产能建设" in unit.raw_text)
    capacity = next(unit for unit in parsed.units if "反应釜总体积" in unit.raw_text)
    units = {unit.unit_id: unit for unit in parsed.units}
    sections = {milestone.unit_id: "operations", capacity.unit_id: "operations"}
    edge = {
        "basis": "source_body_adjacency",
        "left": milestone.unit_id,
        "right": capacity.unit_id,
        "source_id": parsed.source_id,
        "left_page": 1,
        "right_page": 1,
    }
    edges = [edge]
    if boundary == "missing_edge":
        edges = []
    elif boundary == "non_native_edge":
        edge["basis"] = "semantic_similarity"
    elif boundary == "source_mismatch":
        edge["source_id"] = "urn:company-wiki:source:other"
    elif boundary == "different_source":
        units[capacity.unit_id] = replace(capacity, source_id="urn:company-wiki:source:other")
    elif boundary == "different_page":
        units[capacity.unit_id] = replace(
            capacity, coordinates=replace(capacity.coordinates, page_number=2)
        )
        edge["right_page"] = 2
    elif boundary == "different_section":
        sections[capacity.unit_id] = "other_operations"
    elif boundary == "different_role":
        units[capacity.unit_id] = replace(capacity, source_role="news_article")
    budget = WorkBudget(0 if boundary == "budget_exhausted" else 100_000)

    session = SourceOperatingSession(units, work_budget=budget)
    assert session.local_operating_context_dependencies(
        edges, section_ids=sections
    ) == {}
    assert session.complete is (boundary != "budget_exhausted")


def test_independent_native_boundary_is_proof_not_other_target_model_material():
    parsed, units = _case()
    selected = _select(parsed)
    spans = {
        key: {s.span_id for s in _spans_for(selected, unit)}
        for key, unit in units.items()
    }
    assert all(spans.values())
    citations = [
        c
        for g in selected.reading_context["groups"]
        for c in g["citation_views"]
        if spans["target"].intersection(c["support_evidence_ids"])
    ]
    assert citations
    assert all(
        not spans["boundary"].intersection(c["context_evidence_ids"]) for c in citations
    )
    # The target is no dependency of the earlier same-list boundary.
    first = [
        c
        for g in selected.reading_context["groups"]
        for c in g["citation_views"]
        if spans["boundary"].intersection(c["support_evidence_ids"])
    ]
    assert first and all(
        not spans["target"].intersection(c["context_evidence_ids"]) for c in first
    )
    view, texts = _model(selected)
    tasks = [t for t in view.plan.tasks if spans["target"].intersection(t.support_ids)]
    assert tasks and all(
        not spans["boundary"].intersection(t.member_ids) for t in tasks
    )
    assert all(
        any(units["target"].raw_text in text for text in texts[t.key]) for t in tasks
    )
    assert all(
        not any(units["boundary"].raw_text in text for text in texts[t.key])
        for t in tasks
    )
    groups = [
        g
        for g in selected.reading_context["groups"]
        if any(
            spans["target"].intersection(c["support_evidence_ids"])
            for c in g["citation_views"]
        )
    ]
    assert groups and all(
        units["boundary"].unit_id in g["source_proof_unit_ids"] for g in groups
    )


def test_readable_native_ancestry_obeys_joint_character_limit_without_a_deictic():
    parsed, units = _case(parent_chars=2040)
    selected = _select(parsed)
    assert not _spans_for(selected, units["target"])
    assert any(
        d["reason"] == "REFERENCE_ENVELOPE"
        for d in selected.reading_context["deferred"]
    )


def _collect(parsed, semantics, *, furniture=(), account=None):
    from company_wiki.source_catalog import narrative_native_dependencies as native

    account = account if account is not None else WorkBudget(10000)
    return native.collect_native_dependencies(
        semantics,
        originals={u.unit_id: u for u in parsed.units},
        furniture_ids=frozenset(furniture),
        work_budget=account,
    )


def test_native_per_target_map_preserves_within_owner_dependencies_without_owner_wide_union():
    parsed, u = _case()
    a, b, c = (u[k].unit_id for k in ("target", "boundary", "parent"))
    semantic = {"member_unit_ids": [a, b], "required_context_by_unit_id": {a: [b, c]}}
    result = _collect(parsed, [semantic])
    assert result.context_for(a) == frozenset((b, c))
    assert result.context_for(b) == frozenset()
    assert not result.blocked


def test_nested_native_proof_closure_preserves_target_ids_separate_from_physical_refs():
    parsed, units = _case(furniture=True)
    target = units["target"].unit_id
    parent = units["parent"].unit_id
    left = units["boundary"].unit_id
    furniture = [unit.unit_id for unit in parsed.units
                  if unit.raw_text == "Neutral annual report"]
    ordinals = {unit.unit_id: index for index, unit in enumerate(parsed.units)}
    proof = {
        "basis": "observed_adjacent_page_flow",
        "left": left,
        "right": target,
        "left_page": units["boundary"].coordinates.page_number,
        "right_page": units["target"].coordinates.page_number,
        "left_ordinal": ordinals[left],
        "right_ordinal": ordinals[target],
        "column": 0,
        "coordinate_frame": "pdf_page",
        "furniture_unit_ids": furniture,
    }
    semantics = [
        {"member_unit_ids": [target],
         "required_source_unit_ids_by_unit_id": {target: [left, *furniture]},
         "native_source_proofs_by_unit_id": {target: [proof]}},
        {"member_unit_ids": [parent],
         "required_context_by_unit_id": {parent: [target]}},
    ]

    result = _collect(parsed, semantics, furniture=furniture)

    assert not result.blocked
    assert target in result.proof_targets_for(parent)
    assert target not in result.source_for(parent)
    assert result.source_for(parent) == frozenset((left, *furniture))
    assert result.proofs_for(parent) == (proof,)


@pytest.mark.parametrize(
    "fault",
    ("missing", "foreign", "cycle", "nonmember_target", "bad_shape", "fake_furniture"),
)
def test_invalid_native_proof_cannot_become_a_smaller_valid_context(fault):
    from dataclasses import replace

    parsed, u = _case()
    a, b = u["target"].unit_id, u["boundary"].unit_id
    semantics = [{"member_unit_ids": [a, b], "required_context_by_unit_id": {a: [b]}}]
    if fault == "missing":
        semantics[0]["required_context_by_unit_id"][a] = ["absent-original"]
    elif fault == "foreign":
        units = tuple(
            replace(x, source_id="foreign-original") if x.unit_id == b else x
            for x in parsed.units
        )
        parsed = replace(parsed, units=units)
    elif fault == "cycle":
        semantics[0]["required_context_by_unit_id"][b] = [a]
    elif fault == "nonmember_target":
        semantics[0]["member_unit_ids"] = [a]
        semantics[0]["required_context_by_unit_id"] = {b: [a]}
    elif fault == "bad_shape":
        semantics[0]["required_context_by_unit_id"] = {a: "not-an-id-list"}
    else:
        semantics[0]["required_source_unit_ids_by_unit_id"] = {a: [b]}
    before = deepcopy(semantics)
    result = _collect(parsed, semantics)
    assert a in result.blocked
    assert result.diagnostics
    assert semantics == before


def test_native_dependency_collection_refuses_zero_work_before_expanding_fields():
    class NeverRead(dict):
        def get(self, *args):
            raise AssertionError("native proof must be charged before expansion")

    with pytest.raises(WorkBudgetExceeded):
        _collect(_case()[0], [NeverRead()], account=WorkBudget(0))


def test_running_furniture_binds_physical_refs_without_becoming_model_material():
    parsed, u = _case(furniture=True)
    selected = _select(parsed)
    footer_ids = {
        unit.unit_id
        for unit in parsed.units
        if unit.raw_text == "Neutral annual report"
    }
    assert len(footer_ids) == 2
    assert not any(
        span.raw_text == "Neutral annual report" for span in selected.evidence_spans
    )
    support = {s.span_id for s in _spans_for(selected, u["target"])}
    assert support
    groups = [
        g
        for g in selected.reading_context["groups"]
        if any(
            support.intersection(c["support_evidence_ids"]) for c in g["citation_views"]
        )
    ]
    assert groups and all(
        set(g.get("source_proof_unit_ids", ())) == footer_ids | {u["boundary"].unit_id}
        for g in groups
    )
    by_span = {
        span.span_id: unit
        for unit in parsed.units
        for span in _spans_for(selected, unit)
    }
    for group in groups:
        for citation in group["citation_views"]:
            actual = {
                sid
                for sid in (
                    *citation["support_evidence_ids"],
                    *citation["context_evidence_ids"],
                )
            }
            materials = [by_span[sid] for sid in actual]
            assert (
                len(
                    {
                        (unit.coordinates.page_number, unit.metadata["pdf_block"])
                        for unit in materials
                    }
                )
                == 3
            )
    view, texts = _model(selected)
    tasks = [task for task in view.plan.tasks if support.intersection(task.support_ids)]
    assert tasks and all(
        not any("Neutral annual report" in text for text in texts[task.key])
        for task in tasks
    )


def test_native_page_proofs_survive_public_select_transport_and_stay_out_of_model_input(monkeypatch):
    parsed, source_units = _case(furniture=True)
    target_id = source_units["target"].unit_id
    nested_parent = next(unit for unit in parsed.units
                         if unit.raw_text == "(2) 其他业务实现收入9亿元。")
    parent_id = nested_parent.unit_id
    understand = reading._understand

    def add_nested_context(parsed_source, **kwargs):
        pipeline = understand(parsed_source, **kwargs)
        semantics = list(pipeline["structure"]["semantic_units"])
        semantics.append({
            "member_unit_ids": [parent_id, target_id],
            "required_context_by_unit_id": {parent_id: [target_id]},
        })
        pipeline["structure"] = {**pipeline["structure"], "semantic_units": semantics}
        return pipeline

    monkeypatch.setattr(reading, "_understand", add_nested_context)
    package = _select(parsed)
    assert any(group.get("source_proofs") for group in package.reading_context["groups"])

    selected_wire = select_result_fixture(4).to_dict()
    selected_wire["source_ref"]["content_sha256"] = package.source_sha256
    selected_wire["source_ref"]["source_id"] = source_id_for_sha256(package.source_sha256)
    event = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0",
        "source_ref": selected_wire["source_ref"],
        "expected_read_policy_sha256": selected_wire["expected_read_policy_sha256"],
        "source_metadata": selected_wire["source_metadata"],
    })
    parsed_result = SimpleNamespace(
        page_count=parsed.page_count,
        pages_read=parsed.pages_read,
        line_count=0,
        table_scan_pages=(),
        deferred_table_pages=(),
    )
    parser_identity = (
        package.evidence_spans[0].parser_name,
        package.evidence_spans[0].parser_version,
    )
    work = SimpleNamespace(parsed=parsed_result, package=package, material=None,
                           parser_identity=parser_identity)
    raw = NarrativeSelectHandler._result_dict(
        event, PromptReviewValue.from_dict(selected_wire["prompt_review"]), work,
        selector_version="0.9.0",
    )

    public = NarrativeSelectResult.from_dict(raw)
    public_proofs = [proof for group in public.reading_context["groups"]
                     for proof in group.get("source_proofs", ())]
    assert public_proofs
    target_endpoint_bound = False
    for group in public.reading_context["groups"]:
        if group.get("source_proofs"):
            proof_ids = set(group["source_proof_unit_ids"])
            target_ids = set(group["source_proof_target_unit_ids"])
            for proof in group["source_proofs"]:
                endpoints = {proof["left"], proof["right"]}
                assert endpoints <= proof_ids | target_ids
                target_endpoint_bound |= bool(endpoints & target_ids)
                assert set(proof["furniture_unit_ids"]) <= proof_ids | target_ids
    assert target_endpoint_bound
    parent_span_ids = {span.span_id for span in _spans_for(package, nested_parent)}
    nested_groups = [group for group in public.reading_context["groups"]
                     if parent_span_ids & set(group["evidence_ids"])
                     and group.get("source_proofs")]
    assert nested_groups
    assert any(target_id in group["source_proof_target_unit_ids"] for group in nested_groups)
    request = NarrativeModelRequest.from_selection(public)
    assert "source_proofs" not in request.data_json
    assert "source_proof_unit_ids" not in request.data_json
    assert "source_proof_target_unit_ids" not in request.data_json


@pytest.mark.parametrize("fault", ("missing_one", "missing_map", "note_as_furniture"))
def test_source_only_proof_cannot_omit_a_witness_or_hide_footnote(fault):
    from dataclasses import replace

    parsed, u = _case(furniture=True)
    furniture = [
        unit for unit in parsed.units if unit.raw_text == "Neutral annual report"
    ]
    a = u["target"].unit_id
    references = [unit.unit_id for unit in furniture]
    pipeline = reading._understand(
        parsed,
        title="中性年度报告",
        kind="annual_report",
        mime_type="application/pdf",
        work_budget=WorkBudget(16_000_000),
    )
    semantics = deepcopy(pipeline["structure"]["semantic_units"])
    semantic = next(
        row for row in semantics if a in row.get("native_source_proofs_by_unit_id", {})
    )
    baseline = _collect(parsed, semantics, furniture=references)
    assert a not in baseline.blocked
    if fault == "missing_one":
        semantic["required_source_unit_ids_by_unit_id"][a].remove(references[-1])
    elif fault == "missing_map":
        semantic.pop("required_source_unit_ids_by_unit_id")
    else:
        changed = tuple(
            replace(unit, unit_kind="html_footnote")
            if unit.unit_id == references[0]
            else unit
            for unit in parsed.units
        )
        parsed = replace(parsed, units=changed)
    result = _collect(parsed, semantics, furniture=references)
    assert a in result.blocked and result.diagnostics


def test_a_real_cross_page_restriction_stays_readable_despite_structural_proof_use():
    left = "- 报告期内，公司已交付27台专用设备至客户进行生产验证。"
    right = "- 该设备尚未完成量产认证，不代表已经形成批量销售。"
    rows = [
        (1, "一、经营情况", 0, (90, 100, 550, 112)),
        (1, "(1) 设备业务实现收入12亿元。", 1, (90, 640, 550, 672)),
        (1, "报告期内：", 1, (90, 640, 550, 672)),
        (1, left, 2, (110, 720, 550, 732)),
        (2, right, 0, (110, 70, 550, 82)),
    ]
    parsed = _source(rows)
    selected = _select(parsed)
    a, b = parsed.units[-2:]
    left_ids = {s.span_id for s in _spans_for(selected, a)}
    right_ids = {s.span_id for s in _spans_for(selected, b)}
    assert left_ids and right_ids
    views = [
        c
        for g in selected.reading_context["groups"]
        for c in g["citation_views"]
        if left_ids.intersection(c["support_evidence_ids"])
    ]
    assert views and all(
        right_ids.intersection(c["support_evidence_ids"]) for c in views
    )
    from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
    from company_wiki.document_understanding.source_cards import source_cards
    plan = build_summary_task_plan(selected.evidence_spans,
                                   reading_context=selected.reading_context, max_claims=40)
    cards = [card for card in source_cards(plan, {
        span.span_id: span for span in selected.evidence_spans})
        if left_ids.intersection(card.task.support_ids)]
    assert cards and all(left in (card.text or '') and right in (card.text or '') for card in cards)
