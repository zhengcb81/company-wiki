from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from scripts.narrative_evidence_pilot import _anchor_evidence_ids

import company_wiki.source_catalog.narrative_evidence as narrative_evidence_module
from company_wiki.source_catalog.narrative_evidence import (
    NarrativeParseResult,
    SourceSummaryDraft,
    SummaryClaim,
    SummaryValidationError,
    classify_document_kind,
    _make_unit,
    _sentence_fragments,
    _table_scan_signal,
    parse_pdf,
    parse_transcript_text,
    project_summary_quality,
    select_narrative_evidence,
    validate_summary_draft,
    verify_pdf_evidence_spans,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.narrative_replay import verify_replayed_pdf_spans
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def _source(seed: str = "source") -> tuple[str, str]:
    sha = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return source_id_for_sha256(sha), sha


def _unit(
    text: str,
    *,
    source_id: str,
    coords: EvidenceCoordinates | None = None,
    kind: str = "pdf_text_block",
    role: str = "company_filing",
    metadata: dict | None = None,
):
    return _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=coords or EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text=text,
        unit_kind=kind,
        source_role=role,
        language="zh",
        metadata=metadata or {},
    )


def test_pilot_anchor_mapping_returns_only_supporting_span_window() -> None:
    source_id, _source_sha = _source()
    first = _unit(
        "订单交付进入新阶段，航空产业",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=1),
    ).to_evidence_span(topics=(), selection_reasons=())
    second = _unit(
        "形成的外协需求旺盛。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=2),
    ).to_evidence_span(topics=(), selection_reasons=())
    unrelated = _unit(
        "无关的表述。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=3),
    ).to_evidence_span(topics=(), selection_reasons=())

    assert _anchor_evidence_ids([first, unrelated], "订单交付") == (first.span_id,)
    assert _anchor_evidence_ids([first, second, unrelated], "航空产业形成") == (
        first.span_id,
        second.span_id,
    )
    assert _anchor_evidence_ids([unrelated], "订单交付") == ()


def test_sample_document_titles_separate_offering_types_and_ir_negatives() -> None:
    assert classify_document_kind(
        "三角防务：1-1向不特定对象发行可转换公司债券募集说明书.PDF",
        "other",
    ) == "convertible_bond_prospectus"
    assert classify_document_kind(
        "三角防务：向特定对象发行股票并在创业板上市募集说明书（注册稿）.PDF",
        "other",
    ) == "equity_offering_prospectus"
    assert classify_document_kind(
        "中微公司：首次公开发行股票并在科创板上市招股说明书.pdf",
        "other",
    ) == "prospectus"
    assert classify_document_kind("投资者关系管理办法（2025年8月）.pdf") == "ir_policy"
    assert classify_document_kind("关于召开年度业绩说明会的通知.pdf") == "meeting_notice"


def test_pdf_parser_keeps_text_with_a_page_locator(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "one-page.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Company launched a new product and expanded overseas capacity for a repeat customer order.",
    )
    document.save(path)
    document.close()

    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    source_id = source_id_for_sha256(actual_sha)
    parsed = parse_pdf(
        path,
        source_id=source_id,
        source_sha256=actual_sha,
        language="en",
    )
    package = select_narrative_evidence(parsed, title="样本年报.pdf", existing_kind="annual_report")

    assert parsed.page_count == parsed.pages_read == 1
    assert parsed.coverage_complete
    assert any(unit.unit_kind == "pdf_text_block" for unit in parsed.units)
    assert package.evidence_spans
    span = package.evidence_spans[0]
    assert span.coordinates.page_number == 1
    assert span.coordinates.paragraph_index == 0
    assert span.source_id == source_id
    verified, failed = verify_pdf_evidence_spans(
        path,
        source_id=source_id,
        source_sha256=actual_sha,
        evidence_spans=package.evidence_spans,
    )
    assert verified == (span.span_id,)
    assert failed == ()


def test_financial_table_rows_are_dropped_but_business_rows_are_selected() -> None:
    source_id, source_sha = _source()
    financial = _unit(
        "营业收入 | 100.0亿元",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, table_index=0, row_index=1),
        kind="pdf_table_row",
        metadata={"row_cells": ("营业收入", "100.0亿元"), "table_headers": ("项目", "本期发生额")},
    )
    business = _unit(
        "海外市场的新产线已完成调试，预计第四季度投产并服务新增客户。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, table_index=1, row_index=2),
        kind="pdf_table_row",
        metadata={"row_cells": ("海外市场", "新产线已完成调试"), "table_headers": ("项目", "进展")},
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(financial, business),
        page_count=3,
        pages_read=3,
    )

    package = select_narrative_evidence(parsed, title="可转债募集说明书.pdf")

    assert package.document_kind == "convertible_bond_prospectus"
    assert package.dropped_financial_count == 1
    assert len(package.evidence_spans) == 1
    assert package.evidence_spans[0].coordinates.table_index == 1
    assert package.evidence_spans[0].coordinates.row_index == 2


@pytest.mark.parametrize(
    "title",
    ("投资者关系管理办法.pdf", "2026年第一季度报告.pdf"),
)
def test_incomplete_scan_never_auto_skips_as_no_narrative(title: str) -> None:
    source_id, source_sha = _source()
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(),
        page_count=7,
        pages_read=7,
        opaque_pages=(4,),
    )
    package = select_narrative_evidence(parsed, title=title)
    assert package.status == "needs_review"
    assert not package.coverage_complete


def test_complete_known_notice_can_be_skipped_without_saving_evidence() -> None:
    source_id, source_sha = _source()
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(),
        page_count=3,
        pages_read=3,
    )
    package = select_narrative_evidence(
        parsed,
        title="关于召开年度业绩说明会的通知.pdf",
    )
    assert package.status == "skipped_no_narrative"
    assert package.evidence_spans == ()


