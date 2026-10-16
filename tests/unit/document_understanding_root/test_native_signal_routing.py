"""Production native carrier -> existing probe allocator -> one router."""

from hashlib import sha256

from company_wiki.document_normalization import normalize_document
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.document_understanding.layout_hints.contract import WorkBudget


def run_html(body, *, limits=None):
    raw=body.encode()
    digest=sha256(raw).hexdigest()
    source='urn:company-wiki:source:sha256:'+digest
    normal=normalize_document(raw, source_id=source, source_sha256=digest, mime_type='text/html')
    parsed=NarrativeNormalization.language_structure(normal, 'en')
    return understand_units(parsed.units, source_id=source, source_sha256=digest,
                            mime_type='text/html', limits=limits, work_budget=WorkBudget(2_000_000))


def test_visible_native_dei_decides_form_using_its_actual_unit():
    result=run_html('<p>Contents</p><p>General background.</p>'
                    '<p>This statement describes operating conditions, with the filing type '
                    '<ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric>'
                    '. It is not a self-identifying cover heading.</p>'
                    '<p>We launched a new product.</p>')
    assert result['route']['family']=='quarterly'
    carrier=next(u['unit_id'] for u in result['observation']['units'] if 'native_source_carriers' in u['hints'])
    assert any(carrier in reason['unit_ids'] for reason in result['route']['reasons'])


def test_native_form_is_reserved_inside_probe_cap_not_appended():
    body=''.join(f'<p>Background paragraph {index}.</p>' for index in range(30))
    body+='<p><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></p>'
    body+=''.join(f'<p>Other paragraph {index}.</p>' for index in range(30))
    result=run_html(body,limits={'max_probe_units':1,'max_probe_chars':32})
    assert result['route']['family']=='quarterly'
    assert result['profile']['policy_probe']['probed_unit_count']==1
    assert result['profile']['policy_probe']['probed_chars']<=32


def test_financial_colon_labels_do_not_manufacture_call_turns():
    result=run_html('<p>Results for the earnings quarter.</p>'
                    '<table><tr><td>Widget Streams:</td><td>12</td></tr>'
                    '<tr><td>Device Supplies:</td><td>15</td></tr></table>')
    assert result['route']['family']!='earnings_call'


def test_hidden_dei_is_not_observed_and_zero_probe_does_not_route_it():
    hidden=run_html('<div hidden><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></div><p>Ordinary text</p>')
    assert hidden['route']['form_type']=='unknown'
    zero=run_html('<p><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></p>',
                  limits={'max_probe_units':0})
    assert zero['route']['form_type']=='unknown'


def test_attached_native_form_keeps_its_own_policy_not_parent_form():
    result=run_html('<h1>FORM 8-K</h1><p>Current report body.</p>'
                    '<h2>Exhibit 99.1</h2><p><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></p>'
                    '<p>We launched a new product in the quarter.</p>')
    assert result['route']['form_type']=='8-K'
    children=[row for row in result['route']['child_routes'] if row.get('family')=='quarterly']
    assert len(children)==1
    assert result['child_profiles'][children[0]['reading_profile_key']]['form_type']=='10-Q'


def test_conflicting_sibling_native_facts_in_same_scope_stay_unknown():
    result=run_html('<p><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></p>'
                    '<p><ix:nonNumeric name="dei:DocumentType">10-K</ix:nonNumeric></p>'
                    '<p>Business body.</p>')
    assert result['source_signals']['status']=='partial'
    assert result['route']['form_type']=='unknown'


def test_parent_without_form_does_not_borrow_child_native_fact():
    result=run_html('<h1>Current report</h1><p>Parent body.</p><h2>Exhibit 99.1</h2>'
                    '<p><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></p>'
                    '<p>Child business body.</p>')
    assert result['route']['form_type']=='unknown'
    children=[row for row in result['route']['child_routes'] if row.get('family')=='quarterly']
    assert len(children)==1


def test_tiny_cap_does_not_detach_child_form_from_its_boundary():
    result=run_html('<h1>Current report</h1><p>Parent body.</p><h2>Exhibit 99.1</h2>'
                    '<p><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric></p>'
                    '<p>Child business body.</p>', limits={'max_probe_units':1})
    assert result['route']['form_type']=='unknown'
