"""Measured PDF candidate discovery; discovery is not business qualification."""
from copy import deepcopy
import json

import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_pdf_candidates import observe_pdf_candidate


def snapshot(*rows, width=600, height=800):
    blocks = []
    for y, values in rows:
        spans = []
        for value in values:
            if len(value) == 2:
                x, text = value
                end = x + min(80, max(12, len(text) * 7))
            else:
                x, end, text = value
            spans.append({'text': text, 'bbox': (x, y, end, y + 12)})
        blocks.append({'type': 0, 'lines': [{'spans': spans}]})
    return {'width': width, 'height': height, 'blocks': blocks}


def observe(value, **kwargs):
    return observe_pdf_candidate(value, work_budget=kwargs.pop('work_budget', WorkBudget(3_000_000)), **kwargs)


def test_header_without_digits_supports_aligned_numeric_body():
    value = snapshot((100, [(50, '产品'), (200, '产能'), (350, '单位')]),
                     (120, [(50, 'A型设备'), (210, '100'), (350, '台/年')]))
    before = deepcopy(value)
    result = observe(value)
    assert result['candidate'] and value == before
    assert not result.get('business_eligible', False)


def test_project_overview_has_measured_fields_and_body_not_money_only():
    value = snapshot((100, [(20, '项目名称'), (180, '项目品种'), (320, '项目总投资'), (460, '实施主体')]),
                     (120, [(20, '年产400吨某产品'), (180, '某产品'), (320, '26527.49'), (460, '本公司')]))
    assert observe(value)['candidate']


@pytest.mark.parametrize('values', [
    snapshot(),
    snapshot((100, [(50, 550, '公司稳步推进产能扩张，预计2027年完成项目。')]),
             (120, [(50, 550, '项目尚在建设中，未来贡献收入仍存在不确定性。')])),
    snapshot((100, [(50, '科目'), (200, '2025年'), (350, '2024年')]),
             (120, [(50, '资产总计'), (200, '100'), (350, '90')])),
    snapshot((100, [(50, '项目名称'), (200, '项目总投资'), (350, '募集资金')]),
             (120, [(50, '项目A'), (200, '100'), (350, '90')])),
    snapshot((70, [(50, 550, '公司年产能已达到100万吨。')]),
             (100, [(50, '科目'), (200, '2025年'), (350, '2024年')]),
             (120, [(50, '营业收入'), (200, '100'), (350, '90')])),
    snapshot((100, [(50, '产品'), (200, '产能'), (350, '单位')]),
             (200, [(50, 'A型设备'), (200, '100'), (350, '台/年')])),
])
def test_no_page_wide_word_borrowing_or_unmeasured_table(values):
    assert not observe(values)['candidate']


def test_single_operating_prose_line_cannot_certify_adjacent_financial_grid():
    value = snapshot((100, [(50, '产能已达到100万吨')]),
                     (120, [(50, '营业收入'), (250, '100'), (400, '90')]),
                     (140, [(50, '净利润'), (250, '10'), (400, '9')]))
    assert not observe(value)['candidate']


def test_misaligned_header_and_body_are_not_same_table():
    value = snapshot((100, [(20, '产品'), (100, '产能')]),
                     (120, [(330, 'A型设备'), (500, '100')]))
    assert not observe(value)['candidate']


def test_qa_grid_uses_existing_source_syntax_without_digits():
    value = snapshot((100, [(50, '问题：产品进展如何？'), (300, '回答：仍在开发')]),
                     (120, [(50, '问题：是否进入海外？'), (300, '回答：正在验证')]))
    assert observe(value, qa=True)['candidate']
    assert not observe(value, qa=False)['candidate']


def tail_table():
    return snapshot((700, [(50, '产品'), (200, '产能'), (350, '单位')]),
                    (720, [(50, 'A型设备'), (200, '100'), (350, '台/年')]),
                    (740, [(50, 'B型设备'), (200, '200'), (350, '台/年')]))


def test_bottom_table_signature_recovers_unlabeled_next_page_aligned_rows():
    first = observe(tail_table())
    assert first['candidate'] and first['continuation']
    # Content values belong to current DICT, not to the stored signature.
    assert 'A型设备' not in json.dumps(first['continuation'], ensure_ascii=False)
    second = snapshot((80, [(50, 'C型设备'), (200, '300'), (350, '台/年')]),
                      (100, [(50, 'D型设备'), (200, '400'), (350, '台/年')]))
    assert observe(second, previous=first['continuation'])['candidate']
    assert not observe(second)['candidate']


@pytest.mark.parametrize('second', [
    snapshot((80, [(150, 'C型设备'), (300, '300'), (470, '台/年')]),
             (100, [(150, 'D型设备'), (300, '400'), (470, '台/年')])),
    snapshot((60, [(50, 550, '本页首先讨论其他业务，表格已经结束。')]),
             (80, [(50, 'C型设备'), (200, '300'), (350, '台/年')]),
             (100, [(50, 'D型设备'), (200, '400'), (350, '台/年')])),
    snapshot((80, [(50, '资产总计'), (200, '300'), (350, '400')]),
             (100, [(50, '负债合计'), (200, '200'), (350, '100')])),
])
def test_cross_page_wrong_columns_or_prior_prose_or_accounting_do_not_inherit(second):
    previous = observe(tail_table())['continuation']
    assert not observe(second, previous=previous)['candidate']