def test_complete_unknown_document_with_no_candidates_requires_review() -> None:
    source_id, source_sha = _source("n4t2:unknown")
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(parsed, title="unclassified.pdf")

    assert package.status == "needs_review"
    assert package.coverage_complete is True


def test_semiannual_title_is_not_misclassified_as_annual() -> None:
    assert classify_document_kind("中微公司：2025年半年度报告.pdf") == "semi_annual_report"


def test_transcript_parser_excludes_editorial_and_keeps_qa_question_context() -> None:
    source_id, source_sha = _source()
    text = (
        "Editorial summary: new product demand is rising.\n\n"
        "Full Conference Call Transcript\n"
        "CEO: We launched a new product and expanded overseas capacity.\n\n"
        "Questions & Answers\n"
        "Analyst: Is the new product ready for commercial launch?\n\n"
        "CEO: It is too early to speculate on commercial launch, though customer validation continues.\n"
    )
    parsed = parse_transcript_text(text, source_id=source_id, source_sha256=source_sha)
    package = select_narrative_evidence(parsed, title="MSFT_Q4_2026_earnings_call.txt")

    assert parsed.coverage_complete
    assert all("Editorial summary" not in unit.raw_text for unit in parsed.units)
    assert len(package.evidence_spans) >= 3
    roles = [span.structured_value["source_role"] for span in package.evidence_spans]
    assert "management" in roles
    assert "analyst" in roles  # context, never management attribution
    assert any("too early to speculate" in (span.raw_text or "") for span in package.evidence_spans)
    assert all(span.parser_version == narrative_evidence_module.TRANSCRIPT_PARSER_VERSION
               for span in package.evidence_spans)
    verified, failed = verify_transcript_evidence_spans(
        text,
        source_id=source_id,
        source_sha256=source_sha,
        evidence_spans=package.evidence_spans,
    )
    assert len(verified) == len(package.evidence_spans)
    assert failed == ()


def test_transcript_q_and_a_transition_and_two_question_links_are_preserved() -> None:
    source_id, source_sha = _source()
    text = (
        "Full Conference Call Transcript\n"
        "CEO: Welcome to the call.\n"
        "Operator: We will now take questions.\n"
        "CEO: We will now move over to Q&A.\n"
        "Karl Keirstead: First, how does model choice work? And second question, "
        "how should we think about the clinical trial?\n"
        "CEO: On the first question, starter doses are now shipping through the supply chain.\n"
        "CEO: On the second question, it is too early to speculate about the clinical trial results.\n"
    )

    parsed = parse_transcript_text(text, source_id=source_id, source_sha256=source_sha)
    questions = [unit for unit in parsed.units if unit.source_role == "analyst"]
    package = select_narrative_evidence(parsed, title="MSFT_Q4_2026_earnings_call.txt")
    selected_questions = [
        span for span in package.evidence_spans
        if span.structured_value["source_role"] == "analyst"
    ]

    assert len(questions) == 2
    assert questions[0].metadata["qa_group_id"] != questions[1].metadata["qa_group_id"]
    assert {span.structured_value["qa_group_id"] for span in selected_questions} == {
        questions[0].metadata["qa_group_id"], questions[1].metadata["qa_group_id"]
    }
    assert any("starter doses" in (span.raw_text or "") for span in package.evidence_spans)
    assert any("too early to speculate" in (span.raw_text or "") for span in package.evidence_spans)


def test_transcript_without_recognized_start_is_blocked_not_skipped() -> None:
    source_id, source_sha = _source()
    parsed = parse_transcript_text(
        "This editorial page discusses new products and demand.",
        source_id=source_id,
        source_sha256=source_sha,
    )
    package = select_narrative_evidence(parsed, title="unknown.txt")
    assert package.status == "blocked"
    assert parsed.errors == ("transcript_start_missing",)


def test_summary_draft_requires_real_evidence_ids_and_preserves_source_language() -> None:
    source_id, source_sha = _source()
    unit = _unit(
        "公司新产品已通过客户验证并获得重复订单。",
        source_id=source_id,
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(unit,),
        page_count=1,
        pages_read=1,
    )
    package = select_narrative_evidence(parsed, title="年报.pdf")
    span = package.evidence_spans[0]
    draft = SourceSummaryDraft(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        claims=(
            SummaryClaim(
                claim_id="claim-1",
                text="新产品通过客户验证并获得重复订单。",
                evidence_ids=(span.span_id,),
                claim_type="company_statement",
                modality="actual",
            ),
        ),
    )
    validate_summary_draft(
        draft,
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        evidence_spans=package.evidence_spans,
    )
    assert package.summary_input()["summary_scope"] == "selected_evidence_only"
    assert "full_document" not in package.summary_input()
    compact_evidence = package.summary_input()["evidence"][0]
    assert compact_evidence["evidence_id"] == span.span_id
    assert compact_evidence["raw_text"] == span.raw_text
    assert "structured_value" not in compact_evidence

    translated = SourceSummaryDraft(
        source_id=source_id,
        source_sha256=source_sha,
        language="en",
        claims=draft.claims,
    )
    with pytest.raises(SummaryValidationError, match="language"):
        validate_summary_draft(
            translated,
            source_id=source_id,
            source_sha256=source_sha,
            language="zh",
            evidence_spans=package.evidence_spans,
        )


