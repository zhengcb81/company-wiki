"""Thin native-table observation composition over the existing DU4 binder.

No IO, geometry inference, numeric extraction, budget creation or persistence.
Whole original cell owners remain whole; inline fragment refs are provenance,
not instructions to distribute values across a merged cell's columns.
"""
from collections.abc import Mapping
from typing import Any

from .layout_hints.contract import WorkBudget, WorkBudgetExceeded
from .table_measurements import bind_operating_table

NATIVE_TABLE_BRIDGE_VERSION = '2.1.1'


def _each(values, budget):
    for index in range(len(values)):
        budget.charge()
        yield values[index]


def _eligible_cells(table, eligible, budget):
    """Retain admitted native rows and their actual header dependencies only."""
    if eligible is None:
        return table
    active_rows = set()
    needed_refs = set()
    active_groups = set()
    header_rows = set(_each(table['header_rows'], budget))
    for cell in _each(table['cells'], budget):
        if any(ref['unit_id'] in eligible for ref in _each(cell['text_refs'], budget)):
            active_rows.add(cell['row'])
            active_groups.add(cell.get('row_group'))
            needed_refs.update(_each(cell.get('headers', ()), budget))
            for ref in _each(cell.get('header_refs', ()), budget):
                needed_refs.add(ref['unit_id'])
    keep = []
    for cell in _each(table['cells'], budget):
        if (cell['row'] in active_rows or cell['row'] in header_rows
                or cell.get('html_id') in needed_refs
                or any(ref['unit_id'] in needed_refs for ref in _each(cell['text_refs'], budget))
                or (cell.get('is_header') and cell.get('header_scope') in {'col', 'colgroup'})
                or (cell.get('is_header') and cell.get('header_scope') == 'rowgroup'
                    and cell.get('row_group') in active_groups)):
            keep.append(cell)
    projected = {**table, 'cells': keep}
    if table.get('provenance') is not None:
        # PDF observations are sent directly to the strict DU4 binder. A row
        # view must close *all* cell references, not only trim its cell list.
        # HTML rebuilds these records later; preserve that same ownership here.
        retained = {cell['cell_id'] for cell in _each(keep, budget)}
        removed = {cell['cell_id'] for cell in _each(table['cells'], budget)} - retained
        projected['provenance'] = [record for record in _each(table['provenance'], budget)
                                   if not isinstance(record, Mapping) or record.get('cell_id') not in removed]
    return projected


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


def bind_native_tables(observation: Mapping[str, Any], *, work_budget: WorkBudget,
                       layout_hints: Mapping[str, Any] | None = None,
                       eligible_unit_ids: set[str] | None = None) -> dict:
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
            if eligible_unit_ids is not None and not any(
                ref['unit_id'] in eligible_unit_ids for cell in _each(table['cells'], work_budget)
                for ref in _each(cell['text_refs'], work_budget)):
                continue
            native = _observation(_eligible_cells(table, eligible_unit_ids, work_budget), units, work_budget)
            if native is None:
                diagnostics.append({'code':'NATIVE_TABLE_REFS_UNAVAILABLE','scope':table['scope']})
                status = 'partial'
                continue
            result = bind_operating_table(native, work_budget=work_budget)
            results.append(result)
            if work_budget.exhausted:
                raise WorkBudgetExceeded('native table binding exhausted caller work')
        # The format owner projects observed fine slots; both formats use the
        # same measurement binder and caller budget. No second PDF parse.
        from company_wiki.document_normalization.pdf_table_observations import build_pdf_table_observations

        pdf = (build_pdf_table_observations(observation, layout_hints, work_budget=work_budget)
               if eligible_unit_ids is None or eligible_unit_ids else
               {'tables': [], 'diagnostics': [], 'status': 'unavailable'})
        diagnostics.extend(pdf['diagnostics'])
        for table in _each(pdf['tables'], work_budget):
            if eligible_unit_ids is not None:
                work_budget.charge(len(table['units']))
                if not eligible_unit_ids.intersection(table['units']):
                    continue
            results.append(bind_operating_table(_eligible_cells(table, eligible_unit_ids, work_budget),
                                               work_budget=work_budget))
            if work_budget.exhausted:
                raise WorkBudgetExceeded('PDF table binding exhausted caller work')
        if pdf['status'] == 'partial' and (pdf['tables'] or work_budget.exhausted):
            status = 'partial'
        if status != 'partial' and results:
            states = {row['status'] for row in results}
            status = next(iter(states)) if states in ({'complete'}, {'unavailable'}) else 'partial'
    except WorkBudgetExceeded:
        status = 'partial'
        diagnostics.append({'code':'WORK_BUDGET_EXCEEDED'})
    return {'status':status,'tables':results,'diagnostics':diagnostics,
            'work_used':work_budget.used-start}


def close_native_table_dependencies(packages: Mapping[str, Any], bindings: Mapping[str, Any],
                                    *, work_budget: WorkBudget) -> dict[str, Any]:
    """Carry exact bound labels with their value's existing reading package.

    A text ref never invents a new unit. Whole row owners remain body material,
    even when label and value offsets share that owner. The binder has already
    checked parent/page scope; ambiguous measurements stay diagnostic.
    """
    work_budget.charge()
    by_value: dict[str, list[tuple[Mapping[str, Any], str]]] = {}
    for table in _each(bindings.get('tables', ()), work_budget):
        for measurement in _each(table['measurements'], work_budget):
            by_value.setdefault(measurement['value_ref']['unit_id'], []).append(
                (measurement, table.get('status', 'unavailable')))
    rows = []
    for package in _each(packages['packages'], work_budget):
        if package['kind'] != 'operating_table':
            rows.append(package)
            continue
        required = set(package.get('required_context_unit_ids', ()))
        members = list(package['member_unit_ids'])
        body = set(members) - required
        matched: list[tuple[Mapping[str, Any], str]] = []
        for uid in _each(members, work_budget):
            if uid not in body:
                continue
            matched.extend(by_value.get(uid, ()))
        statuses = set()
        for measurement, source_status in _each(matched, work_budget):
            statuses.add(measurement['binding_status'])
            if source_status != 'complete':
                statuses.add('source_incomplete')
            if not measurement['row_label_refs']:
                statuses.add('row_label_unknown')
            if measurement['binding_status'] != 'bound':
                continue
            refs = []
            for name in ('row_label_refs', 'unit_refs', 'scope_refs', 'qualifier_refs'):
                refs.extend(_each(measurement[name], work_budget))
            period = measurement.get('period')
            if period is not None:
                refs.extend(_each(period['raw_label_refs'], work_budget))
            for ref in _each(refs, work_budget):
                if ref['unit_id'] not in body:
                    required.add(ref['unit_id'])
        extra = required - set(members)
        work_budget.charge(len(extra))
        rows.append({**package, 'member_unit_ids': members + sorted(extra),
                     'required_context_unit_ids': sorted(required),
                     'table_binding_status': ('complete' if statuses == {'bound'} else
                                              'partial' if matched else 'unavailable')})
    return {**packages, 'packages': rows}
