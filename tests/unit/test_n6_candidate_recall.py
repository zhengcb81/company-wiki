"""N6-CANDIDATE unit recall: generic operating facts plus preserved negatives."""

from __future__ import annotations

from pathlib import Path

from company_wiki.source_catalog import narrative_candidates, narrative_evidence
from company_wiki.source_catalog.narrative_candidates import assess_unit
from company_wiki.source_catalog.narrative_evidence import _candidate_rules, _make_unit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.source_catalog.narrative_document import NarrativeUnit


_SOURCE_ID = source_id_for_sha256("6c" + "a" * 62)
_RULES = _candidate_rules()


def _unit(
    text: str,
    *,
    page: int = 1,
    paragraph: int = 0,
    kind: str = "pdf_text_block",
    role: str = "company_filing",
    metadata: dict | None = None,
) -> NarrativeUnit:
    language = "zh" if any("一" <= ch <= "鿿" for ch in text) else "en"
    return _make_unit(
        source_id=_SOURCE_ID,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=paragraph),
        raw_text=text,
        unit_kind=kind,
        source_role=role,
        language=language,
        metadata=metadata or {},
    )


def _table_unit(text: str, *, cells: tuple[str, ...]) -> NarrativeUnit:
    return _unit(
        text,
        kind="pdf_table_row",
        metadata={"row_cells": cells, "table_headers": ["项目", "状态", "数量"]},
    )


def test_modules_come_from_this_worktree_src() -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    for module in (narrative_candidates, narrative_evidence):
        location = module.__file__
        assert location is not None
        assert Path(location).resolve().is_relative_to(root)


_POSITIVE_FACTS = (
    (
        "applied_equipment",
        "公司高端薄膜沉积设备已应用于客户12英寸产线。",
        ("specific_business_event",),
    ),
    (
        "field_operation",
        "该型号工业机器人已在客户现场稳定运行超过两年。",
        ("specific_business_event",),
    ),
    (
        "workshop_in_use",
        "新建特种气体车间已投入使用，产能利用率提升至85%。",
        ("specific_business_event",),
    ),
    (
        "customer_validation",
        "公司新型体外诊断试剂已通过第三方客户验证。",
        ("specific_business_event",),
    ),
    (
        "second_curve_production",
        "储能业务作为公司第二增长曲线，本报告期已实现规模化量产。",
        ("specific_business_event",),
    ),
    (
        "ma_completed",
        "公司已完成对某精密部件企业的收购，切入新能源汽车结构件市场。",
        ("specific_business_event",),
    ),
    (
        "ma_planned",
        "公司拟收购上游材料企业控股权，延伸高性能复合材料业务。",
        ("project_plan_or_status",),
    ),
    (
        "industry_scale_forecast",
        "2026年我国工业机器人市场规模有望增长至1,200亿元，下游需求持续扩张。",
        ("current_industry_context",),
    ),
    (
        "import_substitution",
        "2016—2020年进口刀具占总消费的比重从37.17%下降至31.12%，自给能力逐步增强。",
        ("current_industry_context",),
    ),
    (
        "market_space",
        "随着航空及其他军品市场、高端民品市场的不断扩大，中小型飞机锻件业务亦有广阔的市场空间。",
        ("current_industry_context",),
    ),
    (
        "production_sales_growth",
        "报告期内公司锂电隔膜产销量同比分别增长42%和38%，产销率保持高位。",
        ("current_business_progress",),
    ),
    (
        "fundraising_project_use",
        "本次募集资金在扣除发行相关费用后拟用于高端半导体设备扩产升级项目和研发中心建设项目。",
        ("project_plan_or_status",),
    ),
    (
        "project_ramp_output",
        "募投项目达产后，公司预计新增精密数控刀体产品50万件。",
        ("specific_business_event",),
    ),
    (
        "project_started_capacity",
        "2025年公司启动了电子级光刻胶产业园二期建设项目，该项目包含相关材料产能约751吨/年。",
        ("specific_business_event", "project_plan_or_status"),
    ),
    (
        "certification_timeline_without_topics",
        "新能源汽车轻量化部件项目需要通过主机厂供应商认证和产品认证，预计需要6-12个月。",
        ("project_certification_timeline",),
    ),
    (
        "domestic_revenue_share",
        "2025年度公司境内收入约8.19亿元，占比约22%，较比2024年度有所提升。",
        ("quantified_operating_status",),
    ),
    (
        "product_mix_share",
        "从克重口径看，目前达到一个稳定的状态，一口价黄金占比在15%-20%，克重黄金占比在80%-85%。",
        ("quantified_operating_status",),
    ),
    (
        "en_demand_over_capacity",
        "Customer demand continues to exceed available capacity.",
        ("direct_capacity_constraint",),
    ),
    (
        "en_demand_context_revenue",
        "Cloud Services Revenue-- Grew 43% year over year, with customer demand "
        "continuing to exceed available capacity.",
        ("direct_capacity_constraint",),
    ),
)


