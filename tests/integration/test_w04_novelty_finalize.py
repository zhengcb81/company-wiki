"""Public finalizer regressions; no hand-built overlap tokens or source IO."""
from dataclasses import replace
import re

import pytest

from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_routing import route_document
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SHA = "f" * 64
SOURCE = source_id_for_sha256(SHA)
REASONS = ("new_product_commercialization_milestone",)
BACKGROUND = "公司持续推进技术研发并完善工艺支持，围绕制造需求扩展客户服务能力，改善运营效率。"
# Generic filler isolates the overlap effect; a real delivered stage is a
# different quality band and is explicitly tested in phase2.
WEAK = "另一款医疗设备的通用技术背景和服务范围说明。"


def make(page, paragraph, text, score):
    unit = _make_unit(source_id=SOURCE, parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=paragraph),
        raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
        language="zh", metadata={}, quality_flags=())
    return EvidenceCandidate(unit, ("products_rd",), REASONS, score)


def finish(groups, *, limit=2, reverse=False):
    candidates = tuple(make(page, paragraph, text, score)
        for page, members, score in groups
        for paragraph, text in members)
    group_ids = {candidate.unit.unit_id: f"group-{candidate.unit.coordinates.page_number}"
        for candidate in candidates}
    structure = DocumentStructure(source_id=SOURCE, source_sha256=SHA,
        language="zh", units=tuple(candidate.unit for candidate in candidates),
        page_count=max(g[0] for g in groups), pages_read=max(g[0] for g in groups))
    route = replace(route_document("2025年年度报告", existing_kind="annual"), selection_limit=limit)
    package = finalize_selection(structure, route,
        tuple(reversed(candidates)) if reverse else candidates,
        group_ids=group_ids, heading_pattern=re.compile(r"(?!)"),
        dropped_financial_count=0, budget_policy="semantic_coverage/1")
    assert len(package.evidence_spans) <= limit
    assert package.candidate_count == len(candidates)
    assert package.omitted_candidate_count == len(candidates) - len(package.evidence_spans)
    native = {candidate.unit.coordinates.locator(): candidate.unit.raw_text for candidate in candidates}
    assert all(span.raw_text == native[span.locator] for span in package.evidence_spans)
    return package


@pytest.mark.parametrize("old,new", [
    ("累计交付300反应台", "累计交付500反应台"),
    ("累计交付三百反应台", "累计交付五百反应台"),
    ("良率达到85%", "良率达到95%"),
    ("产能达到2.5万台", "产能达到3.5万台"),
    ("可切换6和8英寸晶圆", "可切换8和12英寸晶圆"),
    ("反应腔达到4个", "反应腔达到6个"),
    ("累计交付300台", "累计交付300套"),
    ("交付周期为6-8周", "交付周期为8-12周"),
    ("shipments reached 300 units", "shipments reached 500 units"),
    ("yield reached 85.5%", "yield reached 95.5%"),
    ("capacity reached 2.5 million units", "capacity reached 3.5 million units"),
    ("delivery takes 6 to 8 weeks", "delivery takes 8 to 12 weeks"),
])
def test_new_quantity_or_unit_survives_high_shared_vocabulary(old, new):
    result = finish([(1, [(1, BACKGROUND + "LPCVD设备" + old + "。")], 30),
                     (2, [(1, BACKGROUND + "LPCVD设备" + new + "。")], 29),
                     (3, [(1, WEAK)], 1)])
    assert {span.coordinates.page_number for span in result.evidence_spans} == {1, 2}


@pytest.mark.parametrize("old,new", [
    ("正在进行客户验证", "已通过客户验证"),
    ("已完成客户验证", "计划开展客户验证"),
    ("已完成客户验证", "尚未完成客户验证"),
    ("已获得重复订单", "尚未获得重复订单"),
    ("已累计出货300台", "预计累计出货300台"),
    ("has passed customer validation", "has not passed customer validation"),
    ("customer validation is progressing", "has completed customer validation"),
    ("has received repeat orders", "plans to receive repeat orders"),
])
def test_new_stage_or_polarity_survives_high_shared_vocabulary(old, new):
    result = finish([(1, [(1, BACKGROUND + "新型设备" + old + "。")], 30),
                     (2, [(1, BACKGROUND + "新型设备" + new + "。")], 29),
                     (3, [(1, WEAK)], 1)])
    assert {span.coordinates.page_number for span in result.evidence_spans} == {1, 2}


