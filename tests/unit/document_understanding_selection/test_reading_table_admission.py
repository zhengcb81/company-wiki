"""One shared table purpose service; structural kind alone proves no business value."""

from copy import deepcopy
from dataclasses import replace

import pytest

from company_wiki.document_understanding import understand_units
from company_wiki.source_catalog import narrative_evidence as evidence
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SHA = "d" * 64
SOURCE = source_id_for_sha256(SHA)


def fixture(header, rows, *, note=None, external_heading=None, table=0):
    texts = [header, *rows]
    if note is not None:
        texts.append(note)
    units = tuple(
        evidence._make_unit(
            source_id=SOURCE,
            parser_version="0.1.1",
            coordinates=EvidenceCoordinates(
                page_number=1, table_index=table, row_index=i
            ),
            raw_text=text,
            unit_kind="pdf_table_row",
            source_role="company_filing",
            language="mixed",
            metadata={},
        )
        for i, text in enumerate(texts)
    )
    context = [units[0].unit_id]
    if note is not None:
        context.append(units[-1].unit_id)
    package = {
        "package_id": "actual-table",
        "kind": "operating_table",
        "member_unit_ids": [unit.unit_id for unit in units],
        "anchor_unit_ids": [
            unit.unit_id for unit in units[1:] if unit.unit_id not in context
        ],
        "required_context_unit_ids": context,
        "completeness": "complete",
    }
    if external_heading is not None:
        heading = evidence._make_unit(
            source_id=SOURCE,
            parser_version="0.1.1",
            coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
            raw_text=external_heading,
            unit_kind="pdf_text_block",
            source_role="company_filing",
            language="mixed",
            metadata={},
        )
        units = (*units, heading)
        package["required_context_unit_ids"].append(heading.unit_id)
    pipeline = {
        "reading_plan": {
            "unit_profiles": {
                unit.unit_id: {
                    "section_role": "unknown",
                    "family": "annual",
                    "priority": 2,
                }
                for unit in units
            }
        },
        "structure": {"sections": []},
        "packages": {"packages": [package]},
    }
    parsed = DocumentStructure(
        SOURCE,
        SHA,
        "mixed",
        units,
        page_count=1,
        pages_read=1,
        mime_type="application/pdf",
    )
    return parsed, pipeline


def anchors(result):
    return {uid for uid, value in result[1].items() if not value["context_only"]}


@pytest.mark.parametrize(
    "header,rows",
    [
        ("资本公积 | 2026 | 留存收益", ["四、本期期末余额 | 3000000 | 900000"]),
        ("项目 | 当期转入留存收益 | 税后归属于母公司", ["其他综合收益合计 | 30 | 20"]),
        (
            "Retained earnings | Year ended 2026 | USD million",
            ["Closing equity balance | 30 | 20"],
        ),
        ("Retained\nearnings | 2026 | USD million", ["Retention transfers | 30"]),
        ("項目 | 本期轉入留存收益 | 所有者權益", ["其他綜合收益 | 30 | 20"]),
        ("费用明细 | 2026 | 万元", ["销售费用 | 10", "管理费用 | 20"]),
        ("估值关键参数 | 2026", ["无风险利率 | 3%", "预期股息率 | 1%"]),
    ],
)
def test_actual_read_financial_tables_are_not_business_facts_merely_from_kind(
    header, rows
):
    parsed, pipeline = fixture(header, rows)
    original = deepcopy(pipeline)
    result = reading._candidates(parsed, pipeline)
    assert not anchors(result)
    assert not result[2], (
        "an unqualified financial table cannot become a sent business group"
    )
    assert not result[4], "already read no-business is not an unread failure"
    assert pipeline == original


