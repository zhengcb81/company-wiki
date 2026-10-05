from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from company_wiki.source_catalog.narrative_budget import (
    BudgetItem,
    select_budget_items,
)
from company_wiki.source_catalog.narrative_candidates import (
    CandidateRules,
    assess_unit,
)
from company_wiki.source_catalog.narrative_context import (
    ContextRules,
    build_section_context,
)
from company_wiki.source_catalog.narrative_document import (
    DocumentStructure,
    NarrativeUnit,
)
from company_wiki.source_catalog.narrative_evidence import (
    NarrativeParseResult,
    _make_unit,
)
from company_wiki.source_catalog.narrative_group_candidates import (
    GroupCandidateRules,
    enrich_context_groups,
)
from company_wiki.source_catalog.narrative_neighbors import (
    NeighborRules,
    enrich_neighbor_context,
)
from company_wiki.source_catalog.narrative_pdf_groups import (
    PdfGroupRules,
    build_pdf_context_groups,
)
from company_wiki.source_catalog.narrative_replay import prepare_pdf_replay
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_routing import (
    DEFAULT_SELECTION_LIMIT,
    route_document,
)
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.mark.parametrize(
    ("title", "existing_kind", "expected_kind", "expected_limit"),
    (
        ("2025年度报告.pdf", "unknown", "annual_report", 96),
        ("2026年半年度报告.pdf", "unknown", "semi_annual_report", 96),
        ("2026年第一季度报告.pdf", "unknown", "quarterly_report", 96),
        ("首次公开发行招股说明书.pdf", "unknown", "prospectus", 160),
        (
            "向特定对象发行股票募集说明书.pdf",
            "unknown",
            "equity_offering_prospectus",
            160,
        ),
        (
            "向不特定对象发行可转换公司债券募集说明书.pdf",
            "unknown",
            "convertible_bond_prospectus",
            160,
        ),
        ("2026_Q2_earnings_call.txt", "unknown", "investor_call_transcript", 96),
    ),
)
def test_route_document_owns_kind_and_default_budget(
    title: str,
    existing_kind: str,
    expected_kind: str,
    expected_limit: int,
) -> None:
    route = route_document(title, existing_kind=existing_kind)

    assert route.document_kind == expected_kind
    assert route.selection_limit == expected_limit
    assert route.empty_result_may_skip is False


@pytest.mark.parametrize(
    "title",
    (
        "投资者关系管理办法（2025年8月）.pdf",
        "关于召开2025年度业绩说明会的通知.pdf",
    ),
)
def test_only_known_format_documents_may_skip_after_complete_coverage(
    title: str,
) -> None:
    route = route_document(title)

    assert route.empty_result_may_skip is True


def test_route_document_keeps_explicit_budget_and_rejects_invalid_values() -> None:
    route = route_document("首次公开发行招股说明书.pdf", max_selected=17)
    assert route.selection_limit == 17

    with pytest.raises(ValueError, match="max_selected must be positive"):
        route_document("2025年度报告.pdf", max_selected=0)


def test_pdf_groups_join_visual_continuations_but_isolate_headings() -> None:
    source_id = source_id_for_sha256("a" * 64)

    def unit(text: str, paragraph: int, bbox: tuple[float, ...]) -> NarrativeUnit:
        return _make_unit(
            source_id=source_id,
            parser_version="0.1.0",
            coordinates=EvidenceCoordinates(page_number=7, paragraph_index=paragraph),
            raw_text=text,
            unit_kind="pdf_text_block",
            source_role="company_filing",
            language="zh",
            metadata={"pdf_block": paragraph, "bbox": bbox},
        )

    heading = unit("项目建设的必要性", 0, (100.0, 50.0, 260.0, 64.0))
    first = unit("本项目将建设新产线，", 1, (100.0, 80.0, 460.0, 94.0))
    second = unit("并拓展海外客户。", 2, (95.0, 102.0, 460.0, 116.0))

    groups = build_pdf_context_groups(
        (heading, first, second),
        PdfGroupRules(
            project_heading=re.compile(r"项目建设的必要性"),
            business_heading=re.compile(r"(?!x)x"),
            heading_only=re.compile(r"项目建设的必要性"),
        ),
    )

    assert [group[1] for group in groups] == [(heading,), (first, second)]
    assert groups[1][2] == first.raw_text + second.raw_text


