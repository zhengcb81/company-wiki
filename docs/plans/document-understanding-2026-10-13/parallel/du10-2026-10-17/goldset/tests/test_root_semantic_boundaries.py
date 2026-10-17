"""Independent source-derived corrections, not generated-summary acceptance."""
import json

from _support import load_cases, iter_anchors


CASES = {c['case_id']: c for c in load_cases()}


def test_refs_use_actual_catalog_identity_and_keep_registration_separate():
    for case in CASES.values():
        ref = case['source_ref']
        assert ref.get('schema_version') == '2.0'
        assert ref['source_id'].startswith('urn:company-wiki:source:')
        assert ref['document_id'].startswith('urn:company-wiki:document:')
        assert ref['content_sha256'] == case['source_binding']['expected_sha256']


def test_html_facts_have_exact_canonical_unit_locations():
    case = CASES['du10gs-us-10q-vrsk']
    for _, _, anchor in iter_anchors(case):
        assert anchor.get('location_kind') == 'unit'
        assert anchor['source_locator'].startswith('cwp-html-dom/1|')
        assert anchor['unit_id'].startswith('urn:company-wiki:narrative-unit:')


def test_single_segment_denominator_is_not_falsely_forbidden():
    case = CASES['du10gs-us-10q-vrsk']
    text = json.dumps(case, ensure_ascii=False)
    assert 'one operating segment and one reportable segment, Insurance' in text
    assert 'insurance revenues 范围（非总收入）' not in text
    assert '84%为总收入占比' not in text
    assert '552.1' in text and '230.5' in text and '782.6' in text


def test_baba_global_and_china_ant_scope_do_not_conflict():
    case = CASES['du10gs-hk-ipo-baba']
    boundary = ' '.join(case['summary_guidance']['boundary'])
    assert '含蚂蚁金服中国用户' not in boundary
    assert '8.60' in boundary and '9.60' in boundary


def test_inconsistent_source_is_not_turned_into_definite_quarter_actual():
    case = CASES['du10gs-cn-q3-dfc']
    fact = next(f for f in case['facts'] if f['id'] == 'q3-submarine-hv-cable-revenue')
    assert fact['modality'] == 'unknown'
    assert fact['target_kind'] == 'correctness_if_emitted'
    assert '含了其他收入' not in fact['reason']
    assert {a.get('page') for g in fact['any_support_sets'] for a in g} >= {1, 2, 3}
    for summary in case['allowed_summary']:
        assert '矛盾' in summary or '未解决' in summary


def test_call_role_and_document_type_are_source_attributed():
    case = CASES['du10gs-call-miniso-q4-2024']
    text = case['summary_proposition'] + ' '.join(case['summary_guidance']['must_preserve'])
    assert '董事长' not in text and '招股书' not in text
    assert '创始人兼首席执行官' in text


def test_amec_distinct_products_and_industry_scopes_remain_distinct():
    case = CASES['du10gs-cn-ir-amec-minutes']
    text = case['summary_proposition']
    assert 'XD RIE与YDRIE在研、预计一年左右' not in text
    assert 'XD RIE' in text and '很快' in text and 'YDRIE' in text and '一年左右' in text
    cagr = [f for f in case['facts'] if any('21.81%' in s for s in f['must_preserve'])]
    assert cagr and all(any('等离子体刻蚀设备' in s for s in f['must_preserve']) for f in cagr)


def test_catl_capacity_keeps_distinct_original_period_qualifiers():
    case = CASES['du10gs-cn-annual-catl-capacity']
    text = ' '.join(case['allowed_summary'])
    assert '报告期内' in text and '期末在建' in text
    assert '期末锂电池产能772' not in text
