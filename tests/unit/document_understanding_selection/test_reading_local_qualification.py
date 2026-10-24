"""Measured local qualifier dependencies use shared source relations, not project membership."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from company_wiki.document_understanding import narrative_continuity as continuity
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture

LEFT = "报告期内，公司已交付27台专用设备至客户进行生产验证。"
NEGATIVE = "该设备尚未完成量产认证，不代表已经形成批量销售。"
PENDING = "该设备仍需客户完成认证，预计下一期才能进入量产。"


@pytest.fixture(autouse=True)
def imports_owned_checkout():
    assert Path(continuity.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[3] / "src")


def case(texts, mutate=None, *, budget=None, limits=None):
    parsed, pipeline = source_fixture([(text,) for text in texts])
    wires = deepcopy(pipeline["observation"]["units"])
    if mutate:
        mutate(wires)
    provenance = {u.unit_id: {**u.metadata, "source_id": u.source_id,
                            "paragraph_index": u.coordinates.paragraph_index} for u in parsed.units}
    budget = budget if budget is not None else WorkBudget(100000)
    result = continuity.build_native_continuity(wires, provenance=provenance,
        unit_profiles=pipeline["reading_plan"]["unit_profiles"], work_budget=budget, limits=limits)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units}, work_budget=budget)
    return parsed, result, session


GUIDANCE = "预计2026年公司整体收入达到513-530亿元，持续经营业务收入同比增长18%-22%。"
STRATEGY = "公司将更加聚焦CRDMO核心战略，加速全球化能力建设和产能投放，持续提高生产经营效率。"
GUIDANCE_PREMISE = (
    "上述提及的2026年全年经营业绩展望以公司目前在手订单情况为基础预测，并以全球医药行业发展平稳、"
    "国际贸易环境和主要运营所在地国家监管环境稳定等为前提基础，并不代表公司管理层对2026年度全年"
    "经营业绩的盈利预测，不构成公司对投资者的实质承诺，能否实现取决于内外部环境变化等多种因素影响，"
    "存在较大的不确定性。"
)


def explicit_guidance_case(texts, *, section_ids=None, mutate=None):
    parsed, result, session = case(texts, mutate)
    if section_ids is None:
        section_ids = {unit.unit_id: "s1" for unit in parsed.units}
    dependencies = session.local_qualification_dependencies(
        result["adjacency_edges"], section_ids=section_ids
    )
    return parsed, result, dependencies


def test_explicit_guidance_reference_closes_over_one_same_section_paragraph_gap():
    parsed, result, dependencies = explicit_guidance_case([GUIDANCE, STRATEGY, GUIDANCE_PREMISE])
    ids = [unit.unit_id for unit in parsed.units]
    assert (ids[0], ids[2]) not in {(edge["left"], edge["right"])
                                    for edge in result["adjacency_edges"]}
    assert dependencies == {ids[0]: (ids[2],)}


def test_explicit_guidance_reference_cannot_close_over_a_different_year():
    forecast = "预计2027年公司整体收入达到513-530亿元，持续经营业务收入同比增长18%-22%。"
    parsed, _, dependencies = explicit_guidance_case([forecast, STRATEGY, GUIDANCE_PREMISE])
    assert dependencies == {}


def test_explicit_guidance_reference_needs_one_unambiguous_nearby_issuer_forecast():
    parsed, _, dependencies = explicit_guidance_case([GUIDANCE, GUIDANCE, GUIDANCE_PREMISE])
    ids = [unit.unit_id for unit in parsed.units]
    assert dependencies == {ids[1]: (ids[2],)}
    assert explicit_guidance_case(
        ["合作伙伴预计2026年全年收入达到513-530亿元。", STRATEGY, GUIDANCE_PREMISE]
    )[2] == {}


def test_explicit_guidance_reference_requires_same_nonempty_section():
    parsed, result, session = case([GUIDANCE, STRATEGY, GUIDANCE_PREMISE])
    ids = [unit.unit_id for unit in parsed.units]
    sections = {ids[0]: "s1", ids[1]: "s1", ids[2]: "s2"}
    assert session.local_qualification_dependencies(
        result["adjacency_edges"], section_ids=sections
    ) == {}


def test_explicit_guidance_reference_requires_known_same_page_source_coordinates():
    parsed, result, _ = case([GUIDANCE, STRATEGY, GUIDANCE_PREMISE])
    ids = [unit.unit_id for unit in parsed.units]
    units = {unit.unit_id: unit for unit in parsed.units}
    original = units[ids[2]]
    units[ids[2]] = replace(
        original,
        coordinates=replace(original.coordinates, page_number=original.coordinates.page_number + 1),
    )
    session = SourceOperatingSession(units, work_budget=WorkBudget(100000))
    sections = {unit_id: "s1" for unit_id in ids}
    assert session.local_qualification_dependencies(
        result["adjacency_edges"], section_ids=sections
    ) == {}


def test_explicit_guidance_reference_does_not_run_without_section_evidence():
    _, _, session = case([GUIDANCE, STRATEGY, GUIDANCE_PREMISE])
    assert session.local_qualification_dependencies([], section_ids={}) == {}


def test_explicit_guidance_reference_does_not_attach_beyond_one_intervening_paragraph():
    parsed, _, session = case([GUIDANCE, STRATEGY, STRATEGY, GUIDANCE_PREMISE])
    sections = {unit.unit_id: "s1" for unit in parsed.units}
    assert session.local_qualification_dependencies(
        [], section_ids=sections
    ) == {}


def test_adjacent_complete_source_bodies_are_proven_without_merging_statements():
    parsed, result, _ = case([LEFT, NEGATIVE])
    assert result["windows"] == []
    assert [(e["left"], e["right"]) for e in result["adjacency_edges"]] == [tuple(u.unit_id for u in parsed.units)]
    assert "text" not in result["adjacency_edges"][0]


@pytest.mark.parametrize("right", [NEGATIVE, PENDING])
def test_explicit_local_device_qualification_is_a_required_source_dependency(right):
    parsed, result, session = case([LEFT, right])
    dependencies = session.local_qualification_dependencies(result["adjacency_edges"])
    assert dependencies == {parsed.units[0].unit_id: (parsed.units[1].unit_id,)}
    assert [(u.raw_text, u.coordinates) for u in parsed.units] == [(LEFT, parsed.units[0].coordinates), (right, parsed.units[1].coordinates)]


def test_pending_customer_certification_is_not_completed_approval():
    parsed, _, session = case([LEFT, PENDING])
    relations = session.relations(parsed.units[1].unit_id)["relations"]
    certification = [r for r in relations if r["activity"] == "qualification"]
    assert certification and all(r["stage"] == "not_yet" for r in certification)
    assert all(r["modality"] == "actual" for r in certification)


@pytest.mark.parametrize("right", [
    "未来公司计划进一步完善内部流程。",
    "公司新建制造基地已经投入运行，年产能达到360台。",
    "该平台尚未完成客户认证。",
    "客户的该设备尚未完成量产认证。",
    "该设备已完成量产认证。",
    "请问该设备是否已经完成认证？",
    "该设备已完成认证，但公司尚未商业化另一平台。",
    "该设备已完成认证而另一平台尚未商业化。",
])
def test_future_other_object_party_completed_and_question_prose_do_not_become_qualifiers(right):
    _, result, session = case([LEFT, right])
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}


@pytest.mark.parametrize("change", ["source", "section", "column", "frame", "font", "order", "gap", "page", "table"])
def test_missing_native_scope_or_geometry_proof_cannot_create_a_qualifier_edge(change):
    def mutate(wires):
        right = wires[1]
        if change == "source":
            right["hints"]["source_id"] = "different-source"
        elif change == "section":
            right["hints"]["section_key"] = "different-section"
        elif change == "column":
            right["layout"]["column"] = 1
        elif change == "frame":
            right["layout"]["coordinate_frame"] = "words"
        elif change == "font":
            right["hints"]["font_runs"] = []
        elif change == "order":
            right["ordinal"] = 3
        elif change == "gap":
            right["layout"]["bbox"] = [90, 500, 550, 512]
        elif change == "page":
            right["page"] = 2
        else:
            right["hints"]["table_id"] = "table-one"
    _, result, session = case([LEFT, NEGATIVE], mutate)
    assert result["adjacency_edges"] == []
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}


def test_competing_objects_and_non_issuer_fact_cannot_donate_one_device_identity():
    for left in ["公司已交付甲型设备和乙型设备至客户开展验证。", "供应商已交付27台专用设备至客户开展验证。"]:
        _, result, session = case([left, NEGATIVE])
        assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}


def test_no_whole_project_or_recursive_future_attachment():
    parsed, result, session = case([LEFT, NEGATIVE, "公司新增制造基地已经投入运行。", "未来公司计划进一步完善内部流程。"])
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {parsed.units[0].unit_id: (parsed.units[1].unit_id,)}


def test_dependency_maps_original_edge_ids_to_material_owners_without_self_edges():
    parsed, result, session = case([LEFT, NEGATIVE])
    carrier = replace(parsed.units[0], unit_id="urn:company-wiki:narrative-unit:sha256:" + "d" * 64)
    session = SourceOperatingSession({carrier.unit_id: carrier, parsed.units[1].unit_id: parsed.units[1]},
        work_budget=WorkBudget(100000), originals={u.unit_id: u for u in parsed.units})
    assert session.local_qualification_dependencies(result["adjacency_edges"], origins={parsed.units[0].unit_id: carrier.unit_id}) == {carrier.unit_id: (parsed.units[1].unit_id,)}


def test_adjacency_respects_existing_original_window_char_limit():
    _, result, _ = case([LEFT, NEGATIVE], limits={"max_window_chars": len(LEFT) + len(NEGATIVE) - 1})
    assert result["adjacency_edges"] == []


def test_dependency_budget_exhaustion_is_partial_and_never_restarts_a_scan():
    parsed, result, session = case([LEFT, NEGATIVE])
    session.work_budget = WorkBudget(0)
    session.engine.work_budget = session.work_budget
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}
    assert session.work_budget.exhausted and not session.complete
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {}
    assert session.work_budget.used == 0


@pytest.mark.parametrize("left,right", [
    ("公司已交付專用設備至客戶開展驗證。", "該設備尚未完成量產認證。"),
    ("We delivered dedicated devices to customers for testing.", "This device has not obtained customer certification."),
])
def test_shared_grammar_reference_closure_is_not_company_or_script_specific(left, right):
    parsed, result, session = case([left, right])
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {parsed.units[0].unit_id: (parsed.units[1].unit_id,)}


@pytest.mark.parametrize("basis", [None, "unknown", "inferred_neighbour"])
def test_unproved_edge_is_not_a_positive_source_dependency(basis):
    _, result, session = case([LEFT, NEGATIVE])
    edges = [{**edge, "basis": basis} for edge in result["adjacency_edges"]]
    assert session.local_qualification_dependencies(edges) == {}


def test_a_second_explicit_restriction_inherits_only_an_already_proven_issuer_object():
    parsed, result, session = case([LEFT, NEGATIVE, "该设备仍未量产。"])
    ids = [u.unit_id for u in parsed.units]
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {ids[0]: (ids[1],), ids[1]: (ids[2],)}
    _, unknown_result, unknown_session = case([NEGATIVE, "该设备仍未量产。"])
    assert unknown_session.local_qualification_dependencies(unknown_result["adjacency_edges"]) == {}


@pytest.mark.parametrize("text", [
    "该设备尚未完成量产认证的传闻不属实。",
    "公司已经量产该设备的说法是错误的。",
    "该设备尚未认证是供应商的观点。",
])
def test_nominalised_or_reported_proposition_is_not_an_asserted_operating_state(text):
    parsed, _, session = case([text])
    relations = session.relations(parsed.units[0].unit_id)["relations"]
    assert relations
    assert all(r["polarity"] == r["stage"] == "unknown" and r["modality"] == "uncertain" for r in relations)


def test_successful_validation_and_missing_production_approval_remain_distinct_states():
    parsed, result, session = case([LEFT, "该设备已完成客户验证，但尚未获得量产认证。"])
    relations = session.relations(parsed.units[1].unit_id)["relations"]
    assert any(r["polarity"] == "positive" and r["stage"] == "current" for r in relations)
    assert any(r["polarity"] == "negative" and r["stage"] == "not_yet" for r in relations)
    assert session.local_qualification_dependencies(result["adjacency_edges"]) == {parsed.units[0].unit_id: (parsed.units[1].unit_id,)}


@pytest.mark.parametrize("right,expected", [
    ("该设备尚未向客户交付，仅完成送样。", True),
    ("该设备并未交付，仅完成送样。", True),
    ("该设备已向客户交付。", False),
    ("未来公司计划改善交付流程。", False),
])
def test_shared_observed_negative_state_is_not_limited_to_qualification_activity(right, expected):
    parsed, result, session = case([LEFT, right])
    deps = session.local_qualification_dependencies(result["adjacency_edges"])
    assert (deps == {parsed.units[0].unit_id: (parsed.units[1].unit_id,)}) is expected