def test_pdf_replay_plan_binds_hash_source_version_and_table_pages(
    tmp_path: Path,
) -> None:
    raw = b"immutable-pdf-fixture"
    path = tmp_path / "source.pdf"
    path.write_bytes(raw)
    source_sha = hashlib.sha256(raw).hexdigest()
    source_id = source_id_for_sha256(source_sha)
    unit = _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=11, table_index=2, row_index=3),
        raw_text="新业务已进入客户验证阶段。",
        unit_kind="pdf_table_row",
        source_role="company_filing",
        language="zh",
        metadata={},
    )
    span = unit.to_evidence_span(
        topics=("new_business",),
        selection_reasons=("specific_business_event",),
    )

    plan = prepare_pdf_replay(
        path,
        source_id=source_id,
        source_sha256=source_sha,
        evidence_spans=(span,),
        default_parser_version="9.9.9",
    )

    assert plan.parser_version == "0.1.0"
    assert plan.table_pages == (11,)

    other_unit = _make_unit(
        source_id=source_id,
        parser_version="0.2.0",
        coordinates=EvidenceCoordinates(page_number=12, paragraph_index=0),
        raw_text="海外客户订单已开始交付。",
        unit_kind="pdf_text_block",
        source_role="company_filing",
        language="zh",
        metadata={},
    )
    other_span = other_unit.to_evidence_span(
        topics=("overseas",),
        selection_reasons=("specific_business_event",),
    )
    with pytest.raises(ValueError, match="one parser version"):
        prepare_pdf_replay(
            path,
            source_id=source_id,
            source_sha256=source_sha,
            evidence_spans=(span, other_span),
            default_parser_version="9.9.9",
        )


def _budget_item(
    item_id: str,
    *,
    page: int,
    group_id: str | None = None,
    reasons: tuple[str, ...] = ("specific_business_event",),
    score: int = 1,
) -> BudgetItem[str]:
    return BudgetItem(
        item_id=item_id,
        group_id=group_id,
        page_key=("page", page),
        locator=f"loc:v1/page:{page}/paragraph:0",
        order_key=(page, 0),
        reasons=reasons,
        score=score,
        is_heading=False,
        payload=item_id,
    )


def test_budget_keeps_context_groups_atomic_and_uses_remaining_space() -> None:
    items = (
        _budget_item("g1-a", page=1, group_id="g1", score=10),
        _budget_item("g1-b", page=1, group_id="g1", score=10),
        _budget_item("g1-c", page=1, group_id="g1", score=10),
        _budget_item("small", page=2, score=5),
    )

    selected = select_budget_items(items, limit=2)

    assert tuple(item.payload for item in selected) == ("small",)


def test_budget_reserves_high_value_extension_before_round_robin() -> None:
    items = (
        _budget_item("event", page=1, score=100),
        _budget_item(
            "extension",
            page=9,
            reasons=("downstream_business_extension",),
            score=1,
        ),
        _budget_item(
            "risk", page=2, reasons=("business_risk_or_constraint",), score=20
        ),
    )

    selected = select_budget_items(items, limit=2)
    selected_ids = {item.item_id for item in selected}

    assert "extension" in selected_ids
    assert len(selected_ids) == 2


def test_reserved_budget_uses_numeric_page_order_not_locator_lexicography() -> None:
    items = (
        BudgetItem(
            item_id="page-10",
            group_id=None,
            page_key=("page", 10),
            locator="loc:v1/page:10/paragraph:0",
            order_key=(10, 0),
            reasons=("downstream_center_certification_timeline",),
            score=5,
            is_heading=False,
            payload="page-10",
        ),
        BudgetItem(
            item_id="page-2",
            group_id=None,
            page_key=("page", 2),
            locator="loc:v1/page:2/paragraph:0",
            order_key=(2, 0),
            reasons=("downstream_center_certification_timeline",),
            score=5,
            is_heading=False,
            payload="page-2",
        ),
    )

    selected = select_budget_items(items, limit=1)

    assert tuple(item.payload for item in selected) == ("page-2",)


def test_budget_rejects_duplicate_ids_and_non_positive_limit() -> None:
    duplicate = _budget_item("same", page=1)
    with pytest.raises(ValueError, match="item_id values must be unique"):
        select_budget_items((duplicate, duplicate), limit=1)
    with pytest.raises(ValueError, match="limit must be positive"):
        select_budget_items((duplicate,), limit=0)


def test_legacy_parse_result_is_the_shared_document_structure_type() -> None:
    digest = "a" * 64
    structure = NarrativeParseResult(
        source_id=source_id_for_sha256(digest),
        source_sha256=digest,
        language="zh",
        units=(),
        page_count=1,
        pages_read=1,
    )

    assert isinstance(structure, DocumentStructure)
    assert structure.coverage_complete is True


