"""One local presentation of source-owned summary tasks; no model calls.

Shared original fragments remain a graph. Every fragment body is defined once
and all other uses are references. This compiler reduces global alias lookup;
neither a legal task nor a legal basis proves a paraphrase semantically true.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import logging
from typing import Any

from company_wiki.implementation_identity import code_sha256
from company_wiki.source_catalog.narrative_contracts import narrative_wire_sha256
from company_wiki.source_catalog.narrative_summary_material import (
    SCOPED_VIEW_SCHEMA as SCOPED_VIEW_SCHEMA,
    ScopedClaimBinding as ScopedClaimBinding,
    ScopedModelView as ScopedModelView,
    compile_scoped_material_view as compile_scoped_material_view,
    scoped_material_sha256,
)
from company_wiki.wire_json import encoding_sha256

from .models import canonical_json, canonical_json_hash
from .narrative_contracts import NarrativeSelectResult
from .narrative_summary_protocols import LEGACY_SCOPED, ScopedSummaryProtocol, scoped_protocol_for_prompt


SCOPED_MODEL_PROJECTION_VERSION = 'reading-model-input/4'
# Compatibility name for prompt planning only, never result validity.
MAX_SUMMARY_CLAIMS = 40
SCOPED_PROMPT_VERSION = 'reading-source-scoped/4.1.0'
SCOPED_REQUEST_SCHEMA = 'narrative-model-request/5'
_LOG = logging.getLogger(__name__)
SCOPED_INSTRUCTION = (
    'Summarize only the supplied original-language source tasks. No translation. '
    'Return one JSON object containing drafts_by_task, a sparse object keyed by supplied task keys. '
    'Each task value is an array of clauses, each containing only text, basis_parts and modality. '
    'basis_parts contains unique task-local pN factual support parts, never context-only parts '
    'or another task. Shared source fragments are references, not new facts. Preserve all '
    'subject, product, stage, negation, conditions, values, currency, units and periods. '
    'A source question is not a management statement. Do not infer a contract from an intention. '
    'Preserve original names and product codes. Do not copy task defaults as business facts. '
    'Source identity, language, claim IDs, claim types and quality belong to the program; '
    'do not output them. Use output_plan as advisory compression targets, not '
    'result validity quotas. Preserve each complete qualified fact within the '
    'configured output token budget. Review all supplied tasks before selecting '
    'the most important distinct business updates, their causes and next actions. Reading '
    'hints are program-owned source priorities and value, not business facts; lower priority '
    'numbers take precedence and meaningful facts precede descriptions. Never pad with '
    'headings, metric definitions, generic principles or table numbers whose column, '
    'period, currency or unit is unresolved. A cause with an unresolved subject is not '
    'a standalone fact. Merge repetition only when subject, product, stage, period and '
    'meaning agree; an identical current value does not replace its comparison or causes. '
    'Omit a task with no direct complete support rather than invent support. Do not output reasoning, '
    'Markdown, research conclusions, valuation, ratings or paths. Valid local citations do '
    'not prove that rewritten prose is true.'
)
FIDELITY_INSTRUCTION = (
    'Summarize the supplied original-language source tasks. No translation. '
    'Return only one JSON object with drafts_by_task, keyed by supplied task keys. '
    'Each task is an array of clauses with only text, basis_parts and modality. '
    'Use unique task-local pN factual support parts; never context-only parts or another task. '
    'Cover each supplied supported task before adding detail. Include useful customer chains, '
    'already-sold product ranges and developed-product counts; do not merge developed and sold sets. '
    'Preserve subject, subsidiary, product, stage, period, value, currency and unit. '
    'Preserve reported/news attribution, the degree of a denial, completion conditions and intentions. '
    'Each clause must have a single modality: actual, planned, forecast, negation, question or uncertain. '
    'Separate completed actions, negative statements and future intentions into distinct clauses. '
    'A pending application is not an approval, an intention is not a signed contract, and a source '
    'question is not management confirmation. Do not remove material from a denial of material impact. '
    'Use only directly supported complete facts, not headings, generic aspirations, unresolved table '
    'numbers or inferred company claims. Preserve original names and product codes. '
    'Program reading hints and task defaults are not business facts. '
    'Use output_plan as advisory compression targets and respect the configured output token limit. '
    'Do not shorten away qualifications to meet a clause or character quota. When the finite output budget cannot cover everything, '
    'prioritize distinct material facts and their causes; do not invent facts to fill a task. '
    'Do not output identities, quality flags, reasoning, Markdown, paths, investment conclusions or ratings. '
    'Correct citations do not prove that paraphrased prose is true.'
)
ATOMIC_INSTRUCTION = FIDELITY_INSTRUCTION + (
    ' Every clause can be selected independently: repeat its necessary actor, counterparty, '
    'reporting source and conditions instead of relying on a previous summary clause or pronoun. '
    'A source-only reporting prefix also governs its explicitly coordinated continuation; '
    'do not turn one party reporting a wish into both parties agreeing. Preserve that distinction '
    'even when contact and future cooperation are separate clauses. '
    'Actual includes explicitly ongoing current activities, not only completed events. '
    'Actively developing or continuously improving without a future marker is not a planned action. '
    'Separate project-start events from project design/planned capacity specifications. '
    'Attach the project stage and completion condition to the numeric capacity statement itself; '
    'do not present designed capacity as commissioned capacity, output or shipments. '
    'source_frame_hints are bounded, possibly incomplete source observations referenced by '
    'source_key and normalized clause ordinal, not quotations, business facts or truth judgments. '
    'Always check original source text; absent or limited hints never mean a task may be omitted.'
)


def scoped_instruction(protocol: ScopedSummaryProtocol) -> str:
    return {'legacy': SCOPED_INSTRUCTION, 'fidelity': FIDELITY_INSTRUCTION,
            'atomic': ATOMIC_INSTRUCTION}[protocol.instruction_profile]


def scoped_model_material(view, protocol: ScopedSummaryProtocol) -> dict[str, Any]:
    material = view.to_model_dict()
    if protocol.material_profile == 'source_frames/1':
        from .narrative_frame_hints import compact_frame_hints
        material['source_frame_hints'] = compact_frame_hints(view.source_hint_inputs())
    return material


def scoped_response_schema(per_task_cap: int = 20) -> dict[str, Any]:
    """Validate clause shape; actual configured transport/token limits own size.

    The legacy argument is a planning hint, not a result permission.
    """
    return {'type': 'object', 'required': ['drafts_by_task'], 'additionalProperties': False,
        'properties': {'drafts_by_task': {'type': 'object', 'additionalProperties': {
            'type': 'array', 'items': {
                'type': 'object', 'required': ['text', 'basis_parts', 'modality'],
                'additionalProperties': False, 'properties': {
                    'text': {'type': 'string', 'minLength': 1},
                    'basis_parts': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                    'items': {'type': 'string', 'minLength': 1}},
                    'modality': {'enum': ['actual', 'planned', 'forecast', 'question', 'negation', 'uncertain']},
                }}}}}}


def scoped_boundary_identity(boundary, *, protocol: ScopedSummaryProtocol = LEGACY_SCOPED) -> dict[str, Any]:
    from company_wiki.document_understanding.reading_identity import (
        reading_context_sha256, source_cards_sha256, summary_tasks_sha256,
    )
    from company_wiki.narrative_subject import subject_contract_sha256
    from company_wiki.source_catalog.narrative_claims import summary_claims_sha256
    from . import narrative_model, narrative_model_runtime
    from company_wiki.source_catalog.narrative_summary_protocols import summary_protocols_sha256

    modules = {
        'runtime': narrative_model_runtime,
        'legacy_utilities': narrative_model,
    }
    try:
        dependencies = {
            name: code_sha256(module.__file__, universal_newlines=True)
            for name, module in modules.items()
        }
        dependencies.update({
            'scoped_protocol': code_sha256(__file__, universal_newlines=True),
            'source_material_compiler': scoped_material_sha256(universal_newlines=True),
            'canonical_contracts': narrative_wire_sha256(universal_newlines=True),
            'canonical_encoding': encoding_sha256(universal_newlines=True),
            'summary_protocol_recipes': summary_protocols_sha256(universal_newlines=True),
            'source_task_plan': summary_tasks_sha256(universal_newlines=True),
            'role_quality_owner': summary_claims_sha256(universal_newlines=True),
            'source_task_availability': source_cards_sha256(universal_newlines=True),
            'source_use_contract': reading_context_sha256(universal_newlines=True),
            'subject_contracts': subject_contract_sha256(universal_newlines=True),
        })
    except ValueError as exc:
        raise narrative_model.ModelResponseError('READING_MODEL_IMPLEMENTATION_UNAVAILABLE') from exc
    if protocol.assess_fidelity:
        from .narrative_summary_assessment import assessment_identity
        dependencies['summary_assessment'] = canonical_json_hash(assessment_identity(protocol.assessor_version))
    if protocol.material_profile == 'source_frames/1':
        from . import narrative_frame_hints
        dependencies['source_frame_hints'] = code_sha256(narrative_frame_hints.__file__)
    instruction = scoped_instruction(protocol)
    return {'schema_version': 'reading-model-boundary/1',
        'reading_projection_version': boundary.reading_projection_version,
        'prompt_version': boundary.prompt_version, 'request_schema': boundary.request_schema,
        'decoder_version': boundary.decoder_version,
        'instruction_sha256': hashlib.sha256(instruction.encode()).hexdigest(),
        'response_schema_sha256': canonical_json_hash(scoped_response_schema()),
        'decoder_sha256': canonical_json_hash(dependencies), 'implementation_dependencies': dependencies}


def _scoped_output_plan(task_count: int, max_output_tokens: int | None = None,
                        *, target_override: int | None = None,
                        protocol: ScopedSummaryProtocol = LEGACY_SCOPED) -> dict[str, Any]:
    from .narrative_model import ModelResponseError
    if max_output_tokens is not None and (type(max_output_tokens) is not int or max_output_tokens <= 0):
        raise ModelResponseError('model output budget must be a positive integer')
    # Ask for compact output. These targets never decide whether completed
    # source-valid output may be consumed; actual resources are enforced below HTTP.
    target = (min(MAX_SUMMARY_CLAIMS,max(1,task_count*2)) if protocol.output_profile == 'coverage'
              else min(MAX_SUMMARY_CLAIMS - 4, max(1, task_count)))
    if target_override is not None:
        target = max(1, min(target, int(target_override)))
    if max_output_tokens is not None:
        target = min(target, max(1, (max_output_tokens - 256) // 320))
    return {'max_claims': MAX_SUMMARY_CLAIMS, 'target_claim_count': target, 'target_text_chars': 240,
        # Retain historical plan field names as advisory allocation hints.
        'max_claims_per_task': (min(6,max(2,MAX_SUMMARY_CLAIMS//max(1,task_count)))
                                if protocol.output_profile == 'coverage' else 2),
        'configured_output_tokens': max_output_tokens, 'coverage': 'selected_source_tasks_only',
        'planning': 'advisory_targets_not_result_limits'}


from .narrative_model import NarrativeModelRequest as _LegacyModelRequest  # noqa: E402


@dataclass(frozen=True)
class ScopedModelRequest(_LegacyModelRequest):
    """Actual HTTP base type, with this explicit protocol's output-budget owner."""
    def with_output_budget(self, max_output_tokens: int) -> _LegacyModelRequest:
        from .narrative_model import ModelResponseError
        try:
            envelope = json.loads(self.data_json)
            protocol = scoped_protocol_for_prompt(self.prompt_version)
            if envelope['schema_version'] != protocol.request_schema:
                raise ModelResponseError('MODEL_REQUEST_INVALID')
            plan = _scoped_output_plan(envelope['material']['available_task_count'], max_output_tokens,protocol=protocol)
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelResponseError('MODEL_REQUEST_INVALID') from exc
        if envelope.get('output_plan') == plan:
            return self
        envelope['output_plan'] = plan
        return ScopedModelRequest(self.prompt_version, self.instruction, canonical_json(envelope),
            canonical_json_hash({'selected_input_sha256': self.input_sha256, 'output_plan': plan}))