def test_analyst_question_cannot_be_used_as_company_fact() -> None:
    source_id, source_sha = _source()
    question = _unit(
        "Did the company complete overseas customer qualification for its new product?",
        source_id=source_id,
        coords=EvidenceCoordinates(paragraph_index=15),
        kind="transcript_speaker_block",
        role="analyst",
        metadata={"qa_group_id": 1},
    )
    answer = _unit(
        "It is too early to speculate on the launch; customer validation continues.",
        source_id=source_id,
        coords=EvidenceCoordinates(paragraph_index=16),
        kind="transcript_speaker_block",
        role="management",
        metadata={"qa_group_id": 1},
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="en",
        units=(question, answer),
        line_count=18,
    )
    package = select_narrative_evidence(parsed, title="call transcript.txt")
    question_span = next(
        span for span in package.evidence_spans
        if span.structured_value["source_role"] == "analyst"
    )
    draft = SourceSummaryDraft(
        source_id=source_id,
        source_sha256=source_sha,
        language="en",
        claims=(
            SummaryClaim(
                claim_id="claim-1",
                text="The company completed qualification.",
                evidence_ids=(question_span.span_id,),
                claim_type="company_statement",
                modality="actual",
            ),
        ),
    )
    with pytest.raises(SummaryValidationError, match="non-company"):
        validate_summary_draft(
            draft,
            source_id=source_id,
            source_sha256=source_sha,
            language="en",
            evidence_spans=package.evidence_spans,
        )


