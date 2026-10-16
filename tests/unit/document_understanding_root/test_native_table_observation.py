"""Native HTML slots reach the existing table binder without changing old wire."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json

from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization


HTML = "<html><body><h1>FORM 10-Q</h1><table><thead><tr><th rowspan='2'>Capacity (units)</th><th colspan='2'>As of December 31</th></tr><tr><th>2025</th><th>2026</th></tr></thead><tbody><tr><th scope='row'>Overseas plants</th><td><b>12</b></td><td>18</td></tr><tr><th scope='row'>Domestic plants</th><td></td><td>24</td></tr></tbody></table></body></html>"


def parsed(body):
    raw=body.encode()
    digest=sha256(raw).hexdigest()
    source='urn:company-wiki:source:sha256:'+digest
    normal=normalize_document(raw,source_id=source,source_sha256=digest,mime_type='text/html')
    return NarrativeNormalization.language_structure(normal,'en')


def observe(body):
    document=parsed(body)
    return build_observation(document.units,source_id=document.source_id,
        source_sha256=document.source_sha256,mime_type='text/html',language='en')


def tables(observation):
    return [table for unit in observation['units']
            for table in unit['hints'].get('native_tables',())]


def bind(observation, budget=None):
    from company_wiki.document_understanding.native_table_bridge import bind_native_tables
    return bind_native_tables(observation,work_budget=budget if budget is not None else WorkBudget(100000))


def text(observation,ref):
    row=next(row for row in observation['units'] if row['unit_id']==ref['unit_id'])
    return row['text'][ref['char_start']:ref['char_end']]


def measurement(observation,result,value):
    return next(m for table in result['tables'] for m in table['measurements']
                if text(observation,m['value_ref'])==value)


def test_actual_html_native_grid_merged_headers_two_periods_and_row_labels():
    observation=observe(HTML)
    native,=tables(observation)
    assert native['scope']['table_id']=='html:t0'
    top=native['cells'][0]
    assert (top['row'],top['column'],top['row_span'],top['column_span'])==(0,0,2,1)
    second_year=next(cell for cell in native['cells'] if cell['row']==1 and cell['column']==2)
    assert text(observation,second_year['text_refs'][0])=='2026'
    result=bind(observation)
    earlier=measurement(observation,result,'12')
    later=measurement(observation,result,'18')
    assert earlier['column_id']=='col-1' and earlier['period']['end']=='2025-12-31'
    assert later['column_id']=='col-2' and later['period']['end']=='2026-12-31'
    assert [text(observation,ref) for ref in later['row_label_refs']]==['Overseas plants']


def test_empty_td_has_native_slot_without_a_fabricated_unit_or_shifted_value():
    observation=observe(HTML)
    empty=next(cell for cell in tables(observation)[0]['cells'] if cell['row']==3 and cell['column']==1)
    assert empty['presence']=='empty' and empty['text_refs']==[]
    assert all(unit['text'].strip() for unit in observation['units'])
    found=measurement(observation,bind(observation),'24')
    assert found['column_id']=='col-2' and found['period']['end']=='2026-12-31'


def test_multicolumn_value_and_inline_fragments_are_not_split_into_guessed_columns():
    observation=observe('<table><tr><th>Fiscal year 2025</th><th>Fiscal year 2026</th></tr>'
                        '<tr><td colspan="2"><b>12</b><span>18</span></td></tr></table>')
    cell=tables(observation)[0]['cells'][-1]
    assert [text(observation,ref) for ref in cell['fragment_refs']]==['12','18']
    assert len({ref['unit_id'] for ref in cell['fragment_refs']})==1
    assert text(observation,cell['text_refs'][0])=='12 18'
    result=bind(observation)
    found=measurement(observation,result,'12 18')
    assert found['binding_status']=='ambiguous' and found['column_id'] is None


def test_hidden_cells_do_not_expose_values_or_collapse_later_native_slots():
    observation=observe('<table><tr><th>Fiscal year 2025</th><th>Fiscal year 2026</th></tr>'
                        '<tr><td hidden>91234567</td><td>18</td></tr></table>')
    native=tables(observation)[0]
    hidden=next(c for c in native['cells'] if c['row']==1 and c['column']==0)
    assert hidden['presence']=='unavailable' and hidden['text_refs']==[]
    assert '91234567' not in json.dumps(observation)
    assert measurement(observation,bind(observation),'18')['column_id']=='col-1'


def test_td_only_year_order_never_manufactures_native_column_headers():
    observation=observe('<table><tr><td>2026</td><td>2025</td></tr><tr><td>18</td><td>12</td></tr></table>')
    assert tables(observation)[0]['header_rows']==[]
    found=measurement(observation,bind(observation),'18')
    # Original DU4 binder calls a value with no native header path ambiguous.
    assert found['binding_status']=='ambiguous' and found['period'] is None
    assert any(d['code']=='no_header_path' for d in bind(observation)['tables'][0]['diagnostics'])


def test_same_table_indices_from_two_sources_are_not_combined():
    first=observe('<table><tr><th>Fiscal year 2025</th></tr><tr><td>12</td></tr></table>')
    second=observe('<table><tr><th>Fiscal year 2026</th></tr><tr><td>18</td></tr></table>')
    combined={**first,'units':first['units']+second['units']}
    result=bind(combined)
    assert len(result['tables'])==2
    assert len({table['scope']['parent_id'] for table in result['tables']})==2
    assert measurement(combined,result,'12')['period']['fiscal_label']=='2025'
    assert measurement(combined,result,'18')['period']['fiscal_label']=='2026'


def test_foreign_parent_refs_are_not_reassigned_to_the_table_owner():
    observation=deepcopy(observe(HTML))
    value=next(unit for unit in observation['units'] if unit['text']=='18')
    value['hints']['source_id']='foreign-source'
    found=measurement(observation,bind(observation),'18')
    assert found['binding_status']=='ambiguous' and found['column_id'] is None


def test_zero_budget_does_not_access_observation_or_reset_prior_spend():
    class Unread(dict):
        def get(self,*args,**kwargs):
            raise AssertionError('zero budget traversed input')
        def __getitem__(self,key):
            raise AssertionError('zero budget traversed input')
    budget=WorkBudget(7,used=7)
    result=bind(Unread(),budget)
    assert result['status']=='partial' and result['tables']==[]
    assert budget.used==7 and budget.exhausted


def test_bridge_calls_original_binder_with_the_same_budget_and_original_refs(monkeypatch):
    from company_wiki.document_understanding import native_table_bridge as bridge
    original=bridge.bind_operating_table
    calls=[]
    budget=WorkBudget(100000,used=17)
    def watched(observation,*,work_budget):
        assert work_budget is budget
        calls.append(observation)
        return original(observation,work_budget=work_budget)
    monkeypatch.setattr(bridge,'bind_operating_table',watched)
    observation=observe(HTML)
    before=json.dumps(observation,sort_keys=True)
    result=bridge.bind_native_tables(observation,work_budget=budget)
    assert len(calls)==len(result['tables'])==1
    assert result['work_used']==budget.used-17
    assert json.dumps(observation,sort_keys=True)==before
    assert calls[0]['schema_version']=='du4-table-observation/1'


def test_all_empty_table_does_not_invent_a_narrative_unit():
    observation=observe('<table><tr><td> </td><td></td></tr></table>')
    assert observation['units']==[]
    assert bind(observation)['status']=='unavailable'


def test_coarse_pdf_coordinates_are_not_promoted_to_native_value_slots():
    result=bind({'schema_version':'du-input/1','units':[{
        'unit_id':'pdf-unit','text':'18 12','kind':'table_row','hints':{'table_id':'pdf:t0',
            'row':0,'bbox':[0,0,100,20],'geometry_granularity':'block'}}]})
    assert result['tables']==[] and result['status']=='unavailable'


def test_one_dom_parse_and_one_cached_grid_per_table_preserve_existing_owner_walk(monkeypatch):
    from company_wiki.document_normalization import html_parser
    counts={'parse':0,'rows':0,'cells':0}
    def count(name, original):
        def wrapped(*args,**kwargs):
            counts[name]+=1
            return original(*args,**kwargs)
        return wrapped
    monkeypatch.setattr(html_parser,'BeautifulSoup',count('parse',html_parser.BeautifulSoup))
    monkeypatch.setattr(html_parser,'_table_rows',count('rows',html_parser._table_rows))
    monkeypatch.setattr(html_parser,'_row_cells',count('cells',html_parser._row_cells))
    bind(observe(HTML))
    assert counts=={'parse':1,'rows':1,'cells':4}


def test_real_native_caption_qualifies_values_through_actual_refs_not_a_fake_row():
    observation=observe('<table><caption>Overseas sales (RMB million), excluding same-store sales</caption>'
        '<tr><th>Fiscal year 2025</th></tr><tr><td>18</td></tr></table>')
    native=tables(observation)[0]
    assert [c['row'] for c in native['cells']]==[0,1]
    found=measurement(observation,bind(observation),'18')
    assert any('RMB' in text(observation,ref) for ref in found['unit_refs'])
    assert any('Overseas' in text(observation,ref) for ref in found['scope_refs'])
    assert any('same-store' in text(observation,ref) for ref in found['qualifier_refs'])


def test_all_empty_native_table_with_visible_anchor_is_unavailable_with_empty_refs():
    observation=observe('<p>Source note.</p><table><tr><td></td><td> </td></tr></table>')
    assert len(observation['units'])==1
    assert len(tables(observation)[0]['cells'])==2
    assert all(c['presence']=='empty' and c['text_refs']==[] for c in tables(observation)[0]['cells'])
    assert bind(observation)['status']=='unavailable'


def test_nested_table_does_not_lend_text_or_slots_to_its_outer_cell():
    observation=observe('<table><tr><td><table><tr><th>Fiscal year 2026</th></tr>'
                        '<tr><td>18</td></tr></table></td></tr></table>')
    outer,inner=tables(observation)
    assert outer['scope']['table_id']=='html:t0' and inner['scope']['table_id']=='html:t1'
    assert outer['cells'][0]['presence']=='empty' and outer['cells'][0]['text_refs']==[]
    result=bind(observation)
    assert result['tables'][0]['measurements']==[]
    assert measurement(observation,result,'18')['period']['fiscal_label']=='2026'


def test_exhaustion_reserves_before_accessing_unread_unit_tail():
    class Units:
        def __len__(self):
            return 100000
        def __getitem__(self,index):
            raise AssertionError('unit fetched after failed reservation')
    budget=WorkBudget(1)
    result=bind({'units':Units()},budget)
    assert result['status']=='partial' and result['tables']==[]
    assert budget.used==1 and budget.exhausted


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def test_pre_table_bridge_canonical_identity_and_all_legacy_model_wires_stay_exact():
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.narrative_model import NarrativeModelRequest
    from support.narrative_model_request_fixture import selection
    from unit.test_narrative_reading_transport import with_reading
    from unit.test_narrative_source_owned_model_boundary import http_port
    document=parsed(HTML)
    spans=[u.to_evidence_span(topics=['capacity'],selection_reasons=['source_owned_table']).to_dict()
           for u in document.units]
    canonical=[{'unit_id':u.unit_id,'coordinates':asdict(u.coordinates),'text':u.raw_text,
        'source_locator':u.metadata['source_locator'],'span':span}
        for u,span in zip(document.units,spans,strict=True)]
    assert fingerprint(canonical)=='6edd45a159404099507ebba9d62ef5e820784633f3237c67ad38130bb26b76f4'
    wire=selection(len(spans)).to_dict()
    wire['source_ref'].update(source_id=document.source_id,content_sha256=document.source_sha256,
                             byte_size=len(HTML.encode()),mime_type='text/html')
    wire['source_metadata'].update(title='Native table compatibility',document_kind='quarterly',language='en')
    wire['evidence_spans']=spans
    wire['parser']={'name':document.units[0].parser_name,'version':document.units[0].parser_version}
    selected=with_reading(NarrativeSelectResult.from_dict(wire))
    frozen={
        None:('6e0ad0a8db8de4cd1c0cd353d85e65a30eb6f9b78076c5d1de785d70ba647cea','b12ef7915245da1118eddc5b0300dbadcab1a14638f9cc73690b8ce0426af46c'),
        'reading-model-input/1':('d7827fcaa08514fd64a44d413cccd54f7011fc53e9e643f98697b17845035f97','a588eaef495b16dc3f12fb1a37cb9ec00a86bb10adcf1374e0e327b9d9d81271'),
        'reading-model-input/2':('3ef37a60b06a4e3aef875338c84aec43425a66cfeb915f0dac737c54b7070357','0146ef7dd173751c1979e15b9bfe37b92c6f0387d600d57e5cfcfa0828d11d90'),
        'reading-model-input/3':('4dfc1e2ff73d34a392b3960d3e0d98668e35963b9860c6eda4c873496497e837','cc680ec3778b99ee1881103244e0adc43595e8c4a44353598dfe6f353c425edf'),
    }
    for version,(request_sha,http_sha) in frozen.items():
        request=NarrativeModelRequest.from_selection(selected,reading_projection_version=version)
        assert fingerprint(asdict(request))==request_sha
        assert sha256(http_port().request_bytes(request)).hexdigest()==http_sha