def build_scoped_request(selected: NarrativeSelectResult, *, only_tasks=None,
                         target_claims: int | None = None,
                         protocol: ScopedSummaryProtocol = LEGACY_SCOPED) -> ScopedModelRequest:
    from . import narrative_model as legacy
    if selected.reading_context is None:
        raise legacy.ModelResponseError('READING_MODEL_CONTEXT_UNAVAILABLE')
    # Task planning retains its protocol marker; completed result validity
    # comes from source bindings and shape, never these compression targets.
    if not protocol.allows_subset and (only_tasks is not None or target_claims is not None):
        raise legacy.ModelResponseError('MODEL_REQUEST_INVALID')
    view = compile_scoped_model_view(selected, max_claims=protocol.plan_max_claims)
    if only_tasks is not None:
        visible = [task for task in view.model_tasks if task.key in only_tasks]
        if not visible:
            raise legacy.ModelResponseError('SUMMARY_INPUT_UNAVAILABLE')
        view = replace(view, visible_keys=frozenset(task.key for task in visible))
    if not view.model_tasks or selected.source_metadata.language not in {'zh', 'en', 'mixed'}:
        raise legacy.ModelResponseError('SUMMARY_INPUT_UNAVAILABLE')
    aliases = ['r' + str(i) for i in range(1, len(selected.reading_context['groups']) + 1)]
    strategy = legacy._reading_model_context(selected.reading_context, aliases,
                                             version=protocol.projection)
    strategy.pop('groups')
    envelope = {'schema_version': protocol.request_schema,
        'subject' if selected.subject.kind == 'official_json' else 'source': {
            'language': selected.source_metadata.language, 'title': selected.source_metadata.title,
            'document_kind': selected.source_metadata.document_kind},
        'material': scoped_model_material(view, protocol), 'reading_strategy': strategy,
        'output_plan': (plan := _scoped_output_plan(
            len(view.model_tasks),
            target_override=target_claims,protocol=protocol)),
        'response_schema': scoped_response_schema(plan['max_claims_per_task'])}
    data_json = canonical_json(envelope)
    instruction = scoped_instruction(protocol)
    return ScopedModelRequest(protocol.prompt, instruction, data_json,
        canonical_json_hash({'prompt_version': protocol.prompt, 'instruction': instruction,
            'data_json': data_json, 'task_binding': view.to_binding(), 'subject': selected.subject.to_dict(),
            'selection': selected.selection.to_dict()}))