def test_static_topic_mentions_are_not_selected_without_a_change_or_current_event() -> None:
    source_id, source_sha = _source()
    static = _unit(
        "公司主营业务包括高端装备研发、生产和销售，持续关注行业发展。",
        source_id=source_id,
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(static,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(parsed, title="年报.pdf")

    assert package.evidence_spans == ()
    assert package.status == "needs_review"
    assert package.coverage_complete is True


def test_specific_emerging_business_positions_are_selected_without_generic_product_noise() -> None:
    source_id, source_sha = _source()
    low_altitude = _unit(
        "公司聚焦核心主业，拓展低空经济产业链。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=16, paragraph_index=3),
    )
    cpo_capability = _unit(
        "公司具有CPO全光互连链路产品的解决方案。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, paragraph_index=0),
    )
    generic = _unit(
        "公司主营业务包括多类产品和配套解决方案。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=0),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(low_altitude, cpo_capability, generic),
        page_count=3,
        pages_read=3,
    )

    package = select_narrative_evidence(parsed, title="年报及投资者关系记录.pdf")

    assert {span.coordinates.page_number for span in package.evidence_spans} == {2, 16}
    assert any("低空经济产业链" in (span.raw_text or "") for span in package.evidence_spans)
    assert any("CPO全光互连" in (span.raw_text or "") for span in package.evidence_spans)
    assert all(
        "specific_emerging_business_positioning" in span.structured_value["selection_reasons"]
        for span in package.evidence_spans
    )


@pytest.mark.parametrize(
    ("text", "document_kind", "expected_topic"),
    (
        (
            "2025年报告期，行业供需格局持续收紧，客户验证周期明显缩短。",
            "quarterly_report",
            "industry_dynamics",
        ),
        (
            "报告期内，公司主营业务的交付效率持续提升。",
            "quarterly_report",
            "core_business",
        ),
        (
            "截至2025年，公司第二曲线业务的商业化能力持续提升。",
            "investor_relations",
            "new_business",
        ),
        (
            "报告期内，公司募投项目的建设进度持续加快。",
            "quarterly_report",
            "capacity_projects",
        ),
        (
            "2025年报告期，公司海外市场本地化服务响应能力持续提升。",
            "investor_relations",
            "overseas",
        ),
    ),
)
def test_current_operating_progress_is_selected_for_titleless_known_documents(
    text: str, document_kind: str, expected_topic: str
) -> None:
    source_id, source_sha = _source(f"n4t2:{document_kind}:{expected_topic}")
    unit = _unit(
        text,
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=7, paragraph_index=2),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(unit,),
        page_count=9,
        pages_read=9,
    )

    package = select_narrative_evidence(
        parsed,
        title="",
        existing_kind=document_kind,
    )

    assert package.document_kind == document_kind
    assert package.status == "selected"
    assert len(package.evidence_spans) == 1
    span = package.evidence_spans[0]
    assert span.source_id == source_id
    assert span.coordinates.page_number == 7
    assert expected_topic in span.structured_value["topics"]
    verified, failed = verify_replayed_pdf_spans(package.evidence_spans, parsed.units)
    assert verified == (span.span_id,)
    assert failed == ()


@pytest.mark.parametrize(
    "text",
    (
        "报告期内，公司持续关注海外市场动态，积极做好主营业务经营管理。",
        "公司主营业务是指高端装备研发、生产和销售，海外市场是公司未来的发展方向。",
        "主营业务进展……………………12",
    ),
)
def test_complete_report_with_boilerplate_static_background_or_contents_requires_review(
    text: str,
) -> None:
    source_id, source_sha = _source(f"n4t2:negative:{text}")
    unit = _unit(
        text,
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=0),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(unit,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(
        parsed,
        title="",
        existing_kind="quarterly_report",
    )

    assert package.evidence_spans == ()
    assert package.status == "needs_review"
    assert package.coverage_complete is True


def test_complete_quarterly_financial_table_can_skip_as_non_narrative() -> None:
    source_id, source_sha = _source("n4t2:financial")
    financial = _unit(
        "营业收入 | 100.0亿元",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, table_index=0, row_index=1),
        kind="pdf_table_row",
        metadata={
            "row_cells": ("营业收入", "100.0亿元"),
            "table_headers": ("项目", "本期发生额"),
        },
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(financial,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(
        parsed,
        title="",
        existing_kind="quarterly_report",
    )

    assert package.evidence_spans == ()
    assert package.dropped_financial_count == 1
    assert package.status == "skipped_no_narrative"


def test_capacity_risk_and_operating_permit_milestones_are_selected() -> None:
    source_id, source_sha = _source()
    capacity_risk = _unit(
        "报告期内，公司氟碳类产品的产能已趋饱和。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=33, paragraph_index=3),
    )
    permit_milestone = _unit(
        "公司已取得新增产品和新增产能的生产许可和充装许可。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=33, paragraph_index=5),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(capacity_risk, permit_milestone),
        page_count=33,
        pages_read=33,
    )

    package = select_narrative_evidence(parsed, title="首次公开发行招股说明书.pdf")

    assert len(package.evidence_spans) == 2
    risk_span = next(span for span in package.evidence_spans if "饱和" in (span.raw_text or ""))
    permit_span = next(
        span for span in package.evidence_spans if "生产许可" in (span.raw_text or "")
    )
    assert "business_risk_or_constraint" in risk_span.structured_value["selection_reasons"]
    assert "specific_business_event" in permit_span.structured_value["selection_reasons"]


def test_explicit_capacity_and_certification_constraints_win_tight_prospectus_budget() -> None:
    source_id, source_sha = _source()
    capacity_limit = _unit(
        "报告期内，公司氟碳类产品的产能已趋饱和。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=33, paragraph_index=3),
    )
    qualification_delay = _unit(
        "半导体特种气体产品获得终端客户认证时间较长。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=295, paragraph_index=8),
    )
    ordinary_event = _unit(
        "公司推出新产品并完成客户验证，相关业务持续拓展。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=120, paragraph_index=4),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(capacity_limit, qualification_delay, ordinary_event),
        page_count=295,
        pages_read=295,
    )

    package = select_narrative_evidence(
        parsed,
        title="首次公开发行股票招股说明书.pdf",
        max_selected=2,
    )

    selected = {span.raw_text for span in package.evidence_spans}
    assert selected == {capacity_limit.raw_text, qualification_delay.raw_text}


def test_product_name_context_and_permit_milestone_survive_prospectus_budget() -> None:
    source_id, source_sha = _source()
    capacity_limit = _unit(
        "报告期内，公司氟碳类产品的产能已趋饱和。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=33, paragraph_index=3),
    )
    permit_milestone = _unit(
        "公司已取得新增产品和新增产能的生产许可和充装许可。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=33, paragraph_index=5),
    )
    named_product = _unit(
        "报告期内，公司先后实现了高纯三氟甲烷、高纯",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=295, paragraph_index=4),
    )
    product_milestone = _unit(
        "八氟丙烷等氟碳类新产品的量产，并陆续获得终端客户的认证。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=295, paragraph_index=5),
    )
    generic_events = tuple(
        _unit(
            f"公司推出新产品并完成海外客户验证，相关进展编号{i}。",
            source_id=source_id,
            coords=EvidenceCoordinates(page_number=120, paragraph_index=i),
        )
        for i in (1, 2)
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(capacity_limit, permit_milestone, named_product, product_milestone, *generic_events),
        page_count=295,
        pages_read=295,
    )

    package = select_narrative_evidence(
        parsed,
        title="首次公开发行股票招股说明书.pdf",
        max_selected=5,
    )

    selected = {span.raw_text for span in package.evidence_spans}
    assert capacity_limit.raw_text in selected
    assert permit_milestone.raw_text in selected
    assert named_product.raw_text in selected
    assert product_milestone.raw_text in selected
    pair_group_ids = {
        span.structured_value.get("selection_group_id")
        for span in package.evidence_spans
        if span.raw_text in {named_product.raw_text, product_milestone.raw_text}
    }
    assert len(pair_group_ids) == 1
    assert None not in pair_group_ids
    assert len(package.evidence_spans) <= 5


def test_pdf_candidate_budget_reserves_first_pass_coverage_across_pages() -> None:
    source_id, source_sha = _source()
    high_priority = [
        _unit(
            f"公司已推出新产品并完成海外客户验证，形成订单交付进展{i}。",
            source_id=source_id,
            coords=EvidenceCoordinates(page_number=1, paragraph_index=i),
        )
        for i in range(3)
    ]
    capacity_risk = _unit(
        "报告期内，公司氟碳类产品的产能已趋饱和。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=4),
    )
    lower_priority_other_page = _unit(
        "公司已推出新产品，相关业务正在开拓重点市场。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, paragraph_index=0),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(*high_priority, capacity_risk, lower_priority_other_page),
        page_count=2,
        pages_read=2,
    )

    package = select_narrative_evidence(
        parsed,
        title="首次公开发行招股说明书.pdf",
        max_selected=2,
    )

    assert package.candidate_count > 2
    assert {span.coordinates.page_number for span in package.evidence_spans} == {1, 2}
    assert package.omitted_candidate_count == package.candidate_count - 2
    assert any("产能已趋饱和" in (span.raw_text or "") for span in package.evidence_spans)
    assert package.status == "partial"


def test_visual_context_groups_are_atomic_and_never_exceed_the_span_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id, source_sha = _source()
    heading = _unit(
        "本项目建设的必要性",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=0),
    )
    group_first = _unit(
        "本项目建成后将实现航空产业升级",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=1),
    )
    group_second = _unit(
        "并带动外协加工需求持续增长。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=2),
    )
    standalone = _unit(
        "海外市场新增客户订单，已完成产品验证。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, paragraph_index=0),
    )
    standalone_second = _unit(
        "国际市场新业务已签订合作协议，进入客户验证阶段。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, paragraph_index=1),
    )
    heading_group = "urn:company-wiki:context-group:heading"
    body_group = "urn:company-wiki:context-group:body"
    monkeypatch.setattr(
        narrative_evidence_module,
        "_pdf_context_groups",
        lambda _units: (
            (heading_group, (heading,), "本项目建设的必要性"),
            (
                body_group,
                (group_first, group_second),
                "本项目建成后将实现航空产业升级并带动外协加工需求持续增长。",
            ),
            ("urn:company-wiki:context-group:standalone", (standalone,), standalone.raw_text),
            (
                "urn:company-wiki:context-group:standalone-second",
                (standalone_second,),
                standalone_second.raw_text,
            ),
        ),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(heading, group_first, group_second, standalone, standalone_second),
        page_count=2,
        pages_read=2,
    )

    package = select_narrative_evidence(
        parsed,
        title="向特定对象发行股票募集说明书.pdf",
        max_selected=2,
    )

    assert len(package.evidence_spans) <= 2
    selected_group_ids = {
        span.structured_value.get("selection_group_id")
        for span in package.evidence_spans
        if span.structured_value.get("selection_group_id") is not None
    }
    assert body_group not in selected_group_ids
    assert all(span.coordinates.page_number == 2 for span in package.evidence_spans)

    package_with_room = select_narrative_evidence(
        parsed,
        title="向特定对象发行股票募集说明书.pdf",
        max_selected=3,
    )
    selected_body_group = [
        span
        for span in package_with_room.evidence_spans
        if span.structured_value.get("selection_group_id") == body_group
    ]
    assert len(package_with_room.evidence_spans) == 3
    assert {span.coordinates.paragraph_index for span in selected_body_group} == {1, 2}


