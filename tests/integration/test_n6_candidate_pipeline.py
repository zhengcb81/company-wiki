"""N6-CANDIDATE integration: units -> assess -> section/group -> neighbor -> finalize."""

from __future__ import annotations

from pathlib import Path

from company_wiki.source_catalog import (
    narrative_candidates,
    narrative_context,
    narrative_evidence,
    narrative_group_candidates,
    narrative_neighbors,
)
from company_wiki.source_catalog.narrative_document import (
    DocumentStructure,
    NarrativeEvidencePackage,
)
from company_wiki.source_catalog.narrative_evidence import (
    _make_unit,
    select_narrative_evidence,
)
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.source_catalog.narrative_document import NarrativeUnit


_ANNUAL_DIGEST = "a1" + "0" * 62
_IR_DIGEST = "b2" + "0" * 62
_TRANSCRIPT_DIGEST = "c3" + "0" * 62


def _unit(
    text: str,
    *,
    digest: str,
    paragraph: int | None = 0,
    page: int = 1,
    role: str = "company_filing",
    language: str = "zh",
    kind: str = "pdf_text_block",
    block: int | None = None,
    metadata: dict | None = None,
    table: tuple[int, int] | None = None,
    char_range: tuple[int, int] | None = None,
) -> NarrativeUnit:
    if table is not None:
        coordinates = EvidenceCoordinates(
            page_number=page, table_index=table[0], row_index=table[1]
        )
    elif char_range is not None:
        coordinates = EvidenceCoordinates(
            page_number=None, char_start=char_range[0], char_end=char_range[1]
        )
    else:
        coordinates = EvidenceCoordinates(page_number=page, paragraph_index=paragraph)
    values: dict = dict(metadata or {})
    if block is not None:
        values.setdefault("pdf_block", block)
    return _make_unit(
        source_id=source_id_for_sha256(digest),
        parser_version="0.1.0",
        coordinates=coordinates,
        raw_text=text,
        unit_kind=kind,
        source_role=role,
        language=language,
        metadata=values,
    )


def test_modules_come_from_this_worktree_src() -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    for module in (
        narrative_candidates,
        narrative_context,
        narrative_group_candidates,
        narrative_neighbors,
        narrative_evidence,
    ):
        location = module.__file__
        assert location is not None
        assert Path(location).resolve().is_relative_to(root)


def _annual_report_units() -> tuple[NarrativeUnit, ...]:
    return (
        _unit(
            "报告期内，公司高性能钕铁硼磁材业务",
            digest=_ANNUAL_DIGEST,
            paragraph=0,
            block=7,
        ),
        _unit(
            "已通过海外头部风电客户验证，",
            digest=_ANNUAL_DIGEST,
            paragraph=1,
            block=7,
        ),
        _unit("并开始批量交付。", digest=_ANNUAL_DIGEST, paragraph=2, block=7),
        _unit(
            "2025年度公司境内收入约8.19亿元，占比约22%，较比2024年度有所提升。",
            digest=_ANNUAL_DIGEST,
            paragraph=3,
            block=8,
        ),
        _unit(
            "公司将持续推进各项管理工作，不断提升运营效率。",
            digest=_ANNUAL_DIGEST,
            paragraph=4,
            block=9,
        ),
        _unit(
            "营业收入 146,274.71 117,233.75",
            digest=_ANNUAL_DIGEST,
            paragraph=None,
            kind="pdf_table_row",
            table=(0, 3),
            metadata={
                "row_cells": ("营业收入", "146,274.71", "117,233.75"),
                "table_headers": ["项目", "金额（元）", "报告期"],
            },
        ),
        _unit("第四节 风险因素……13", digest=_ANNUAL_DIGEST, paragraph=5, block=10),
    )


def _spans_by_text(package: NarrativeEvidencePackage) -> dict[str, object]:
    return {span.raw_text: span for span in package.evidence_spans}


