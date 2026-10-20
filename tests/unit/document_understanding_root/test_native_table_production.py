"""Native table bindings must travel through the real reading pipeline."""
from dataclasses import replace
from hashlib import sha256

import pymupdf as fitz
import pytest

from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_catalog.narrative_reading import _understand


def _html(year=2025, value=18, *, observed_headers=True):
    raw = (f'<h1>Operating capacity</h1><table><thead><tr>'
           f'<th>Capacity (units)</th><th>As of December 31, {year}</th></tr></thead>'
           f'<tbody><tr><th scope="row">Overseas plants</th><td>{value}</td></tr>'
           '</tbody></table>').encode()
    if not observed_headers:
        raw = (raw.replace(b'<th>', b'<td>').replace(b'<th scope="row">', b'<td>')
               .replace(b'</th>', b'</td>').replace(b'<thead>', b'<tbody>')
               .replace(b'</thead>', b'</tbody>'))
    digest = sha256(raw).hexdigest()
    normalized = normalize_document(raw, source_id='urn:company-wiki:source:sha256:' + digest,
                                    source_sha256=digest, mime_type='text/html')
    return NarrativeNormalization.language_structure(normalized, 'en')


def _read(parsed):
    return _understand(parsed, title='Operating capacity update', kind='unknown',
                       mime_type=parsed.mime_type, work_budget=WorkBudget(2_000_000))


def _text(parsed, ref):
    return next(unit.raw_text for unit in parsed.units if unit.unit_id == ref['unit_id'])[
        ref['char_start']:ref['char_end']]


def test_actual_html_pipeline_exposes_same_native_value_period_and_row_label():
    parsed = _html()
    result = _read(parsed)
    table, = result['table_bindings']['tables']
    value = next(item for item in table['measurements'] if _text(parsed, item['value_ref']) == '18')
    assert value['binding_status'] == 'bound'
    assert value['period']['end'] == '2025-12-31'
    assert [_text(parsed, ref) for ref in value['row_label_refs']] == ['Overseas plants']
    uid = value['value_ref']['unit_id']
    package = next(p for p in result['packages']['packages'] if uid in p['member_unit_ids'])
    # The complete row is already an atomic body. Its row label need not be
    # relabelled as external context to remain a required selected dependency.
    required = set(package['required_context_unit_ids']) | set(package['member_unit_ids'])
    refs = value['row_label_refs'] + value['unit_refs'] + value['period']['raw_label_refs']
    assert {ref['unit_id'] for ref in refs} <= required


def test_actual_multi_parent_pipeline_retains_independent_table_bindings():
    first, second = _html(), _html(2026, 24)
    parsed = replace(first, units=first.units + second.units)
    result = _read(parsed)
    tables = result['table_bindings']['tables']
    assert len(tables) == 2
    assert {table['scope']['parent_id'] for table in tables} == {first.source_id, second.source_id}
    for table in tables:
        assert all(next(u for u in parsed.units if u.unit_id == item['value_ref']['unit_id']).source_id
                   == table['scope']['parent_id'] for item in table['measurements'])


def test_real_pdf_parser_fine_cells_reach_existing_binder_through_pipeline():
    from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes

    with fitz.open() as document:
        page = document.new_page(width=600, height=400)
        page.insert_text((50, 45), 'Operating capacity (units)')
        for y in (65, 95, 125):
            page.draw_line((50, y), (550, y))
        for x in (50, 290, 550):
            page.draw_line((x, 65), (x, 125))
        page.insert_text((55, 85), 'Capacity (units)')
        page.insert_text((295, 85), 'As of December 31, 2025')
        page.insert_text((55, 115), 'Overseas plants')
        page.insert_text((295, 115), '18')
        raw = document.tobytes()
    digest = sha256(raw).hexdigest()
    parsed = parse_pdf_bytes(raw, source_id='urn:company-wiki:source:sha256:' + digest,
                             source_sha256=digest, language='en', full_table_scan=True,
                             selector_version='0.9.0')
    assert any(unit.metadata.get('reading_layout', {}).get('upstream_hints', {}).get('cells')
               for unit in parsed.units)
    result = _read(parsed)
    tables = result['table_bindings']['tables']
    assert tables
    values = [item for table in tables for item in table['measurements']]
    assert any(_text(parsed, item['value_ref']) == '18' for item in values)
    # PDF's unobserved row role/span remains unknown, never copied from HTML.
    assert all(ref['unit_id'] in {unit.unit_id for unit in parsed.units}
               for item in values for ref in [item['value_ref'], *item['row_label_refs']])


