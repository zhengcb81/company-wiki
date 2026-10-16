"""Parent composition preserves local graphs without rereading native material."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization


def _parent(label):
    raw = (f'<h1>Business {label}</h1><p>We launched a new {label} product '
           'serving international customers.</p>').encode()
    digest = sha256(raw).hexdigest()
    source = 'urn:company-wiki:source:sha256:' + digest
    normal = normalize_document(raw, source_id=source, source_sha256=digest,
                                mime_type='text/html')
    parsed = NarrativeNormalization.language_structure(normal, 'en')
    pipeline = understand_units(parsed.units, source_id=source, source_sha256=digest,
                                mime_type='text/html', work_budget=WorkBudget(2_000_000))
    return parsed, pipeline


@pytest.fixture
def parents():
    return [_parent('Alpha'), _parent('Beta')]


def _compose(parents, budget=None):
    from company_wiki.source_catalog.narrative_parent_composition import compose_parent_pipelines
    return compose_parent_pipelines([p for _, p in parents], [d.source_id for d, _ in parents],
                                    work_budget=budget if budget is not None else WorkBudget(100_000))


def test_real_two_parent_sections_semantics_and_header_closure_survive(parents):
    result = _compose(parents)
    assert len(result['structure']['sections']) == 2
    assert len(result['structure']['semantic_units']) == 2
    assert result['reading_plan']['structure'] is result['structure']
    for parsed, _ in parents:
        head, body = parsed.units
        section = next(s for s in result['structure']['sections'] if body.unit_id in s['body_unit_ids'])
        assert section['heading_unit_ids'] == [head.unit_id]
        assert any(body.unit_id in s['member_unit_ids'] for s in result['structure']['semantic_units'])
        assert not any(u.unit_id in section['body_unit_ids'] for other, _ in parents
                       if other.source_id != parsed.source_id for u in other.units)
    assert result['plan']['section_count'] == 2
    assert result['plan']['semantic_unit_count'] == 2
    assert result['packages']['package_count'] == 2
    from company_wiki.source_catalog.narrative_reading import _prose_reading_packages
    joined = replace(parents[0][0], units=parents[0][0].units + parents[1][0].units)
    packages, _, _, _ = _prose_reading_packages(joined, result)
    for parsed, _ in parents:
        head, body = parsed.units
        package = next(p for p in packages if body.unit_id in p['member_unit_ids'])
        assert head.unit_id in package['required_context_unit_ids']
        assert not any(unit.unit_id in package['required_context_unit_ids']
                       for other, _ in parents if other.source_id != parsed.source_id for unit in other.units)


def test_local_ids_and_every_contractual_reference_share_parent_namespace(parents):
    for _, part in parents:
        section = part['structure']['sections'][0]
        section['parent_id'] = 's0'
        section['parent_section_id'] = 's0'
        part['structure']['sections'].insert(0, {**section, 'section_id': 's0',
                                                'parent_id': None, 'parent_section_id': None})
        part['structure']['diagnostics'] = [{'code': 'TEST', 'section_ids': ['s1'],
                                            'semantic_ids': ['m1'], 'detail': 's1 m1 g1'}]
        part['packages']['diagnostics'] = [{'code': 'TEST', 'package_ids': ['m1']}]
        part['layout_hints']['groups'] = [{'group_id': 'g1', 'parent_table_id': 'g0',
                                          'member_unit_ids': [], 'cells': []},
                                         {'group_id': 'g0', 'parent_table_id': None}]
        part['layout_hints']['relations'] = [{'from_group_id': 'g1', 'to_group_id': 'g0',
                                             'kind': 'header_for'}]
    result = _compose(parents)
    sections = {s['section_id']: s for s in result['structure']['sections']}
    assert len(sections) == 4
    semantics = {s['semantic_id']: s for s in result['structure']['semantic_units']}
    assert len(semantics) == 2
    for package in result['packages']['packages']:
        assert package['package_id'] in semantics
        assert package['section_ids'] == semantics[package['package_id']]['section_ids']
        child = sections[package['section_ids'][0]]
        assert child['parent_id'] in sections
        assert child['parent_section_id'] == child['parent_id']
    groups = {g['group_id']: g for g in result['layout_hints']['groups']}
    assert len(groups) == 4
    for edge in result['layout_hints']['relations']:
        assert groups[edge['from_group_id']]['parent_table_id'] == edge['to_group_id']
    for diagnostic in result['structure']['diagnostics']:
        if diagnostic['code'] == 'TEST':
            assert diagnostic['section_ids'][0] in sections
            assert diagnostic['semantic_ids'][0] in semantics
            assert diagnostic['detail'] == 's1 m1 g1'
    assert all(d['package_ids'][0] in semantics for d in result['packages']['diagnostics']
               if d['code'] == 'TEST')


def test_same_profile_id_different_families_remain_distinct_and_routes_bound(parents):
    for index, (_, part) in enumerate(parents):
        family = ['annual', 'interim'][index]
        part['profile'] = {**part['profile'], 'profile_id': 'shared', 'family': family}
        part['child_profiles'] = {'child': {**part['profile'], 'family': family + '_child'}}
        part['route']['child_routes'] = [{'reading_profile_key': 'child', 'family': family + '_child'}]
        for view in part['reading_plan']['unit_profiles'].values():
            view.update(profile_id='shared', family=family)
        part['reading_plan']['used_profiles'] = [
            {'profile_id': 'shared', 'reading_profile_key': None, 'family': family},
            {'profile_id': 'shared', 'reading_profile_key': 'child', 'family': family + '_child'}]
    result = _compose(parents)
    assert len(result['child_profiles']) == 4
    for key, profile in result['child_profiles'].items():
        assert any(used['reading_profile_key'] == key and used['family'] == profile['family']
                   for used in result['reading_plan']['used_profiles'])
    for view in result['reading_plan']['unit_profiles'].values():
        assert result['child_profiles'][view['reading_profile_key']]['family'] == view['family']
    for route in result['parent_routes'].values():
        assert route['child_routes'][0]['reading_profile_key'] in result['child_profiles']


def test_input_unchanged_native_identity_and_large_metadata_shared(parents):
    before = deepcopy([part for _, part in parents])
    class Opaque:
        def __deepcopy__(self, memo):
            raise AssertionError('must not copy native metadata')
        def __iter__(self):
            raise AssertionError('must not inspect native metadata')
    opaque = Opaque()
    parents[0][1]['observation']['metadata']['large_native'] = opaque
    parents[0][1]['observation']['units'][0]['hints']['words'] = opaque
    result = _compose(parents)
    assert result['observation']['metadata'] is parents[0][1]['observation']['metadata']
    assert result['observation']['units'][0] is parents[0][1]['observation']['units'][0]
    assert result['observation']['units'][0]['hints']['words'] is opaque
    for _, part in parents:
        for package in part['packages']['packages']:
            output = next(p for p in result['packages']['packages']
                          if p['member_unit_ids'] == package['member_unit_ids'])
            assert output['member_unit_ids'] is package['member_unit_ids']
    del parents[0][1]['observation']['metadata']['large_native']
    del parents[0][1]['observation']['units'][0]['hints']['words']
    assert [part for _, part in parents] == before


def test_all_coverages_and_native_signals_aggregated_without_page_identity_loss(parents):
    for index, (_, part) in enumerate(parents):
        for owner in ('observation', 'structure', 'layout_hints'):
            part[owner]['coverage'].update(opaque_pages=[1], complete=False)
        part['structure']['coverage']['deferred_unit_ids'] = [f'deferred-{index}']
        part['structure']['coverage']['excluded_furniture_unit_ids'] = [f'furniture-{index}']
        part['source_signals']['source_form_evidence'] = [{'parent_id': parents[index][0].source_id,
                                                          'value': ['10-K', '10-Q'][index]}]
    result = _compose(parents)
    assert not result['structure']['coverage']['complete']
    assert result['structure']['coverage']['deferred_unit_ids'] == ['deferred-0', 'deferred-1']
    assert result['structure']['coverage']['excluded_furniture_unit_ids'] == ['furniture-0', 'furniture-1']
    assert len(result['structure']['coverage']['parent_coverages']) == 2
    assert len(result['source_signals']['source_form_evidence']) == 2
    assert {r['parent_id'] for r in result['source_signals']['source_form_evidence']} == {p.source_id for p, _ in parents}
    assert result['packages']['coverage'] is result['structure']['coverage']


def test_single_parent_exact_compatibility(parents):
    budget = WorkBudget(10, used=3)
    assert _compose(parents[:1], budget) is parents[0][1]
    assert budget.used >= 3


def test_zero_budget_does_not_even_inspect_inputs():
    from company_wiki.source_catalog.narrative_parent_composition import compose_parent_pipelines
    class Untouchable:
        def __len__(self):
            raise AssertionError('unpaid len')
        def __iter__(self):
            raise AssertionError('unpaid iter')
        def __getitem__(self, key):
            raise AssertionError('unpaid item')
    budget = WorkBudget(0)
    result = compose_parent_pipelines(Untouchable(), Untouchable(), work_budget=budget)
    assert result['analysis_status'] == 'deferred'
    assert not result['structure']['coverage']['complete']
    assert budget.used == 0 and budget.exhausted
    assert 'source_ref' not in result  # no original inspected, no invented parent


def test_known_long_array_reserved_before_iteration_and_no_budget_reset(parents):
    class LongUnread(list):
        def __len__(self):
            return 100_000
        def __iter__(self):
            raise AssertionError('unpaid long array')
    parents[0][1]['structure']['sections'] = LongUnread()
    budget = WorkBudget(200, used=17)
    result = _compose(parents, budget)
    assert result['analysis_status'] == 'deferred'
    assert budget.used >= 17 and budget.exhausted
    assert result['structure']['sections'] == []
    assert result['structure']['coverage']['unobserved_parent_count'] == 2
    assert not result['structure']['coverage']['complete']


def test_bad_lengths_and_duplicate_parent_ids_are_data_errors(parents):
    from company_wiki.source_catalog.narrative_parent_composition import compose_parent_pipelines
    with pytest.raises(ValueError, match='length'):
        compose_parent_pipelines([parents[0][1]], [], work_budget=WorkBudget(100))
    with pytest.raises(ValueError, match='duplicate'):
        compose_parent_pipelines([p for _, p in parents], [parents[0][0].source_id] * 2,
                                 work_budget=WorkBudget(100_000))


def test_native_relations_and_layout_cells_remain_parent_owned_objects(parents):
    for parsed, part in parents:
        head, body = parsed.units
        part['structure']['relations'] = [{'from_unit_ids': [head.unit_id],
                                           'to_unit_ids': [body.unit_id], 'kind': 'header_for'}]
        part['layout_hints']['groups'] = [{'group_id': 'g1', 'parent_table_id': None,
                                          'cells': [{'member_unit_ids': [body.unit_id], 'row': 0,
                                                     'column': None, 'row_span': None, 'column_span': None}]}]
    result = _compose(parents)
    for index, (_, part) in enumerate(parents):
        assert result['structure']['relations'][index] is part['structure']['relations'][0]
        assert result['layout_hints']['groups'][index]['cells'] is part['layout_hints']['groups'][0]['cells']


def test_supplied_namespace_must_be_actual_parent_source(parents):
    from company_wiki.source_catalog.narrative_parent_composition import compose_parent_pipelines
    with pytest.raises(ValueError, match='source'):
        compose_parent_pipelines([p for _, p in parents], ['unrelated', parents[1][0].source_id],
                                 work_budget=WorkBudget(100_000))


def test_partial_parent_never_upgraded_to_complete(parents):
    parents[1][1]['analysis_status'] = 'deferred'
    result = _compose(parents)
    assert result['analysis_status'] == 'deferred'
    assert not result['structure']['coverage']['complete']
    assert result['structure']['coverage']['unobserved_parent_count'] == 1
    assert len(result['structure']['sections']) == 1


def test_actual_reading_entry_keeps_second_parent_structure_and_heading_dependency(parents):
    from company_wiki.source_catalog.narrative_reading import _prose_reading_packages, _understand

    joined = replace(parents[0][0], units=parents[0][0].units + parents[1][0].units)
    result = _understand(joined, title='Company update', kind='unknown',
                         mime_type='text/html', work_budget=WorkBudget(2_000_000))
    packages, _, _, _ = _prose_reading_packages(joined, result)
    assert len(result['structure']['sections']) == 2
    assert len(result['structure']['semantic_units']) == 2
    for parsed, _ in parents:
        head, body = parsed.units
        section = next(section for section in result['structure']['sections']
                       if body.unit_id in section['body_unit_ids'])
        assert section['heading_unit_ids'] == [head.unit_id]
        package = next(package for package in packages if body.unit_id in package['member_unit_ids'])
        assert head.unit_id in package['required_context_unit_ids']
        assert all(unit.source_id == parsed.source_id for unit in joined.units
                   if unit.unit_id in package['member_unit_ids'] + package['required_context_unit_ids'])


def test_actual_reading_entry_borrows_native_metadata_and_reuses_one_budget(parents, monkeypatch):
    from company_wiki.source_catalog import narrative_reading as reading

    class NativeMetadata:
        def __deepcopy__(self, memo):
            raise AssertionError('native metadata must remain owned by its original parent')

    native = NativeMetadata()
    budget = WorkBudget(2_000_000, used=19)
    owner = reading.understand_units
    calls = []

    def observed(*args, **kwargs):
        calls.append(kwargs['work_budget'])
        result = owner(*args, **kwargs)
        result['observation']['metadata']['native_marker'] = native
        return result

    monkeypatch.setattr(reading, 'understand_units', observed)
    joined = replace(parents[0][0], units=parents[0][0].units + parents[1][0].units)
    result = reading._understand(joined, title='Company update', kind='unknown',
                                mime_type='text/html', work_budget=budget)
    assert calls == [budget, budget]
    assert 19 < budget.used < budget.max_work_units
    assert result['observation']['metadata']['native_marker'] is native
    assert all(metadata['native_marker'] is native for metadata in result['parent_metadata'].values())