@pytest.mark.parametrize(
    "header,rows",
    [
        (
            "截至2026年6月30日門店網絡 | 中國內地 | 海外",
            ["直營店 | 269 | 105", "合夥人門店 | 3500 | 2700"],
        ),
        ("Product shipments | thousand units | current period", ["15"]),
        ("产能利用率 | 2026 | %", ["生产线A | 86", "生产线B | 72"]),
        ("在手订单数量 | 截至2026年6月末 | 套", ["设备A | 45"]),
        (
            "Remaining performance obligations | Expected to be recognized over the next 12 months | USD million",
            ["Commercial contracts | 2700"],
        ),
        ("客户集中度 | 2026 | 收入占比", ["前五大客户 | 31%"]),
    ],
)
def test_real_operating_tables_keep_all_original_context_even_in_financial_notes(
    header, rows
):
    note = "注：本期口径不包含尚未交付的项目。"
    parsed, pipeline = fixture(header, rows, note=note)
    result = reading._candidates(parsed, pipeline)
    expected = {unit.unit_id for unit in parsed.units[1:-1]}
    assert anchors(result) == expected
    assert {candidate.unit.unit_id for candidate in result[0]} == {
        unit.unit_id for unit in parsed.units
    }
    for uid in expected:
        assert result[1][uid]["value_band"] == "meaningful_fact"
        assert set(result[1][uid]["required"]) >= {
            parsed.units[0].unit_id,
            parsed.units[-1].unit_id,
        }
    assert result[1][parsed.units[0].unit_id]["context_only"]
    assert result[1][parsed.units[-1].unit_id]["context_only"]


def test_neighbouring_business_heading_cannot_certify_a_financial_table():
    parsed, pipeline = fixture(
        "项目 | 期末余额", ["货币资金 | 30"], external_heading="門店網絡與產能利用率"
    )
    assert not anchors(reading._candidates(parsed, pipeline))


def test_accounting_footnote_cannot_use_an_operating_keyword_to_promote_the_table():
    parsed, pipeline = fixture(
        "所有者权益 | 期末余额",
        ["资本公积 | 30"],
        note="注：门店数变化与本表留存收益结转无关。",
    )
    assert not anchors(reading._candidates(parsed, pipeline))


def test_footnote_is_not_table_purpose_even_without_a_known_account_keyword():
    parsed, pipeline = fixture(
        "项目 | 2026 | 金额",
        ["余额 | 30"],
        note="注：门店数量的经营披露与本表不属于同一口径。",
    )
    assert not anchors(reading._candidates(parsed, pipeline))


def test_operating_table_can_keep_an_account_reference_inside_its_bound_note():
    parsed, pipeline = fixture(
        "門店網絡 | 2026 | 家",
        ["直營店 | 50"],
        note="注：上述门店不包括在租赁负债之外另行披露的未签约计划。",
    )
    result = reading._candidates(parsed, pipeline)
    assert anchors(result) == {parsed.units[1].unit_id}
    assert parsed.units[-1].unit_id in result[1][parsed.units[1].unit_id]["required"]


@pytest.mark.parametrize("mode", ["empty", "missing-member", "truncated"])
def test_unread_or_empty_table_is_deferred_instead_of_being_declared_no_value(mode):
    parsed, pipeline = fixture(
        "Number of stores | 2026 | stores", [] if mode == "empty" else ["50"]
    )
    package = pipeline["packages"]["packages"][0]
    if mode == "missing-member":
        package["member_unit_ids"].append("unread-source-row")
    if mode == "truncated":
        package["truncated"] = True
    result = reading._candidates(parsed, pipeline)
    assert not anchors(result)
    assert result[4], "missing table rows are unknown, not known no-business"
    assert not result[2]


def test_du_structure_and_source_share_retained_earnings_disambiguation():
    parsed, _ = fixture("结转留存收益 | 2026 | 元", ["四、本期期末余额 | 30"])
    pipeline = understand_units(
        parsed.units,
        source_id=SOURCE,
        source_sha256=SHA,
        declared_kind="annual_report",
        mime_type="application/pdf",
        language="en",
    )
    assert not [
        p for p in pipeline["packages"]["packages"] if p["kind"] == "operating_table"
    ]


