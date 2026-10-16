"""Public producer seams: runtime policy and final source-bound summary."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

from company_wiki.document_normalization import normalize_document, replay_unit, NormalizationLimits
from company_wiki.document_understanding import understand_units
from company_wiki.document_understanding.summary_input import build_summary_input


def _parsed():
    raw = """<html lang="zh"><h1>2025年年度报告</h1>
    <p>公司代码：688099</p><h2>第三节 管理层讨论与分析</h2>
    <h3>报告期内公司从事的主要业务</h3><p>公司主营业务为仪器制造。</p>
    <h3>海外市场进展</h3><p>海外市场已签约新渠道，但销售尚未开始。</p></html>""".encode()
    doc = normalize_document(raw, source_id='source-test', source_sha256=sha256(raw).hexdigest(),
                             mime_type='text/html')
    result = understand_units(doc.units, source_id=doc.source_id, source_sha256=doc.source_sha256,
                              title='2025年年度报告', mime_type='text/html', language='zh', declared_kind='annual_report',
                              metadata={'regime': 'cn_exchange'})
    return raw, doc, result


def test_actual_pipeline_consumes_catalog_not_just_route():
    units = [SimpleNamespace(unit_id=str(i), raw_text=text, unit_kind='pdf_text_block',
                             metadata={'source_locator': 'original:' + str(i)},
                             source_role='company_filing', language='zh',
                             coordinates=SimpleNamespace(page_number=page, table_index=None,
                                                         row_index=None, column_index=None))
             for i, (page, text) in enumerate([(1, '2025 年年度报告'), (1, '公司代码：688099'),
                 (9, '第三节 管理层讨论与分析'), (10, '主要会计数据和财务指标'),
                 (11, '报告期内公司从事的主要业务')])]
    result = understand_units(units, source_id='s', source_sha256='d', declared_kind='annual_report',
                              language='zh', metadata={'regime': 'cn_exchange'})
    assert result['route']['profile_id'] == 'cn_annual'
    assert any(c['id'] == 'cn_annual_report' for c in result['profile'].get('policy_components', ()))
    assert result['profile']['reading_questions']
    assert result['route']['profile_version'] == result['profile']['profile_version']


def test_final_original_material_selects_business_questions_and_replays():
    raw, doc, result = _parsed()
    request = build_summary_input(result)
    facets = {f['id']: f for f in request.get('business_facets', ())}
    assert 'facet_overseas' in facets
    assert facets['facet_overseas']['selection_basis']
    assert any(c['required_when'] == 'quantity_emitted' for c in facets['facet_overseas']['required_context'])
    assert request['reading_policy_version']
    source = {unit.unit_id: unit for unit in doc.units}
    members = [member for pkg in request['evidence_packages'] for member in pkg['members']]
    assert members
    for member in members:
        assert replay_unit(raw, source_sha256=doc.source_sha256,
                           unit=source[member['unit_id']], limits=NormalizationLimits()) == member['text']
    assert any('销售尚未开始' in m['text'] for m in members)


def test_withheld_text_cannot_select_a_business_facet():
    _, _, result = _parsed()
    request = build_summary_input(result, max_chars=0)
    assert not request['evidence_packages']
    assert request.get('business_facets') == []
    assert request.get('reading_policies') == []


def _version_case():
    return {'observation': {'units': [
        {'unit_id': 'a', 'text': 'Product launch remains a plan.', 'locator': 'original:a'},
        {'unit_id': 'b', 'text': 'Shareholder administrative notice.', 'locator': 'original:b'}]},
        'reading_plan': {'unit_profiles': {
            'a': {'profile_id': 'one', 'profile_version': 'one/v1', 'family': 'presentation',
                  'summary_focus': 'distinguish plan from completed', 'policy_components': []},
            'b': {'profile_id': 'two', 'profile_version': 'two/v1', 'family': 'administrative',
                  'summary_focus': 'administrative only', 'policy_components': []}}},
        'packages': {'packages': [{'package_id': 'a', 'member_unit_ids': ['a'],
                                 'required_context_unit_ids': []}]}}


def test_policy_fingerprint_ignores_unsent_configuration():
    original = _version_case()
    before = build_summary_input(original)
    unused = deepcopy(original)
    unused['reading_plan']['unit_profiles']['b']['profile_version'] = 'two/v999'
    assert build_summary_input(unused).get('reading_policy_version') == before.get('reading_policy_version')
    assert before.get('reading_policy_version')


def test_policy_fingerprint_changes_with_used_configuration():
    original = _version_case()
    before = build_summary_input(original)
    original['reading_plan']['unit_profiles']['a']['summary_focus'] = 'preserve stage and denial'
    after = build_summary_input(original)
    assert after.get('reading_policy_version') != before.get('reading_policy_version')


def test_same_profile_children_are_resolved_only_from_each_read_range(monkeypatch):
    from company_wiki.document_understanding import profiles
    from company_wiki.document_understanding.observation_adapter import build_observation
    units = [SimpleNamespace(unit_id=uid, raw_text=text, unit_kind='pdf_text_block',
                              source_role='company_filing', language='en',
                              metadata={'source_locator': 'original:' + uid},
                              coordinates=SimpleNamespace(page_number=1, table_index=None,
                                                          row_index=None, column_index=None))
             for uid, text in [('one', 'scope one'), ('two', 'scope two'), ('out', 'outside')]]
    observation = build_observation(units, source_id='s', source_sha256='d')
    route = profiles.route_document(observation)
    route['child_routes'] = [{'profile_id': 'investor_qa', 'unit_ids': [uid], 'reason': 'IN_DOCUMENT_QA_RANGE'}
                             for uid in ('one', 'two')]
    seen = []

    def resolve(profile, obs, actual_route, *, limits=None):
        # The combination owner now reuses the actual prepared Observation;
        # child mappings remain compatible. Keep the same scope assertions.
        from company_wiki.document_understanding.profiles.observation import Observation
        ids = obs.unit_ids if isinstance(obs, Observation) else tuple(u['unit_id'] for u in obs['units'])
        seen.append(ids)
        value = dict(profile)
        value['profile_version'] = '/'.join(ids)
        return value

    monkeypatch.setattr(profiles, 'route_document', lambda obs, **kwargs: deepcopy(route))
    monkeypatch.setattr(profiles, 'resolve_reading_profile', resolve, raising=False)
    result = understand_units(units, source_id='s', source_sha256='d')
    assert ('one',) in seen and ('two',) in seen
    chosen = result['reading_plan']['unit_profiles']
    assert chosen['one']['profile_version'] == 'one'
    assert chosen['two']['profile_version'] == 'two'
    assert chosen['out']['profile_version'] == 'one/two/out'


def test_html_frontend_carries_actual_dom_levels_without_changing_identity():
    from company_wiki.document_normalization.units import verify_unit_identity
    raw = b'<h1>Annual report</h1><h2>Business</h2><h3>Overview</h3><h3>Risks</h3>'
    doc = normalize_document(raw, source_id='html-test', source_sha256=sha256(raw).hexdigest(),
                             mime_type='text/html')
    headings = [unit for unit in doc.units if unit.unit_kind == 'html_heading']
    assert [unit.metadata.get('heading_level') for unit in headings] == [1, 2, 3, 3]
    assert [unit.metadata.get('tag_name') for unit in headings] == ['h1', 'h2', 'h3', 'h3']
    assert all(unit.coordinates.page_number is None for unit in headings)
    for unit in doc.units:
        assert unit.parser_version == '1.0.0'
        verify_unit_identity(unit, format_name='html')
        assert replay_unit(raw, source_sha256=doc.source_sha256, unit=unit,
                           limits=NormalizationLimits()) == unit.raw_text


def test_top_instructions_use_only_final_sent_child_policy():
    original = _version_case()
    original['profile'] = {'profile_id': 'unused-parent', 'summary_focus': 'unused parent focus',
                           'negative_hints': ['unused parent instructions'], 'semantic_units': ['project']}
    actual = original['reading_plan']['unit_profiles']['a']
    actual.update(negative_hints=['keep stage qualifiers'], semantic_units=['paragraph_event'])
    request = build_summary_input(original)
    assert request['focus'] == actual['summary_focus']
    assert request['negative_hints'] == actual['negative_hints']
    assert request['prefer_semantic_units'] == actual['semantic_units']
    assert 'unused parent' not in str(request)
    original['profile']['summary_focus'] = 'other unused instruction'
    assert build_summary_input(original) == request
    actual['negative_hints'] = ['changed used qualifier instruction']
    assert build_summary_input(original)['reading_policy_version'] != request['reading_policy_version']


def test_confusion_checks_are_instructions_without_example_facts():
    case = _version_case()
    case['observation']['units'][0]['text'] = '公司在海外注册子公司，但销售尚未开始。'
    request = build_summary_input(case)
    facet = next(f for f in request['business_facets'] if f['id'] == 'facet_overseas')
    assert any('注册' in c['risk'] and '不等于' in c['risk'] for c in facet.get('confusion_checks', ()))
    assert facet['applicable_mechanisms']
    assert all(set(c) == {'risk', 'required_context_slots'} for c in facet['confusion_checks'])
    assert 'source_meaning' not in str(facet) and 'wrong_assertion' not in str(facet)
    assert '3,118' not in str(facet)


def _layout_dependency_case():
    from company_wiki.document_understanding.layout_bridge import bind_layout_context
    from company_wiki.document_understanding.orchestration import build_dependency_packages
    source = {'source_id': 's', 'source_sha256': 'd'}
    structure = {'source_ref': source, 'sections': [{'section_id': 's1', 'section_role': 'operating_metrics',
        'heading_unit_ids': [], 'body_unit_ids': ['row', 'cap', 'hdr', 'note']}], 'coverage': {'complete': True},
        'semantic_units': [
            {'semantic_id': 'row-sem', 'kind': 'operating_table', 'member_unit_ids': ['row'],
             'anchor_unit_ids': ['row'], 'required_context_unit_ids': [], 'section_ids': ['s1'], 'completeness': 'complete'},
            {'semantic_id': 'header-sem', 'kind': 'background', 'member_unit_ids': ['hdr'],
             'anchor_unit_ids': ['hdr'], 'required_context_unit_ids': ['note'], 'section_ids': ['s1'], 'completeness': 'complete'}]}
    layout = {'source_ref': source, 'coverage': {'complete': True}, 'groups': [
        {'group_id': 'table-row', 'kind': 'table_row', 'member_unit_ids': ['row'],
         'required_context_unit_ids': ['cap', 'hdr']}]}
    bound = bind_layout_context(structure, layout)
    packages = build_dependency_packages(bound)
    return {'source_ref': source, 'structure': bound, 'packages': packages, 'observation': {'units': [
        {'unit_id': uid, 'locator': 'original:' + uid, 'text': text, 'kind': kind}
        for uid, kind, text in [('row', 'table_row', 'Overseas stores: 20'),
            ('cap', 'table_caption', 'Stores at year end'), ('hdr', 'table_header', 'Region | count'),
            ('note', 'footnote', 'Franchised stores are excluded.')]]}}


def test_layout_required_context_is_really_sent_with_transitive_originals():
    case = _layout_dependency_case()
    request = build_summary_input(case, selected_unit_ids=['row'], max_packages=1)
    members = [m for p in request['evidence_packages'] for m in p['members']]
    assert {m['unit_id'] for m in members} == {'row', 'cap', 'hdr', 'note'}
    original = {u['unit_id']: u for u in case['observation']['units']}
    assert all(m['locator'] == original[m['unit_id']]['locator']
               and m['text'] == original[m['unit_id']]['text'] for m in members)
    assert request['budget']['chars_used'] == sum(len(m['text']) for m in members)


def test_restored_context_cannot_bypass_character_or_context_budgets():
    case = _layout_dependency_case()
    for kwargs in ({'max_chars': 22}, {'max_context_units': 0}):
        request = build_summary_input(case, selected_unit_ids=['row'], max_packages=1, **kwargs)
        assert not request['evidence_packages']
        assert request['deferred']
