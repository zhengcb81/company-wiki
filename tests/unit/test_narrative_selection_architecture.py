from __future__ import annotations

import re

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
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import NarrativeParseResult, _make_unit
from company_wiki.source_catalog.narrative_routing import route_document
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.mark.parametrize(
    ("title", "existing_kind", "expected_kind", "expected_limit"),
    (
        ("2025年度报告.pdf", "unknown", "annual_report", 160),
        ("2026年半年度报告.pdf", "unknown", "semi_annual_report", 160),
        ("2026年第一季度报告.pdf", "unknown", "quarterly_report", 160),
        ("首次公开发行招股说明书.pdf", "unknown", "prospectus", 320),
        (
            "向特定对象发行股票募集说明书.pdf",
            "unknown",
            "equity_offering_prospectus",
            320,
        ),
        (
            "向不特定对象发行可转换公司债券募集说明书.pdf",
            "unknown",
            "convertible_bond_prospectus",
            320,
        ),
        ("2026_Q2_earnings_call.txt", "unknown", "investor_call_transcript", 160),
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
        page_key=("page", str(page)),
        locator=(page, item_id),
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
        _budget_item("risk", page=2, reasons=("business_risk_or_constraint",), score=20),
    )

    selected = select_budget_items(items, limit=2)
    selected_ids = {item.item_id for item in selected}

    assert "extension" in selected_ids
    assert len(selected_ids) == 2


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
        parser_version="test",
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
        parser_version="test",
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
        ("body", (unit("本项目用于新产品产业化并拓展海外客户。", 1),), "本项目用于新产品产业化并拓展海外客户。"),
        ("next", (unit("三、财务会计信息", 2),), "三、财务会计信息"),
        ("outside", (unit("本段不属于项目上下文。", 3),), "本段不属于项目上下文。"),
    )
    rules = ContextRules(
        project_heading=re.compile(r"项目建设必要性"),
        business_heading=re.compile(r"主营业务"),
        heading_only=re.compile(r"^[一二三四五六七八九十]+、"),
    )

    context = build_section_context(
        "equity_offering_prospectus", groups, rules
    )

    assert context.project_scores == {"body": 120}
    assert "outside" not in context.project_scores