def test_shared_purpose_service_has_an_explicit_bounded_unknown_outcome():
    from company_wiki.document_understanding.structure import table_purpose

    proof = table_purpose.qualify_table(
        ["门店数量 | 2026"], ["直营店 | 50"], max_chars=0
    )
    assert proof.status == "incomplete"
    assert not proof.eligible
    assert proof.reason == "TABLE_PURPOSE_RESOURCE_LIMIT"
    # Both actual service entrypoints must preserve bounded unknown. Which
    # helper structure.tables imports is not a source/extraction contract.
    native = table_purpose.qualify_native_rows(
        ["门店数量 | 2026"], [{"text": "直营店 | 50"}], max_chars=0
    )
    assert native == proof


def test_structural_table_name_alone_cannot_bypass_explicit_source_qualification():
    parsed, _ = fixture("项目 | 2026", ["100"])
    admitted, _ = reading._admitted(
        parsed.units[1], {"section_role": "business"}, "operating_table"
    )
    assert not admitted


def test_project_construction_stage_and_capacity_keep_the_amount_column_and_context():
    parsed, pipeline = fixture(
        "项目名称 | 建设周期 | 预计投产阶段 | 设计产能 | 拟投入资金（万元）",
        ["精密设备生产基地 | 24个月 | 2027年计划投产 | 每年3000套 | 10000"],
        note="注：投产安排取决于客户验收，不代表已形成收入。",
    )
    result = reading._candidates(parsed, pipeline)
    assert anchors(result) == {parsed.units[1].unit_id}
    assert set(result[1][parsed.units[1].unit_id]["required"]) == {
        parsed.units[0].unit_id,
        parsed.units[-1].unit_id,
    }


@pytest.mark.parametrize(
    "header,rows",
    [
        (
            "项目名称 | 募集资金使用 | 项目总投资（万元）",
            ["补充流动资金 | 10000 | 10000"],
        ),
        ("项目名称 | 在建工程账面余额 | 2026年末（万元）", ["项目A | 10000"]),
    ],
)
def test_fund_allocation_and_construction_book_balances_do_not_prove_operating_progress(
    header, rows
):
    parsed, pipeline = fixture(header, rows)
    assert not anchors(reading._candidates(parsed, pipeline))


