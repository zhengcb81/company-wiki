"""Finite task-emission and source-constraint observations, never an NLI verdict.

This module consumes already selected source scopes. It neither reads originals
nor rewrites missing facts, creates tasks, retries a model or authorizes usage.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
import re
from typing import Any

from company_wiki.document_normalization.text_matching import matching_reading_text
from company_wiki.source_catalog.narrative_evidence import summary_claim_type_for_roles
from company_wiki.document_understanding.summary_tasks import SourceSummaryTask
from company_wiki.source_contract import EvidenceSpan
from .models import canonical_json_hash
from .narrative_contracts import NarrativeSelectResult
from .narrative_model_scoped import compile_scoped_material_view

ASSESSMENT_SCHEMA = 'summary-assessment/1'
ASSESSMENT_VERSION = 'source-summary-assessment/1.0.0'
ATOMIC_ASSESSMENT_VERSION = 'source-summary-assessment/1.1.0'
ASSESSMENT_VERSIONS = frozenset({ASSESSMENT_VERSION, ATOMIC_ASSESSMENT_VERSION})
MAX_DIAGNOSTICS = 64
ASSESSMENT_MAX_BYTES = 64 * 1024
_PARTS = re.compile(r'(?<!\d)[,，]|[,，](?!\d)|[。；;!?]|(?<=[.!?])\s+')
_REPORTED = re.compile(r'(?:根据|据)[^,，。;!?]{0,35}?(?:报道|报告)|'
                       r'\baccording to\s+[^,。;!?]{0,60}?\breports?\b|'
                       r'\breportedly\b', re.I)
_FUTURE = re.compile(r'(?<!已)(?<!经)将(?=申请|恢复|建设|开发|投产|扩建|销售|启动)|'
                     r'拟(?:于|在|申请|恢复|建设|开发|投产)|'
                     r'(?:建成|投产|完成|获批|批准|交割)后[^,，。;!?]{0,30}将(?:为|提供|支持)|'
                     r'(?:计划|希望|预期|预计)(?=(?:将)?(?:建立|合作|建设|开发|申请|恢复|投产|扩建|销售|启动|完成(?!率|度)|增加|减少))|'
                     r'\b(?:will|plans? to|intends? to|expects? to|hopes? to)\b', re.I)
_DEGREE_NEGATION = re.compile(r'(?:未|没有|并无|不)[^。;!?]{0,100}(?:重大|实质性)[^。;!?]{0,15}影响|'
                             r'\bnot\s+materially\s+(?:affect\w*|impact\w*)', re.I)
_DEGREE = re.compile(r'重大|实质性|\bmaterial(?:ly)?\b', re.I)
_NEGATION = re.compile(r'未|没有|并无|不|\b(?:not|no|never)\b', re.I)
_IMPACT = re.compile(r'影响|\b(?:affect\w*|impact\w*)\b', re.I)
_FUNCTION_WORDS = frozenset('a an the this that these those our their its we they it '
                           'company group have has had is are was were will would '
                           'to for of in on by and or not'.split())


def assessment_identity(version: str | None = None) -> dict[str, Any]:
    """A software recipe, not a copied source or a human review receipt."""
    version = version or ASSESSMENT_VERSION
    if version not in ASSESSMENT_VERSIONS:
        raise ValueError('unknown summary assessor version')
    from company_wiki.document_normalization import text_matching
    from company_wiki.document_understanding import summary_tasks, source_cards
    from company_wiki.source_catalog import narrative_evidence
    from . import models, narrative_model_scoped
    modules={'matching':text_matching,'task_plan':summary_tasks,'admission':source_cards,
             'scoped_view':narrative_model_scoped,'encoding':models,'claim_roles':narrative_evidence}
    files={key:Path(module.__file__) for key,module in modules.items() if module.__file__}
    files['assessment']=Path(__file__)
    if version == ATOMIC_ASSESSMENT_VERSION:
        from company_wiki.document_understanding import assertion_frames
        files['assertion_frames'] = Path(assertion_frames.__file__)
    dependencies={key:hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                  for key,path in files.items()}
    return {'version':version,'implementation_sha256':canonical_json_hash(dependencies),
            'dependencies':dependencies}


def _anchors(value: str) -> tuple[set[str], set[tuple[str, str]]]:
    text=matching_reading_text(value).casefold()
    compact=''.join(c for c in text if c.isalnum())
    cjk={compact[i:i+4] for i in range(max(0,len(compact)-3))
         if any(ord(c)>127 for c in compact[i:i+4])}
    words=[word for word in re.findall(r'[a-z][a-z0-9-]*',text) if word not in _FUNCTION_WORDS]
    return cjk,set(zip(words,words[1:]))


def _same_proposition(source: str, claim: str) -> bool:
    # A shared local phrase only enables a possible-violation diagnostic. It
    # cannot certify equivalence, attribution, completeness or truth.
    left,right=_anchors(source),_anchors(claim)
    return bool(left[0]&right[0] or left[1]&right[1])


def _source_parts(source: str):
    pending=''
    for raw in _PARTS.split(matching_reading_text(source)):
        part=raw.strip()
        if not part:
            continue
        reported=_REPORTED.search(part)
        if reported and not part[reported.end():].strip(' :：'):
            pending=part
            continue
        if pending:
            part=pending+'，'+part
            pending=''
        yield part


def prose_diagnostics(source: str, claim: str, modality: str) -> list[dict[str, str]]:
    """Observe a few anchored constraints; unsupported cases honestly abstain."""
    result=[]
    claim_parts=tuple(_source_parts(claim))
    for part in _source_parts(source):
        reported=_REPORTED.search(part)
        proposition=part[reported.end():].lstrip(' ,，:：') if reported else part
        for claim_part in claim_parts:
            if not _same_proposition(proposition,claim_part):
                continue
            if reported and not _REPORTED.search(claim_part):
                result.append({'rule_code':'possible_attribution_loss'})
            if (_DEGREE_NEGATION.search(part) and _NEGATION.search(claim_part)
                    and _IMPACT.search(claim_part) and not _DEGREE.search(claim_part)):
                result.append({'rule_code':'possible_negation_degree_loss'})
            if _FUTURE.search(part) and modality not in {'planned','forecast','uncertain'}:
                result.append({'rule_code':'possible_modality_mismatch'})
    return [dict(rule_code=code) for code in dict.fromkeys(row['rule_code'] for row in result)]


def atomic_prose_diagnostics(source: str, claim: str, modality: str) -> list[dict[str, str]]:
    """Additional finite observations; v1 rules above retain their interpretation."""
    from company_wiki.document_understanding.assertion_frames import source_assertion_frames
    result = prose_diagnostics(source, claim, modality)
    claim_frames = source_assertion_frames(claim)
    for frame in source_assertion_frames(source):
        matches = [part for part in claim_frames
                   if _same_proposition(frame.matching_text, part.matching_text)]
        if not matches:
            continue
        if frame.ongoing_activity and modality == 'planned':
            result.append({'rule_code': 'possible_current_action_as_future'})
        if frame.reporting_prefix and not any(part.reporting_prefix for part in matches):
            result.append({'rule_code': 'possible_attribution_loss'})
        if (frame.quantity_basis == 'project_capacity_specification' and modality == 'actual'
                and any(re.search(r'产能|\bcapacity\b', part.matching_text, re.I)
                        and part.quantity_basis != 'project_capacity_specification' for part in matches)):
            result.append({'rule_code': 'possible_project_capacity_basis_loss'})
    return [dict(rule_code=code) for code in dict.fromkeys(row['rule_code'] for row in result)]


def assess_summary(
    selected: NarrativeSelectResult, claims: Sequence[Mapping[str, Any]], *,
    requested_task_keys: Sequence[str], plan_max_claims: int,
    assessor_version: str | None = None,
) -> dict[str, Any]:
    """Bind final retained clauses to exact source scopes, not claim-ID aliases."""
    return assess_summary_material(selected.evidence_spans,selected.reading_context,claims,
        requested_task_keys=requested_task_keys,plan_max_claims=plan_max_claims,
        assessor_version=assessor_version)


def assess_summary_material(
    evidence_spans: Sequence[EvidenceSpan], reading_context: Mapping[str,Any] | None,
    claims: Sequence[Mapping[str,Any]], *, requested_task_keys: Sequence[str], plan_max_claims: int,
    assessor_version: str | None = None,
) -> dict[str,Any]:
    """Consume the same owned source material from a selection or final bundle."""
    version = assessor_version or ASSESSMENT_VERSION
    identity = assessment_identity(version)
    diagnostics_for_prose = atomic_prose_diagnostics if version == ATOMIC_ASSESSMENT_VERSION else prose_diagnostics
    view=compile_scoped_material_view(evidence_spans,reading_context,max_claims=plan_max_claims)
    admission=view.to_binding()['source_admission']
    admitted=view.admitted_task_keys
    requested=set(requested_task_keys)
    if len(requested)!=len(requested_task_keys) or requested-admitted:
        raise ValueError('requested summary tasks must be unique source-admitted tasks')
    by_scope: dict[tuple[tuple[str,...],tuple[str,...],str], list[SourceSummaryTask]]= {}
    for task in view.plan.tasks:
        if task.key in requested:
            key=(task.support_ids,task.context_ids,summary_claim_type_for_roles(task.support_roles))
            by_scope.setdefault(key,[]).append(task)
    known={span.span_id:span for span in evidence_spans}
    emitted=set()
    diagnostics: list[dict[str, Any]]=[]
    diagnostic_count=0
    diagnostic_claim_ids: set[str]=set()

    def record(row: dict[str, Any]) -> None:
        nonlocal diagnostic_count
        diagnostic_count+=1
        diagnostic_claim_ids.add(row['claim_id'])
        if len(diagnostics)<MAX_DIAGNOSTICS:
            diagnostics.append(row)

    for claim in claims:
        claim_type=claim.get('claim_type')
        scope=(tuple(claim.get('evidence_ids',())),tuple(claim.get('context_evidence_ids',())),claim_type)
        matches=by_scope.get((scope[0],scope[1],claim_type),[]) if isinstance(claim_type,str) else []
        if len(matches)!=1:
            record({'task_key':None,'claim_id':claim['claim_id'],
                                'source_span_id':None,'rule_code':
                                'ambiguous_claim_scope' if matches else 'unmatched_claim_scope'})
            continue
        task=matches[0]
        emitted.add(task.key)
        for sid in task.support_ids:
            for row in diagnostics_for_prose(known[sid].raw_text or '',claim['text'],claim['modality']):
                record({'task_key':task.key,'claim_id':claim['claim_id'],
                                    'source_span_id':sid,**row})
    order=[task.key for task in view.plan.tasks]
    result={'schema_version':ASSESSMENT_SCHEMA,'validator':identity,
            'source_plan_sha256':view.plan.binding_sha256,
            'plan_max_claims':plan_max_claims,
            'source_admission_sha256':canonical_json_hash(admission),
            'claims_sha256':canonical_json_hash(list(claims)),
            'scope':'selected_source_tasks_only',
            'source_admitted_task_keys':[key for key in order if key in admitted],
            'requested_task_keys':[key for key in order if key in requested],
            'emitted_task_keys':[key for key in order if key in emitted],
            'missing_requested_task_keys':[key for key in order if key in requested-emitted],
            'budget_deferred_task_keys':[key for key in order if key in admitted-requested],
            'excluded_tasks':[{'task_key':key,**admission[key]} for key in order if key not in admitted],
            'requested_emission_complete':emitted==requested,
            'admitted_emission_complete':emitted==admitted,
            'subfact_coverage_status':'not_evaluated','semantic_status':'not_evaluated',
            'known_constraint_status':'diagnostics_found' if diagnostics else 'no_known_violation',
            'diagnostics':diagnostics,'diagnostic_count':diagnostic_count,
            'diagnostics_limited':diagnostic_count>len(diagnostics),
            'diagnostic_claim_ids':[claim['claim_id'] for claim in claims if claim['claim_id'] in diagnostic_claim_ids]}
    from .models import canonical_json
    if len(canonical_json(result).encode('utf-8'))>ASSESSMENT_MAX_BYTES:
        raise ValueError('summary assessment exceeds its finite byte bound')
    return result


def validate_assessment_wire(value: Any, claims: Sequence[Mapping[str,Any]] | None) -> dict[str,Any]:
    """Shape/algebra only without source material; full binding is checked below."""
    import json
    from .models import canonical_json, _to_plain
    fields={'schema_version','validator','source_plan_sha256','plan_max_claims',
        'source_admission_sha256','claims_sha256','scope','source_admitted_task_keys',
        'requested_task_keys','emitted_task_keys','missing_requested_task_keys',
        'budget_deferred_task_keys','excluded_tasks','requested_emission_complete',
        'admitted_emission_complete','subfact_coverage_status','semantic_status',
        'known_constraint_status','diagnostics','diagnostic_count','diagnostics_limited','diagnostic_claim_ids'}
    if not isinstance(value,Mapping) or set(value)!=fields:
        raise ValueError('invalid summary assessment fields')
    encoded=canonical_json(_to_plain(value)).encode('utf-8')
    if len(encoded)>ASSESSMENT_MAX_BYTES:
        raise ValueError('summary assessment exceeds its finite byte bound')
    report=json.loads(encoded)

    def require(condition: bool) -> None:
        if not condition:
            raise ValueError('invalid summary assessment')

    def sha(value: Any) -> bool:
        return isinstance(value,str) and re.fullmatch(r'[a-f0-9]{64}',value) is not None

    require(report['schema_version']==ASSESSMENT_SCHEMA)
    require(report['scope']=='selected_source_tasks_only')
    require(report['semantic_status']==report['subfact_coverage_status']=='not_evaluated')
    require(type(report['plan_max_claims']) is int and report['plan_max_claims']>0)
    require(all(sha(report[key]) for key in ('source_plan_sha256','source_admission_sha256','claims_sha256')))
    if claims is not None:
        require(report['claims_sha256']==canonical_json_hash(list(claims)))
    validator=report['validator']
    require(isinstance(validator,dict) and set(validator)=={'version','implementation_sha256','dependencies'})
    require(isinstance(validator['version'],str) and validator['version'] in ASSESSMENT_VERSIONS)
    deps=validator['dependencies']
    dep_keys = {'matching','task_plan','admission','scoped_view','encoding','claim_roles','assessment'}
    if validator['version'] == ATOMIC_ASSESSMENT_VERSION:
        dep_keys.add('assertion_frames')
    require(isinstance(deps,dict) and set(deps)==dep_keys)
    require(all(sha(digest) for digest in deps.values()))
    require(validator['implementation_sha256']==canonical_json_hash(deps))
    keys={}
    for name in ('source_admitted_task_keys','requested_task_keys','emitted_task_keys',
                 'missing_requested_task_keys','budget_deferred_task_keys'):
        rows=report[name]
        require(isinstance(rows,list) and all(isinstance(k,str) and re.fullmatch(r't[1-9][0-9]*',k) for k in rows))
        require(len(rows)==len(set(rows)))
        keys[name]=set(rows)
    admitted=keys['source_admitted_task_keys']
    requested=keys['requested_task_keys']
    emitted=keys['emitted_task_keys']
    require(emitted<=requested<=admitted)
    require(keys['missing_requested_task_keys']==requested-emitted)
    require(keys['budget_deferred_task_keys']==admitted-requested)
    for key,actual in (('requested_emission_complete',emitted==requested),
                       ('admitted_emission_complete',emitted==admitted)):
        require(type(report[key]) is bool and report[key]==actual)
    excluded=report['excluded_tasks']
    require(isinstance(excluded,list))
    excluded_keys: set[str]=set()
    for row in excluded:
        require(isinstance(row,dict) and row.get('status') in ('unavailable','duplicate'))
        expected={'task_key','status','reason'}|({'representative'} if row['status']=='duplicate' else set())
        require(set(row)==expected)
        require(isinstance(row['task_key'],str) and re.fullmatch(r't[1-9][0-9]*',row['task_key']) is not None)
        require(row['task_key'] not in admitted|excluded_keys)
        excluded_keys.add(row['task_key'])
        require(isinstance(row['reason'],str) and re.fullmatch(r'[a-z][a-z0-9_]{0,79}',row['reason']) is not None)
        if row['status']=='duplicate':
            require(isinstance(row['representative'],str) and row['representative'] in admitted)
    count=report['diagnostic_count']
    diagnostics=report['diagnostics']
    require(isinstance(diagnostics,list) and len(diagnostics)<=MAX_DIAGNOSTICS)
    require(type(count) is int and count>=len(diagnostics))
    require(type(report['diagnostics_limited']) is bool and report['diagnostics_limited']==(count>len(diagnostics)))
    require(report['known_constraint_status']==('diagnostics_found' if count else 'no_known_violation'))
    risks=report['diagnostic_claim_ids']
    require(isinstance(risks,list) and all(isinstance(key,str) and bool(key)
        and key==key.strip() and len(key)<=128 for key in risks))
    if claims is not None:
        claim_ids={claim['claim_id'] for claim in claims}
        require(all(key in claim_ids for key in risks))
    require(len(risks)==len(set(risks)) and bool(risks)==bool(count))
    rules={'possible_attribution_loss','possible_negation_degree_loss','possible_modality_mismatch',
           'unmatched_claim_scope','ambiguous_claim_scope'}
    if validator['version'] == ATOMIC_ASSESSMENT_VERSION:
        rules |= {'possible_current_action_as_future', 'possible_project_capacity_basis_loss'}
    for row in diagnostics:
        require(isinstance(row,dict) and set(row)=={'task_key','claim_id','source_span_id','rule_code'})
        require(isinstance(row['rule_code'],str) and row['rule_code'] in rules and row['claim_id'] in risks)
        if row['rule_code'] in {'unmatched_claim_scope','ambiguous_claim_scope'}:
            require(row['task_key'] is None and row['source_span_id'] is None)
        else:
            require(isinstance(row['task_key'],str) and row['task_key'] in requested)
            require(isinstance(row['source_span_id'],str) and re.fullmatch(
                r'urn:company-wiki:evidence-span:sha256:[a-f0-9]{64}',row['source_span_id']) is not None)
    return report


def validate_assessment_material(
    value: Any, evidence_spans: Sequence[EvidenceSpan], reading_context: Mapping[str,Any] | None,
    claims: Sequence[Mapping[str,Any]], *, plan_max_claims: int,
    assessor_version: str | None = None,
) -> dict[str,Any]:
    """Recompute all source observations; recorded software recipe stays historical."""
    report=validate_assessment_wire(value,claims)
    version = report['validator']['version']
    if assessor_version is not None and assessor_version != version:
        raise ValueError('summary assessor differs from the declared protocol')
    view=compile_scoped_material_view(evidence_spans,reading_context,max_claims=plan_max_claims)
    expected=assess_summary_material(evidence_spans,reading_context,claims,
        requested_task_keys=[task.key for task in view.model_tasks],plan_max_claims=plan_max_claims,
        assessor_version=version)
    # This field records the producing implementation, not permission or a
    # claim that today's installed files are identical to immutable history.
    expected['validator']=report['validator']
    if report!=expected:
        raise ValueError('summary assessment differs from its actual source/claims')
    return report


def validate_assessment_quality(report: Mapping[str,Any], claims: Sequence[Mapping[str,Any]],
                                draft_status: str) -> None:
    """Program diagnostics remain visible after every later quality projection."""
    if (report['diagnostic_count'] or not report['requested_emission_complete']) and draft_status!='needs_review':
        raise ValueError('incomplete or risky assessed summary must retain quality diagnostics')
    risks=set(report['diagnostic_claim_ids'])
    if any(claim['claim_id'] in risks and claim.get('needs_review') is not True for claim in claims):
        raise ValueError('assessed claim lost its program quality diagnostic')
