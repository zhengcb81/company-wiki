"""Compose already analysed originals without copying or inventing source material.

Local graph identifiers belong to one immutable parent. Native unit IDs, text,
locators, fine arrays and policy material retain their existing owners. The
first source_ref/route/profile are compatibility views, not a synthetic source;
parent_routes and parent_coverages preserve each original's actual decisions.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded

_LOCAL_IDS = ('section_id', 'parent_section_id', 'semantic_id', 'package_id',
              'group_id', 'parent_table_id', 'from_group_id', 'to_group_id')
_LOCAL_LISTS = ('section_ids', 'semantic_ids', 'package_ids', 'group_ids')
_COVERAGE_LISTS = ('unassigned_unit_ids', 'deferred_unit_ids', 'excluded_furniture_unit_ids',
                   'opaque_pages', 'deferred_pages')
_COVERAGE_COUNTS = ('structured_unit_count', 'processed_unit_count', 'source_unit_count',
                    'unobserved_unit_count')


class _Composer:
    def __init__(self, budget: WorkBudget):
        self.budget = budget

    def rows(self, value):
        # All existing contracts expose sized arrays/maps. Reserve before any
        # traversal; opaque native values are never passed through this helper.
        self.budget.charge(1 + len(value))
        return value

    def shell(self, value):
        return dict(self.rows(value))

    def local(self, parent, value):
        return parent + ':' + str(value) if value is not None else None

    def reading_key(self, parent, value):
        return parent + '|' + str(value or 'root')

    def ids(self, row, parent, *, section=False):
        result = self.shell(row)
        for name in _LOCAL_IDS + (('parent_id',) if section else ()):
            if name in row:
                result[name] = self.local(parent, row[name])
        for name in _LOCAL_LISTS:
            if name in row:
                result[name] = [self.local(parent, item) for item in self.rows(row[name])]
        # Diagnostics can contain contracted IDs, whereas detail/basis and
        # semantic-kind strings must remain literal and are never searched.
        if 'diagnostics' in row:
            result['diagnostics'] = [self.ids(item, parent) if isinstance(item, Mapping) else item
                                     for item in self.rows(row['diagnostics'])]
        return result

    def coverage(self, owners):
        result: dict[str, Any] = {}
        parent_coverages = {}
        scans = []
        complete = True
        for parent, owner in self.rows(owners):
            self.budget.charge()
            coverage = owner.get('coverage', {})
            if not result:
                result = self.shell(coverage)
                for key in _COVERAGE_LISTS:
                    if key in result:
                        result[key] = []
                for key in _COVERAGE_COUNTS:
                    if key in result:
                        result[key] = 0
            parent_coverages[parent] = coverage
            complete = complete and bool(coverage.get('complete', coverage.get('native_scan') == 'complete'))
            scans.append(coverage.get('native_scan', 'unavailable'))
            for key in _COVERAGE_LISTS:
                if key in coverage:
                    result.setdefault(key, []).extend(self.rows(coverage[key]))
            for key in _COVERAGE_COUNTS:
                if key in coverage:
                    result[key] = result.get(key, 0) + coverage[key]
        result['parent_coverages'] = parent_coverages
        result['complete'] = complete
        if any('native_scan' in coverage for coverage in parent_coverages.values()):
            result['native_scan'] = ('complete' if all(scan == 'complete' for scan in scans)
                                     else 'unavailable' if all(scan == 'unavailable' for scan in scans)
                                     else 'partial')
        return result

    def part(self, part, parent):
        """Prepare one atomic overlay; no partially bound graph is committed."""
        observation = self.shell(part['observation'])
        # Native units and their fine evidence are borrowed, not copied/walked.
        self.rows(observation['units'])
        structure = self.shell(part['structure'])
        structure['sections'] = [self.ids(row, parent, section=True)
                                  for row in self.rows(structure.get('sections', ()))]
        structure['semantic_units'] = [self.ids(row, parent)
                                        for row in self.rows(structure.get('semantic_units', ()))]
        self.rows(structure.get('relations', ()))  # endpoints are source-bound unit IDs
        structure['diagnostics'] = [self.ids(row, parent)
                                     for row in self.rows(structure.get('diagnostics', ()))]
        packages = self.shell(part['packages'])
        packages['packages'] = [self.ids(row, parent) for row in self.rows(packages.get('packages', ()))]
        packages['diagnostics'] = [self.ids(row, parent)
                                    for row in self.rows(packages.get('diagnostics', ()))]
        reading = self.shell(part['reading_plan'])
        reading['unit_profiles'] = {
            uid: {**self.shell(view), 'reading_profile_key': self.reading_key(parent, view.get('reading_profile_key'))}
            for uid, view in self.rows(reading.get('unit_profiles', {})).items()}
        reading['used_profiles'] = [
            {**self.shell(view), 'reading_profile_key': self.reading_key(parent, view.get('reading_profile_key'))}
            for view in self.rows(reading.get('used_profiles', ()))]
        reading['diagnostics'] = [self.ids(row, parent)
                                   for row in self.rows(reading.get('diagnostics', ()))]
        self.rows(reading.get('policy_components', ()))
        layout = self.shell(part.get('layout_hints') or {})
        layout['groups'] = [self.ids(row, parent) for row in self.rows(layout.get('groups', ()))]
        layout['relations'] = [self.ids(row, parent) for row in self.rows(layout.get('relations', ()))]
        layout['diagnostics'] = [self.ids(row, parent) for row in self.rows(layout.get('diagnostics', ()))]
        self.rows(layout.get('unit_hints', ()))
        self.rows(layout.get('reading_order', ()))
        route = self.shell(part['route'])
        if 'child_routes' in route:
            route['child_routes'] = [
                {**self.shell(child), 'reading_profile_key': self.reading_key(parent, child.get('reading_profile_key'))}
                for child in self.rows(route['child_routes'])]
        profiles = {self.reading_key(parent, None): part['profile']}
        profiles.update({self.reading_key(parent, key): profile
                         for key, profile in self.rows(part.get('child_profiles', {})).items()})
        diagnostics = [self.ids(row, parent) for row in self.rows(part.get('diagnostics', ()))]
        self.rows(part.get('non_selectable_unit_ids', ()))
        signals = self.shell(part.get('source_signals') or {})
        for key in ('source_form_evidence', 'turn_evidence', 'reserved_unit_ids', 'diagnostics'):
            self.rows(signals.get(key, ()))
        self.rows(signals.get('observed_counts', {}))
        return {'observation': observation, 'structure': structure, 'packages': packages,
                'reading_plan': reading, 'layout_hints': layout, 'route': route,
                'child_profiles': profiles, 'diagnostics': diagnostics, 'source_signals': signals,
                'non_selectable_unit_ids': part.get('non_selectable_unit_ids', ()),
                'plan': part.get('plan', {}), 'original': part}

    def combine(self, prepared):
        first = prepared[0][1]
        output = self.shell(first['original'])
        output['parent_routes'] = {parent: part['route'] for parent, part in self.rows(prepared)}
        output['parent_source_refs'] = [part['observation']['source_ref'] for _, part in self.rows(prepared)]
        output['parent_metadata'] = {parent: part['observation'].get('metadata')
                                     for parent, part in self.rows(prepared)}
        output['route'] = first['route']
        for owner, names in (
            ('observation', ('units',)),
            ('structure', ('sections', 'semantic_units', 'relations', 'diagnostics')),
            ('packages', ('packages', 'diagnostics')),
            ('reading_plan', ('used_profiles', 'policy_components', 'diagnostics')),
            ('layout_hints', ('unit_hints', 'groups', 'relations', 'reading_order', 'diagnostics')),
        ):
            shell = self.shell(first[owner])
            for name in names:
                combined = []
                for _, part in self.rows(prepared):
                    combined.extend(self.rows(part[owner].get(name, ())))
                shell[name] = combined
            if owner in {'observation', 'structure', 'layout_hints'}:
                shell['coverage'] = self.coverage([(parent, part[owner]) for parent, part in self.rows(prepared)])
            output[owner] = shell
        output['child_profiles'] = {}
        output['reading_plan']['unit_profiles'] = {}
        output['non_selectable_unit_ids'] = []
        output['diagnostics'] = []
        for _, part in self.rows(prepared):
            output['child_profiles'].update(self.rows(part['child_profiles']))
            output['reading_plan']['unit_profiles'].update(self.rows(part['reading_plan']['unit_profiles']))
            output['non_selectable_unit_ids'].extend(self.rows(part['non_selectable_unit_ids']))
            output['diagnostics'].extend(self.rows(part['diagnostics']))
        output['reading_plan']['structure'] = output['structure']
        output['packages']['coverage'] = output['structure']['coverage']
        output['packages']['non_selectable_unit_ids'] = output['non_selectable_unit_ids']
        output['packages']['package_count'] = len(output['packages']['packages'])
        signals = self.shell(first['source_signals'])
        for key in ('source_form_evidence', 'turn_evidence', 'reserved_unit_ids', 'diagnostics'):
            signals[key] = [row for _, part in self.rows(prepared)
                            for row in self.rows(part['source_signals'].get(key, ()))]
        counts: dict[str, int] = {}
        for _, part in self.rows(prepared):
            for key, count in self.rows(part['source_signals'].get('observed_counts', {})).items():
                counts[key] = counts.get(key, 0) + count
        signals['observed_counts'] = counts
        statuses = [part['source_signals'].get('status', 'unavailable') for _, part in self.rows(prepared)]
        signals['status'] = ('complete' if all(s == 'complete' for s in statuses)
                             else 'unavailable' if all(s == 'unavailable' for s in statuses) else 'partial')
        signals['work_used'] = sum(part['source_signals'].get('work_used', 0) for _, part in self.rows(prepared))
        output['source_signals'] = signals
        bindings = [part['original'].get('table_bindings', {}) for _, part in self.rows(prepared)]
        states = {binding.get('status', 'unavailable') for binding in self.rows(bindings)}
        output['table_bindings'] = {
            'status': next(iter(states)) if len(states) == 1 else 'partial',
            'tables': [table for binding in self.rows(bindings)
                       for table in self.rows(binding.get('tables', ()))],
            'diagnostics': [diagnostic for binding in self.rows(bindings)
                            for diagnostic in self.rows(binding.get('diagnostics', ()))],
            'work_used': sum(binding.get('work_used', 0) for binding in self.rows(bindings)),
        }
        plan = self.shell(first['plan'])
        plan.update(section_count=len(output['structure']['sections']),
                    semantic_unit_count=len(output['structure']['semantic_units']),
                    package_count=output['packages']['package_count'])
        expectations = [part['plan'].get('expects_business_narrative') for _, part in self.rows(prepared)]
        plan['expects_business_narrative'] = (True if any(v is True for v in expectations)
                                             else False if all(v is False for v in expectations) else None)
        plan['read_first_roles'] = list(dict.fromkeys(role for _, part in self.rows(prepared)
                                                    for role in self.rows(part['plan'].get('read_first_roles', ()))))
        output['plan'] = plan
        return output


def _deferred(budget, count=None, prepared_count=0):
    coverage = {'complete': False, 'unobserved_ids_limited': True}
    if count is not None:
        coverage['unobserved_parent_count'] = count - prepared_count
        coverage['prepared_parent_count'] = prepared_count
        coverage['uncomposed_parent_count'] = count
    return {'schema_version': 'du-pipeline/1', 'analysis_status': 'deferred',
            'observation': {'units': [], 'coverage': coverage},
            'structure': {'sections': [], 'semantic_units': [], 'relations': [], 'coverage': coverage},
            'diagnostics': [{'code': 'WORK_BUDGET_EXCEEDED', 'unit_ids': [],
                             'detail': 'parent composition deferred; unread originals are unknown, not absent'}],
            'work': {'used': budget.used, 'limit': budget.max_work_units, 'exhausted': budget.exhausted}}


def compose_parent_pipelines(parts: Sequence[Mapping[str, Any]], parent_ids: Sequence[str],
                             *, work_budget: WorkBudget) -> dict[str, Any]:
    """Compose finite existing pipeline views using the caller's shared budget.

    A single parent is the original result, byte/identity compatible. A failed
    reservation never walks a long array or fabricates unknown tail IDs. Work
    interrupted before a complete combined graph discards that graph safely.
    """
    total = None
    prepared = []
    engine = _Composer(work_budget)
    try:
        work_budget.charge()
        total = len(parts)
        if total != len(parent_ids):
            raise ValueError('parts/parent_ids length mismatch')
        if total == 0:
            raise ValueError('at least one parent is required')
        if total == 1:
            work_budget.charge()
            return parts[0]  # type: ignore[return-value]
        seen = set()
        interrupted = False
        for index in range(total):
            work_budget.charge()
            parent = parent_ids[index]
            if not isinstance(parent, str) or not parent:
                raise ValueError('parent ID must be a nonempty string')
            if parent in seen:
                raise ValueError('duplicate parent ID')
            seen.add(parent)
            part = parts[index]
            if part.get('source_ref', {}).get('source_id') != parent:
                raise ValueError('parent namespace must match actual source_ref.source_id')
            if part.get('analysis_status') == 'deferred':
                interrupted = True
                break
            prepared.append((parent, engine.part(part, parent)))
        if not prepared:
            return _deferred(work_budget, total)
        result = engine.combine(prepared)
        if interrupted:
            result['analysis_status'] = 'deferred'
            for owner in ('observation', 'structure', 'layout_hints'):
                result[owner]['coverage']['complete'] = False
                result[owner]['coverage']['unobserved_parent_count'] = total - len(prepared)
                result[owner]['coverage']['unobserved_ids_limited'] = True
            result['diagnostics'].append({'code': 'PARENT_ANALYSIS_DEFERRED', 'unit_ids': [],
                                          'detail': 'unexamined parent tail is unknown'})
        work_budget.charge()
        result['work'] = {**result.get('work', {}), 'used': work_budget.used,
                          'limit': work_budget.max_work_units, 'exhausted': work_budget.exhausted,
                          'source_unit_count': len(result['observation']['units']),
                          'scope': 'native_signals_layout_structure_strategy_and_parent_composition'}
        return result
    except WorkBudgetExceeded:
        # Do not spend an exhausted budget constructing a plausible prefix graph.
        # Source preparation can still reuse originals; enhancement is deferred.
        return _deferred(work_budget, total, len(prepared))
