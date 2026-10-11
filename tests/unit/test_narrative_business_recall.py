"""Versioned bounded business recall; source data and budget remain authoritative."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_SELECTOR_VERSION, _make_unit, parse_transcript_text,
    select_narrative_evidence,
)
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "narrative_real_transcript" / "MSFT_Q4_2026_earnings_call.txt"
FIXTURE_SHA = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
LEGACY_SHA = "11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f"
SHA = "a" * 64


def units(texts, *, role="management", kind="transcript_sentence", metadata=None):
    output = []
    start = 0
    for index, text in enumerate(texts):
        output.append(_make_unit(
            source_id=source_id_for_sha256(SHA), parser_version="0.3.1",
            coordinates=EvidenceCoordinates(paragraph_index=index,
                char_start=start, char_end=start + len(text)),
            raw_text=text, unit_kind=kind, source_role=role,
            language="zh" if any("\u3400" <= c <= "\u9fff" for c in text) else "en",
            metadata={"speaker": "Issuer officer", "qa_group_id": "qa-1",
                "qa_parent_id": 1, **(metadata or {})},
        ))
        start += len(text) + 1
    return tuple(output)


def structure(members):
    return DocumentStructure(source_id=source_id_for_sha256(SHA),
        source_sha256=SHA, language=members[0].language, units=tuple(members),
        line_count=len(members))


def selected(members, *, limit=96, version="0.7.0"):
    return select_narrative_evidence(structure(members), title="Company earnings call",
        existing_kind="investor_call_transcript", max_selected=limit,
        selector_version=version)


def package_fingerprint(package):
    data = {"fixture_sha256": FIXTURE_SHA, "document_kind": package.document_kind,
        "status": package.status, "selection_limit": package.selection_limit,
        "candidate_count": package.candidate_count,
        "dropped_financial_count": package.dropped_financial_count,
        "source_units": package.source_units,
        "omitted_candidate_count": package.omitted_candidate_count,
        "coverage_complete": package.coverage_complete,
        "spans": [span.to_dict() for span in package.evidence_spans]}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


def test_default_old_selector_keeps_entire_ordered_fingerprint():
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    parsed = parse_transcript_text(raw.decode(), source_id=source_id_for_sha256(FIXTURE_SHA),
        source_sha256=FIXTURE_SHA, language="en", parser_version="0.3.1")
    default = select_narrative_evidence(parsed, title=FIXTURE.name,
        existing_kind="investor_call_transcript")
    effective_default = select_narrative_evidence(parsed, title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version=NARRATIVE_SELECTOR_VERSION)
    assert package_fingerprint(default) == package_fingerprint(effective_default)
    legacy = select_narrative_evidence(parsed, title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version="0.6.0")
    assert package_fingerprint(legacy) == LEGACY_SHA


@pytest.mark.parametrize("text, reason", [
    ("And so what we launched with Orion is essentially saying, let's sort of really make sure that you have the red team agents that know how to find vulnerabilities.", "specific_business_event"),
    ("Our service uses a diversified model mix to reduce token cost and remain available if one provider fails.", "operating_mechanism"),
    ("Efficiency depends on workload mix, token usage and silicon price performance.", "operating_mechanism"),
    ("公司产能具有一定弹性，但突发订单下短期配备的人工、组装检测设备和供应商短期供货能力仍会限制生产。", "business_risk_or_constraint"),
    ("公司的产品分为控制器与执行器，控制器通过直销供给设备厂，执行器由海外渠道销售；关键部件须完成客户验证。", "business_structure"),
    ("We serve equipment makers through direct sales while overseas distributors handle local service and qualification.", "business_structure"),
    ("公司主要采用以销定产的生产模式，生产流程按照模块化设计，先组装模块再组装整机。", "business_structure"),
    ("报告期内公司营业收入增长，主要通过提高付费转化率和广告价格实现，海外需求尚存在不确定性。", "operating_mechanism"),
    ("Our new service targets industrial customers through a local distributor network, with on-site qualification required before adoption.", "business_structure"),
    ("Industry demand is shifting toward low-power equipment as new export licensing restricts overseas delivery.", "current_industry_context"),
    ("We plan to use existing manufacturing expertise to build an overseas service network for local equipment customers.", "business_strategy"),
])
def test_concrete_generic_business_meaning_does_not_require_launch(text, reason):
    package = selected(units([text]))
    assert [span.raw_text for span in package.evidence_spans] == [text]
    assert reason in package.evidence_spans[0].structured_value["selection_reasons"]
    assert package.selection_limit == 96


@pytest.mark.parametrize("text", [
    "We take security and shareholder returns seriously and always seek excellence.",
    "The dividend increased by 20% and financing proceeds supported liquidity.",
    "Revenue increased by 20% while our product philosophy remains unchanged.",
    "本公司依法经营，坚持创新发展，为客户创造价值。",
    "订单式生产是指根据客户订单安排生产的通用生产方式。",
    "Forward-looking statements may differ materially from actual results.",
    "We believe that innovation and customer success are important to everyone.",
    "Our service targets excellence and customer happiness.",
    "We value customers because they are important to us.",
    "The product team released the annual financial statements and dividend notice.",
])
def test_boilerplate_definition_and_finance_are_not_business_facts(text):
    assert selected(units([text])).evidence_spans == ()


@pytest.mark.parametrize("role", ["analyst", "investor_question", "operator", "editorial"])
def test_noncompany_role_cannot_seed_company_fact(role):
    package = selected(units([
        "Our service uses a diversified model mix to reduce token cost and remain available if one provider fails."
    ], role=role))
    assert not any(span.structured_value["source_role"] == "management"
        for span in package.evidence_spans)
    assert package.evidence_spans == ()


def test_unchanged_framework_and_efficiency_form_small_atomic_support_group():
    texts = ["The return calculation has not changed.",
        "Efficiency depends on workload mix, token usage and silicon price performance."]
    package = selected(units(texts), limit=2)
    assert {span.raw_text for span in package.evidence_spans} == set(texts)
    groups = {span.structured_value.get("selection_group_id") for span in package.evidence_spans}
    assert len(groups) == 1 and None not in groups
    assert package.summary_input()["evidence"][0]["context_member_count"] == 2
    refused = selected(units(texts), limit=1)
    assert refused.evidence_spans == ()
    assert refused.candidate_count == refused.omitted_candidate_count == 2
    assert refused.status == "partial"


@pytest.mark.parametrize("key, value", [
    ("qa_group_id", "qa-2"), ("qa_parent_id", 2),
    ("speaker", "Different officer"), ("parent_content_sha256", "b" * 64),
    ("record_pointer", {"record_pointer": "/datas/0/records/2"}["record_pointer"]), ("section", "Separate business"),
])
def test_required_context_does_not_cross_source_actor_or_record_boundary(key, value):
    members = units(["The return calculation has not changed.",
        "Efficiency depends on workload mix, token usage and silicon price performance."],
        metadata={"parent_content_sha256": "c" * 64, "record_pointer": "/datas/0/records/1"})
    members = (members[0], replace(members[1], metadata={**members[1].metadata, key: value}))
    package = selected(members)
    assert "The return calculation has not changed." not in {
        span.raw_text for span in package.evidence_spans}
    assert package.evidence_spans
    assert not any(span.structured_value.get("selection_group_id")
        for span in package.evidence_spans)


def test_required_qualifier_group_is_atomic_and_source_order_deterministic():
    texts = ["Our production capacity is flexible because assembly uses standardized modules.",
        "But sudden orders remain limited by short-term labor and supplier delivery capacity."]
    members = units(texts)
    package = selected(members, limit=2)
    assert {span.raw_text for span in package.evidence_spans} == set(texts)
    group = {span.structured_value.get("selection_group_id") for span in package.evidence_spans}
    assert len(group) == 1 and None not in group
    other = selected(tuple(reversed(members)), limit=2)
    assert [span.to_dict() for span in package.evidence_spans] == [span.to_dict() for span in other.evidence_spans]
    tight = selected(members, limit=1)
    assert tight.status == "partial" and tight.evidence_spans == ()


@pytest.mark.parametrize("version", ["0.8.0", "", [], {}, True])
def test_unknown_or_nonstring_version_is_explicit_value_error(version):
    with pytest.raises(ValueError, match="selector version"):
        selected(units(["Our product is supplied through overseas distributors."]), version=version)


def test_native_whole_field_oversize_stays_omitted_partial_never_fake_sliced():
    text = "Our service uses model routing to reduce token cost. " * 35
    members = units([text.strip()], kind="official_json_field", metadata={
        "field_pointer": "/datas/0/records/0/content", "parent_content_sha256": SHA})
    package = selected(members)
    assert package.evidence_spans == ()
    assert package.candidate_count == package.omitted_candidate_count == 1
    assert package.status == "partial"


def test_pure_group_diagnostics_are_bounded_locator_only():
    from company_wiki.source_catalog.narrative_business_groups import enrich_business_groups
    from company_wiki.source_catalog.narrative_evidence import _candidate_rules
    from company_wiki.source_catalog.narrative_candidates import assess_unit
    member = units([("Our service uses model routing to reduce token cost. " * 35).strip()],
        kind="official_json_field")[0]
    rules = _candidate_rules(selector_version="0.7.0")
    assessed = assess_unit(member, rules).candidate
    assert assessed is not None
    result = enrich_business_groups((member,), initial_candidates=(assessed,),
        initial_group_ids={}, rules=rules)
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.reason == "business_group_character_limit"
    assert diagnostic.locators == (member.coordinates.locator(),)
    assert not hasattr(diagnostic, "raw_text")
    assert member.unit_id in result.excluded_unit_ids


@pytest.mark.parametrize("count", [8, 9])
def test_eight_unit_limit_keeps_complete_conditions_and_exposes_overflow(count):
    texts = ["Our production capacity is flexible because assembly uses standardized modules."]
    texts += [f"But production remains limited by supplier delivery capacity for component {i}." for i in range(count - 1)]
    package = selected(units(texts), limit=96)
    if count == 8:
        assert len(package.evidence_spans) == 8
        assert len({s.structured_value.get("selection_group_id") for s in package.evidence_spans}) == 1
    else:
        assert package.evidence_spans == () and package.status == "partial"
        assert package.candidate_count == package.omitted_candidate_count == 9


def test_required_character_overflow_does_not_keep_only_optimistic_seed():
    seed = "Our production capacity is flexible because assembly uses standardized modules " + "x" * 1040 + "."
    qualifier = "But sudden orders remain limited by short-term labor and supplier delivery capacity."
    assert len(seed) < 1200 < len(seed) + len(qualifier) + 1
    package = selected(units([seed, qualifier]))
    assert package.evidence_spans == () and package.status == "partial"
    assert package.candidate_count == package.omitted_candidate_count == 2


def test_pure_financial_table_drops_without_operating_exemption():
    package = selected(units(["营业收入 2025年度 12345.67 2024年度 9876.54"],
        role="company_filing", kind="pdf_table_row"))
    assert package.evidence_spans == ()
    assert package.dropped_financial_count == 1


def test_adjacent_pdf_page_with_different_named_product_does_not_join():
    members = units(["Alpha product is supplied through distributors to equipment customers.",
        "But Beta product production capacity remains limited by supplier shortages."],
        role="company_filing", kind="pdf_text_block")
    members = tuple(replace(u, coordinates=replace(u.coordinates, page_number=i + 1))
        for i, u in enumerate(members))
    package = selected(members)
    assert len(package.evidence_spans) == 2
    assert not any(s.structured_value.get("selection_group_id") for s in package.evidence_spans)


def test_locator_diagnostics_are_capped_without_hiding_remaining_omissions():
    from company_wiki.source_catalog.narrative_business_groups import enrich_business_groups
    from company_wiki.source_catalog.narrative_evidence import _candidate_rules
    from company_wiki.source_catalog.narrative_candidates import assess_unit
    text = ("Our service uses model routing to reduce token cost. " * 35).strip()
    members = units([text] * 20, kind="official_json_field")
    rules = _candidate_rules(selector_version="0.7.0")
    candidates = tuple(a for u in members if (a := assess_unit(u, rules).candidate) is not None)
    result = enrich_business_groups(members, initial_candidates=candidates, initial_group_ids={}, rules=rules)
    assert len(result.diagnostics) == 16 and len(result.excluded_unit_ids) == 20
    package = selected(members)
    assert package.status == "partial"
    assert package.candidate_count == package.omitted_candidate_count == 20


def test_explicit_legacy_fingerprint_survives_new_global_default(monkeypatch):
    from company_wiki.source_catalog import narrative_evidence as n
    raw = FIXTURE.read_bytes()
    parsed = parse_transcript_text(raw.decode(), source_id=source_id_for_sha256(FIXTURE_SHA),
        source_sha256=FIXTURE_SHA, language="en", parser_version="0.3.1")
    monkeypatch.setattr(n, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
    legacy = select_narrative_evidence(parsed, title=FIXTURE.name,
        existing_kind="investor_call_transcript", selector_version="0.6.0")
    assert package_fingerprint(legacy) == LEGACY_SHA


@pytest.mark.parametrize("finance_heading", [False, True])
def test_explicit_legacy_fundraising_uses_effective_rules_after_default_upgrade(monkeypatch, finance_heading):
    from company_wiki.source_catalog import narrative_evidence as n
    headers = ("序号", "募集资金运用方向", "项目总投资", "拟投入募集资金")
    texts = ["本次募集资金扣除费用后将投资于以下", "项目：",
        "Revenue increased by 20% | 工业设备扩产升级项目 | 100 | 90"
        if finance_heading else "1 | 工业设备扩产升级项目 | 100 | 90"]
    members = units(texts, role="company_filing", kind="pdf_text_block")
    members = tuple(replace(u, coordinates=replace(u.coordinates, page_number=2),
        metadata={**u.metadata, "bbox": (80, 390 + 20 * i, 510, 404 + 20 * i),
            "pdf_block": 9 if i < 2 else 10}) for i, u in enumerate(members))
    row = replace(members[2], unit_kind="pdf_table_row",
        coordinates=EvidenceCoordinates(page_number=2, table_index=0, row_index=1),
        metadata={**members[2].metadata, "bbox": (80, 455, 510, 500),
            "table_headers": headers,
            "row_cells": ("1", "工业设备扩产升级项目", "100", "90")})
    parsed = structure((*members[:2], row))
    baseline = n.select_narrative_evidence(parsed, title="招股说明书",
        existing_kind="prospectus", selector_version="0.6.0")
    assert len(baseline.evidence_spans) == 3
    actual_rules = n._candidate_rules
    requested_versions = []
    def observe_rules(*, selector_version=None):
        requested_versions.append(selector_version)
        return actual_rules(selector_version=selector_version)
    monkeypatch.setattr(n, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
    monkeypatch.setattr(n, "_candidate_rules", observe_rules)
    replay = n.select_narrative_evidence(parsed, title="招股说明书",
        existing_kind="prospectus", selector_version="0.6.0")
    assert replay == baseline
    assert requested_versions and set(requested_versions) == {"0.6.0"}


def test_candidate_rules_extension_preserves_old_positional_signature():
    import re
    from company_wiki.source_catalog.narrative_candidates import CandidateRules
    from company_wiki.source_catalog.n6_candidate_operating_facts import detect_operating_fact
    def topic(_text):
        return ()
    def financial(_unit, _topics):
        return False
    high_value = re.compile("launched")
    rules = CandidateRules(topic, financial, detect_operating_fact, high_value)
    assert rules.high_value_event is high_value
    assert not rules.reject_text("neutral text")


@pytest.mark.parametrize("text, eligible", [
    ("行业出口许可政策近期收紧，出口审批周期延长。", True),
    ("Recent export licensing restrictions have tightened across the semiconductor industry.", True),
    ("公司关注行业最新动态，保持高度重视。", False),
    ("行业出口许可政策近期受到关注。", False),
    ("Recent export licensing policies are important across the industry.", False),
])
def test_concrete_industry_operating_change_needs_no_company_product_noun(text, eligible):
    from company_wiki.source_catalog.narrative_business_policy import detect_business_fact
    fact = detect_business_fact(text)
    assert fact.eligible is eligible
    if eligible:
        assert "current_industry_context" in fact.reasons
        assert "industry_dynamics" in fact.topics
        package = selected(units([text], role="company_filing"))
        assert [s.raw_text for s in package.evidence_spans] == [text]
    else:
        assert selected(units([text], role="company_filing")).evidence_spans == ()
