import hashlib

import pytest

from tools.document_understanding_benchmark import evaluate
from tools.document_understanding_benchmark.checkers import check_context, check_recall_fact
from tools.document_understanding_benchmark.records import validate_gold, validate_observed


def fact(*groups, target='required_business', importance='critical'):
    return {'id': 'project', 'importance': importance, 'target_kind': target,
            'any_support_sets': list(groups), 'must_preserve': [], 'must_not_assert': []}


def anchor(page, text):
    return {'page': page, 'exact_quote': text}


def obs(rows=None):
    item = {'schema_version': 'du-observed/1', 'sample_id': 's', 'source_sha256': 'a'*64,
            'selected_locators': [], 'selected_text': '', 'claims': [], 'semantic_units': [],
            'coverage': {'native_scan': 'complete', 'complete': True},
            'route': {'family': 'quarterly'}, 'metrics': {}, 'execution': {'calls': 0}}
    if rows is not None:
        item['selected_evidence'] = rows
        item['selected_locators'] = [row['locator'] for row in rows]
    return item


def row(page, text, locator=None, **kw):
    return {'locator': locator or f'page:{page}', 'page': page, 'text': text, **kw}


def gold(f):
    return {'schema_version': 'du-gold/1', 'sample_id': 's', 'source_sha256': 'a'*64,
            'scope': 'development', 'expected_route_families': ['quarterly'], 'facts': [f]}


def check(result, key):
    return next(item for item in result['checks'] if item['check_id'] == key)


def test_flat_text_and_generated_claim_cannot_self_prove_source_recall():
    f = fact([anchor(12, 'Project Alpha'), anchor(13, 'two-year construction')])
    o = obs()
    o['selected_locators'] = ['page:80']
    o['selected_text'] = 'Project Alpha two-year construction'
    o['claims'] = [{'text': 'Project Alpha two-year construction', 'evidence_locators': ['page:80']}]
    assert check_recall_fact(f, o)['status'] == 'NOT_EVALUATED'


def test_correct_quotes_on_unrelated_pages_cannot_match_gold_support():
    f = fact([anchor(12, 'Project Alpha'), anchor(13, 'two-year construction')])
    o = obs([row(80, 'Project Alpha'), row(81, 'two-year construction')])
    assert check_recall_fact(f, o)['status'] == 'FAIL'


def test_unselected_source_rows_are_not_recalled():
    o = obs([row(12, 'Project Alpha')])
    o['selected_locators'] = []
    assert check_recall_fact(fact([anchor(12, 'Project Alpha')]), o)['status'] == 'FAIL'


def test_support_group_is_and_while_equivalent_groups_are_or():
    f = fact([anchor(12, 'Project Alpha'), anchor(13, 'two-year construction')],
             [anchor(20, 'Alpha project takes two years')])
    assert check_recall_fact(f, obs([row(12, 'Project Alpha')]))['status'] == 'FAIL'
    assert check_recall_fact(f, obs([row(12, 'Project Alpha'), row(13, 'two-year construction')]))['status'] == 'PASS'
    assert check_recall_fact(f, obs([row(20, 'Alpha project takes two years')]))['status'] == 'PASS'


def test_readable_alternative_not_dragged_down_by_an_opaque_alternative():
    f = fact([anchor(1, 'equivalent business fact')], [anchor(2, 'equivalent business fact')])
    o = obs([row(2, 'equivalent business fact')])
    o['coverage'] = {'native_scan': 'partial', 'opaque_pages': [1], 'complete': False}
    assert check_recall_fact(f, o)['status'] == 'PASS'


def test_only_unread_support_groups_are_unavailable():
    f = fact([anchor(1, 'business fact')], [anchor(2, 'business fact')])
    o = obs([])
    o['coverage'] = {'native_scan': 'partial', 'opaque_pages': [1, 2], 'complete': False}
    assert check_recall_fact(f, o)['status'] == 'UNAVAILABLE'


def test_readable_miss_is_fail_even_when_other_group_is_opaque():
    f = fact([anchor(1, 'business fact')], [anchor(2, 'business fact')])
    o = obs([row(2, 'unrelated paragraph')])
    o['coverage'] = {'native_scan': 'partial', 'opaque_pages': [1], 'complete': False}
    assert check_recall_fact(f, o)['status'] == 'FAIL'


