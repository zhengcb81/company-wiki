"""Source hierarchy is retained; generic navigation is not mandatory model prose."""
from __future__ import annotations

import pytest

from unit.document_understanding_selection.test_reading_guidance_condition_scope import _model, _spans_for
from unit.document_understanding_selection.test_reading_multilevel_native_ancestry import _ancestors
from unit.document_understanding_selection.test_reading_native_list_ancestry import _run_public, _source


def _case(*, specific_title=False, body_count=5):
    title = "五、欧洲地区经营情况" if specific_title else "五、报告期内主要经营情况"
    rows = [(1, "第三节 管理层讨论与分析", 0, (90, 100, 550, 112)),
            (1, title, 1, (90, 200, 550, 212)),
            (1, "(1) 仪器业务实现收入12亿元。", 2, (90, 640, 550, 672)),
            (1, "报告期内：", 2, (90, 640, 550, 672)),
            (1, "- 维护服务保持增长。", 3, (110, 690, 550, 702)),
            (1, "i. 服务客户数量增长15%。", 4, (125, 720, 550, 732)),
            (1, "1 / 2", 5, (280, 780, 330, 792)),
            (2, "- 制造服务保持增长。", 0, (110, 70, 550, 82))]
    texts = ["i. 服务收入达到8亿元，同比增长18%。", "客户数量同比增长20%。",
             "新增订单金额达到2亿元。", "全年交付设备达到300台。", "已验收设备达到280台。"][:body_count]
    rows += [(2, text, 1, (125, 100, 550, 220)) for text in texts]
    rows += [(2, "(2) 消费业务实现收入9亿元。", 2, (90, 300, 550, 332)),
             (2, "报告期内：", 2, (90, 300, 550, 332)),
             (2, "- 订阅用户数量增长12%。", 3, (110, 360, 550, 372)),
             (2, "2 / 2", 4, (280, 780, 330, 792))]
    return _source(rows), texts


def test_nested_original_fact_fits_unchanged_envelope_with_its_semantic_ancestry():
    parsed, texts = _case()
    pipeline, selected, _work = _run_public(parsed)
    target = next(u for u in parsed.units if u.raw_text == texts[0])
    source_ancestors = _ancestors(pipeline, target)
    assert {parsed.units[0].unit_id, parsed.units[1].unit_id} <= source_ancestors
    support = {s.span_id for s in _spans_for(selected, target)}
    assert support, "mandatory navigation headings must not displace the actual five-fragment fact"
    view, model_text = _model(selected)
    tasks = [t for t in view.plan.tasks if support.intersection(t.support_ids)]
    assert tasks
    own = [parsed.units[2], parsed.units[3], parsed.units[7]]
    for task in tasks:
        assert all({s.span_id for s in _spans_for(selected, u)}.intersection(task.member_ids) for u in own)
        assert all(any(text in item for item in model_text[task.key]) for text in texts)
        assert not any("消费业务" in item for item in model_text[task.key])
    # The old 8 original units /4 blocks /2048 chars check remains unchanged.
    assert len(texts) + len(own) == 8


def test_specific_region_in_outer_heading_is_required_semantic_context():
    parsed, texts = _case(specific_title=True, body_count=1)
    _pipeline, selected, _work = _run_public(parsed)
    target = next(u for u in parsed.units if u.raw_text == texts[0])
    support = {s.span_id for s in _spans_for(selected, target)}
    view, model_text = _model(selected)
    tasks = [t for t in view.plan.tasks if support.intersection(t.support_ids)]
    assert tasks and all(any("欧洲地区经营情况" in item for item in model_text[t.key]) for t in tasks)


def test_weak_native_caption_does_not_replace_the_outer_navigation_context():
    parsed, texts = _case(body_count=1)
    from unit.document_understanding_selection.test_reading_native_list_ancestry import _source
    rows = [(u.coordinates.page_number,
             "(1) 本节内容：" if u == parsed.units[2] else u.raw_text,
             u.metadata["pdf_block"], tuple(u.metadata["reading_layout"]["layout"]["bbox"]))
            for u in parsed.units]
    parsed = _source(rows)
    _pipeline, selected, _work = _run_public(parsed)
    target = next(u for u in parsed.units if u.raw_text == texts[0])
    support = {s.span_id for s in _spans_for(selected, target)}
    view, model_text = _model(selected)
    tasks = [t for t in view.plan.tasks if support.intersection(t.support_ids)]
    assert tasks and all(any("主要经营情况" in item for item in model_text[t.key]) for t in tasks)


def test_independently_required_owner_context_cannot_be_removed_as_navigation():
    from company_wiki.resource_budget import new_document_work_budget
    from company_wiki.source_catalog import narrative_reading as reading
    parsed, texts = _case(body_count=1)
    budget = new_document_work_budget()
    contexts = {}
    pipeline = reading._understand(parsed, title="Neutral annual report", kind="annual_report",
        mime_type="application/pdf", work_budget=budget, _native_contexts=contexts)
    target = next(u for u in parsed.units if u.raw_text == texts[0])
    explicit = parsed.units[1].unit_id
    owners = [p for p in pipeline["packages"]["packages"] if target.unit_id in p["member_unit_ids"]]
    assert owners
    for owner in owners:
        owner["required_context_unit_ids"] = list(dict.fromkeys([*owner["required_context_unit_ids"], explicit]))
    packages, *_rest = reading._prose_reading_packages(parsed, pipeline,
        work_budget=budget, _native_contexts=contexts)
    results = [p for p in packages if target.unit_id in p["member_unit_ids"]]
    assert results and all(explicit in p["required_context_unit_ids"] for p in results)


@pytest.mark.parametrize("text", ["五、欧洲地区经营情况", "五、主要经营情况（不含已出售业务）",
    "Business review for Europe", "Operating metrics (USD billion)", "(1) 仪器业务实现收入12亿元。"])
def test_specific_subject_period_unit_or_qualifier_is_never_generic_navigation(text):
    from company_wiki.document_understanding.profiles.registry import is_generic_navigation_heading
    assert not is_generic_navigation_heading(text)


@pytest.mark.parametrize("text", ["第三节 管理层讨论与分析", "五、报告期内主要经营情况",
    "管理層討論及分析", "管理層討論與分析", "Business review", "PART II Management discussion and analysis",
    "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations"])
def test_exact_generic_policy_titles_cover_explicit_market_outline_variants(text):
    from company_wiki.document_understanding.profiles.registry import is_generic_navigation_heading
    assert is_generic_navigation_heading(text)


@pytest.mark.parametrize("text,expected", [
    ("Management’s Discussion and Analysis", True),
    ("Item 7. Management’s Discussion and Analysis", True),
    ("Management’s Discussion and Analysis for Europe", False),
])
def test_typographic_apostrophe_does_not_change_exact_navigation_scope(text, expected):
    from company_wiki.document_understanding.profiles.registry import is_generic_navigation_heading
    assert is_generic_navigation_heading(text) is expected