def test_numbered_project_rationale_heading_survives_a_tight_budget() -> None:
    source_id, source_sha = _source()
    rationale = _unit(
        "（1）航空产业形成“小核心、大协作”的发展格局，主机厂中小锻件外协需求旺盛",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=3),
    )
    generic_events = tuple(
        _unit(
            f"公司已推出新产品并完成海外客户验证，新增市场进展{i}。",
            source_id=source_id,
            coords=EvidenceCoordinates(page_number=page, paragraph_index=i),
        )
        for page, i in ((2, 1), (3, 1), (4, 1))
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(rationale, *generic_events),
        page_count=101,
        pages_read=101,
    )

    package = select_narrative_evidence(
        parsed,
        title="向特定对象发行股票募集说明书.pdf",
        max_selected=1,
    )

    assert len(package.evidence_spans) == 1
    assert "航空产业形成" in (package.evidence_spans[0].raw_text or "")
    assert "specific_project_rationale" in package.evidence_spans[0].structured_value[
        "selection_reasons"
    ]


def test_split_project_rationale_heading_keeps_its_short_continuation() -> None:
    source_id, source_sha = _source()
    heading = _unit(
        "（1）航空产业形成“小核心、大协作”的发展格局，主机厂中小锻件外协需",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=3),
    )
    continuation = _unit(
        "求旺盛",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=4),
    )
    generic_events = tuple(
        _unit(
            f"公司已推出新产品并完成海外客户验证，新增市场进展{i}。",
            source_id=source_id,
            coords=EvidenceCoordinates(page_number=page, paragraph_index=1),
        )
        for page, i in ((2, 1), (3, 1))
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(heading, continuation, *generic_events),
        page_count=101,
        pages_read=101,
    )

    package = select_narrative_evidence(
        parsed,
        title="向特定对象发行股票募集说明书.pdf",
        max_selected=2,
    )

    selected = [
        span for span in package.evidence_spans if span.coordinates.page_number == 101
    ]
    assert [span.coordinates.paragraph_index for span in selected] == [3, 4]
    assert "需求旺盛" in "".join(span.raw_text or "" for span in selected)
    assert len(
        {span.structured_value.get("selection_group_id") for span in selected[:3]}
    ) == 1


def test_project_certification_timeline_is_selected_as_a_narrow_fragment_group() -> None:
    source_id, source_sha = _source()
    generic_certification = _unit(
        "供应商认证一般需要1-3个月，具体根据客户要求及项目情况而定。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=2, paragraph_index=1),
    )
    generic_event = _unit(
        "公司已推出新产品并完成客户验证。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=1),
    )
    project_name_prefix = _unit(
        "航空数字",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=37),
        metadata={"pdf_block": 22, "block_char_start": 0, "block_char_end": 4},
    )
    project_timeline = _unit(
        "化集成中心项目需要进行合格供应商认证和产品认证，预计需要4-9个月。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=38),
        metadata={"pdf_block": 22, "block_char_start": 4, "block_char_end": 38},
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(generic_certification, generic_event, project_name_prefix, project_timeline),
        page_count=3,
        pages_read=3,
    )

    package = select_narrative_evidence(
        parsed,
        title="向特定对象发行股票募集说明书.pdf",
        max_selected=2,
    )

    assert [span.raw_text for span in package.evidence_spans] == [
        project_name_prefix.raw_text,
        project_timeline.raw_text,
    ]
    assert "project_certification_timeline" in package.evidence_spans[1].structured_value[
        "selection_reasons"
    ]
    assert len(
        {span.structured_value.get("selection_group_id") for span in package.evidence_spans}
    ) == 1


def test_prospectus_reserves_extension_and_named_timeline_groups() -> None:
    source_id, source_sha = _source()
    project_intro = _unit(
        "航空数字化集成中心项目属于在公",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=12),
        metadata={"pdf_block": 23},
    )
    extension = _unit(
        "司现有业务锻件制造的基础上，向下游装配产业领域的延伸和拓展，需要进行",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=13),
        metadata={"pdf_block": 23},
    )
    certification = _unit(
        "合格供应商认证和产品认证。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=14),
        metadata={"pdf_block": 23},
    )
    timeline_name = _unit(
        "航空数字",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=37),
        metadata={"pdf_block": 24, "block_char_start": 0, "block_char_end": 4},
    )
    timeline = _unit(
        "化集成中心项目需要进行合格供应商认证和产品认证，预计需要4-9个月。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=38),
        metadata={"pdf_block": 24, "block_char_start": 4, "block_char_end": 38},
    )
    generic_event = _unit(
        "公司已推出新产品并完成客户验证。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=1, paragraph_index=1),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(generic_event, project_intro, extension, certification, timeline_name, timeline),
        page_count=3,
        pages_read=3,
    )

    package = select_narrative_evidence(
        parsed,
        title="向特定对象发行股票募集说明书.pdf",
        max_selected=5,
    )

    selected = [
        span for span in package.evidence_spans if span.coordinates.page_number == 3
    ]
    assert [span.raw_text for span in selected] == [
        project_intro.raw_text,
        extension.raw_text,
        certification.raw_text,
        timeline_name.raw_text,
        timeline.raw_text,
    ]
    assert "downstream_business_extension" in selected[1].structured_value[
        "selection_reasons"
    ]
    assert len(
        {span.structured_value.get("selection_group_id") for span in selected[:3]}
    ) == 1
    timeline_span = next(span for span in selected if span.raw_text == timeline.raw_text)
    assert "downstream_center_certification_timeline" in timeline_span.structured_value[
        "selection_reasons"
    ]
    assert len({span.structured_value.get("selection_group_id") for span in selected}) == 2


