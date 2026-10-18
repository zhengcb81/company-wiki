import pytest
from company_wiki.document_understanding import narrative_continuity as n
from company_wiki.document_understanding.operating_states.relations import independent_statement_start
from company_wiki.resource_budget import WorkBudget
from unit.document_understanding_selection.test_reading_native_continuity import native
from unit.du11_reference_readiness.test_native_page_local_positions import inspect

def rows(right_text="our customers next year.",counter=False):
    left=native("The company plans to deliver the products to",33,page=7,box=[90,720,550,732],block=34,column=0)
    header=native("Annual report",34,page=8,kind="header")
    footer=native("8 / 210",35,page=8,kind="paragraph" if counter else "footer",scope="page-marker" if counter else "body",box=[290,770,330,782])
    right=native(right_text,36,page=8,box=[90,80,550,92],block=2,column=0)
    for index,row in enumerate((header,footer,right)):row[1]["paragraph_index"]=index
    return [left,header,footer,right]

@pytest.mark.parametrize('right',["本集團另一項目尚未獲准量產。","Our new platform is not yet approved for production."])
def test_unknown_counter_does_not_wrongly_defer_a_fresh_independent_statement(right):
    r=rows(right,counter=True); original=[x[0]['text'] for x in r]; result=inspect(r,[r[1][0]['unit_id']])
    assert not result['windows'] and r[-1][0]['unit_id'] not in result['deferred_unit_ids']
    assert [x[0]['text'] for x in r]==original

def test_unproved_local_prefix_gap_cannot_become_positive_furniture():
    r=rows();r[2][1]['paragraph_index']=3;r[3][1]['paragraph_index']=4
    result=inspect(r,[r[1][0]['unit_id'],r[2][0]['unit_id']])
    assert not result['windows'] and {r[0][0]['unit_id'],r[-1][0]['unit_id']}<=set(result['deferred_unit_ids'])

def test_same_page_paragraph_reset_is_still_an_order_barrier():
    a=native("The company plans to deliver devices to",33,page=7,box=[90,700,550,712],column=0)
    b=native("our customers next year.",34,page=7,box=[90,720,550,732],column=0);b[1]['paragraph_index']=0
    assert not inspect([a,b])['windows']

def test_pending_counter_path_obeys_existing_shared_budget():
    r=rows(counter=True);budget=WorkBudget(12)
    result=n.build_native_continuity([x[0] for x in r],provenance={x[0]['unit_id']:x[1] for x in r},unit_profiles={x[0]['unit_id']:x[2] for x in r},source_page_flow=n.SourcePageFlow(frozenset([r[1][0]['unit_id']]),independent_statement_start),work_budget=budget)
    assert not result['windows'] and not result['complete'] and budget.used<=12
    assert budget.used==result['work_units'] and not budget.exhausted
    assert any(d['code']=='CONTINUITY_WORK_LIMIT' for d in result['diagnostics'])
    assert result['unexamined_from_index'] is not None

def test_proven_furniture_passes_only_four_original_scalar_refs(monkeypatch):
    r=rows();observed=[];actual=n._Analysis.page_edge
    def spy(self,left,right,furniture):
        observed.extend(furniture);return actual(self,left,right,furniture)
    monkeypatch.setattr(n._Analysis,'page_edge',spy)
    result=inspect(r,[r[1][0]['unit_id'],r[2][0]['unit_id']])
    assert len(result['windows'])==1 and len(observed)==2
    assert all(set(x)=={'unit_id','page','ordinal','paragraph_index'} for x in observed)
    assert [x['unit_id'] for x in observed]==[r[1][0]['unit_id'],r[2][0]['unit_id']]