def test_unproven_table_mapping_remains_visible_in_real_selected_material():
    from types import SimpleNamespace

    from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence

    parsed = _html(observed_headers=False)
    package = select_reading_evidence(parsed, title='Operating capacity update', max_selected=96)
    assert package.evidence_spans
    uncertain = [span for span in package.evidence_spans if '18' in span.raw_text]
    assert uncertain and all('table_structure_ambiguous' in span.quality_flags for span in uncertain)
    assert any('table_structure_ambiguous' in text for text in package.reading_context['constraints'])
    # Actual model compiler, using only its two required source-owned inputs.
    view = compile_scoped_model_view(SimpleNamespace(evidence_spans=package.evidence_spans,
                 reading_context=package.reading_context), max_claims=20).to_model_dict()
    fragments = view['shared_fragments'] + [part for task in view['tasks'] for part in task['parts']
                                           if 'text' in part]
    numeric = [row for row in fragments if '18' in row['text']]
    assert numeric and all('table_structure_ambiguous' in
                          row.get('quality_flags', view['fragment_defaults']['quality_flags'])
                          for row in numeric)


def test_complete_table_mapping_is_not_marked_ambiguous_and_native_identity_stays_exact():
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence

    parsed = _html()
    package = select_reading_evidence(parsed, title='Operating capacity update', max_selected=96)
    numeric = [span for span in package.evidence_spans if span.raw_text == '18']
    assert numeric and all('table_structure_ambiguous' not in span.quality_flags for span in numeric)
    original = next(unit for unit in parsed.units if unit.raw_text == '18')
    assert numeric[0].source_id == original.source_id
    assert numeric[0].coordinates == original.coordinates


def test_native_binder_algorithm_is_a_real_decision_dependency(monkeypatch):
    from company_wiki.document_understanding import decision_inventory, native_table_bridge

    pipeline = _read(_html())
    before = decision_inventory.build_decision_trace(pipeline)
    assert before['versions']['native_table_bridge'] == native_table_bridge.NATIVE_TABLE_BRIDGE_VERSION
    assert decision_inventory.current_decision_trace(before) == before
    monkeypatch.setattr(native_table_bridge, 'NATIVE_TABLE_BRIDGE_VERSION', 'next')
    assert decision_inventory.current_decision_trace(before) != before


def test_financial_table_is_not_bound_before_business_purpose_is_known():
    raw = (b'<h1>Operating update</h1><table><tr><th>Cash and cash equivalents</th>'
           b'<th>As of December 31, 2025</th></tr><tr><th scope="row">Total assets</th>'
           b'<td>900</td></tr></table><table><tr><th>Capacity (units)</th>'
           b'<th>As of December 31, 2025</th></tr><tr><th scope="row">Overseas plants</th>'
           b'<td>18</td></tr></table>')
    digest = sha256(raw).hexdigest()
    normalized = normalize_document(raw, source_id='urn:company-wiki:source:sha256:' + digest,
                                    source_sha256=digest, mime_type='text/html')
    parsed = NarrativeNormalization.language_structure(normalized, 'en')
    result = _read(parsed)
    actual = {_text(parsed, item['value_ref']) for table in result['table_bindings']['tables']
              for item in table['measurements']}
    assert '18' in actual and '900' not in actual
    assert any(unit.raw_text == '900' for unit in parsed.units), 'purpose selection must not erase originals'


def test_mixed_native_table_account_row_cannot_borrow_operating_header_or_context():
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence

    raw = (b'<h1>Operating capacity</h1><table><thead><tr><th>Capacity (units)</th>'
           b'<th>As of December 31, 2025</th></tr></thead><tbody>'
           b'<tr><th scope="row">Cash and cash equivalents</th><td>900</td></tr>'
           b'<tr><th scope="row">Overseas plants</th><td>18</td></tr></tbody></table>')
    digest = sha256(raw).hexdigest()
    normalized = normalize_document(raw, source_id='urn:company-wiki:source:sha256:' + digest,
                                    source_sha256=digest, mime_type='text/html')
    parsed = NarrativeNormalization.language_structure(normalized, 'en')
    result = _read(parsed)
    values = {_text(parsed, item['value_ref']) for table in result['table_bindings']['tables']
              for item in table['measurements']}
    assert '18' in values and '900' not in values
    package = select_reading_evidence(parsed, title='Operating capacity update', max_selected=96)
    assert any(span.raw_text == '18' for span in package.evidence_spans)
    assert not any(span.raw_text in {'900', 'Cash and cash equivalents'} for span in package.evidence_spans)
    assert any(unit.raw_text == '900' for unit in parsed.units)


def test_dependency_closure_preserves_partial_source_binding():
    from copy import deepcopy
    from company_wiki.document_understanding.native_table_bridge import close_native_table_dependencies

    pipeline = _read(_html())
    bindings = deepcopy(pipeline['table_bindings'])
    bindings['status'] = 'partial'
    for table in bindings['tables']:
        table['status'] = 'partial'
        table['diagnostics'].append({'code': 'observation_truncated'})
    closed = close_native_table_dependencies(pipeline['packages'], bindings,
                                             work_budget=WorkBudget(2_000_000))
    tables = [entry for entry in closed['packages'] if entry['kind'] == 'operating_table']
    assert tables and all(entry['table_binding_status'] == 'partial' for entry in tables)


