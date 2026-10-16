"""Gold QA must observe the declared source and the exact exception scope."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools.document_understanding_benchmark.tests import anchor_verify as verifier
from tools.document_understanding_benchmark.tests import test_gold_anchor_integrity as integrity
from tools.document_understanding_benchmark.checkers import check_basis_fact
from tools.document_understanding_benchmark.gold import GOLD_DIR


def record(path, *, line=2):
    return {"sample_id":"sample", "source_sha256":sha256(path.read_bytes()).hexdigest(),
            "facts":[{"id":"fact", "any_support_sets":[[{"line":line,"location_kind":"line","exact_quote":"Revenue 100"}]]}]}


@pytest.mark.parametrize("line", [1, 999])
def test_quote_on_a_different_line_cannot_verify(tmp_path, line):
    path=tmp_path/'source.txt'
    path.write_text('Opening\nRevenue 100\nClosing\n',encoding='utf8')
    assert not verifier.verify_gold_anchors(record(path,line=line),path)[0]['ok']


def test_correct_line_and_range_keep_physical_line_numbers(tmp_path):
    path=tmp_path/'source.txt'
    path.write_text('Opening\nRevenue 100\nClosing\n',encoding='utf8')
    gold=record(path)
    assert verifier.verify_gold_anchors(gold,path)[0]['ok']
    anchor=gold['facts'][0]['any_support_sets'][0][0]
    anchor.update(line=2,line_end=3,exact_quote='Revenue 100\nClosing')
    assert verifier.verify_gold_anchors(gold,path)[0]['ok']


def test_mismatched_original_bytes_are_rejected_before_extraction(tmp_path, monkeypatch):
    path=tmp_path/'source.txt'
    path.write_text('Revenue 100',encoding='utf8')
    gold=record(path)
    gold['source_sha256']='0'*64
    seen=[]
    monkeypatch.setattr(verifier,'extract_text_pages',lambda p: seen.append(p) or {None:'Revenue 100'})
    with pytest.raises(ValueError,match='SHA|sha|hash'):
        verifier.verify_gold_anchors(gold,path)
    assert not seen


def test_single_fact_unverifiable_does_not_skip_another_fact(tmp_path,monkeypatch):
    path=tmp_path/'source.txt'
    path.write_text('Revenue 100',encoding='utf8')
    gold=record(path)
    gold['sample_id']='holdout-cn-glodon-q1'
    gold['facts'][0]['id']='unrelated-bad-anchor'
    seen=[]
    monkeypatch.setattr(integrity,'load_gold_dir',lambda:[gold])
    monkeypatch.setattr(integrity,'_bindings',lambda:{gold['sample_id']:str(path)})
    monkeypatch.setattr(verifier,'verify_gold_anchors',lambda *a,**k:seen.append(1) or [
        {'sample_id':gold['sample_id'],'fact_id':'unrelated-bad-anchor','set_index':0,
         'anchor_index':0,'ok':False,'where':'line 999','quote':'absent'}])
    monkeypatch.setenv('DU_BENCH_ALLOW_REAL_DATA','1')
    with pytest.raises(AssertionError,match='unrelated-bad-anchor'):
        integrity.test_all_gold_anchors_verify_or_are_corrected_with_evidence()
    assert len(seen)==1


@pytest.mark.parametrize('claim_text',['营业收入23亿元','营业收入2,305,344,625.4元'])
def test_legitimate_rounded_revenue_is_not_an_explicit_falsehood(claim_text):
    gold=json.loads((GOLD_DIR/'du5-cn-proya-q1.json').read_text(encoding='utf8'))
    fact=next(f for f in gold['facts'] if f['id']=='q1-revenue-yoy-decline')
    anchor=fact['any_support_sets'][0][0]
    loc='loc:synthetic/page:1'
    observation={'sample_id':gold['sample_id'],'source_sha256':gold['source_sha256'],
                 'selected_locators':[loc],'selected_evidence':[{'locator':loc,'page':1,'text':anchor['exact_quote'],'source_role':'company_filing'}],
                 'claims':[{'text':claim_text,'evidence_locators':[loc],'role':'company_filing','modality':'actual','quantities':[]}],
                 'coverage':{'native_scan':'complete','complete':True}}
    before=deepcopy(fact)
    result=check_basis_fact(fact,observation)
    assert 'must_not_assert_violated' not in json.dumps(result),result
    assert fact==before