def test_legacy_selector_does_not_call_new_table_qualification(monkeypatch):
    parsed, _ = fixture("Product shipments | 2026 | thousand units", ["15"])
    original = evidence.select_narrative_evidence(
        parsed,
        title="Annual report",
        existing_kind="annual_report",
        max_selected=10,
        selector_version="0.8.0",
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("legacy selector called opt-in table qualification")

    monkeypatch.setattr(reading, "_qualified_table", unexpected, raising=False)
    replay = evidence.select_narrative_evidence(
        parsed,
        title="Annual report",
        existing_kind="annual_report",
        max_selected=10,
        selector_version="0.8.0",
    )
    assert replay == original
    assert parsed == replace(parsed)



@pytest.mark.parametrize("unit", ["套", "USD million"])
def test_background_table_route_keeps_declared_original_header_unit_period_and_note(unit):
    parsed, pipeline = fixture(
        "在手订单数量 | 截至2026年6月末 | " + unit,
        ["设备甲 | 45"], note="注：统计不包含尚未交付的试用订单。",
    )
    pipeline["packages"]["packages"][0]["kind"] = "background"
    for profile in pipeline["reading_plan"]["unit_profiles"].values():
        profile["section_role"] = "business"
    before = deepcopy(pipeline)
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    row, header, note = parsed.units[1], parsed.units[0], parsed.units[2]
    assert row.unit_id in metadata and not metadata[row.unit_id]["context_only"]
    assert set(metadata[row.unit_id]["required"]) == {header.unit_id, note.unit_id}
    assert metadata[header.unit_id]["context_only"] and metadata[note.unit_id]["context_only"]
    assert complete and not withheld
    assert pipeline == before
    assert {candidate.unit.unit_id for candidate in candidates} == {unit.unit_id for unit in parsed.units}



def test_two_background_tables_keep_their_own_original_context_when_package_order_changes():
    parsed, pipeline = fixture("在手订单数量 | 2026 | 套", ["设备甲 | 45"], note="注：不含试用订单。")
    other, other_pipeline = fixture("门店数量 | 2025 | 家", ["直营网点 | 12"], note="注：不含临时网点。", table=1)
    parsed = replace(parsed, units=(*parsed.units, *other.units))
    pipeline["packages"]["packages"].extend(other_pipeline["packages"]["packages"])
    pipeline["reading_plan"]["unit_profiles"].update(other_pipeline["reading_plan"]["unit_profiles"])
    for package in pipeline["packages"]["packages"]:
        package["kind"] = "background"
    for profile in pipeline["reading_plan"]["unit_profiles"].values():
        profile["section_role"] = "business"
    for reverse in (False, True):
        if reverse:
            pipeline["packages"]["packages"].reverse()
        _, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
        assert complete and not withheld
        for start in (0, 3):
            assert set(metadata[parsed.units[start+1].unit_id]["required"]) == {
                parsed.units[start].unit_id, parsed.units[start+2].unit_id,
            }


@pytest.mark.parametrize("broken", ["missing-header", "reused-next-page-table-id"])
def test_background_table_with_unproven_native_context_is_not_a_complete_numeric_fact(broken):
    parsed, pipeline = fixture("在手订单数量 | 2026 | 套", ["设备甲 | 45"], note="注：不含试用订单。")
    pipeline["packages"]["packages"][0]["kind"] = "background"
    for profile in pipeline["reading_plan"]["unit_profiles"].values():
        profile["section_role"] = "business"
    row = parsed.units[1].unit_id
    if broken == "missing-header":
        parsed = replace(parsed, units=parsed.units[1:])
    else:
        changed = replace(parsed.units[1], coordinates=replace(parsed.units[1].coordinates, page_number=2))
        parsed = replace(parsed, units=(parsed.units[0], changed, parsed.units[2]), page_count=2, pages_read=2)
    result = reading._candidates(parsed, pipeline)
    assert row not in anchors(result)
    assert result[4], "unread original header must remain explicitly deferred"


def test_background_original_context_reaches_public_citation_views_with_support_roles(monkeypatch):
    parsed, supplied = fixture("在手订单数量 | 2026 | 套", ["设备甲 | 45"], note="注：不含试用订单。")
    actual = reading._understand(parsed, title="年度报告", kind="annual_report", mime_type="application/pdf")
    supplied["packages"]["packages"][0]["kind"] = "background"
    for profile in supplied["reading_plan"]["unit_profiles"].values():
        profile["section_role"] = "business"
    actual["packages"] = supplied["packages"]
    actual["reading_plan"]["unit_profiles"] = supplied["reading_plan"]["unit_profiles"]
    monkeypatch.setattr(reading, "_understand", lambda *a, **k: actual)
    selected = reading.select_reading_evidence(parsed, title="年度报告", existing_kind="annual_report", max_selected=3)
    by_text = {span.raw_text: span.span_id for span in selected.evidence_spans}
    row = by_text[parsed.units[1].raw_text]
    expected = {by_text[parsed.units[0].raw_text], by_text[parsed.units[2].raw_text]}
    views = [view for group in selected.reading_context["groups"] for view in group["citation_views"]]
    row_views = [view for view in views if view["support_evidence_ids"] == [row]]
    assert row_views and all(set(view["context_evidence_ids"]) == expected for view in row_views)
    assert all(not expected.intersection(view["support_evidence_ids"]) for view in views)