def test_candidate_engine_returns_typed_reasoned_candidate() -> None:
    digest = "b" * 64
    unit = _make_unit(
        source_id=source_id_for_sha256(digest),
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="The company launched a new overseas product platform this quarter.",
        unit_kind="pdf_text_block",
        source_role="management",
        language="en",
        metadata={},
    )
    rules = CandidateRules(
        topics=lambda _text: ("new_business",),
        financial_table=lambda _unit, _topics: False,
        high_value_event=re.compile(r"launched", re.IGNORECASE),
        progress=re.compile(r"this quarter", re.IGNORECASE),
    )

    assessment = assess_unit(unit, rules)

    assert assessment.dropped_financial is False
    assert assessment.candidate is not None
    assert assessment.candidate.unit is unit
    assert assessment.candidate.topics == ("new_business",)
    assert "specific_business_event" in assessment.candidate.reasons
    assert "management_statement" in assessment.candidate.reasons


def test_candidate_engine_reports_financial_drop_without_candidate() -> None:
    digest = "c" * 64
    unit = _make_unit(
        source_id=source_id_for_sha256(digest),
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, table_index=0, row_index=0),
        raw_text="Revenue | 100 | 120",
        unit_kind="pdf_table_row",
        source_role="company_filing",
        language="en",
        metadata={},
    )
    rules = CandidateRules(
        topics=lambda _text: (),
        financial_table=lambda _unit, _topics: True,
    )

    assessment = assess_unit(unit, rules)

    assert assessment.candidate is None
    assert assessment.dropped_financial is True


def test_section_context_is_bounded_by_the_next_heading() -> None:
    digest = "d" * 64
    source_id = source_id_for_sha256(digest)

    def unit(text: str, paragraph: int):
        return _make_unit(
            source_id=source_id,
            parser_version="test",
            coordinates=EvidenceCoordinates(page_number=1, paragraph_index=paragraph),
            raw_text=text,
            unit_kind="pdf_text_block",
            source_role="company_filing",
            language="zh",
            metadata={},
        )

    groups = (
        ("heading", (unit("项目建设必要性", 0),), "项目建设必要性"),
        (
            "body",
            (unit("本项目用于新产品产业化并拓展海外客户。", 1),),
            "本项目用于新产品产业化并拓展海外客户。",
        ),
        ("next", (unit("三、财务会计信息", 2),), "三、财务会计信息"),
        ("outside", (unit("本段不属于项目上下文。", 3),), "本段不属于项目上下文。"),
    )
    rules = ContextRules(
        project_heading=re.compile(r"项目建设必要性"),
        business_heading=re.compile(r"主营业务"),
        heading_only=re.compile(r"^[一二三四五六七八九十]+、"),
    )

    context = build_section_context("equity_offering_prospectus", groups, rules)

    assert context.project_scores == {"body": 120}
    assert "outside" not in context.project_scores


def test_context_group_emits_one_atomic_quantified_target() -> None:
    digest = "e" * 64
    source_id = source_id_for_sha256(digest)

    def unit(text: str, paragraph: int):
        return _make_unit(
            source_id=source_id,
            parser_version="test",
            coordinates=EvidenceCoordinates(page_number=1, paragraph_index=paragraph),
            raw_text=text,
            unit_kind="pdf_text_block",
            source_role="company_filing",
            language="zh",
            metadata={},
        )

    members = (unit("公司计划未来市场覆盖超", 0), unit("过60%的区域。", 1))
    rules = GroupCandidateRules(
        topics=lambda _text: ("core_business",),
        quantified_market_coverage_target=re.compile(r"覆盖超过60%"),
        window_finder=lambda _members, _pattern: ((0, 1),),
    )

    result = enrich_context_groups(
        (("visual", members, "公司计划未来市场覆盖超过60%的区域。"),),
        initial_candidates=(),
        initial_group_ids={},
        project_scores={},
        business_scores={},
        rules=rules,
    )

    assert len(result.candidates) == 2
    group_ids = {result.group_ids[item.unit.unit_id] for item in result.candidates}
    assert group_ids == {"visual:market-coverage-target:0"}
    assert all(
        "quantified_market_coverage_target" in item.reasons
        for item in result.candidates
    )


