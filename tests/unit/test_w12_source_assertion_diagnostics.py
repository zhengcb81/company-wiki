"""Source-owned requirement and action diagnostics through the public summary recipe."""

from dataclasses import replace
from hashlib import sha256
import json
import socket

import pytest

from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request, resolve_model_boundary
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.document_understanding.assertion_frames import ASSERTION_FRAME_PROFILE, source_assertion_frames
from company_wiki.source_catalog.narrative_contracts import NarrativeSelectResult
from company_wiki.source_catalog.narrative_summary_protocols import ASSERTION_ASSESSMENT_VERSION
from support.fresh_summary_fixture import grouped_selection
from unit.test_narrative_reading_transport import reading_context


PROJECTION = "reading-model-input/8"
HISTORICAL_PROJECTION = "reading-model-input/7"


@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    def reject(*_args, **_kwargs):
        pytest.fail("an assertion diagnostic must not make an external request")

    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)


def selection_with_context(support, contexts=(), *, language="zh"):
    texts = (*contexts, support)
    original = grouped_selection(texts, groups=("business",) * len(texts), language=language)
    ids = [span.span_id for span in original.evidence_spans]
    group_id = "urn:company-wiki:reading-group:sha256:" + sha256(json.dumps(ids).encode()).hexdigest()
    context = reading_context(original)
    context.update(schema_version="du-production-reading/2", groups=[{
        "group_id": group_id,
        "kind": "business_progress",
        "section_role": "business",
        "evidence_ids": ids,
        "citation_views": [{"support_evidence_ids": ids[-1:], "context_evidence_ids": ids[:-1]}],
    }])
    return NarrativeSelectResult.from_dict(replace(original, reading_context=context).to_dict())


@pytest.mark.parametrize("source,language", [
    ("客户需求扩大，公司已完成区域物流网络改造。", "zh"),
    ("供需关系保持稳定，公司已完成年度货运安排。", "zh"),
    ("冷链供需通过平台进行匹配，公司已完成服务接口改造。", "zh"),
    ("市場對檢測服務的需求增長，公司已擴大跨境服務。", "zh"),
    ("公司已完成客户需求确认。", "zh"),
    ("公司已完成客戶需求審核。", "zh"),
    ("内需通过下游渠道测量。", "zh"),
    ("报告列出投产所需确认的材料。", "zh"),
    ("管理层讨论是否需要履行验收流程。", "zh"),
    ("Customer demand increased after the group expanded its logistics network.", "en"),
])
def test_business_demand_does_not_create_a_pending_condition_in_model_input(source, language):
    selected = selection_with_context(source, language=language)
    request = build_model_request(selected, reading_projection_version=PROJECTION)
    material = json.loads(request.data_json)["material"]

    assert material["available_task_count"] == 1
    assert source in json.dumps(material, ensure_ascii=False)
    assert not any(row.get("condition_present") for rows in material["source_frame_hints"]["sources"].values()
                   for row in rows)


@pytest.mark.parametrize("source,language", [
    ("公司已完成设备安装，该项目仍需监管批准后方可投产。", "zh"),
    ("该项目需经安全审查才可开始正式生产。", "zh"),
    ("该交易需要监管批准后才能交割。", "zh"),
    ("该项目仍需客户确认。", "zh"),
    ("交易所需要完成合规验收。", "zh"),
    ("The operator finished installation, and the facility requires approval before it starts.", "en"),
])
def test_explicit_approval_remains_a_pending_condition(source, language):
    selected = selection_with_context(source, language=language)
    request = build_model_request(selected, reading_projection_version=PROJECTION)
    sources = json.loads(request.data_json)["material"]["source_frame_hints"]["sources"]

    assert any(row.get("condition_present") for rows in sources.values() for row in rows)


def test_non_predicate_fragments_do_not_donate_or_cancel_the_actual_requirement():
    frames = source_assertion_frames(
        "该项目已经完成客户需求确认且不再需要加签但仍需完成安全验收。", profile=ASSERTION_FRAME_PROFILE,
    )
    frame, = frames
    assert frame.pending_requirement == "完成安全验收"
    assert frame.requirement_proposition.endswith("但")


