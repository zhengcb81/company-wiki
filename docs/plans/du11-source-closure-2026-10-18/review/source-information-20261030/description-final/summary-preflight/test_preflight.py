import sys
sys.path[:0]=['.','src','tests']
import pytest
from unit.test_phase_c_observer import selected, _gold, _envelope
from tools.document_understanding_benchmark import phase_c_observer as observer

def test_omitted_kind_counts_all_narrative_facts():
    source=selected(2);gold=_gold(source)
    for fact in gold['facts']: fact.pop('target_kind')
    report=observer.gold_observation(gold,source,_envelope(source,'reading-model-input/4'))
    assert report['required_count']==report['supported_count']==2
    assert report['sent_tasks']['required_count']==report['sent_tasks']['supported_count']==2

def test_document_metadata_default_is_context_not_business():
    source=selected(1);gold=_gold(source)
    meta={**gold['facts'][0],'id':'document-meta','fact_scope':'document_meta'}
    meta.pop('target_kind')
    gold['facts'].append(meta)
    report=observer.gold_observation(gold,source,_envelope(source,'reading-model-input/4'))
    assert report['required_count']==report['supported_count']==1

@pytest.mark.parametrize('invalid',(None,'required_bussiness'))
def test_invalid_explicit_kind_cannot_hide_behind_a_valid_fact(invalid):
    source=selected(2);gold=_gold(source)
    gold['facts'][1]['target_kind']=invalid
    with pytest.raises(ValueError):
        observer.gold_observation(gold,source,_envelope(source,'reading-model-input/4'))

@pytest.mark.parametrize('facts',([], [{'id':'meta','fact_scope':'document_meta'}],
    [{'id':'context','target_kind':'disposition_context'}]))
def test_zero_business_denominator_never_approves(facts):
    source=selected(1)
    with pytest.raises(ValueError):
        observer.gold_observation({'facts':facts},source,_envelope(source,'reading-model-input/4'))

def test_unsent_source_tasks_do_not_fill_current_request_gold():
    source=selected(3);gold=_gold(source)
    report=observer.gold_observation(gold,source,_envelope(source,'reading-model-input/4',['t2']))
    assert report['full_selection']['supported_count']==3
    assert report['sent_tasks']['supported_count']==1
    assert len(report['sent_tasks']['not_sent_ids'])==2
    with pytest.raises(ValueError): observer.gold_admission_missing(report,attempt_no=1)
