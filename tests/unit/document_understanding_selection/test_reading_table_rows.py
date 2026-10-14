"""Selective table rows: financial neighbours are neither facts nor context."""

from copy import deepcopy

import pytest

from company_wiki.document_understanding import understand_units
from company_wiki.document_understanding.structure.table_purpose import qualify_table
from company_wiki.source_catalog import narrative_evidence as evidence
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SHA = "8" * 64
SOURCE = source_id_for_sha256(SHA)


def fixture(header, rows, note="注：规划投产时间不是已经确认的收入。"):
    texts = [header, *rows, note]
    units = tuple(
        evidence._make_unit(
            source_id=SOURCE, parser_version="0.1.1",
            coordinates=EvidenceCoordinates(page_number=2, table_index=0, row_index=index),
            raw_text=text, unit_kind="pdf_table_row", source_role="company_filing",
            language="mixed", metadata={},
        )
        for index, text in enumerate(texts)
    )
    context = [units[0].unit_id, units[-1].unit_id]
    package = {
        "package_id": "mixed-table", "kind": "operating_table",
        "member_unit_ids": [unit.unit_id for unit in units],
        "anchor_unit_ids": [unit.unit_id for unit in units[1:-1]],
        "required_context_unit_ids": context, "completeness": "complete",
    }
    pipeline = {
        "reading_plan": {"unit_profiles": {unit.unit_id: {
            "family": "annual", "section_role": "financial_notes", "priority": 2,
        } for unit in units}},
        "structure": {"sections": []}, "packages": {"packages": [package]},
    }
    parsed = DocumentStructure(SOURCE, SHA, "mixed", units, page_count=2,
                               pages_read=2, mime_type="application/pdf")
    return parsed, pipeline


@pytest.mark.parametrize("header,row", [
    ("Project | Construction timeline | Expected commissioning", "Production line A | 24 months | H2 2027"),
    ("项目名称 | 建设周期 | 预计投产", "生产基地A | 24个月 | 2027年下半年"),
    ("項目名稱 | 建設週期 | 預計投產", "生產基地A | 24個月 | 2027年下半年"),
])
def test_project_time_fields_have_eligible_original_body_rows(header, row):
    result = qualify_table([header], [row])
    assert result.eligible
    assert result.eligible_row_indices == (0,)


MIXED = [
    ("Number of stores | Lease liabilities | 2026", ["Lease liabilities | 125 million", "Directly operated stores | 62 | 125 million"], (1,)),
    ("門店數量 | 使用權資產 | 2026", ["使用權資產 | 125百萬元", "直營門店 | 62 | 125百萬元"], (1,)),
    ("项目 | 本期数 | 2026", ["Retained earnings | 250", "Remaining performance obligations | 800 million"], (1,)),
    ("项目名称 | 建设周期 | 预计投产 | 账面余额", ["生产基地A | 24个月 | 2027年下半年 | 10000", "在建工程账面余额 | 10000"], (0,)),
]


@pytest.mark.parametrize("header,rows,indices", MIXED)
def test_shared_service_selects_rows_instead_of_promoting_whole_table(header, rows, indices):
    result = qualify_table([header], rows)
    assert result.eligible
    assert result.eligible_row_indices == indices


@pytest.mark.parametrize("header,rows,indices", MIXED)
def test_source_filters_financial_rows_before_graph_cost_and_sent_context(header, rows, indices):
    parsed, pipeline = fixture(header, rows)
    original = deepcopy(pipeline)
    result = reading._candidates(parsed, pipeline)
    expected = {parsed.units[1 + index].unit_id for index in indices}
    rejected = {unit.unit_id for index, unit in enumerate(parsed.units[1:-1]) if index not in indices}
    context = {parsed.units[0].unit_id, parsed.units[-1].unit_id}
    assert {uid for uid, item in result[1].items() if not item["context_only"]} == expected
    assert {candidate.unit.unit_id for candidate in result[0]} == expected | context
    assert len(result[2]) == 1
    assert set(result[2][0]["member_unit_ids"]) == expected | context
    assert set(result[2][0]["required_context_unit_ids"]) == context
    for uid in expected:
        assert not rejected.intersection(result[1][uid]["required"])
        assert set(result[1][uid]["required"]) >= context
    assert pipeline == original


@pytest.mark.parametrize("header,rows,indices", MIXED)
def test_du_table_draft_only_contains_operating_rows_and_native_qualifiers(header, rows, indices):
    parsed, _ = fixture(header, rows)
    pipeline = understand_units(parsed.units, source_id=SOURCE, source_sha256=SHA,
                                declared_kind="annual_report", mime_type="application/pdf", language="mixed")
    tables = [package for package in pipeline["packages"]["packages"] if package["kind"] == "operating_table"]
    assert len(tables) == 1
    expected = {parsed.units[1 + index].unit_id for index in indices}
    context = {parsed.units[0].unit_id, parsed.units[-1].unit_id}
    assert set(tables[0]["anchor_unit_ids"]) == expected
    assert set(tables[0]["member_unit_ids"]) == expected | context
    assert set(tables[0]["required_context_unit_ids"]) == context
    rejected = {unit.unit_id for index, unit in enumerate(parsed.units[1:-1]) if index not in indices}
    candidates = reading._candidates(parsed, pipeline)
    assert not rejected.intersection(candidate.unit.unit_id for candidate in candidates[0])


@pytest.mark.parametrize("header,rows", [
    ("Retained earnings | 2026", ["Retention transfers | 30"]),
    ("Clients | Accounts receivable | USD million", ["Customer A | 20"]),
    ("项目名称 | 募集资金使用 | 项目总投资", ["客户服务中心项目 | 10000 | 10000"]),
    ("项目名称 | 在建工程账面余额", ["订单处理中心 | 10000"]),
    ("所有者权益 | 2026", ["未分配利润 | 30", "留存收益 | 20"]),
])
def test_pure_accounting_and_named_project_amounts_stay_rejected(header, rows):
    result = qualify_table([header], rows)
    assert not result.eligible
    assert result.status == "not_business"
    assert result.eligible_row_indices == ()


@pytest.mark.parametrize("header,rows", [
    ("Number of stores | 2026", []),
    ("Number of stores | 2026", ["", "注：行值待补"]),
])
def test_no_body_is_explicitly_incomplete_without_selected_row_indices(header, rows):
    result = qualify_table([header], rows)
    assert result.status == "incomplete"
    assert result.eligible_row_indices == ()


@pytest.mark.parametrize("limit", [0, 10, 25])
def test_resource_stop_never_publishes_a_partly_evaluated_eligibility_list(limit):
    result = qualify_table(["Number of stores | 2026"], ["Directly operated | 50", "Partner operated | 600"], max_chars=limit)
    assert result.status == "incomplete"
    assert result.eligible_row_indices == ()


def test_row_index_result_is_an_immutable_source_order_subset():
    result = qualify_table(["项目 | 2026"], ["Cash and cash equivalents | 30", "Capacity utilization | 85%", "Order backlog | 80"])
    assert result.eligible_row_indices == (1, 2)
    assert isinstance(result.eligible_row_indices, tuple)
