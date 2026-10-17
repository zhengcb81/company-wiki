"""Current algorithms and actual source pre-reading policy remain causal."""
from copy import deepcopy

from company_wiki.document_understanding import decision_inventory as inventory
from company_wiki.document_understanding.geometry_intent import reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_reading import _native_layout_summary


def test_current_bridge_version_invalidates_pdf_but_not_other_carriers(monkeypatch):
    before_pdf = inventory._versions(pdf_frontend=True, mime_type='application/pdf')
    before_html = inventory._versions(pdf_frontend=False, mime_type='text/html')
    monkeypatch.setattr(reading, 'BRIDGE_VERSION', 'pdf-geometry-reading/test-changed')
    assert inventory._versions(pdf_frontend=True, mime_type='application/pdf') != before_pdf
    assert inventory._versions(pdf_frontend=False, mime_type='text/html') == before_html


def test_source_planning_is_bounded_and_survives_real_summary_projection():
    scope = {'profile_id': 'cn_annual', 'family': 'annual', 'regime': 'cn_exchange', 'form_type': 'unknown'}
    planning = {'request_digest': 'a' * 64, 'profile_scope': scope, 'complete': False,
                'navigation_missing': True, 'reason_counts': {'exploration_deferred': 300},
                'deferred_pages': list(range(1, 301)), 'deferred_page_count': 300,
                'windows': ['not durable'] * 1000}
    parsed = DocumentStructure('s', 'a' * 64, 'en', (), layout_coverage={'planning': planning})
    compact = _native_layout_summary(parsed)['planning']
    assert compact['complete'] is False and compact['navigation_missing'] is True
    assert compact['profile_scope'] == scope and compact['request_digest'] == 'a' * 64
    assert compact['deferred_page_count'] == 300 and len(compact['deferred_pages']) == 128
    assert 'windows' not in compact


def test_source_pre_reading_scope_is_checked_even_if_post_policy_differs(monkeypatch):
    from unit.document_understanding_selection.test_reading_decision_inventory import _pipeline
    from company_wiki.document_understanding.profiles import registry
    pipeline = _pipeline()
    pipeline['observation'] = {'metadata': {'mime_type': 'application/pdf',
        'native_layout_frontend_version': 'pdf-reading-layout/2'}}
    pipeline['native_layout_frontend'] = {'planning': {'profile_scope': {
        'profile_id': 'offering', 'family': 'offering', 'regime': 'cn_exchange', 'form_type': 'unknown'}}}
    before = inventory.build_decision_trace(pipeline)
    assert any(s['scope_id'].endswith('|pdf-native-intent') for s in before['scopes'])
    changed = deepcopy(registry._CATALOG)
    target = next(f for f in changed['families'] if f['id'] == 'offering_cn_convertible')
    target['sections'][0]['questions'].append('Changed pre-read project requirement')
    monkeypatch.setattr(registry, '_CATALOG', changed)
    assert inventory.current_decision_trace(before) != before