def decode_planned(support, contexts, language, *, claim_text=None, projection=PROJECTION):
    selected = selection_with_context(support, contexts, language=language)
    selected_before = selected.to_dict()
    request = build_model_request(selected, reading_projection_version=projection)
    view = compile_scoped_model_view(selected, max_claims=40)
    task, = view.model_tasks
    assert task.support_ids == (selected.evidence_spans[-1].span_id,)
    assert task.context_ids == tuple(span.span_id for span in selected.evidence_spans[:-1])
    aliases = [key for key, sid in view.to_binding()["task_parts"][task.key].items() if sid in task.support_ids]
    expected_text = support if claim_text is None else claim_text
    response = NarrativeModelResponse(
        "offline", "assertion-fixture", request.prompt_version,
        json.dumps({"drafts_by_task": {task.key: [{
            "text": expected_text, "basis_parts": aliases, "modality": "planned",
        }]}}, ensure_ascii=False).encode(),
    )
    report = {}
    summary = NarrativeSummarizeHandler._completed_result(
        selected, selected.prompt_review, response, reading_projection_version=projection,
        execution_report=report,
    )
    claim, = summary.to_dict()["draft"]["claims"]
    assert selected.to_dict() == selected_before
    assert claim["text"] == expected_text
    assert claim["modality"] == "planned"
    assert claim["evidence_ids"] == list(task.support_ids)
    assert claim.get("context_evidence_ids", []) == list(task.context_ids)
    assert claim["claim_type"] == "company_statement"
    return claim, report


@pytest.mark.parametrize("context,support,language", [
    ("报告期内：", "提前启动区域冷链仓建设，以改善当地生鲜服务。", "zh"),
    ("報告期內：", "提前啟動區域冷鏈倉建設，以改善當地生鮮服務。", "zh"),
    ("During the quarter:", "The operator began construction of a cold-storage facility.", "en"),
    ("经营动态：", "公司已启动冷库建设，投产验收仍需主管部门批准。", "zh"),
    ("经营动态：", "报告期内，提前启动区域冷库建设。", "zh"),
])
def test_start_in_reported_period_can_flag_planned_draft_without_rewriting_it(context, support, language):
    claim, report = decode_planned(support, (context,), language)

    assert report["validator"]["version"] == ASSERTION_ASSESSMENT_VERSION
    assert claim["needs_review"]
    assert any(row["rule_code"] == "possible_current_action_as_future"
               and row["source_span_id"] == claim["evidence_ids"][0]
               for row in report["diagnostics"])


@pytest.mark.parametrize("contexts,support,language", [
    (("报告期内：",), "公司计划明年启动新生产线建设。", "zh"),
    (("报告期内：",), "若取得监管批准，公司将启动新生产线建设。", "zh"),
    (("报告期内：",), "公司尚未启动新生产线建设。", "zh"),
    (("报告期内：",), "如果取得监管批准，提前启动新生产线建设。", "zh"),
    (("报告期内：",), "如果设备验收合格，团队正在建设配套网络，则新订单可以交付。", "zh"),
    (("报告期内：", "下一步："), "提前启动新生产线建设。", "zh"),
    (("报告期内：",), "公司计划提前启动新生产线建设。", "zh"),
    (("报告期内：",), "公司尚未提前启动新生产线建设。", "zh"),
    (("报告期内：",), "本期尚不具备提前启动供应链项目的条件。", "zh"),
    (("报告期内：",), "管理层讨论了提前启动新厂区建设的建议。", "zh"),
    (("报告期内：",), "拟于年底试行新的物流项目，正式启动冷链服务。", "zh"),
    (("报告期内：",), "公司是否已经启动新生产线建设？", "zh"),
    (("报告期内：",), "公司已经提前启动新生产线了吗？", "zh"),
    (("供应商报告期内：",), "另一家公司拟于明年启动新生产线建设。", "zh"),
    (("During the quarter:",), "The operator plans to start construction of the new facility.", "en"),
    (("During the quarter:",), "The operator had not started construction of the new facility.", "en"),
    (("During the quarter:",), "Management asked whether the operator had started construction.", "en"),
])
def test_action_status_does_not_borrow_from_a_past_heading_or_other_subject(contexts, support, language):
    _claim, report = decode_planned(support, contexts, language)

    assert not any(row["rule_code"] == "possible_current_action_as_future" for row in report["diagnostics"])