def test_operating_facts_are_selected_with_reusable_reasons() -> None:
    for name, text, expected_reasons in _POSITIVE_FACTS:
        assessment = assess_unit(_unit(text, paragraph=sum(map(ord, name)) % 97), _RULES)
        candidate = assessment.candidate
        assert candidate is not None, f"{name} should be a candidate"
        assert assessment.dropped_financial is False, name
        for reason in expected_reasons:
            assert reason in candidate.reasons, (
                f"{name}: missing {reason} in {candidate.reasons}"
            )
        assert "business_narrative_signal" in candidate.reasons, name


def test_operating_fact_topics_never_relabel_domestic_revenue_as_overseas() -> None:
    assessment = assess_unit(
        _unit("2025年度公司境内收入约8.19亿元，占比约22%，较比2024年度有所提升。"),
        _RULES,
    )

    assert assessment.candidate is not None
    assert "overseas" not in assessment.candidate.topics


_NEGATIVE_CASES = (
    (
        "profit_loss_row",
        "营业收入 146,274.71 117,233.75",
        ("146,274.71", "117,233.75"),
        True,
    ),
    ("totals_row", "合计 1,028.38 2,056.76", ("1,028.38", "2,056.76"), True),
    (
        "product_financial_row",
        "高端数控刀片 1,028.38 2,056.76",
        ("高端数控刀片", "1,028.38", "2,056.76"),
        True,
    ),
    (
        "financing_total",
        "公司本次可转债计划募集资金总额不超过人民币40,000.00万元（含本数）。",
        None,
        False,
    ),
    ("table_of_contents", "第四节 风险因素……13", None, False),
    (
        "promise_boilerplate",
        "本公司及全体董事、监事、高级管理人员承诺本募集说明书内容真实、准确、完整，"
        "不存在虚假记载、误导性陈述或重大遗漏。",
        None,
        False,
    ),
    (
        "vague_continuation",
        "公司将持续推进各项管理工作，不断提升运营效率。",
        None,
        False,
    ),
    ("isolated_affirmative", "是的。", None, False),
    ("procedural_label", "上市公司接待人员姓名", None, False),
    (
        "fundraising_boilerplate",
        "本次募集资金将严格按照规定存储在董事会指定的专门账户集中管理，专款专用，"
        "规范使用募集资金。",
        None,
        False,
    ),
    (
        "generic_progress",
        "报告期内公司整体经营情况良好，各项指标稳步增长。",
        None,
        False,
    ),
)


def test_negative_examples_stay_out_of_candidates() -> None:
    for name, text, cells, expect_financial_drop in _NEGATIVE_CASES:
        if cells is None:
            unit = _unit(text, paragraph=sum(map(ord, name)) % 97)
        else:
            unit = _table_unit(text, cells=cells)
        assessment = assess_unit(unit, _RULES)
        assert assessment.candidate is None, f"{name} must not become a candidate"
        assert assessment.dropped_financial is expect_financial_drop, name


def test_quantified_operating_table_row_is_not_swallowed_by_financial_filter() -> None:
    unit = _table_unit(
        "新建特种气体车间已投入使用 1,028.38 2,056.76",
        cells=("新建特种气体车间", "已投入使用", "1,028.38", "2,056.76"),
    )

    assessment = assess_unit(unit, _RULES)

    assert assessment.dropped_financial is False
    assert assessment.candidate is not None
    assert "specific_business_event" in assessment.candidate.reasons


def test_excluded_roles_stay_excluded_for_operating_fact_text() -> None:
    role = "analyst"
    unit = _unit(
        "Customer demand continues to exceed available capacity.",
        role=role,
        paragraph=5,
    )

    assert assess_unit(unit, _RULES).candidate is None