def test_adjacent_named_product_context_is_grouped_with_event() -> None:
    digest = "f" * 64
    source_id = source_id_for_sha256(digest)

    def unit(text: str, paragraph: int):
        return _make_unit(
            source_id=source_id,
            parser_version="test",
            coordinates=EvidenceCoordinates(page_number=1, paragraph_index=paragraph),
            raw_text=text,
            unit_kind="pdf_text_block",
            source_role="company_filing",
            language="zh",
            metadata={},
        )

    subject = unit("新一代海外检测设备产品系列", 0)
    event = unit("上述产品已经取得客户验证并开始批量交付。", 1)
    initial = (
        assess_unit(
            event,
            CandidateRules(
                topics=lambda _text: ("new_business",),
                high_value_event=re.compile(r"验证|批量交付"),
            ),
        ).candidate,
    )
    assert initial[0] is not None

    result = enrich_neighbor_context(
        (subject, event),
        initial_candidates=(initial[0],),
        initial_group_ids={},
        rules=NeighborRules(
            topics=lambda text: ("new_business",) if "产品" in text else (),
            high_value_event=re.compile(r"验证|批量交付"),
            named_product_context=re.compile(r"设备产品系列"),
        ),
    )

    assert {item.unit.unit_id for item in result.candidates} == {
        subject.unit_id,
        event.unit_id,
    }
    assert result.group_ids[subject.unit_id] == result.group_ids[event.unit_id]


def test_finalize_deduplicates_pdf_views_and_prefers_table_locator() -> None:
    digest = "1" * 64
    source_id = source_id_for_sha256(digest)
    text_unit = _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="新产品已经取得客户验证并开始批量交付。",
        unit_kind="pdf_text_block",
        source_role="company_filing",
        language="zh",
        metadata={},
    )
    table_unit = _make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, table_index=0, row_index=0),
        raw_text=text_unit.raw_text,
        unit_kind="pdf_table_row",
        source_role="company_filing",
        language="zh",
        metadata={},
    )
    structure = DocumentStructure(
        source_id=source_id,
        source_sha256=digest,
        language="zh",
        units=(text_unit, table_unit),
        page_count=1,
        pages_read=1,
    )
    candidates = (
        assess_unit(
            text_unit,
            CandidateRules(
                topics=lambda _text: ("products_rd",),
                high_value_event=re.compile(r"客户验证|批量交付"),
            ),
        ).candidate,
        assess_unit(
            table_unit,
            CandidateRules(
                topics=lambda _text: ("products_rd",),
                high_value_event=re.compile(r"客户验证|批量交付"),
            ),
        ).candidate,
    )
    assert all(candidate is not None for candidate in candidates)

    package = finalize_selection(
        structure,
        route_document("2025年度报告.pdf", max_selected=1),
        tuple(candidate for candidate in candidates if candidate is not None),
        group_ids={},
        heading_pattern=re.compile(r"a^"),
        dropped_financial_count=0,
    )

    assert len(package.evidence_spans) == 1
    assert package.evidence_spans[0].structured_value["unit_kind"] == "pdf_table_row"


@pytest.mark.parametrize(
    ("existing_kind", "expected_kind"),
    [
        ("quarterly_report", "quarterly_report"),
        ("investor_relations", "investor_relations"),
    ],
)
def test_route_document_keeps_known_kind_when_title_is_absent(
    existing_kind: str,
    expected_kind: str,
) -> None:
    route = route_document("", existing_kind=existing_kind)

    assert route.document_kind == expected_kind
    assert route.selection_limit == DEFAULT_SELECTION_LIMIT
    assert route.empty_result_may_skip is False
    assert DEFAULT_SELECTION_LIMIT == 96


def _empty_quarterly_structure() -> DocumentStructure:
    digest = "2" * 64
    return DocumentStructure(
        source_id=source_id_for_sha256(digest),
        source_sha256=digest,
        language="zh",
        units=(),
        page_count=3,
        pages_read=3,
    )


def test_finalize_keeps_legacy_conservative_status_by_default() -> None:
    package = finalize_selection(
        _empty_quarterly_structure(),
        route_document("2026年第一季度报告.pdf"),
        (),
        group_ids={},
        heading_pattern=re.compile(r"a^"),
        dropped_financial_count=0,
    )
    assert package.status == "needs_review"


def test_finalize_allows_no_narrative_skip_only_for_proven_zero_signal() -> None:
    structure = _empty_quarterly_structure()
    route = route_document("2026年第一季度报告.pdf")

    proven = finalize_selection(
        structure,
        route,
        (),
        group_ids={},
        heading_pattern=re.compile(r"a^"),
        dropped_financial_count=0,
        narrative_signal_present=False,
    )
    assert proven.status == "skipped_no_narrative"

    with_signal = finalize_selection(
        structure,
        route,
        (),
        group_ids={},
        heading_pattern=re.compile(r"a^"),
        dropped_financial_count=0,
        narrative_signal_present=True,
    )
    assert with_signal.status == "needs_review"

    dropped_financial = finalize_selection(
        structure,
        route,
        (),
        group_ids={},
        heading_pattern=re.compile(r"a^"),
        dropped_financial_count=1,
        narrative_signal_present=False,
    )
    assert dropped_financial.status == "needs_review"
