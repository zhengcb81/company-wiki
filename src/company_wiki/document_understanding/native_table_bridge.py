"""Thin native-table observation composition over the existing DU4 binder.

No IO, geometry inference, numeric extraction, budget creation or persistence.
Whole original cell owners remain whole; inline fragment refs are provenance,
not instructions to distribute values across a merged cell's columns.
"""
from collections.abc import Mapping
from typing import Any

from .layout_hints.contract import WorkBudget, WorkBudgetExceeded
from .table_measurements import bind_operating_table


def _each(values, budget):
    for index in range(len(values)):
        budget.charge()
        yield values[index]


def _observation(table, units, budget):
    cells = table['cells']
    native_ids: dict[str, list[dict[str, Any]]] = {}
    row_headers: dict[int, list[dict[str, Any]]] = {}
    group_headers: dict[int, list[dict[str, Any]]] = {}
    refs_needed: dict[str, None] = {}
    for cell in _each(cells, budget):
        for ref in _each(cell['text_refs'], budget):
            refs_needed[ref['unit_id']] = None
        if cell['html_id']:
            native_ids.setdefault(cell['html_id'], []).append(cell)
        if cell['is_header'] and cell['header_scope'] == 'row':
            for row in _each(range(cell['row'], cell['row'] + (cell['row_span'] or 1)), budget):
                row_headers.setdefault(row, []).extend(cell['text_refs'])
        if cell['is_header'] and cell['header_scope'] == 'rowgroup':
            group_headers.setdefault(cell['row_group'], []).extend(cell['text_refs'])
    for ref in _each(table['context_refs'], budget):
        refs_needed[ref['unit_id']] = None
    projected = []
    provenance = []
    for cell in _each(cells, budget):
        labels = []
        for refs in (table['context_refs'], row_headers.get(cell['row'],()),
                     group_headers.get(cell['row_group'],())):
            for ref in _each(refs, budget):
                labels.append(ref)
        for target in _each(cell['headers'], budget):
            owners = native_ids.get(target, ())
            if len(owners) == 1:
                for ref in _each(owners[0]['text_refs'], budget):
                    labels.append(ref)
        for ref in _each(labels, budget):
            refs_needed[ref['unit_id']] = None
        projected.append({key: cell[key] for key in ('cell_id','row','column','row_span',
                                                     'column_span','presence','text_refs')} | {'header_refs': labels})
        provenance.append({'kind':'native_slot', **{key:cell[key]
            for key in ('cell_id','row','column','row_span','column_span')}})
    selected_units = {}
    for uid in refs_needed:
        budget.charge()
        if uid not in units:
            # The source view may outlive a reduced observation. Never recover
            # missing text from another source or invent an empty source unit.
            return None
        selected_units[uid] = units[uid]
    return {'schema_version':'du4-table-observation/1','scope':table['scope'],
        'units':selected_units,'cells':projected,'header_rows':table['header_rows'],
        'provenance':provenance,'truncated':not table['position_complete']}


def bind_native_tables(observation: Mapping[str, Any], *, work_budget: WorkBudget) -> dict:
    """Return existing binder results and a small transient coverage summary."""
    start = work_budget.used
    tables = []
    diagnostics = []
    results = []
    status = 'unavailable'
    try:
        work_budget.charge()  # Before reading any input, including a zero cap.
        units = {}
        seen = set()
        for unit in _each(observation.get('units', ()), work_budget):
            hints = unit.get('hints') or {}
            units[unit['unit_id']] = {'text':unit['text'],
                'parent_id':hints.get('source_id') or observation.get('source_ref',{}).get('source_id'),
                'role':unit.get('role'),'kind':unit['kind'],'locator':unit.get('locator')}
            for table in _each(hints.get('native_tables', ()), work_budget):
                scope = table['scope']
                key = (scope['parent_id'],scope['table_id'],scope['page'])
                if key not in seen:
                    seen.add(key)
                    tables.append(table)
        for table in _each(tables, work_budget):
            native = _observation(table, units, work_budget)
            if native is None:
                diagnostics.append({'code':'NATIVE_TABLE_REFS_UNAVAILABLE','scope':table['scope']})
                status = 'partial'
                continue
            result = bind_operating_table(native, work_budget=work_budget)
            results.append(result)
            if work_budget.exhausted:
                raise WorkBudgetExceeded('native table binding exhausted caller work')
        if status != 'partial' and results:
            states = {row['status'] for row in results}
            status = next(iter(states)) if states in ({'complete'}, {'unavailable'}) else 'partial'
    except WorkBudgetExceeded:
        status = 'partial'
        diagnostics.append({'code':'WORK_BUDGET_EXCEEDED'})
    return {'status':status,'tables':results,'diagnostics':diagnostics,
            'work_used':work_budget.used-start}