def test_prospectus_defaults_to_more_narrative_capacity_than_quarterly_reports() -> None:
    source_id, source_sha = _source()
    units = tuple(
        _unit(
            f"公司推出新产品并通过客户验证，业务进展编号{i}。",
            source_id=source_id,
            coords=EvidenceCoordinates(page_number=1, paragraph_index=i),
        )
        for i in range(200)
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=units,
        page_count=1,
        pages_read=1,
    )

    prospectus = select_narrative_evidence(parsed, title="首次公开发行招股说明书.pdf")
    quarterly = select_narrative_evidence(parsed, title="2026年一季报.pdf")

    assert prospectus.selection_limit > quarterly.selection_limit
    assert len(prospectus.evidence_spans) == prospectus.selection_limit
    assert len(quarterly.evidence_spans) == quarterly.selection_limit
    assert len(prospectus.evidence_spans) > len(quarterly.evidence_spans)
    assert prospectus.status == "partial"
    assert quarterly.status == "partial"


def test_future_market_coverage_plan_is_selected_as_a_plan() -> None:
    source_id, source_sha = _source()
    unit = _unit(
        "预计未来五到十年，公司将通过自主研发和行业合作覆盖集成电路关键设备市场超过60%。",
        source_id=source_id,
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(unit,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(parsed, title="半年报.pdf")

    assert len(package.evidence_spans) == 1
    assert "project_plan_or_status" in package.evidence_spans[0].structured_value["selection_reasons"]


def test_split_quantified_market_coverage_target_is_kept_as_one_budgeted_group() -> None:
    source_id, source_sha = _source()
    prefix_text = "预计未来五到十年，中微公司将通过自主研发以及携手行业合作伙伴，覆盖集成电路关键领域超"
    suffix_text = "过60%的设备市场。"
    prefix = _unit(
        prefix_text,
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=21, paragraph_index=3),
        metadata={
            "pdf_block": 3,
            "block_char_start": 0,
            "block_char_end": len(prefix_text),
        },
    )
    suffix = _unit(
        suffix_text,
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=21, paragraph_index=4),
        metadata={
            "pdf_block": 3,
            "block_char_start": len(prefix_text),
            "block_char_end": len(prefix_text) + len(suffix_text),
        },
    )
    competing_event = _unit(
        "公司推出新产品并获得海外客户订单。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=22, paragraph_index=1),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(prefix, suffix, competing_event),
        page_count=22,
        pages_read=22,
    )

    package = select_narrative_evidence(parsed, title="半年报.pdf", max_selected=2)

    assert {span.coordinates.paragraph_index for span in package.evidence_spans} == {3, 4}
    assert len(package.evidence_spans) == 2
    assert len({span.structured_value["selection_group_id"] for span in package.evidence_spans}) == 1
    assert all(
        "quantified_market_coverage_target" in span.structured_value["selection_reasons"]
        for span in package.evidence_spans
    )
    assert _anchor_evidence_ids(
        list(package.evidence_spans), "60%的设备市场"
    ) == (package.evidence_spans[1].span_id,)


def test_adjacent_product_context_is_retained_for_a_validation_event() -> None:
    source_id, source_sha = _source()
    subject = _unit(
        "四款MOCVD新产品包括用于功率器件、Micro-LED和红黄光LED的设备。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=24),
    )
    event = _unit(
        "其中GaAs MOCVD设备已进入客户端验证阶段，部分获得批量订货。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=25),
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(subject, event),
        page_count=15,
        pages_read=15,
    )

    package = select_narrative_evidence(parsed, title="一季报.pdf")

    assert {span.coordinates.paragraph_index for span in package.evidence_spans} == {24, 25}
    assert any(
        "adjacent_subject_context" in span.structured_value["selection_reasons"]
        for span in package.evidence_spans
    )


def test_pdf_block_sentences_are_split_before_topic_matching() -> None:
    fragments = _sentence_fragments(
        "与公司签订《劳动合同》的董事、监事及核心技术人员从本公司领取薪酬。"
        "公司推出新产品并获得海外客户订单。"
    )

    assert [fragment[2] for fragment in fragments] == [
        "与公司签订《劳动合同》的董事、监事及核心技术人员从本公司领取薪酬。",
        "公司推出新产品并获得海外客户订单。",
    ]