def test_line_support_uses_actual_source_line_range():
    f = fact([{'line': 25, 'exact_quote': 'Backlog is conditional'}])
    o = obs([{'locator': 'lines:20:30', 'line': 20, 'line_end': 30, 'text': 'Backlog is conditional'}])
    assert check_recall_fact(f, o)['status'] == 'PASS'
    o['selected_evidence'][0]['line_end'] = 24
    assert check_recall_fact(f, o)['status'] == 'FAIL'


def test_optional_financial_fact_omission_has_no_business_recall_denominator():
    f = fact([anchor(1, 'EPS 0.12')], target='correctness_if_emitted')
    result = evaluate(obs([]), gold(f))
    assert result['metrics']['critical_fact_recall_denominator'] == 0
    assert check(result, 'basis.project')['status'] == 'NOT_EVALUATED'
    assert all(r['status'] != 'FAIL' for r in result['checks'])
    assert result['execution']['limits']


def test_optional_financial_claim_still_rejects_explicit_contradiction():
    f = fact([anchor(1, 'Revenue declined 6.45%')], target='correctness_if_emitted')
    f['must_not_assert'] = ['Revenue grew 6.45%']
    o = obs([row(1, 'Revenue declined 6.45%')])
    o['claims'] = [{'text': 'Revenue grew 6.45%', 'evidence_locators': ['page:1']}]
    assert check(evaluate(o, gold(f)), 'basis.project')['status'] == 'FAIL'


def test_target_kind_is_validated_and_legacy_metadata_gets_context_default():
    f = fact([anchor(1, 'audit status')])
    f.pop('target_kind')
    f['fact_scope'] = 'document_meta'
    assert validate_gold(gold(f))['facts'][0]['target_kind'] == 'disposition_context'
    f['target_kind'] = 'invented'
    with pytest.raises(ValueError):
        validate_gold(gold(f))


def test_declared_complete_cannot_replace_actual_required_context():
    o = obs([row(1, 'amount 100')])
    o['semantic_units'] = [{'semantic_id': 'table', 'locators': ['page:1'],
                            'required_locators': ['page:1', 'page:2'],
                            'dependencies_resolved': True, 'completeness': 'complete'}]
    assert check_context(o, {})['status'] == 'FAIL'


def test_legacy_complete_without_dependency_observation_is_not_evaluated():
    o = obs([row(1, 'amount 100')])
    o['semantic_units'] = [{'semantic_id': 'table', 'locators': ['page:1'], 'completeness': 'complete'}]
    assert check_context(o, {})['status'] == 'NOT_EVALUATED'


def test_verified_context_requires_every_source_bound_locator():
    o = obs([row(1, 'amount 100'), row(2, 'USD million; annual period')])
    o['semantic_units'] = [{'semantic_id': 'table', 'locators': ['page:1'],
                            'required_locators': ['page:1', 'page:2'],
                            'dependencies_resolved': True, 'completeness': 'complete'}]
    assert check_context(validate_observed(o), {})['status'] == 'PASS'


def test_ordinary_business_miss_reports_recall_partial_not_false_full_failure():
    f = fact([anchor(1, 'ordinary business fact')], importance='normal')
    result = evaluate(obs([]), gold(f))
    assert result['status'] == 'PARTIAL'
    assert result['metrics']['fact_recall'] == 0


def test_unaudited_claims_do_not_produce_whole_quality_pass():
    f = fact([anchor(1, 'new overseas order')])
    o = obs([row(1, 'new overseas order')])
    o['claims'] = [{'text': 'new overseas order', 'evidence_locators': ['page:1']}]
    result = evaluate(o, gold(f))
    assert result['status'] == 'PARTIAL'
    assert check(result, 'semantics.entailment')['status'] == 'NOT_EVALUATED'


def test_sec_html_uses_existing_public_normalization_and_emits_real_locator_rows(tmp_path):
    from tools.document_understanding_benchmark.observer import observe_native, carrier_support
    content = b'<html><body><h1>Business</h1><p>We launched new cloud services for overseas customers.</p></body></html>'
    path = tmp_path / 'company-10k.htm'
    path.write_bytes(content)
    assert carrier_support(path)['supported'] is True
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    result = observe_native(path, sha256=hashlib.sha256(content).hexdigest(), sample_id='s', existing_kind='annual_report')
    assert result['execution']['parse_entry'] == 'normalize_document'
    assert result['metrics']['source_units'] > 0
    assert result['selected_evidence']
    assert all(r['locator'] in result['selected_locators'] and r['text'] for r in result['selected_evidence'])
    assert before == (path.read_bytes(), path.stat().st_mtime_ns)


