"""Finite task-emission and source-constraint observations, never an NLI verdict.

This module consumes already selected source scopes. It neither reads originals
nor rewrites missing facts, creates tasks, retries a model or authorizes usage.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from company_wiki.document_model.text_matching import matching_reading_text
from company_wiki.implementation_identity import code_sha256
from .narrative_claims import summary_claim_type_for_roles, summary_claims_sha256
from company_wiki.document_understanding.summary_tasks import SourceSummaryTask
from company_wiki.source_contract import EvidenceSpan
from company_wiki.wire_json import canonical_json, canonical_json_hash, encoding_sha256, plain_json
from .narrative_contracts import NarrativeSelectResult
from .narrative_summary_material import compile_scoped_material_view, scoped_material_sha256
from .narrative_summary_protocols import CLAUSE_SCOPE_ASSESSMENT_VERSION

ASSESSMENT_SCHEMA = 'summary-assessment/1'
ASSESSMENT_VERSION = 'source-summary-assessment/1.0.0'
ATOMIC_ASSESSMENT_VERSION = 'source-summary-assessment/1.1.0'
QUALIFIED_ASSESSMENT_VERSION = 'source-summary-assessment/1.2.0'
_QUALIFIER_ASSESSMENTS = frozenset({QUALIFIED_ASSESSMENT_VERSION, CLAUSE_SCOPE_ASSESSMENT_VERSION})
ASSESSMENT_VERSIONS = frozenset({
    ASSESSMENT_VERSION, ATOMIC_ASSESSMENT_VERSION, *_QUALIFIER_ASSESSMENTS,
})
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
    from company_wiki.document_model.reading_identity import text_matching_sha256
    from company_wiki.document_understanding.reading_identity import (
        assertion_frames_sha256, source_cards_sha256, summary_tasks_sha256,
    )
    dependencies = {
        'matching': text_matching_sha256(), 'task_plan': summary_tasks_sha256(),
        'admission': source_cards_sha256(), 'scoped_view': scoped_material_sha256(),
        'encoding': encoding_sha256(), 'claim_roles': summary_claims_sha256(),
        'assessment': code_sha256(__file__),
    }
    if version == ATOMIC_ASSESSMENT_VERSION or version in _QUALIFIER_ASSESSMENTS:
        dependencies['assertion_frames'] = assertion_frames_sha256()
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


def source_frame_modality_diagnostics(source: str, claim: str, modality: str) -> list[dict[str, str]]:
    """Observe source-frame modality not covered by the original lexical rules."""
    from company_wiki.document_understanding.assertion_frames import source_assertion_frames

    result: list[dict[str, str]] = []
    if modality not in {'planned', 'forecast', 'uncertain'}:
        claim_frames = source_assertion_frames(claim)
        if any(frame.future_marker and any(
                _same_proposition(frame.matching_text, part.matching_text)
                for part in claim_frames
        ) for frame in source_assertion_frames(source)):
            result.append({'rule_code': 'possible_modality_mismatch'})
    return [dict(rule_code=code) for code in dict.fromkeys(row['rule_code'] for row in result)]


def qualified_prose_diagnostics(source: str, claim: str, modality: str) -> list[dict[str, str]]:
    """Observe finite source-frame modality without changing historical rules."""
    result = atomic_prose_diagnostics(source, claim, modality)
    result.extend(source_frame_modality_diagnostics(source, claim, modality))
    return [dict(rule_code=code) for code in dict.fromkeys(row['rule_code'] for row in result)]


def _historical_condition_losses(evidence_spans, support, cited, claim_frames):
    """Replay 1.2's span-level condition semantics for immutable assessments."""
    from company_wiki.document_understanding.assertion_frames import source_assertion_frames

    frames_by_span = {span.span_id: source_assertion_frames(span.raw_text or '')
                      for span in evidence_spans if span.span_id in cited}
    matching_support = {
        sid for sid in support
        if any(_same_proposition(frame.matching_text, part.matching_text)
               for frame in frames_by_span[sid] for part in claim_frames)
    }
    if any(
        frame.anaphoric_pending_condition and _same_proposition(frame.matching_text, part.matching_text)
        for frames in frames_by_span.values() for frame in frames for part in claim_frames
    ):
        return
    has_matching_support = False
    for sid, frames in frames_by_span.items():
        if has_matching_support and any(frame.anaphoric_pending_condition for frame in frames):
            yield sid
        has_matching_support = has_matching_support or sid in matching_support


def _condition_losses(evidence_spans, support, cited, claim_frames):
    """Diagnose an omitted prerequisite of the preceding proposition in cited source order."""
    from company_wiki.document_understanding.assertion_frames import source_assertion_frames

    conditions = {' '.join(frame.pending_requirement.casefold().split())
                  for frame in claim_frames if frame.pending_requirement}
    previous_scope = None
    antecedent_matches = False
    for span in evidence_spans:
        if span.span_id not in cited:
            previous_scope = None
            antecedent_matches = False
            continue
        scope = (span.source_id, span.structured_value.get('source_role'),
                 span.structured_value.get('speaker'), span.structured_value.get('turn_id'))
        if scope != previous_scope:
            antecedent_matches = False
        previous_scope = scope
        for frame in source_assertion_frames(span.raw_text or ''):
            requirement = frame.pending_requirement
            backward_reference = frame.anaphoric_pending_condition or frame.coordinated_pending_condition
            if not backward_reference:
                proposition = frame.requirement_proposition or frame.matching_text
                antecedent_matches = span.span_id in support and any(
                    _same_proposition(proposition, claim_frame.matching_text) for claim_frame in claim_frames
                )
            if (antecedent_matches and requirement
                    and ' '.join(requirement.casefold().split()) not in conditions):
                yield span.span_id