def test_same_action_phrase_does_not_bind_another_actor():
    _claim, report = decode_planned(
        "供应商提前启动新生产线建设。", ("报告期内：",), "zh",
        claim_text="公司提前启动新生产线建设。",
    )

    assert not any(row["rule_code"] == "possible_current_action_as_future" for row in report["diagnostics"])


@pytest.mark.parametrize("source", [
    "提前启动区域冷链仓建设，拟明年正式启动冷链服务。",
    "拟于年底推进商业运营，公司已经启动冷库建设。",
    "原项目尚不具备开工条件，另一家单位已正式启动冷库建设。",
    "管理层讨论了正式启动厂区扩建的建议，运营团队已启动新的仓储建设。",
    "管理层讨论是否正式启动厂区扩建，运营团队已启动新的仓储建设。",
    "交付组已将旧设备迁出，提前启动新仓建设。",
])
def test_a_started_action_and_its_distinct_nearby_plan_remain_independent(source):
    frames = source_assertion_frames(source, profile=ASSERTION_FRAME_PROFILE, reporting_period=True)
    starts = [frame.matching_text for frame in frames if frame.reported_start]
    assert len(starts) == 1 and "建设" in starts[0]
    _claim, actual_report = decode_planned(source, ("报告期内：",), "zh", claim_text=starts[0])
    assert any(row["rule_code"] == "possible_current_action_as_future" for row in actual_report["diagnostics"])
    other_clause, = [frame.matching_text for frame in frames if not frame.reported_start]
    _claim, other_report = decode_planned(source, ("报告期内：",), "zh", claim_text=other_clause)
    assert not any(row["rule_code"] == "possible_current_action_as_future" for row in other_report["diagnostics"])


def test_unavailable_word_boundaries_leave_the_qualified_proposal_unclassified(monkeypatch):
    monkeypatch.setattr("company_wiki.document_understanding.assertion_frames.chinese_word_boundaries", lambda _text: None)
    source = "管理层讨论了正式启动厂区扩建。"
    claim, report = decode_planned(source, ("报告期内：",), "zh")
    assert claim["text"] == source
    assert not any(row["rule_code"] == "possible_current_action_as_future" for row in report["diagnostics"])


@pytest.mark.parametrize("source,claim_text,expected", [
    ("运营方认为客户需求正在增长。", "运营方认为客户数量继续增长。", False),
    ("区域配送中心开始交货前仍需监管批准。", "区域配送中心开始交货。", True),
])
def test_assessor_observes_same_requirement_predicate_as_prompt(source, claim_text, expected):
    _claim, report = decode_planned(source, (), "zh", claim_text=claim_text)
    has_condition_loss = any(row["rule_code"] == "possible_condition_scope_loss" for row in report["diagnostics"])
    assert has_condition_loss is expected


def test_new_recipe_does_not_change_historical_prompt_or_diagnostic_semantics():
    record = selection_with_context("客户需求扩大，公司已完成区域物流网络改造。")
    original = build_model_request(record, reading_projection_version=HISTORICAL_PROJECTION)
    revised = build_model_request(record, reading_projection_version=PROJECTION)
    old_wire, new_wire = map(lambda request: json.loads(request.data_json), (original, revised))

    assert original.prompt_version == "reading-source-scoped/4.3.0"
    assert revised.prompt_version == "reading-source-scoped/4.4.0"
    assert old_wire["schema_version"] == "narrative-model-request/8"
    assert new_wire["schema_version"] == "narrative-model-request/9"
    assert old_wire["material"]["source_frame_hints"]["schema_version"] == "source-frame-hints/1"
    assert new_wire["material"]["source_frame_hints"]["schema_version"] == "source-frame-hints/2"
    assert resolve_model_boundary(PROJECTION).decoder_version == resolve_model_boundary(HISTORICAL_PROJECTION).decoder_version
    assert original.input_sha256 != revised.input_sha256
    original_hints = old_wire["material"]["source_frame_hints"]["sources"]
    revised_hints = new_wire["material"]["source_frame_hints"]["sources"]
    assert any(row.get("condition_present") for rows in original_hints.values() for row in rows)
    assert not any(row.get("condition_present") for rows in revised_hints.values() for row in rows)

    _claim, report = decode_planned("提前启动区域冷链仓建设。", ("报告期内：",), "zh",
                                    projection=HISTORICAL_PROJECTION)
    assert report["validator"]["version"] == "source-summary-assessment/1.4.0"
    assert not report["diagnostics"]