@pytest.mark.parametrize('different', ['source_id', 'table_id', 'page'])
def test_native_row_purpose_is_scoped_before_mapping_back_to_original_cells(different):
    from company_wiki.document_understanding.structure.table_purpose import qualify_native_rows

    def cell(text, owner):
        return {'text': text, 'page': owner.get('page', 1), 'hints': {
            'source_id': owner.get('source_id', 'source-a'),
            'table_id': owner.get('table_id', 'table-a'), 'row': 1}}

    other = {different: 2 if different == 'page' else 'other'}
    body = [cell('Cash and cash equivalents', {}), cell('900', {}),
            cell('Overseas plants', other), cell('18', other)]
    result = qualify_native_rows(['Capacity (units)', 'As of December 31, 2025'], body)
    assert result.eligible_row_indices == (2, 3)


def test_actual_truncated_native_observation_retains_binding_uncertainty():
    from copy import deepcopy
    from company_wiki.document_understanding.native_table_bridge import (
        bind_native_tables, close_native_table_dependencies,
    )

    pipeline = _read(_html())
    observation = deepcopy(pipeline['observation'])
    for unit in observation['units']:
        for table in unit['hints'].get('native_tables', ()):
            table['position_complete'] = False
    bindings = bind_native_tables(observation, work_budget=WorkBudget(2_000_000))
    assert bindings['tables'] and bindings['tables'][0]['status'] == 'partial'
    closed = close_native_table_dependencies(pipeline['packages'], bindings,
                                             work_budget=WorkBudget(2_000_000))
    assert all(entry['table_binding_status'] == 'partial'
               for entry in closed['packages'] if entry['kind'] == 'operating_table')


def test_native_row_zero_budget_does_not_visit_headers_or_body():
    from company_wiki.document_understanding.structure.table_purpose import qualify_native_rows

    class Unread:
        def __iter__(self):
            raise AssertionError('zero work must not enumerate source material')

    result = qualify_native_rows(Unread(), Unread(), caption_texts=Unread(), max_chars=0)
    assert result.status == 'incomplete'


def test_native_row_small_budget_stops_before_next_header_or_body():
    from company_wiki.document_understanding.structure.table_purpose import qualify_native_rows

    def headers():
        yield 'Capacity'
        raise AssertionError('budget exhausted at the first original header')

    def body():
        raise AssertionError('header budget cannot be borrowed by body')
        yield

    result = qualify_native_rows(headers(), body(), max_chars=2)
    assert result.status == 'incomplete'


def test_actual_rowspan_account_header_cannot_leave_continuation_number_as_business():
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence

    raw = (b'<h1>Operating capacity</h1><table><thead><tr><th>Capacity (units)</th>'
           b'<th>As of December 31, 2025</th></tr></thead><tbody>'
           b'<tr><th scope="row" rowspan="2">Cash and cash equivalents</th><td>900</td></tr>'
           b'<tr><td>910</td></tr>'
           b'<tr><th scope="row">Overseas plants</th><td>18</td></tr></tbody></table>')
    digest = sha256(raw).hexdigest()
    parsed = NarrativeNormalization.language_structure(normalize_document(raw,
        source_id='urn:company-wiki:source:sha256:' + digest, source_sha256=digest,
        mime_type='text/html'), 'en')
    result = _read(parsed)
    values = {_text(parsed, item['value_ref']) for table in result['table_bindings']['tables']
              for item in table['measurements']}
    assert values == {'18'}
    selected = select_reading_evidence(parsed, title='Operating capacity update', max_selected=96)
    assert any(span.raw_text == '18' for span in selected.evidence_spans)
    assert not any(span.raw_text in {'900', '910', 'Cash and cash equivalents'}
                   for span in selected.evidence_spans)


def test_observed_operating_rowspan_keeps_both_values_and_exact_original_label():
    raw = (b'<table><thead><tr><th>Capacity (units)</th><th>As of December 31, 2025</th>'
           b'</tr></thead><tbody><tr><th scope="row" rowspan="2">Overseas plants</th>'
           b'<td>18</td></tr><tr><td>24</td></tr></tbody></table>')
    digest = sha256(raw).hexdigest()
    parsed = NarrativeNormalization.language_structure(normalize_document(raw,
        source_id='urn:company-wiki:source:sha256:' + digest, source_sha256=digest,
        mime_type='text/html'), 'en')
    result = _read(parsed)
    values = [item for table in result['table_bindings']['tables'] for item in table['measurements']]
    assert {_text(parsed, item['value_ref']) for item in values} == {'18', '24'}
    assert all([_text(parsed, ref) for ref in item['row_label_refs']] == ['Overseas plants']
               for item in values)