def test_same_amount_for_different_subject_is_not_repetition():
    result = finish([(1, [(1, BACKGROUND + "薄膜设备累计交付300反应台。")], 30),
                     (2, [(1, BACKGROUND + "LPCVD设备累计交付300反应台。")], 29),
                     (3, [(1, WEAK)], 1)])
    assert {span.coordinates.page_number for span in result.evidence_spans} == {1, 2}


def test_numeric_multiset_cannot_rebind_quantity_across_subjects():
    groups = [(1, [(9, BACKGROUND + "LPCVD设备累计交付300反应台，"),
                   (10, "ALD设备累计交付500反应台。")], 30),
              (2, [(9, BACKGROUND + "LPCVD设备累计交付500反应台，"),
                   (10, "ALD设备累计交付300反应台。")], 29),
              (3, [(1, WEAK)], 1)]
    package = finish(groups, limit=4)
    assert {span.coordinates.page_number for span in package.evidence_spans} == {1, 2}
    assert package == finish(groups, limit=4, reverse=True)


def test_prismo_completed_validation_new_chambers_and_wafer_sizes_survive():
    result = finish([(1, [(1, BACKGROUND + "PRISMO设备已经交付客户，正在进行生产验证。")], 30),
                     (2, [(1, BACKGROUND + "PRISMO设备已经验证通过，具有4个反应腔，可切换6和8英寸晶圆。")], 29),
                     (3, [(1, WEAK)], 1)])
    assert {span.coordinates.page_number for span in result.evidence_spans} == {1, 2}


def test_short_subset_cannot_suppress_long_group_new_fact():
    short = BACKGROUND + "新型设备已完成客户验证。"
    long = short + "新型设备新增4个反应腔，可切换6和8英寸晶圆。"
    result = finish([(1, [(1, short)], 30), (2, [(1, long)], 29), (3, [(1, WEAK)], 1)])
    assert {span.coordinates.page_number for span in result.evidence_spans} == {1, 2}


def test_same_complete_fact_with_only_layout_changes_is_soft_deprioritized():
    text = BACKGROUND + "LPCVD设备已累计交付300反应台。"
    repeated = BACKGROUND + "LPCVD 设备已累计交付 300 反应台！"
    # Repetition is a tie-break within the same quality band. A generic filler
    # cannot displace a fact solely because that fact has a layout duplicate.
    other_realized = "医疗设备已完成客户验证并取得重复订单。"
    result = finish([(1, [(1, text)], 30), (2, [(1, repeated)], 29),
                     (3, [(1, other_realized)], 1)])
    assert {span.coordinates.page_number for span in result.evidence_spans} == {1, 3}


def test_finalizer_builds_one_native_order_signature_before_pure_budget(monkeypatch):
    from company_wiki.source_catalog import narrative_finalize as module
    seen = []
    original = module.select_budget_items
    def observe(items, **kwargs):
        seen.extend(items)
        return original(items, **kwargs)
    monkeypatch.setattr(module, "select_budget_items", observe)
    finish([(1, [(10, "备已累计交付300反应台。"), (9, "LPCVD设")], 30),
            (2, [(1, WEAK)], 1)], limit=3, reverse=True)
    members = [item for item in seen if item.page_key == ("page", 1)]
    assert len(members) == 2
    assert members[0].coverage_signature == members[1].coverage_signature
    signature = members[0].coverage_signature
    assert signature.complete
    assert "lpcvd设备已累计交付300反应台" in signature.protected_sentences
    assert any(stage == "shipment" and realized for stage, _predicate, realized, _reason in signature.stage_signals)