def claim_qualifier_diagnostics(
    evidence_spans: Sequence[EvidenceSpan], support_ids: Sequence[str],
    context_ids: Sequence[str], claim: str, modality: str, *, include_existing_atomic: bool = True,
    assessor_version: str = CLAUSE_SCOPE_ASSESSMENT_VERSION,
) -> list[dict[str, str]]:
    """Cited support supplies the proposition, and cited context can qualify it."""
    from company_wiki.document_understanding.assertion_frames import source_assertion_frames

    by_id = {span.span_id: span for span in evidence_spans}
    support = [sid for sid in support_ids if sid in by_id]
    cited = set(support) | {sid for sid in context_ids if sid in by_id}
    diagnostics: list[dict[str, str]] = []
    for sid in support:
        source_text = by_id[sid].raw_text or ''
        direct = (qualified_prose_diagnostics(source_text, claim, modality)
                  if include_existing_atomic else
                  source_frame_modality_diagnostics(source_text, claim, modality))
        diagnostics.extend({'source_span_id': sid, **row}
                           for row in direct)

    condition_losses = (_historical_condition_losses if assessor_version == QUALIFIED_ASSESSMENT_VERSION
                        else _condition_losses)
    diagnostics.extend(
        {'source_span_id': sid, 'rule_code': 'possible_condition_scope_loss'}
        for sid in condition_losses(evidence_spans, set(support), cited, source_assertion_frames(claim))
    )
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for row in diagnostics:
        unique[(row['source_span_id'], row['rule_code'])] = row
    return list(unique.values())


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
    if version == ATOMIC_ASSESSMENT_VERSION:
        diagnostics_for_prose = atomic_prose_diagnostics
    else:
        diagnostics_for_prose = prose_diagnostics
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
        if version in _QUALIFIER_ASSESSMENTS:
            rows = claim_qualifier_diagnostics(
                evidence_spans, task.support_ids, task.context_ids,
                claim['text'], claim['modality'], assessor_version=version,
            )
            for row in rows:
                record({'task_key': task.key, 'claim_id': claim['claim_id'], **row})
        else:
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
    return result


def validate_assessment_wire(value: Any, claims: Sequence[Mapping[str,Any]] | None) -> dict[str,Any]:
    """Shape/algebra only without source material; full binding is checked below."""
    import json
    fields={'schema_version','validator','source_plan_sha256','plan_max_claims',
        'source_admission_sha256','claims_sha256','scope','source_admitted_task_keys',
        'requested_task_keys','emitted_task_keys','missing_requested_task_keys',
        'budget_deferred_task_keys','excluded_tasks','requested_emission_complete',
        'admitted_emission_complete','subfact_coverage_status','semantic_status',
        'known_constraint_status','diagnostics','diagnostic_count','diagnostics_limited','diagnostic_claim_ids'}
    if not isinstance(value,Mapping) or set(value)!=fields:
        raise ValueError('invalid summary assessment fields')
    encoded=canonical_json(plain_json(value)).encode('utf-8')
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
    if validator['version'] == ATOMIC_ASSESSMENT_VERSION or validator['version'] in _QUALIFIER_ASSESSMENTS:
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
    if validator['version'] in _QUALIFIER_ASSESSMENTS:
        rules |= {'possible_current_action_as_future', 'possible_project_capacity_basis_loss',
                  'possible_condition_scope_loss'}
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
    historical_assessor_versions: tuple[str, ...] = (),
) -> dict[str,Any]:
    """Recompute all source observations; recorded software recipe stays historical."""
    report=validate_assessment_wire(value,claims)
    version = report['validator']['version']
    if assessor_version is not None and version not in (assessor_version, *historical_assessor_versions):
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


def assessment_sha256() -> str:
    return code_sha256(__file__)


__all__ = ['ASSESSMENT_MAX_BYTES', 'ASSESSMENT_SCHEMA', 'ASSESSMENT_VERSION', 'ASSESSMENT_VERSIONS', 'ATOMIC_ASSESSMENT_VERSION', 'CLAUSE_SCOPE_ASSESSMENT_VERSION', 'MAX_DIAGNOSTICS', 'QUALIFIED_ASSESSMENT_VERSION', 'assess_summary', 'assess_summary_material', 'assessment_identity', 'assessment_sha256', 'atomic_prose_diagnostics', 'claim_qualifier_diagnostics', 'prose_diagnostics', 'qualified_prose_diagnostics', 'source_frame_modality_diagnostics', 'validate_assessment_material', 'validate_assessment_quality', 'validate_assessment_wire']