def test_order_production_definition_is_not_mistaken_for_a_recent_order() -> None:
    source_id, source_sha = _source()
    definition = _unit(
        "订单式生产是指公司在与客户签订订单后，根据订单情况安排生产。",
        source_id=source_id,
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(definition,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(parsed, title="招股说明书.pdf")

    assert package.evidence_spans == ()


def test_specific_cooperation_event_does_not_require_a_predeclared_topic_word() -> None:
    source_id, source_sha = _source()
    event = _unit(
        "公司已与合作方签署项目合作意向书。",
        source_id=source_id,
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(event,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(parsed, title="投资者关系活动记录.pdf")

    assert len(package.evidence_spans) == 1
    assert package.evidence_spans[0].structured_value["topics"] == ("new_business",)
    assert "specific_business_event" in package.evidence_spans[0].structured_value[
        "selection_reasons"
    ]


def test_pilot_line_milestone_is_classified_as_operational_evidence() -> None:
    source_id, source_sha = _source()
    event = _unit(
        "硫化锂中试线建设工作正在按计划推进，预计6月底完成建设并开展中试工作。",
        source_id=source_id,
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(event,),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(parsed, title="投资者关系活动记录.pdf")

    assert len(package.evidence_spans) == 1
    assert "capacity_projects" in package.evidence_spans[0].structured_value["topics"]
    assert package.status == "selected"


def test_table_scan_signal_requires_a_specific_event_or_current_industry_context() -> None:
    assert not _table_scan_signal("市场需求持续增长，公司研发项目较多。")
    assert _table_scan_signal("2025年新产线已完成客户验证并进入量产。")
    assert _table_scan_signal("本报告期行业竞争格局和政策变化明显。")
    assert _table_scan_signal("问：新产品什么时候量产？答：已通过客户验证。")


def test_pdf_investor_question_is_selected_only_as_context_for_a_selected_answer() -> None:
    source_id, source_sha = _source()
    question = _unit(
        "问：新产品什么时候通过客户验证？",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=5, table_index=0, row_index=0, column_index=1),
        kind="pdf_table_qa_fragment",
        role="investor_question",
        metadata={"qa_group_id": "p5:t0:r0:c1:q1", "qa_state": "question_paired"},
    )
    answer = _unit(
        "答：新产品已通过客户验证并取得首批订单。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=5, table_index=0, row_index=0, column_index=1),
        kind="pdf_table_qa_fragment",
        role="management",
        metadata={"qa_group_id": "p5:t0:r0:c1:q1", "qa_state": "answer_paired"},
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(question, answer),
        page_count=5,
        pages_read=5,
    )

    package = select_narrative_evidence(parsed, title="投资者关系活动记录.pdf")

    roles = [span.structured_value["source_role"] for span in package.evidence_spans]
    assert roles == ["investor_question", "management"]
    assert package.status == "selected"


def test_financing_project_heading_selects_and_groups_split_paragraph_context() -> None:
    source_id, source_sha = _source()
    heading = _unit(
        "2、项目建设的必要性",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=0),
        metadata={"pdf_block": 1, "bbox": (100.0, 70.0, 280.0, 84.0)},
    )
    first_line = _unit(
        "本项目以延伸锻件产业链、拓展航空零部件精密加工业务为目标，",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=1),
        metadata={"pdf_block": 2, "bbox": (100.0, 105.0, 480.0, 118.0)},
    )
    second_line = _unit(
        "并向下游装配延伸，逐步实现零件交付。",
        source_id=source_id,
        coords=EvidenceCoordinates(page_number=101, paragraph_index=2),
        metadata={"pdf_block": 3, "bbox": (90.0, 129.0, 480.0, 142.0)},
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        units=(heading, first_line, second_line),
        page_count=101,
        pages_read=101,
    )

    package = select_narrative_evidence(
        parsed,
        title="西安三角防务向特定对象发行股票募集说明书.pdf",
    )

    assert [span.raw_text for span in package.evidence_spans] == [
        first_line.raw_text,
        second_line.raw_text,
    ]
    group_ids = {
        span.structured_value["selection_group_id"] for span in package.evidence_spans
    }
    assert len(group_ids) == 1
    summary_group = package.summary_input()["evidence"][0]
    assert summary_group["context_member_count"] == 2
    assert summary_group["evidence_ids"] == [span.span_id for span in package.evidence_spans]
    assert summary_group["raw_text"] == first_line.raw_text + second_line.raw_text
    assert len(summary_group["locators"]) == 2


def test_company_statement_rejects_unknown_roles_and_unstable_locators_need_review() -> None:
    source_id, source_sha = _source()
    # Rebuild an unstable EvidenceSpan through the normal unit constructor.
    unstable_unit = _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, table_index=0, row_index=0, column_index=1),
        raw_text="新产品已通过客户验证并获得订单。",
        unit_kind="pdf_table_qa_fragment",
        source_role="company_filing",
        language="zh",
        metadata={"cell_fragment_sha256": "test"},
        quality_flags=("locator_unstable",),
    ).to_evidence_span(topics=("new_business",), selection_reasons=("test",))
    draft = SourceSummaryDraft(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        claims=(
            SummaryClaim(
                claim_id="claim-1",
                text="新产品已通过验证。",
                evidence_ids=(unstable_unit.span_id,),
                claim_type="company_statement",
                modality="actual",
            ),
        ),
    )

    # Status is program-owned quality metadata, not a second citation gate.
    validate_summary_draft(
        draft, source_id=source_id, source_sha256=source_sha, language="zh",
        evidence_spans=(unstable_unit,),
    )
    projected = project_summary_quality(draft, evidence_spans=(unstable_unit,))
    assert projected.status == "needs_review"
    assert projected.claims[0].needs_review is True
    assert projected.claims[0].text == draft.claims[0].text

    unknown_unit = _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=2),
        raw_text="新产品已通过客户验证并获得订单。",
        unit_kind="pdf_text_block",
        source_role="unknown",
        language="zh",
        metadata={},
    ).to_evidence_span(topics=("new_business",), selection_reasons=("test",))
    ordinary_draft = SourceSummaryDraft(
        source_id=source_id,
        source_sha256=source_sha,
        language="zh",
        claims=(
            SummaryClaim(
                claim_id="claim-2",
                text="新产品已通过验证。",
                evidence_ids=(unknown_unit.span_id,),
                claim_type="company_statement",
                modality="actual",
            ),
        ),
    )
    with pytest.raises(SummaryValidationError, match="non-company evidence"):
        validate_summary_draft(
            ordinary_draft,
            source_id=source_id,
            source_sha256=source_sha,
            language="zh",
            evidence_spans=(unknown_unit,),
        )


