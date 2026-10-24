"""Independent M1 review probes; offline source fixtures, never product outputs.

Expected meanings below were read from the bound originals, not from selection.
This file only reads author delivery and originals. Reports go to this directory.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.checkers import _support_set_status
from tools.document_understanding_benchmark.evaluate import evaluate
from tools.document_understanding_benchmark.gold import load_gold, load_gold_dir
from tools.document_understanding_benchmark.tests.anchor_verify import verify_gold_anchors
from tools.document_understanding_benchmark.textutil import text_contains

HERE = Path(__file__).resolve().parent
AUTHOR = HERE.parent / 'm1-source-checkpoints'
REPO = next(p for p in HERE.parents if (p / 'pyproject.toml').exists())
BINDINGS = json.loads((AUTHOR / 'source-bindings.json').read_text(encoding='utf-8'))
GOLDS = {g['sample_id']: g for g in load_gold_dir(AUTHOR / 'gold')}
FACTS = [(sid, f['id']) for sid, g in GOLDS.items() for f in g['facts']]


def fact(sid, fid):
    return next(f for f in GOLDS[sid]['facts'] if f['id'] == fid)


def support(f):
    return '\n'.join(a['exact_quote'] for a in f['any_support_sets'][0])


def observation(sid, f, *, drop_fragment=None):
    rows = [dict(locator=f'loc:independent/{sid}/{i}', text=a['exact_quote'],
                 page=a.get('page'), scope_id=f['id'])
            for i, a in enumerate(f['any_support_sets'][0])
            if drop_fragment is None or not text_contains(a['exact_quote'], drop_fragment)]
    return dict(schema_version='du-observed/1', sample_id=sid,
                source_sha256=GOLDS[sid]['source_sha256'], route=None,
                selected_locators=[r['locator'] for r in rows],
                selected_evidence=rows, context_evidence=rows,
                selected_text='\n'.join(r['text'] for r in rows),
                semantic_units=[], claims=[],
                coverage=dict(native_scan='complete', complete=False, opaque_pages=[],
                              deferred_unit_ids=[], unassigned_unit_ids=[]),
                metrics={}, execution=dict(mode='offline_independent_source_fixture', calls=0))


@pytest.mark.parametrize('sid', list(GOLDS))
def test_real_original_hash_and_every_anchor(sid):
    b = BINDINGS[sid]
    p = Path(b['original_path'])
    assert hashlib.sha256(p.read_bytes()).hexdigest() == b['source_sha256']
    assert p.stat().st_size == b['byte_size']
    assert all(r['ok'] for r in verify_gold_anchors(GOLDS[sid], p))


@pytest.mark.parametrize('sid', list(GOLDS))
def test_old_ids_importance_and_all_errors_retained(sid):
    b = BINDINGS[sid]
    path = REPO / b['old_gold_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == b['old_gold_sha256']
    old = load_gold(path)
    new = GOLDS[sid]
    new_errors = {e for f in new['facts'] for e in f['must_not_assert']}
    for f in old['facts']:
        revised = fact(sid, f['id'])
        assert revised['importance'] == f['importance']
        assert set(f['must_not_assert']) <= new_errors
    assert new['scope'] == 'development'
    assert new['support_set_frozen_before_output'] is False


def test_manifest_can_replay_each_old_fact_and_record():
    manifest = json.loads((AUTHOR / 'revision_manifest.json').read_text(encoding='utf-8'))
    for sample in manifest['samples']:
        sid = sample['sample_id']
        old = json.loads((REPO / BINDINGS[sid]['old_gold_path']).read_text(encoding='utf-8'))
        replay = copy.deepcopy(old)
        by_id = {f['id']: f for f in replay['facts']}
        for rev in sample['fact_revisions']:
            for change in rev['changes']:
                key, before, after = change['field'], change['old'], change['new']
                if key == 'fact':
                    assert before is None and rev['fact_id'] not in by_id
                    by_id[rev['fact_id']] = copy.deepcopy(after)
                    replay['facts'].append(by_id[rev['fact_id']])
                else:
                    f = by_id[rev['fact_id']]
                    assert f.get(key) == before, (sid, rev['fact_id'], key)
                    if after is None:
                        f.pop(key, None)
                    else:
                        f[key] = copy.deepcopy(after)
        for change in sample['record_revisions']:
            assert replay.get(change['field']) == change['old']
            if change['new'] is None:
                replay.pop(change['field'], None)
            else:
                replay[change['field']] = copy.deepcopy(change['new'])
        # load_gold adds derived/default fields (gold_quote_chars and optional
        # None values); replay the delivered bytes, not those runtime extras.
        delivered = json.loads((AUTHOR / sample['new_gold_path']).read_text(encoding='utf-8'))
        assert replay == delivered, sid
        assert hashlib.sha256((AUTHOR / sample['new_gold_path']).read_bytes()).hexdigest() == sample['new_gold_sha256']


def test_author_v1_sufficiency_fixes_are_replayable_to_final_facts():
    revision = json.loads((AUTHOR / 'author-revision-2.json').read_text(encoding='utf-8'))
    for sample in revision['revisions']:
        old_path = AUTHOR / sample['author_v1_gold_path']
        final_path = AUTHOR / sample['author_v2_gold_path']
        assert hashlib.sha256(old_path.read_bytes()).hexdigest() == sample['author_v1_sha256']
        assert hashlib.sha256(final_path.read_bytes()).hexdigest() == sample['author_v2_sha256']
        replay = json.loads(old_path.read_text(encoding='utf-8'))
        by_id = {f['id']: f for f in replay['facts']}
        for change in sample['changes']:
            f = by_id[change['fact_id']]
            for field in change['fields']:
                assert f.get(field['field']) == field['old']
                f[field['field']] = field['new']
        assert replay['facts'] == json.loads(final_path.read_text(encoding='utf-8'))['facts']


def test_final_binding_file_binds_actual_gold_and_receipts():
    freeze = json.loads((AUTHOR / 'author-final-bindings.json').read_text(encoding='utf-8'))
    for name, expected in freeze['gold_sha256'].items():
        assert hashlib.sha256((AUTHOR / 'gold' / name).read_bytes()).hexdigest() == expected
    for name, key in [('revision_manifest.json', 'revision_manifest_sha256'),
                      ('author-revision-2.json', 'author_revision_2_sha256'),
                      ('author-report.json', 'author_report_sha256'),
                      ('author-compatibility.json', 'author_compatibility_sha256')]:
        assert hashlib.sha256((AUTHOR / name).read_bytes()).hexdigest() == freeze[key]


@pytest.mark.parametrize('sid', list(GOLDS))
def test_same_frozen_observation_replays_old_and_new_without_becoming_success(sid):
    observed_path = AUTHOR.parent / 'baseline-selection' / f'{sid}.json.gz'
    observed = json.loads(gzip.decompress(observed_path.read_bytes()))['observed']
    old = load_gold(REPO / BINDINGS[sid]['old_gold_path'])
    old_result = evaluate(observed, old)
    new_result = evaluate(observed, GOLDS[sid])
    assert old_result['status'] in {'FAIL', 'PARTIAL'}
    assert new_result['status'] in {'FAIL', 'PARTIAL'}
    expected = next(s for s in json.loads((AUTHOR / 'author-report.json').read_text(encoding='utf-8'))['samples']
                    if s['sample_id'] == sid)
    assert new_result['status'] == expected['existing_baseline_evaluation_status']


@pytest.mark.parametrize('sid,fid', FACTS)
def test_all_facts_have_single_joint_support_and_existing_oracle_can_consume(sid, fid):
    f = fact(sid, fid)
    assert len(f['any_support_sets']) == 1, (sid, fid, 'every OR would need separate entailment')
    obs = observation(sid, f)
    status, _ = _support_set_status(f['any_support_sets'][0], obs,
        require_same_scope=bool(f.get('require_same_scope')), context=f['target_kind'] == 'disposition_context')
    assert status == 'PASS'
    result = evaluate(obs, {**GOLDS[sid], 'facts': [f]})
    basis = next(c for c in result['checks'] if c['check_id'] == 'basis.' + fid)
    assert basis['status'] in {'PASS', 'NOT_EVALUATED'}


def test_buyout_comparison_retains_intervening_questioner_negation():
    f = fact('du5-cn-gbits-call', 'outpost-buyout-revenue-recognition')
    assert text_contains(support(f), '说话人1 09:41它不像'), '09:42 alone changes the comparison polarity'
    assert '它不像' in f['must_preserve']
    assert f['require_same_scope'] is False


def test_azure_outlook_carries_both_removed_business_groups():
    f = fact('du5-us-msft-ex991', 'azure-fy27q1-growth-outlook')
    for fragment in ['GitHub cloud', 'Security Copilot', 'Healthcare and Life Sciences cloud', 'Industry solutions cloud']:
        assert text_contains(support(f), fragment), fragment
    for fragment in ['constant currency', 'less than 1 point', 'July 29, 2026']:
        assert text_contains(support(f), fragment)


def test_current_total_range_joins_explicit_adjusted_no_change():
    f = fact('du5-us-msft-ex991', 'total-company-fy27q1-revenue-outlook')
    assert text_contains(support(f), 'Adjusted Outlook')
    assert text_contains(support(f), 'Total Company No change to outlook')
    assert text_contains(support(f), '$89.85 to $90.95 billion')


@pytest.mark.parametrize('fid,fragment', [
    ('buydown-no-return-negation', '会不会'),
    ('yy-user-base-scale', '2000多用户'),
    ('outpost-buyout-revenue-recognition', '利息负债什么类似的处理'),
    ('yy-roi-decline-actual', 'Oa'),
])
def test_asr_is_not_resolved_by_gold(fid, fragment):
    f = fact('du5-cn-gbits-call', fid)
    assert text_contains(support(f), fragment)
    assert f['role'] == 'unknown'
    if fid in {'buydown-no-return-negation', 'yy-user-base-scale'}:
        assert f['modality'] == 'unknown' and f['quantity_basis'] == 'unknown'


def test_anonymous_discourse_roles_not_upgraded_to_corporate_identity():
    assert all(f['role'] == 'unknown' for f in GOLDS['du5-cn-gbits-call']['facts'])
    assert fact('du5-cn-gbits-call', 'yy-flow-decline-premise')['modality'] == 'question'
    assert fact('du5-cn-gbits-call', 'lei-ting-profit-analyst-inference')['modality'] == 'question'


def test_financial_migration_does_not_discard_operating_responsibility():
    sid = 'du5-hk-kingsoft-interim'
    must = {'gross-margin-decline', 'no-material-investments-or-capex-plans',
            'h2-2025-business-outlook', 'single-operating-segment',
            'cloud-revenue-operating-drivers', 'cloud-service-growth-causal-split',
            'idc-purchase-commitment-stage'}
    required = {f['id'] for f in GOLDS[sid]['facts'] if f['target_kind'] == 'required_business'}
    assert must <= required
    assert fact(sid, 'cloud-revenue-operating-drivers')['importance'] == 'critical'
    assert fact(sid, 'cloud-service-growth-causal-split')['importance'] == 'critical'
    for fragment in ['AI', '行業雲項目', '主動縮減', '抵銷']:
        assert text_contains(support(fact(sid, 'cloud-revenue-operating-drivers')), fragment)
    for fragment in ['公有雲服務', 'AI相關服務增長', '行業雲服務', 'IT需求', '複製行業解決方案']:
        assert text_contains(support(fact(sid, 'cloud-service-growth-causal-split')), fragment)


def test_wrong_page_is_rejected_not_fixed_by_whole_document_search():
    sid = 'du5-cn-proya-q1'
    changed = copy.deepcopy(GOLDS[sid])
    f = next(f for f in changed['facts'] if f['id'] == 'operating-cash-flow-collapse')
    amount = next(a for a in f['any_support_sets'][0] if '106,971,167.62' in a['exact_quote'])
    assert amount['page'] == 2
    amount['page'] = 1
    rows = verify_gold_anchors(changed, Path(BINDINGS[sid]['original_path']))
    assert any(not r['ok'] and r['fact_id'] == f['id'] for r in rows)


def test_wrong_original_sha_is_refused_without_substitution():
    sid = 'du5-cn-gbits-call'
    changed = {**GOLDS[sid], 'source_sha256': '0' * 64}
    with pytest.raises(ValueError, match='SHA mismatch'):
        verify_gold_anchors(changed, Path(BINDINGS[sid]['original_path']))


def test_same_discourse_support_cannot_be_spliced_from_different_scopes():
    sid, fid = 'du5-cn-gbits-call', 'yy-stabilize-target-uncertain'
    f = fact(sid, fid)
    obs = observation(sid, f)
    for i, row in enumerate(obs['selected_evidence']):
        row['scope_id'] = f'unrelated-turn-{i}'
    status, _ = _support_set_status(f['any_support_sets'][0], obs,
        require_same_scope=True, context=False)
    assert status != 'PASS'


def test_context_channel_does_not_satisfy_required_business():
    sid = 'du5-hk-kingsoft-interim'
    business = fact(sid, 'cloud-revenue-operating-drivers')
    meta = fact(sid, 'unit-and-fx-convention')
    for f, expected in [(business, 'not-pass'), (meta, 'PASS')]:
        obs = observation(sid, f)
        obs['selected_evidence'] = []
        obs['selected_locators'] = []
        status, _ = _support_set_status(f['any_support_sets'][0], obs,
            require_same_scope=bool(f.get('require_same_scope')), context=f['target_kind'] == 'disposition_context')
        assert (status == 'PASS') == (expected == 'PASS')


@pytest.mark.parametrize('sid,fid,remove', [
    ('du5-cn-proya-q1', 'cash-flow-drop-driver', '收回货款减少'),
    ('du5-cn-proya-q1', 'eps-basic-diluted-unit', '稀释每股收益'),
    ('du5-hk-kingsoft-interim', 'idc-purchase-commitment-stage', '人民幣千元'),
    ('du5-hk-kingsoft-interim', 'cloud-service-growth-causal-split', 'IT需求'),
    ('du5-cn-gbits-call', 'outpost-buyout-revenue-recognition', '它不像'),
    ('du5-cn-gbits-call', 'yy-stabilize-target-uncertain', '目前也不太好判断'),
    ('du5-us-msft-ex991', 'seat-growth-includes-github', 'at end of period'),
    ('du5-us-msft-ex991', 'azure-fy27q1-growth-outlook', 'Healthcare and Life Sciences'),
    ('du5-us-msft-ex991', 'total-company-fy27q1-revenue-outlook', 'No change to outlook'),
    ('du5-us-msft-ex991', 'forward-looking-caveat', 'not undertake any duty'),
])
def test_semantically_complementary_evidence_cannot_be_omitted(sid, fid, remove):
    f = fact(sid, fid)
    assert text_contains(support(f), remove), 'source-semantic requirement missing from the gold itself'
    obs = observation(sid, f, drop_fragment=remove)
    status, _ = _support_set_status(f['any_support_sets'][0], obs,
        require_same_scope=bool(f.get('require_same_scope')), context=f['target_kind'] == 'disposition_context')
    assert status != 'PASS', (sid, fid, remove)


@pytest.mark.parametrize('sid,fid,bad', [
    ('du5-cn-proya-q1', 'cash-flow-drop-driver', '现金流量下降主要系采购支出增加'),
    ('du5-hk-kingsoft-interim', 'cloud-service-growth-causal-split', '行業雲收入增長23.0%'),
    ('du5-hk-kingsoft-interim', 'idc-purchase-commitment-stage', '一年期IDC採購承諾已成為公司收入'),
    ('du5-hk-kingsoft-interim', 'net-loss-us-gaap-widened', '淨虧損為人民幣772,973百萬元'),
    ('du5-cn-proya-q1', 'eps-basic-diluted-unit', '稀释每股收益高于基本每股收益'),
    ('du5-us-msft-ex991', 'restated-segment-fy26-revenue', "These are as-reported segment figures"),
    ('du5-cn-gbits-call', 'buydown-no-return-negation', '公司明确承诺买量不会再回到原有水平'),
    ('du5-cn-gbits-call', 'buydown-no-return-negation', '公司明确承诺买量一定回到原有水平'),
    ('du5-cn-gbits-call', 'yy-user-base-scale', '公司披露用户数2000万'),
    ('du5-cn-gbits-call', 'outpost-buyout-revenue-recognition', '原文已经确认利息负债就是预计负债'),
    ('du5-us-msft-ex991', 'azure-fy27q1-growth-outlook', '44% to 45% is a GAAP reported growth rate'),
    ('du5-us-msft-ex991', 'commercial-bookings-definition', 'Bookings is a GAAP revenue amount'),
    ('du5-us-msft-ex991', 'total-company-fy27q1-revenue-outlook', "FY27 Q1 actual revenue was $90 billion"),
])
def test_existing_evaluator_rejects_independent_source_risk_mutations(sid, fid, bad):
    f = fact(sid, fid)
    obs = observation(sid, f)
    obs['claims'] = [dict(text=support(f) + '\n' + bad, role='unknown', modality='unknown',
                          evidence_locators=obs['selected_locators'], quantities=[])]
    result = evaluate(obs, {**GOLDS[sid], 'facts': [f]})
    basis = next(c for c in result['checks'] if c['check_id'] == 'basis.' + fid)
    assert basis['status'] == 'FAIL'
    assert any('must_not_assert' in str(o) for o in basis['observed'])
