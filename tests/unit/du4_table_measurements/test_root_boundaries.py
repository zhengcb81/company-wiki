"""Source-scoped table facts, explicit endpoints and honest work accounting."""
import builtins

import pytest

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bindings as binder
from .builders import DEFAULT_PARENT, cell, observation, text_ref, unit


def table(header, *, parent=DEFAULT_PARENT, page=1, row_label=None):
    units={'h':unit('h',header, parent_id=parent, locator={'page_number':page}), 'v':unit('v','42')}
    refs=[text_ref('h',header,header)]
    if row_label:
        units['r']=unit('r',row_label)
        refs.append(text_ref('r',row_label,row_label))
    return observation(units,[cell('h',0,1,text_refs=refs[:1]),
                              cell('v',1,1,text_refs=[text_ref('v','42','42')],header_refs=refs)],
                       header_rows=[0])


@pytest.mark.parametrize('parent,page', [('other-parent',1), (DEFAULT_PARENT,2)])
def test_foreign_header_cannot_supply_current_value_date_or_unit(parent,page):
    result=binder.bind_operating_table(table('As of December 31, 2024 (RMB millions)',parent=parent,page=page),
                                      work_budget=WorkBudget(10000))
    value=result['measurements'][0]
    assert value['binding_status']!='bound'
    assert value['period'] is None
    assert value['unit_refs']==[]


@pytest.mark.parametrize('presence',['unavailable','empty','merged_unknown'])
def test_unobserved_header_cannot_supply_a_confident_period(presence):
    data=table('As of December 31, 2024')
    data['cells'][0]['presence']=presence
    result=binder.bind_operating_table(data,work_budget=WorkBudget(10000))
    value=result['measurements'][0]
    assert value['binding_status']!='bound'
    assert value['period'] is None


@pytest.mark.parametrize('label,start,end', [
    ('Six months from January 1, 2024 to June 30, 2024','2024-01-01','2024-06-30'),
    ('Six months from October 1, 2023 to March 31, 2024','2023-10-01','2024-03-31'),
])
def test_explicit_period_end_is_not_the_first_date_in_the_label(label,start,end):
    result=binder.bind_operating_table(table(label),work_budget=WorkBudget(10000))
    period=result['measurements'][0]['period']
    assert period['start']==start and period['end']==end
    assert period['duration_months']==6


def test_row_currency_does_not_erase_compatible_header_scale():
    data=table('2024 (millions)',row_label='Revenue (RMB)')
    result=binder.bind_operating_table(data,work_budget=WorkBudget(10000))
    refs=result['measurements'][0]['unit_refs']
    labels=[data['units'][r['unit_id']]['text'][r['char_start']:r['char_end']] for r in refs]
    assert any('RMB' in label for label in labels)
    assert any('millions' in label for label in labels)


def test_composite_header_keeps_its_scale_when_row_already_specifies_currency():
    data=table('2024 (RMB in millions)',row_label='Revenue (RMB)')
    result=binder.bind_operating_table(data,work_budget=WorkBudget(10000))
    refs=result['measurements'][0]['unit_refs']
    labels=[data['units'][r['unit_id']]['text'][r['char_start']:r['char_end']] for r in refs]
    assert any('RMB' in label for label in labels)
    assert any('millions' in label for label in labels)


@pytest.mark.parametrize('label', ['As of December 31, 2023 or 2024',
                                  'Six months or twelve months ended June 30, 2024'])
def test_conflicts_inside_one_header_cannot_become_the_first_match(label):
    result=binder.bind_operating_table(table(label),work_budget=WorkBudget(10000))
    value=result['measurements'][0]
    assert value['binding_status']=='ambiguous'
    assert value['period'] is None


def test_sparse_native_column_does_not_materialize_unobserved_columns():
    data=table('As of December 31, 2024')
    for item in data['cells']:
        item['column']=10**9
        item['column_span']=1
    result=binder.bind_operating_table(data,work_budget=WorkBudget(10000))
    assert result['status']=='complete'
    assert [column['native_column'] for column in result['columns']]==[10**9]


def test_header_rows_cannot_be_traversed_on_an_empty_budget():
    class Rows(list):
        def __iter__(self):
            pytest.fail('header rows traversed with zero work')
    data=observation({},[],header_rows=[])
    data['header_rows']=Rows(range(10000))
    result=binder.bind_operating_table(data,work_budget=WorkBudget(0))
    assert result['status']=='partial' and result['work_used']==0


def test_provenance_tail_is_not_walked_after_budget_exhaustion():
    class Records(list):
        def __iter__(self):
            pytest.fail('unpaid provenance walk')
    data=observation({'u':unit('u','x')},[cell('c',1,0,presence='unavailable')])
    data['provenance']=Records([{'kind':'native_slot','cell_id':'c'}]*10000)
    result=binder.bind_operating_table(data,work_budget=WorkBudget(2))
    assert result['status']=='partial'


def test_merged_span_cannot_expand_after_budget_is_spent(monkeypatch):
    visits=[]
    class Range:
        def __init__(self,*args):
            self.values=builtins.range(*args)
        def __iter__(self):
            for value in self.values:
                visits.append(1)
                yield value
        def __len__(self):
            return len(self.values)
        def __getitem__(self,index):
            visits.append(1)
            return self.values[index]
    monkeypatch.setattr(binder,'range',Range,raising=False)
    data=observation({'u':unit('u','7')},[cell('c',1,0,text_refs=[text_ref('u','7','7')],
                                                       presence='merged_unknown',column_span=5000)])
    result=binder.bind_operating_table(data,work_budget=WorkBudget(4))
    assert result['status']=='partial'
    assert len(visits)<=5
