"""Independent scope/value/budget controls for ROOT's PDF table projection repair."""
from copy import deepcopy
import pytest
from company_wiki.document_normalization.pdf_table_observations import adapter
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table

def row(uid, values, number, *, table='p1:t0', parent='source-a', page=1, kind='table_row'):
    text=' | '.join(values)
    entries=[]
    offset=0
    for column,value in enumerate(values):
        entries.append({'table_id':table,'row':number,'column':column,'text':value,
                        'char_start':offset,'char_end':offset+len(value),
                        'char_alignment':'exact','coordinate_frame':'dict','page':page})
        offset+=len(value)+3
    return {'unit_id':uid,'text':text,'page':page,'kind':kind,'role':'company_filing',
            'locator':{'page_number':page},
            'hints':{'source_id':parent,'table_id':table,'row':number,'cells':entries}}

def observation(units):
    return {'schema_version':'du-input/1','source_ref':{'source_id':'source-a'},'units':units}

def hints(header='h', target=('h','r')):
    return {'schema_version':'du2-layout-hints/1','groups':[
        {'group_id':'header','kind':'table_row','member_unit_ids':[header]},
        {'group_id':'table','kind':'table_region','member_unit_ids':list(target)}],
        'relations':[{'kind':'header_for','from_group_id':'header','to_group_id':'table'}]}

def project(units, layout=None, budget=None):
    return adapter.build_pdf_table_observations(observation(units),layout,work_budget=budget or WorkBudget(2000000))

def measurements(result):
    output=[]
    for table in result['tables']:
        bound=bind_operating_table(table,work_budget=WorkBudget(2000000))
        for value in bound['measurements']:
            ref=value['value_ref']
            output.append((table['units'][ref['unit_id']]['text'][ref['char_start']:ref['char_end']],value))
    return output

def test_two_numeric_columns_are_both_values_without_invented_label():
    result=project([row('h',['2025年','2024年'],0),row('r',['10','20'],1)],hints())
    assert result['status']=='partial'  # observation lacks a row-label role
    values=measurements(result)
    assert {text for text,_ in values}=={'10','20'}
    assert all(value['row_label_refs']==[] for _,value in values)

def test_leading_text_is_not_sufficient_to_prove_row_label_either():
    result=project([row('h',['项目','2025年'],0),row('r',['海外产能','20'],1)],hints())
    assert result['status']=='partial'
    assert {text for text,_ in measurements(result)}=={'海外产能','20'}
    assert all(value['row_label_refs']==[] for _,value in measurements(result))

def test_fragment_refs_survive_but_never_as_complete_numeric_values():
    header=row('h',['项目','2025年'],0)
    pieces=[]
    for uid,text,start in [('a','12',0),('b','34',2)]:
        piece=row(uid,[text],1)
        piece['hints']['cells'][0].update(column=1,partial_cell=True,native_cell_char_start=start,native_cell_char_end=start+2)
        pieces.append(piece)
    result=project([header]+pieces,hints(target=('h','a','b')))
    assert result['status']=='partial'
    cell=next(c for c in result['tables'][0]['cells'] if c['row']==1)
    assert {r['unit_id'] for r in cell['text_refs']}=={'a','b'}
    assert cell['presence']=='unavailable'
    values=measurements(result)
    assert {text for text,_ in values}=={'12','34'}
    assert all(value['binding_status']=='unavailable' for _,value in values)

@pytest.mark.parametrize('field,value',[('page',9),('source_id','foreign-parent'),('table_id','p9:t9')])
def test_bad_fine_scope_is_rejected_and_declares_loss(field,value):
    data=row('r',['门店','18','19'],1)
    data['hints']['cells'][-1][field]=value
    result=project([row('h',['项目','2025年','2024年'],0),data],hints())
    assert result['status']=='partial'
    assert result['tables'][0]['truncated']
    assert '19' not in {text for text,_ in measurements(result)}

def test_header_relation_does_not_apply_across_parent_or_table_scope():
    units=[row('r',['10','20'],0),row('target',['30','40'],0,parent='foreign',table='p1:t1')]
    result=project(units,hints(header='r',target=('target',)))
    assert result['status']=='partial'
    assert all(table['header_rows']==[] for table in result['tables'])
    assert 'FOREIGN_HEADER_RELATION_DROPPED' in {d['code'] for d in result['diagnostics']}

def test_pdf_synthetic_row_zero_kind_is_not_observed_header_role():
    result=project([row('r',['门店','18'],0,kind='table_header')])
    assert result['status']=='partial'
    assert result['tables'][0]['header_rows']==[]
    assert 'HEADER_ROLE_UNCONFIRMED' in {d['code'] for d in result['diagnostics']}

def test_zero_remaining_work_never_iterates_slots_after_index(monkeypatch):
    budget=WorkBudget(4)
    original=adapter._build_table
    class Trap(list):
        def __iter__(self):
            assert budget.used<budget.max_work_units,'slot traversal with no work remaining'
            return super().__iter__()
    def guarded(scope,*args):
        scope.order=Trap(scope.order)
        return original(scope,*args)
    monkeypatch.setattr(adapter,'_build_table',guarded)
    result=project([row('r',['a','b'],0)],budget=budget)
    assert result['status']=='partial' and result['tables']==[]
    assert budget.used==4

def test_rows_are_prepared_once_not_quadratic_and_inputs_are_readonly():
    consumed=[]
    for n in (100,200,400):
        units=[row(f'r{i}',['门店','18'],i) for i in range(n)]
        original=deepcopy(units)
        budget=WorkBudget(2000000,used=17)
        result=project(units,budget=budget)
        assert len(result['tables'])==1 and result['status']=='partial'
        assert units==original
        assert result['work_used']==budget.used-17
        consumed.append(result['work_used'])
    assert consumed[1]<3*consumed[0]
    assert consumed[2]<3*consumed[1]


def test_multiple_carriers_without_partial_flag_do_not_prove_whole_values():
    a=row('a',['12'],1)
    b=row('b',['34'],1)
    for unit in (a,b):
        unit['hints']['cells'][0]['column']=1
    result=project([row('h',['项目','2025年'],0),a,b],hints(target=('h','a','b')))
    assert result['status']=='partial'
    values=measurements(result)
    assert {text for text,_ in values}=={'12','34'}
    assert all(value['binding_status']=='unavailable' for _,value in values)


def test_unrelated_layout_groups_are_not_foreign_table_evidence():
    header=row('h',['2025年'],0)
    data=row('r',['20'],1)
    paragraph={'unit_id':'unrelated','text':'Other section','page':2,'kind':'heading','hints':{'source_id':'source-a'}}
    layout=hints()
    layout['groups'].extend([
        {'group_id':'other-header','kind':'table_row','member_unit_ids':['unrelated']},
        {'group_id':'other-region','kind':'table_region','member_unit_ids':['unrelated']}])
    layout['relations'].append({'kind':'header_for','from_group_id':'other-header','to_group_id':'other-region'})
    result=project([header,data,paragraph],layout)
    assert result['status']=='complete'
    assert not any(d['code']=='FOREIGN_HEADER_RELATION_DROPPED' for d in result['diagnostics'])
    assert [text for text,_ in measurements(result)]==['20']