def test_pipeline_completes_context_and_keeps_negatives_out() -> None:
    units = _annual_report_units()
    structure = DocumentStructure(
        source_id=source_id_for_sha256(_ANNUAL_DIGEST),
        source_sha256=_ANNUAL_DIGEST,
        language="zh",
        units=units,
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(structure, title="2025年度报告.pdf")
    spans = _spans_by_text(package)

    assert "报告期内，公司高性能钕铁硼磁材业务" in spans
    assert "已通过海外头部风电客户验证，" in spans
    assert "并开始批量交付。" in spans
    assert "2025年度公司境内收入约8.19亿元，占比约22%，较比2024年度有所提升。" in spans
    assert "公司将持续推进各项管理工作，不断提升运营效率。" not in spans
    assert "营业收入 146,274.71 117,233.75" not in spans
    assert "第四节 风险因素……13" not in spans
    assert package.dropped_financial_count == 1

    subject = spans["报告期内，公司高性能钕铁硼磁材业务"]
    hit = spans["已通过海外头部风电客户验证，"]
    tail = spans["并开始批量交付。"]
    assert subject.structured_value["selection_group_id"]
    assert (
        subject.structured_value["selection_group_id"]
        == hit.structured_value["selection_group_id"]
        == tail.structured_value["selection_group_id"]
    )

    revenue = spans["2025年度公司境内收入约8.19亿元，占比约22%，较比2024年度有所提升。"]
    assert "overseas" not in revenue.structured_value["topics"]
    assert (
        "quantified_operating_status" in revenue.structured_value["selection_reasons"]
    )

    assert package.status in {"selected", "partial"}
    span_ids = [span.span_id for span in package.evidence_spans]
    assert len(span_ids) == len(set(span_ids))


def test_pipeline_is_deterministic() -> None:
    structure = DocumentStructure(
        source_id=source_id_for_sha256(_ANNUAL_DIGEST),
        source_sha256=_ANNUAL_DIGEST,
        language="zh",
        units=_annual_report_units(),
        page_count=1,
        pages_read=1,
    )

    first = select_narrative_evidence(structure, title="2025年度报告.pdf")
    second = select_narrative_evidence(structure, title="2025年度报告.pdf")

    def fingerprint(package: NarrativeEvidencePackage):
        return (
            package.status,
            package.candidate_count,
            package.dropped_financial_count,
            [
                (
                    span.span_id,
                    span.locator,
                    span.raw_text,
                    span.structured_value.get("selection_group_id"),
                    tuple(span.structured_value.get("selection_reasons", ())),
                    tuple(span.structured_value.get("topics", ())),
                )
                for span in package.evidence_spans
            ],
        )

    assert fingerprint(first) == fingerprint(second)


def _ir_record_units() -> tuple[NarrativeUnit, ...]:
    return (
        _unit(
            "从克重口径看，目前达到一个稳定的状态，一口价黄金占比",
            digest=_IR_DIGEST,
            paragraph=0,
            block=1,
        ),
        _unit("在15%-20%，其中高端产品占比", digest=_IR_DIGEST, paragraph=1, block=1),
        _unit("在30%左右", digest=_IR_DIGEST, paragraph=2, block=1),
        _unit("上市公司接待人员姓名", digest=_IR_DIGEST, paragraph=3, block=2),
    )


def test_ir_record_selects_product_mix_and_is_not_skipped() -> None:
    structure = DocumentStructure(
        source_id=source_id_for_sha256(_IR_DIGEST),
        source_sha256=_IR_DIGEST,
        language="zh",
        units=_ir_record_units(),
        page_count=1,
        pages_read=1,
    )

    package = select_narrative_evidence(structure, title="投资者关系活动记录.pdf")
    spans = _spans_by_text(package)

    assert "从克重口径看，目前达到一个稳定的状态，一口价黄金占比" in spans
    assert "在15%-20%，其中高端产品占比" in spans
    assert "在30%左右" in spans
    assert "上市公司接待人员姓名" not in spans
    assert package.status in {"selected", "partial"}

    first = spans["从克重口径看，目前达到一个稳定的状态，一口价黄金占比"]
    group_id = first.structured_value["selection_group_id"]
    assert group_id
    for text in ("在15%-20%，其中高端产品占比", "在30%左右"):
        assert spans[text].structured_value["selection_group_id"] == group_id
    for span in package.evidence_spans:
        assert "overseas" not in span.structured_value["topics"]


def _transcript_units() -> tuple[NarrativeUnit, ...]:
    return (
        _unit(
            "Customer demand continues to exceed available capacity.",
            digest=_TRANSCRIPT_DIGEST,
            paragraph=None,
            page=1,
            role="management",
            language="en",
            kind="transcript_line",
            char_range=(100, 160),
        ),
        _unit(
            "We added 31 new data centers across 5 continents this quarter.",
            digest=_TRANSCRIPT_DIGEST,
            paragraph=None,
            page=1,
            role="management",
            language="en",
            kind="transcript_line",
            char_range=(200, 265),
            metadata={"qa_group_id": "qa:1"},
        ),
        _unit(
            "Can you share more about capacity constraints this quarter?",
            digest=_TRANSCRIPT_DIGEST,
            paragraph=None,
            page=1,
            role="investor_question",
            language="en",
            kind="transcript_line",
            char_range=(300, 362),
            metadata={"qa_group_id": "qa:1"},
        ),
    )


def test_transcript_pipeline_keeps_fact_and_qa_roles() -> None:
    structure = DocumentStructure(
        source_id=source_id_for_sha256(_TRANSCRIPT_DIGEST),
        source_sha256=_TRANSCRIPT_DIGEST,
        language="en",
        units=_transcript_units(),
        line_count=3,
    )

    package = select_narrative_evidence(structure, title="2026_Q2_earnings_call.txt")
    spans = _spans_by_text(package)

    demand = spans["Customer demand continues to exceed available capacity."]
    assert "direct_capacity_constraint" in demand.structured_value["selection_reasons"]

    answer = spans["We added 31 new data centers across 5 continents this quarter."]
    question = spans["Can you share more about capacity constraints this quarter?"]
    assert answer.structured_value["source_role"] == "management"
    assert question.structured_value["source_role"] == "investor_question"
    assert question.structured_value.get("selection_group_id") is None
    assert package.status in {"selected", "partial"}