def test_trailing_prose_cancels_continuation_even_after_valid_table():
    first = tail_table()
    first['blocks'].extend(snapshot((765, [(50, 550, '上述项目仍有投资风险，具体详见下一章节。')]))['blocks'])
    result = observe(first)
    assert result['candidate'] and result['continuation'] is None


def test_top_running_header_is_not_promoted_to_table_or_prose_break():
    previous = observe(tail_table())['continuation']
    second = snapshot((80, [(50, 'C型设备'), (200, '300'), (350, '台/年')]),
                      (100, [(50, 'D型设备'), (200, '400'), (350, '台/年')]))
    second['blocks'].insert(0, {'type': 0, 'lines': [{'spans': [
        {'text': '某公司年度报告', 'bbox': (50, 30, 550, 38)}]}]})
    assert observe(second, previous=previous)['candidate']


@pytest.mark.parametrize('bad', [None, [], {'blocks': None}, {'blocks': [{'type': 0, 'lines': None}]},
    {'blocks': [{'type': 0, 'lines': [{'spans': [{'text': '产能', 'bbox': [0, float('nan'), 100, 10]}]}]}]}])
def test_empty_or_malformed_is_bounded_unknown(bad):
    result = observe(bad)
    assert result['candidate'] is False and result['continuation'] is None


def test_zero_work_stops_before_snapshot_walk():
    class Unread(dict):
        def get(self, *args):
            raise AssertionError('zero work must precede access')
    result = observe(Unread(), work_budget=WorkBudget(0))
    assert not result['candidate'] and result['reason'] == 'work_budget_exhausted'


def test_previous_untrusted_shape_cannot_force_a_candidate():
    value = snapshot((80, [(50, 'A设备'), (200, '100')]),
                     (100, [(50, 'B设备'), (200, '200')]))
    assert not observe(value, previous={'candidate': True, 'continuation': True})['candidate']


def test_numbered_section_prose_breaks_previous_page_continuation():
    previous = observe(tail_table())['continuation']
    second = snapshot((60, [(50, '1、其他业务情况')]),
                      (80, [(50, 'C型设备'), (200, '300'), (350, '台/年')]),
                      (100, [(50, 'D型设备'), (200, '400'), (350, '台/年')]))
    assert not observe(second, previous=previous)['candidate']


def test_outside_page_boxes_are_not_observed_table_geometry():
    value = snapshot((100, [(-50, -30, '产品'), (900, 940, '产能')]),
                     (120, [(-50, -30, 'A设备'), (900, 940, '100')]))
    result = observe(value)
    assert not result['candidate'] and result['partial']


def test_two_column_prose_does_not_become_an_operating_table():
    value = snapshot((100, [(50, 280, '公司产能在2025年增长100%，未来仍将继续扩大。'),
                            (330, 560, '行业需求保持增长，预计2026年继续发展。')]),
                     (120, [(50, 280, '新工厂计划未来投入运营，产能规划仍有不确定性。'),
                            (330, 560, '公司关注环境变化，长期增长仍待验证。')]))
    assert not observe(value)['candidate']


def test_description_only_project_table_does_not_require_digits():
    value = snapshot((100, [(50, '项目名称'), (220, '主要产品'), (400, '建设地点')]),
                     (120, [(50, '机床项目'), (220, '高端机床'), (400, '苏州')]))
    assert observe(value)['candidate']


def test_description_only_two_column_paragraphs_still_do_not_qualify():
    value = snapshot((100, [(50, 280, '公司产能不断提高，未来仍将继续扩大。'),
                            (330, 560, '行业需求保持增长，未来继续发展。')]),
                     (120, [(50, 280, '新工厂计划未来投入运营，产能规划仍有不确定性。'),
                            (330, 560, '公司关注环境变化，长期增长仍待验证。')]))
    assert not observe(value)['candidate']


def test_repeated_measured_rows_reuse_semantic_owner_results_within_call(monkeypatch):
    import company_wiki.source_catalog.narrative_pdf_candidates as candidates
    original = candidates.qualify_table
    calls = []

    def counted(headers, rows, **kwargs):
        calls.append((tuple(headers), tuple(rows)))
        return original(headers, rows, **kwargs)

    monkeypatch.setattr(candidates, 'qualify_table', counted)
    rows = [(100, [(50, '产品'), (200, '产能'), (350, '单位')])]
    rows.extend((120 + index * 20, [(50, 'A型设备'), (200, '100'), (350, '台/年')])
                for index in range(30))
    value = snapshot(*rows, height=1000)
    budget = WorkBudget(3_000_000)
    assert observe(value, work_budget=budget)['candidate']
    assert len(calls) <= 4
    assert len(calls) == len(set(calls))
    first_calls = len(calls)
    assert observe(value)['candidate']
    assert len(calls) == first_calls * 2  # no cache survives into a new page call
