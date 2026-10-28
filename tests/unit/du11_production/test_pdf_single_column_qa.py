"""A wide Q/A cell needs discovery, not a forged speaker or business fact."""
from copy import deepcopy

import pytest

from unit.du11_production.test_pdf_candidates import observe, snapshot


def qa_page(*, bottom=False):
    first, second = (700, 720) if bottom else (100, 120)
    return snapshot(
        (first, [(50, 550, '问题：是否已经生产新型材料？')]),
        (second, [(50, 550, '回答：目前尚未生产，计划仍在验证。')]),
    )


def test_wide_single_cell_qa_is_a_provisional_discovery_without_qualification():
    value = qa_page()
    before = deepcopy(value)
    result = observe(value, qa=True)
    assert result['candidate']
    assert not result.get('business_eligible', False)
    assert not result['partial']
    assert value == before


def test_wide_qa_without_qa_reading_intent_cannot_request_discovery():
    assert not observe(qa_page(), qa=False)['candidate']


def test_qa_intent_does_not_relax_single_column_operating_table_discovery():
    value = snapshot((100, [(50, 150, '产能')]),
                     (120, [(50, 150, '100台/年')]))
    assert not observe(value, qa=True)['candidate']
    assert not observe(value, qa=False)['candidate']


def test_existing_centered_date_does_not_break_two_column_qa_continuation():
    value = snapshot(
        (680, [(50, '问题：是否已经投产？'), (300, '回答：仍在验证。')]),
        (700, [(50, '问题：客户进展如何？'), (300, '回答：尚未完成验收。')]),
        (720, [(250, 350, '2025年6月')]),
        (740, [(50, '客户验证尚未完成'), (300, '生产进度仍不确定')]),
    )
    result = observe(value, qa=True)
    assert result['candidate']
    assert result['continuation'] is not None
    assert result['continuation']['kind'] == 'qa'
    assert len(result['continuation']['columns']) == 2


@pytest.mark.parametrize('rows', (
    ((100, [(50, 550, '本公司计划继续扩大业务覆盖。')]),
     (120, [(50, 550, '新增项目尚未进入实际生产阶段。')])),
    ((100, [(50, 250, '问题：项目是否投产？')]),
     (120, [(350, 550, '回答：仍在建设。')])),
    ((100, [(50, 550, '问题：项目是否投产？')]),
     (240, [(50, 550, '回答：仍在建设。')])),
))
def test_intent_or_words_do_not_replace_same_column_and_nearby_rows(rows):
    assert not observe(snapshot(*rows), qa=True)['candidate']


def test_single_column_qa_continuation_retains_measured_shape_and_explicit_type():
    prior = observe(qa_page(bottom=True), qa=True)
    assert prior['candidate'] and prior['continuation']
    continuation = snapshot(
        (80, [(50, 550, '项目仍须取得客户验证，')]),
        (100, [(50, 550, '报告期内未开展批量生产。')]),
    )
    assert observe(continuation, qa=True, previous=prior['continuation'])['candidate']
    assert not observe(continuation, qa=True)['candidate']
    assert not observe(continuation, qa=False, previous=prior['continuation'])['candidate']
    forged = {**prior['continuation'], 'kind': 'operating', 'fields': ['产能']}
    assert not observe(continuation, previous=forged)['candidate']


@pytest.mark.parametrize('change', ('columns', 'width', 'starts_with_other_column'))
def test_one_column_continuation_does_not_override_current_measured_layout(change):
    prior = observe(qa_page(bottom=True), qa=True)['continuation']
    assert prior is not None
    rows = ((80, [(50, 550, '项目仍须取得客户验证，')]),
            (100, [(50, 550, '报告期内未开展批量生产。')]))
    if change == 'columns':
        rows = ((80, [(300, 550, '项目仍须取得客户验证，')]),
                (100, [(300, 550, '报告期内未开展批量生产。')]))
    elif change == 'starts_with_other_column':
        rows = ((60, [(300, 550, '其他业务介绍')]), *rows)
    current = snapshot(*rows, width=800 if change == 'width' else 600)
    assert not observe(current, qa=True, previous=prior)['candidate']