def _clause_object(raw: Any) -> dict[str, Any] | None:
    """A clause object, tolerating one JSON-encoding layer from a transport.

    Some OpenAI-compatible servers serialise each array item as a JSON string.
    The bytes still carry the exact object; decode it and keep every contract
    check. A string that is not such an object remains a contract error.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except (json.JSONDecodeError, RecursionError):
            return None
        return decoded if isinstance(decoded, dict) else None
    return None


def decode_scoped_draft(response, *, selected: NarrativeSelectResult,
                        protocol: ScopedSummaryProtocol = LEGACY_SCOPED) -> dict[str, Any]:
    """Recover whole local clauses, never repair IDs or authorize their prose."""
    from company_wiki.source_catalog.narrative_claims import (
        SummaryValidationError, project_summary_claim_quality, summary_claim_type_for_roles,
        validate_summary_claim,
    )
    from . import narrative_model as legacy
    from .narrative_contracts import NarrativeContractError, _claim_from_dict, _claim_to_dict
    if response.prompt_version != protocol.prompt:
        raise legacy.ModelResponseError('model response prompt version differs from request')
    if selected.reading_context is None:
        raise legacy.ModelResponseError('READING_MODEL_CONTEXT_UNAVAILABLE')
    try:
        payload = json.loads(response.response_bytes.decode('utf-8'),
            object_pairs_hook=legacy._unique_object, parse_constant=legacy._invalid_json_number)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise legacy.ModelResponseError('model response is not strict UTF-8 JSON') from exc
    if (not isinstance(payload, dict)
            or set(payload) not in ({'drafts_by_task'}, {'drafts_by_task', 'type'})
            or not isinstance(payload['drafts_by_task'], dict)):
        raise legacy.ModelResponseError('model response must contain only drafts_by_task')
    if 'type' in payload:
        # Some JSON-object transports echo their presentation marker into the
        # generated object. It supplies no source identity or claim semantics.
        if payload['type'] != 'json_object':
            raise legacy.ModelResponseError('unsupported response presentation type')
        _LOG.info('ignored response presentation metadata type=json_object')
    tasks = payload['drafts_by_task']
    if any(not isinstance(rows, list) for rows in tasks.values()):
        raise NarrativeContractError('scoped task clauses must be arrays')
    count = sum(len(rows) for rows in tasks.values())
    view = compile_scoped_model_view(selected, max_claims=MAX_SUMMARY_CLAIMS)
    if set(tasks) - {task.key for task in view.plan.tasks}:
        raise legacy.ModelCitationError('scoped draft references an unknown source task')
    known = {span.span_id: span for span in selected.evidence_spans}
    retained = []
    first_error = None
    for task in view.plan.tasks:
        for ordinal, raw in enumerate(tasks.get(task.key, []), 1):
            raw = _clause_object(raw)
            # Preserve the source-language owner: an explicit translation
            # contradicts the entire response, even if another clause is valid.
            if isinstance(raw, dict):
                legacy._reject_translation(raw)
            try:
                if not isinstance(raw, dict) or set(raw) != {'text', 'basis_parts', 'modality'}:
                    raise NarrativeContractError('scoped clause must contain only text, basis_parts and modality')
                try:
                    binding = view.resolve_basis(task.key, raw['basis_parts'])
                except ValueError as exc:
                    raise legacy.ModelCitationError(str(exc)) from exc
                claim = {'claim_id': task.key + '-' + str(ordinal), 'text': raw['text'],
                    'evidence_ids': list(binding.support_ids),
                    'claim_type': summary_claim_type_for_roles(task.support_roles),
                    'modality': raw['modality'], 'needs_review': False}
                if binding.context_ids:
                    claim['context_evidence_ids'] = list(binding.context_ids)
                typed = _claim_from_dict(claim)
                try:
                    validate_summary_claim(typed, known, 'draft')
                except SummaryValidationError as exc:
                    raise NarrativeContractError(str(exc)) from exc
                retained.append(typed)
            except (NarrativeContractError, legacy.ModelResponseError) as exc:
                if first_error is None:
                    first_error = exc
    if not retained:
        if first_error is not None:
            raise first_error
        raise NarrativeContractError('summary draft must contain at least one claim')
    claims, status = project_summary_claim_quality(retained, evidence_spans=selected.evidence_spans,
                                                  discarded_claims=len(retained) != count)
    identity = ({'subject_id': selected.subject.item_key, 'subject_sha256': selected.subject.subject_sha256}
                if selected.subject.kind == 'official_json' else
                {'source_id': selected.source_ref.source_id, 'source_sha256': selected.source_ref.content_sha256})
    wire_claims = [_claim_to_dict(claim) for claim in claims]
    if protocol.assess_fidelity:
        from .narrative_summary_assessment import assess_summary
        report = assess_summary(selected,wire_claims,plan_max_claims=protocol.plan_max_claims,
                                requested_task_keys=[task.key for task in view.model_tasks],
                                assessor_version=protocol.assessor_version)
        for claim in wire_claims:
            if claim['claim_id'] in report['diagnostic_claim_ids']:
                claim['needs_review'] = True
        if report['diagnostic_count'] or not report['requested_emission_complete']:
            status = 'needs_review'
    return {**identity, 'language': selected.source_metadata.language,
            'claims': wire_claims, 'status': status}


def compile_scoped_model_view(selected: NarrativeSelectResult, *, max_claims: int) -> ScopedModelView:
    """Compile a transient view of this pinned selection, with no extra IO."""
    return compile_scoped_material_view(selected.evidence_spans,selected.reading_context,max_claims=max_claims)