@pytest.mark.parametrize("text", (
    "公司业务主要包括研发、生产及销售，并持续关注海外市场。",
    "公司重视销售渠道和客户群体的管理，积极做好主营业务。",
    "公司产品包括各类设备与配套解决方案。",
    "公司高度重视生产流程，持续关注行业发展。",
))
def test_new_business_policy_does_not_promote_generic_categories_or_labels(text: str) -> None:
    source_id, source_sha = _source(text)
    unit = _unit(text, source_id=source_id)
    parsed = NarrativeParseResult(source_id=source_id, source_sha256=source_sha,
        language="zh", units=(unit,), page_count=1, pages_read=1)
    package = select_narrative_evidence(parsed, title="年报.pdf", selector_version="0.7.0")
    assert package.evidence_spans == ()
    assert package.status == "needs_review"
    assert package.coverage_complete is True


@pytest.mark.parametrize("text", (
    "公司的产品包括工业控制器与电动执行器。",
    "公司的产品分为控制器与执行器，产品用于设备厂的运动控制。",
    "公司主要采用以销定产的生产模式，生产流程按照模块化设计。",
    "公司通过海外经销商销售工业设备，并由本地渠道提供安装服务。",
))
def test_new_business_policy_retains_concrete_static_operating_relationships(text: str) -> None:
    source_id, source_sha = _source(text)
    unit = _unit(text, source_id=source_id)
    parsed = NarrativeParseResult(source_id=source_id, source_sha256=source_sha,
        language="zh", units=(unit,), page_count=1, pages_read=1)
    package = select_narrative_evidence(parsed, title="招股说明书.pdf", selector_version="0.7.0")
    assert [span.raw_text for span in package.evidence_spans] == [text]
    assert package.selection_limit == 160
    assert "business_structure" in package.evidence_spans[0].structured_value["selection_reasons"]
    assert verify_replayed_pdf_spans(package.evidence_spans, parsed.units) == (
        (package.evidence_spans[0].span_id,), ())


@pytest.mark.parametrize("limit", (1, 2))
def test_already_selected_product_and_referential_event_are_an_atomic_original_pair(limit: int) -> None:
    source_id, source_sha = _source("referential-product-pair")
    texts = ("四款MOCVD新产品包括用于功率器件、Micro-LED和红黄光LED的设备。",
        "其中GaAs MOCVD设备已进入客户端验证阶段，部分获得批量订货。")
    members = tuple(_unit(text, source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=24 + i))
        for i, text in enumerate(texts))
    parsed = NarrativeParseResult(source_id=source_id, source_sha256=source_sha,
        language="zh", units=members, page_count=3, pages_read=3)
    package = select_narrative_evidence(parsed, title="一季报.pdf", max_selected=limit,
        selector_version="0.7.0")
    if limit == 1:
        assert package.evidence_spans == ()
        assert package.status == "partial"
        assert package.omitted_candidate_count == package.candidate_count == 2
    else:
        assert [span.raw_text for span in package.evidence_spans] == list(texts)
        assert len({span.structured_value["selection_group_id"] for span in package.evidence_spans}) == 1
        assert "adjacent_subject_context" in package.evidence_spans[0].structured_value["selection_reasons"]
        assert tuple(span.coordinates.paragraph_index for span in package.evidence_spans) == (24, 25)
        assert verify_replayed_pdf_spans(package.evidence_spans, parsed.units) == (
            tuple(span.span_id for span in package.evidence_spans), ())


@pytest.mark.parametrize("boundary", ("speaker", "qa_group_id", "parent_content_sha256", "section"))
def test_already_selected_product_context_does_not_bridge_distinct_boundaries(boundary: str) -> None:
    source_id, source_sha = _source("separate-product-pair")
    texts = ("四款MOCVD新产品包括用于功率器件、Micro-LED和红黄光LED的设备。",
        "其中GaAs MOCVD设备已进入客户端验证阶段，部分获得批量订货。")
    members = tuple(_unit(text, source_id=source_id,
        coords=EvidenceCoordinates(page_number=3, paragraph_index=24 + i),
        metadata={boundary: str(i)}) for i, text in enumerate(texts))
    parsed = NarrativeParseResult(source_id=source_id, source_sha256=source_sha,
        language="zh", units=members, page_count=3, pages_read=3)
    package = select_narrative_evidence(parsed, title="一季报.pdf", selector_version="0.7.0")
    assert {span.raw_text for span in package.evidence_spans} == set(texts)
    assert all("adjacent_subject_context" not in span.structured_value["selection_reasons"]
        for span in package.evidence_spans)
    groups = [span.structured_value.get("selection_group_id") for span in package.evidence_spans]
    assert not (groups[0] is not None and groups[0] == groups[1])


@pytest.mark.parametrize("text, selected", (
    ("公司产品包括各类设备及配套服务等。", False),
    ("公司产品包括各类设备以及配套解决方案等等。", False),
    ("公司产品包括产品、设备及相关服务等类型。", False),
    ("公司的产品包括工业控制器与电动执行器等。", True),
    ("公司的产品包括工业控制器以及等离子刻蚀设备等。", True),
))
def test_component_enumeration_grammar_is_not_a_specific_operating_object(
    text: str, selected: bool,
) -> None:
    source_id, source_sha = _source(text)
    unit = _unit(text, source_id=source_id)
    parsed = NarrativeParseResult(source_id=source_id, source_sha256=source_sha,
        language="zh", units=(unit,), page_count=1, pages_read=1)
    package = select_narrative_evidence(parsed, title="招股说明书.pdf", selector_version="0.7.0")
    assert bool(package.evidence_spans) is selected
    if selected:
        assert [span.raw_text for span in package.evidence_spans] == [text]
        assert "business_structure" in package.evidence_spans[0].structured_value["selection_reasons"]
        assert verify_replayed_pdf_spans(package.evidence_spans, parsed.units) == (
            (package.evidence_spans[0].span_id,), ())
    else:
        assert package.status == "needs_review"
        assert package.coverage_complete is True
