"""Emission is observable; source replay never proves paraphrase semantics."""
from copy import deepcopy

import pytest

from company_wiki.automation.narrative_summary_assessment import assess_summary, prose_diagnostics
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.source_catalog.narrative_evidence import summary_claim_type_for_roles
from unit.test_scoped_source_admission import source_with_metadata


def claim(source, index=0, *, claim_id="arbitrary-id"):
    task=compile_scoped_model_view(source,max_claims=20).plan.tasks[index]
    return {"claim_id":claim_id,"text":source.evidence_spans[index].raw_text,
            "evidence_ids":list(task.support_ids),"context_evidence_ids":list(task.context_ids),
            "claim_type":summary_claim_type_for_roles(task.support_roles),
            "modality":"actual","needs_review":False}


def test_missing_tasks_remain_visible_without_claiming_semantic_pass():
    source=source_with_metadata({}, {}, {})
    report=assess_summary(source,[claim(source)],plan_max_claims=20,requested_task_keys=["t1","t2","t3"])
    assert report['emitted_task_keys']==['t1']
    assert report['missing_requested_task_keys']==['t2','t3']
    assert not report['requested_emission_complete']
    assert report['semantic_status']=='not_evaluated'


def test_budget_deferred_and_unavailable_are_distinct_not_hidden():
    source=source_with_metadata({}, {}, {'quality_flags':['table_structure_ambiguous']})
    report=assess_summary(source,[claim(source)],plan_max_claims=20,requested_task_keys=['t1'])
    assert report['source_admitted_task_keys']==['t1','t2']
    assert report['budget_deferred_task_keys']==['t2']
    assert report['excluded_tasks'][0]['task_key']=='t3'
    assert report['excluded_tasks'][0]['reason']=='source_table_unresolved'
    assert report['requested_emission_complete']
    assert not report['admitted_emission_complete']


def test_claim_prefix_cannot_forge_emission_and_inputs_are_immutable():
    source=source_with_metadata({}, {})
    emitted=claim(source,claim_id='t2-1')
    frozen=deepcopy(source.to_dict()),deepcopy(emitted)
    report=assess_summary(source,[emitted],plan_max_claims=20,requested_task_keys=['t1','t2'])
    assert report['emitted_task_keys']==['t1']
    assert (source.to_dict(),emitted)==frozen
    bad=deepcopy(emitted)
    bad['context_evidence_ids']=[source.evidence_spans[1].span_id]
    assert assess_summary(source,[bad],plan_max_claims=20,requested_task_keys=['t1','t2'])['emitted_task_keys']==[]


@pytest.mark.parametrize('keys',[['unknown'],['t1','t1']])
def test_requested_set_requires_real_unique_admitted_tasks(keys):
    with pytest.raises(ValueError):
        assess_summary(source_with_metadata({}),[],plan_max_claims=20,requested_task_keys=keys)


def codes(source,text,modality='actual'):
    return {row['rule_code'] for row in prose_diagnostics(source,text,modality)}


def test_reported_proposition_keeps_attribution_but_not_unrelated_denial():
    source='根据相应新闻报道，您所描述的情况涉及该公司的家电产品，该事项未对子公司经营构成重大影响。'
    assert 'possible_attribution_loss' in codes(source,'所涉事项涉及家电产品，未对经营构成重大影响。')
    assert not codes(source,'据新闻报道，所涉事项涉及家电产品。')
    assert 'possible_attribution_loss' not in codes(source,'该事项未对子公司经营构成重大影响。','negation')


def test_degree_and_future_constraints_are_proposition_local():
    source='该事项未对工厂经营构成重大影响。公司将申请恢复审核。公司已收到问询函。'
    assert 'possible_negation_degree_loss' in codes(source,'该事项未对工厂经营产生影响。','negation')
    assert 'possible_modality_mismatch' in codes(source,'公司已恢复审核。')
    assert not codes(source,'公司已收到问询函。')
    assert not codes(source,'公司将申请恢复审核。','planned')
    assert not codes('The company will restore the listing review. The company received questions.',
                     'The company received questions.')
    assert not codes('公司已将设备转入生产。','公司已将设备转入生产。')
    assert not codes('公司计划完成率达到80%。','公司计划完成率达到80%。')
    assert 'possible_negation_degree_loss' in codes(source,
        '该事项未对工厂经营产生影响，另一个项目有重大进展。','negation')
    assert 'possible_attribution_loss' in codes(
        'According to reports, Orion will open a factory.',
        'According to reports, demand is rising. Orion will open a factory.','planned')
    assert 'possible_modality_mismatch' in codes(
        '项目建成后将为工厂提供产能保障。','工厂已获得产能保障。')


def test_plan_marker_is_explicit_and_diagnostic_truncation_is_visible():
    source=source_with_metadata({})
    first=assess_summary(source,[],plan_max_claims=20,requested_task_keys=['t1'])
    second=assess_summary(source,[],plan_max_claims=40,requested_task_keys=['t1'])
    assert first['source_plan_sha256']!=second['source_plan_sha256']
    assert 'admission' in first['validator']['dependencies']
    # Even malformed caller input cannot grow diagnostics without bound.
    # Canonical production validation additionally caps retained clauses.
    invalid=[{**claim(source,claim_id=f'c{i}'),'evidence_ids':[]} for i in range(80)]
    report=assess_summary(source,invalid,plan_max_claims=20,requested_task_keys=['t1'])
    assert report['diagnostic_count']==80
    assert len(report['diagnostics'])==64
    assert report['diagnostics_limited']
    assert report['known_constraint_status']=='diagnostics_found'


def test_same_support_with_different_task_intent_is_not_arbitrarily_assigned():
    source=source_with_metadata({})
    wire=source.to_dict()
    wire['reading_context']['groups']=[
        {'group_id':name,'kind':'business_progress','section_role':role,
         'evidence_ids':[source.evidence_spans[0].span_id]}
        for name,role in [('native-a','business'),('native-b','risk')]]
    source=NarrativeSelectResult.from_dict(wire)
    item=claim(source)
    assert assess_summary(source,[item],plan_max_claims=40,
        requested_task_keys=['t1'])['emitted_task_keys']==['t1']
    report=assess_summary(source,[item],plan_max_claims=40,requested_task_keys=['t1','t2'])
    assert report['emitted_task_keys']==[]
    assert report['diagnostics'][0]['rule_code']=='ambiguous_claim_scope'


def test_no_known_violation_is_not_a_general_semantic_verdict():
    source=source_with_metadata({})
    item=claim(source)
    item['text']='An unfamiliar paraphrase requiring independent semantic review.'
    report=assess_summary(source,[item],plan_max_claims=20,requested_task_keys=['t1'])
    assert report['known_constraint_status']=='no_known_violation'
    assert report['semantic_status']=='not_evaluated'
    assert report['requested_emission_complete']
    assert report['subfact_coverage_status']=='not_evaluated'