def test_same_page_different_projects_cannot_be_composed_as_one_scope():
    f = fact([anchor(12, 'Project Alpha'), anchor(12, 'two-year construction')])
    f['require_same_scope'] = True
    o = obs([row(12, 'Project Alpha', 'page:12:alpha', scope_id='alpha'),
             row(12, 'two-year construction', 'page:12:beta', scope_id='beta')])
    assert check_recall_fact(f, o)['status'] == 'FAIL'


def test_cross_page_project_scope_requires_observed_scope_or_reports_unknown():
    f = fact([anchor(12, 'Project Alpha'), anchor(13, 'two-year construction')])
    f['require_same_scope'] = True
    o = obs([row(12, 'Project Alpha'), row(13, 'two-year construction')])
    assert check_recall_fact(f, o)['status'] == 'NOT_EVALUATED'
    for material in o['selected_evidence']:
        material['scope_id'] = 'project-alpha'
    assert check_recall_fact(f, o)['status'] == 'PASS'


def test_role_period_scope_constraints_are_checked_against_source_not_claim():
    a = anchor(12, 'qualification complete')
    a.update(source_role='management_answer', period='2026Q2', scope_id='beta')
    f = fact([a])
    o = obs([row(12, 'qualification complete', source_role='analyst_question', period='2026Q1', scope_id='alpha')])
    assert check_recall_fact(f, o)['status'] == 'FAIL'


def test_known_html_document_scope_uses_replayed_dom_locator_without_fake_page():
    f = fact([{'location_kind': 'document', 'exact_quote': 'Azure consumption-based services'}])
    o = obs([{'locator': 'loc:v1/paragraph:8', 'text': 'Azure consumption-based services'}])
    assert check(evaluate(o, gold(f)), 'recall.project')['status'] == 'PASS'


def test_financial_only_gold_accepts_zero_selection_zero_claims_zero_calls():
    import json
    from tools.document_understanding_benchmark.gold import GOLD_DIR
    original_gold = json.loads((GOLD_DIR / 'cn-q-sparse.json').read_text(encoding='utf8'))
    o = obs([])
    o['sample_id'] = original_gold['sample_id']
    o['source_sha256'] = original_gold['source_sha256']
    result = evaluate(o, original_gold)
    assert result['status'] == 'PASS'
    assert result['metrics']['critical_fact_recall_denominator'] == 0
    assert result['metrics']['claim_count'] == result['metrics']['selected_span_count'] == 0
    assert o['execution']['calls'] == 0
    assert result['metrics']['optional_correctness_facts'] > 0


def test_mutation_does_not_count_preexisting_partial_as_detection(monkeypatch):
    from tools.document_understanding_benchmark import mutations
    f = fact([anchor(1, 'new overseas order')])
    o = obs([row(1, 'new overseas order')])
    o['claims'] = [{'text': 'new overseas order', 'evidence_locators': ['page:1']}]
    def unmeasured_rewrite(value, _gold):
        value['claims'][0]['text'] += ' due to an unsubstantiated macroeconomic cause'
        return value
    monkeypatch.setattr(mutations, 'MUTATIONS', (('meaning_only', 'semantic-only rewrite', unmeasured_rewrite, 'basis.'),))
    report = mutations.run_mutation_suite(o, gold(f))
    assert report['baseline_status'] == 'PARTIAL'
    assert report['mutations_detected'] == 0
    assert report['rows'][0]['outcome'] == 'NOT_DETECTED'


def test_selected_locator_without_original_material_is_integrity_failure():
    o = obs([])
    o['selected_locators'] = ['page:99:invented']
    f = fact([anchor(1, 'business fact')])
    assert check(evaluate(o, gold(f)), 'integrity.selected_source_material')['status'] == 'FAIL'


@pytest.mark.parametrize('indices', [[], [0, 0]])
def test_partial_or_duplicate_review_cannot_certify_every_claim(indices):
    f = fact([anchor(1, 'new overseas order')])
    o = obs([row(1, 'new overseas order')])
    o['claims'] = [{'text': 'new overseas order', 'evidence_locators': ['page:1']},
                   {'text': 'new overseas order with unsupported cause', 'evidence_locators': ['page:1']}]
    review = {'schema_version': 'du-review/1', 'sample_id': 's',
              'claims': [{'claim_index': i, 'verdict': 'ENTAILED'} for i in indices]}
    assert check(evaluate(o, gold(f), review=review), 'semantics.entailment')['status'] == 'PARTIAL'
