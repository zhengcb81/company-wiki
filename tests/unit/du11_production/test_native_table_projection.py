"""A row-limited native table remains a closed input to the strict binder."""
from copy import deepcopy
import pytest

from company_wiki.document_understanding import native_table_bridge as bridge
from company_wiki.document_normalization import pdf_table_observations as pdf
from company_wiki.resource_budget import WorkBudget
from unit.du4_table_measurements.builders import cell, observation, text_ref, unit


@pytest.mark.parametrize('invalid', [None, {'kind':'native_slot', 'cell_id':'ghost'}, {'kind':'native_slot'}])
def test_pdf_eligible_rows_keep_only_their_original_cell_provenance(monkeypatch, invalid):
    texts = {'h':'产能（台/年）', 'a':'120', 'b':'999'}
    units = {uid:unit(uid, text) for uid, text in texts.items()}
    cells = [cell('r0c0', 0, 0, text_refs=[text_ref('h', texts['h'], texts['h'])]),
             cell('r1c0', 1, 0, text_refs=[text_ref('a', '120', '120')]),
             cell('r2c0', 2, 0, text_refs=[text_ref('b', '999', '999')])]
    table = observation(units, cells, header_rows=[0], provenance=[
        {'kind':'native_slot', 'cell_id':c['cell_id'], 'row':c['row'], 'column':c['column'],
         'row_span':1, 'column_span':1} for c in cells])
    if invalid is not None:
        table['provenance'].append(invalid)
    original = deepcopy(table)
    monkeypatch.setattr(pdf, 'build_pdf_table_observations', lambda *a, **kw:
        {'tables':[table], 'diagnostics':[], 'status':'complete'})
    source = {'source_ref':{'source_id':'parent-1'}, 'units':[
        {'unit_id':uid, 'text':text, 'kind':'pdf_table_row', 'hints':{}} for uid,text in texts.items()]}
    if invalid is not None:
        with pytest.raises(ValueError, match='provenance points at unknown cell'):
            bridge.bind_native_tables(source, work_budget=WorkBudget(100_000), eligible_unit_ids={'a'})
        assert table == original
        return
    result = bridge.bind_native_tables(source, work_budget=WorkBudget(100_000), eligible_unit_ids={'a'})
    assert result['tables']
    for measurement in result['tables'][0]['measurements']:
        assert measurement['value_ref']['unit_id'] != 'b'
    projected = bridge._eligible_cells(table, {'a'}, WorkBudget(100_000))
    assert {c['cell_id'] for c in projected['cells']} == {'r0c0', 'r1c0'}
    assert {p['cell_id'] for p in projected['provenance']} == {'r0c0', 'r1c0'}
    assert table == original
