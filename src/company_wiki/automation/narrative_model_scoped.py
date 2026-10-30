"""One local presentation of source-owned summary tasks; no model calls.

Shared original fragments remain a graph. Every fragment body is defined once
and all other uses are references. This compiler reduces global alias lookup;
neither a legal task nor a legal basis proves a paraphrase semantically true.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import json
import logging
from pathlib import Path
from types import MappingProxyType
from typing import Any

from company_wiki.document_understanding.summary_tasks import SourceSummaryTask, SummaryTaskPlan, build_summary_task_plan
from company_wiki.document_understanding.source_cards import SourceCard, source_cards, source_task_admission
from company_wiki.source_contract import EvidenceSpan

from .models import canonical_json, canonical_json_hash
from .narrative_contracts import NarrativeSelectResult
from .narrative_summary_protocols import LEGACY_SCOPED, ScopedSummaryProtocol, scoped_protocol_for_prompt


SCOPED_VIEW_SCHEMA = "source-scoped-model-view/1"
SCOPED_MODEL_PROJECTION_VERSION = 'reading-model-input/4'
# A long filing's selection turns into dozens of local task groups; a twenty
# clause ceiling made a real provider drop required facts (CN covered 8 of 10,
# and the 22-clause draft that covered them was rejected). Forty keeps the
# summary bounded while leaving room for every selected business update.
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
    'do not output them. Respect output_plan.max_claims_per_task per task and '
    'output_plan.max_claims in total; the response schema arrays are bounded but the '
    'program enforces the smaller per-task cap, so exceeding it rejects the whole response. '
    'Each clause is at most 280 characters. Emit up to output_plan.target_claim_count '
    'clauses (never more than output_plan.max_claims in total), at most '
    'output_plan.max_claims_per_task per task. Review all supplied tasks before selecting '
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
    'Respect output_plan.max_claims and max_claims_per_task and the configured output token limit. '
    'Each clause is at most 280 characters. When the finite output budget cannot cover everything, '
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
        supported = {sid for task in view.model_tasks for sid in task.support_ids}
        material['source_frame_hints'] = compact_frame_hints(
            (view._source_keys[sid], view._spans[sid].raw_text or '')
            for sid in view.plan.evidence_order if sid in supported)
    return material


def scoped_response_schema(per_task_cap: int = 20) -> dict[str, Any]:
    """One finite clause schema, not one copy per task.

    The array bound is the enforced share of the global cap, so a provider that
    follows the schema cannot exceed the contract even when it ignores prose.
    """
    cap = max(1, min(20, int(per_task_cap)))
    return {'type': 'object', 'required': ['drafts_by_task'], 'additionalProperties': False,
        'properties': {'drafts_by_task': {'type': 'object', 'additionalProperties': {
            'type': 'array', 'maxItems': cap, 'items': {
                'type': 'object', 'required': ['text', 'basis_parts', 'modality'],
                'additionalProperties': False, 'properties': {
                    'text': {'type': 'string', 'minLength': 1, 'maxLength': 280},
                    'basis_parts': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                    'items': {'type': 'string', 'minLength': 1}},
                    'modality': {'enum': ['actual', 'planned', 'forecast', 'question', 'negation', 'uncertain']},
                }}}}}}


def scoped_boundary_identity(boundary, *, protocol: ScopedSummaryProtocol = LEGACY_SCOPED) -> dict[str, Any]:
    from company_wiki.document_understanding import (
        summary_tasks, source_cards as source_card_module, reading_context_contract,
    )
    from company_wiki.source_catalog import narrative_evidence
    from company_wiki import narrative_subject
    from . import models, narrative_contracts, narrative_model, narrative_model_runtime, narrative_summary_protocols

    dependencies = {}
    for name, module in {
            'runtime': narrative_model_runtime, 'scoped_protocol': __import__(__name__, fromlist=['']),
            'source_task_plan': summary_tasks, 'role_quality_owner': narrative_evidence,
            'source_task_availability': source_card_module,
            'source_use_contract': reading_context_contract,
            'legacy_utilities': narrative_model, 'canonical_contracts': narrative_contracts,
            'canonical_encoding': models, 'subject_contracts': narrative_subject,
            'summary_protocol_recipes': narrative_summary_protocols,
        }.items():
        filename = module.__file__
        if filename is None:
            raise narrative_model.ModelResponseError('READING_MODEL_IMPLEMENTATION_UNAVAILABLE')
        dependencies[name] = hashlib.sha256(Path(filename).read_bytes()
            .replace(b'\r\n', b'\n').replace(b'\r', b'\n')).hexdigest()
    if protocol.assess_fidelity:
        from .narrative_summary_assessment import assessment_identity
        dependencies['summary_assessment'] = canonical_json_hash(assessment_identity(protocol.assessor_version))
    if protocol.material_profile == 'source_frames/1':
        from . import narrative_frame_hints
        dependencies['source_frame_hints'] = hashlib.sha256(
            Path(narrative_frame_hints.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
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
    # Ask for fewer than the hard cap so a model that overshoots by a clause or
    # two still lands inside the contract instead of dead-lettering the item.
    target = (min(MAX_SUMMARY_CLAIMS,max(1,task_count*2)) if protocol.output_profile == 'coverage'
              else min(MAX_SUMMARY_CLAIMS - 4, max(1, task_count)))
    if target_override is not None:
        target = max(1, min(target, int(target_override)))
    if max_output_tokens is not None:
        target = min(target, max(1, (max_output_tokens - 256) // 320))
    return {'max_claims': MAX_SUMMARY_CLAIMS, 'target_claim_count': target, 'target_text_chars': 240,
        # The response schema can only bound each task array; this is the hard
        # per-task share of the global cap the decoder actually enforces.
        'max_claims_per_task': (min(6,max(2,MAX_SUMMARY_CLAIMS//max(1,task_count)))
                                if protocol.output_profile == 'coverage' else 2),
        'configured_output_tokens': max_output_tokens, 'coverage': 'selected_source_tasks_only',
        'planning': 'soft_target_within_existing_caps'}


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
    # The task-plan binding keeps its original twenty-claim marker for wire
    # compatibility; the effective summary budget is output_plan.max_claims
    # (MAX_SUMMARY_CLAIMS) and the decoder enforces the same number.
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
    from company_wiki.source_catalog.narrative_evidence import (
        SummaryValidationError, project_summary_claim_quality, summary_claim_type_for_roles,
        validate_summary_claim,
    )
    from . import narrative_model as legacy
    from .narrative_contracts import NarrativeContractError, _claim_from_dict, _claim_to_dict, assert_no_physical_paths
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
    if count > MAX_SUMMARY_CLAIMS:
        raise NarrativeContractError('summary claims exceed forty')
    view = compile_scoped_model_view(selected, max_claims=MAX_SUMMARY_CLAIMS)
    per_task_cap = _scoped_output_plan(len(view.model_tasks) if protocol.assess_fidelity else len(tasks),
                                      protocol=protocol)['max_claims_per_task']
    if any(len(rows) > per_task_cap for rows in tasks.values()):
        raise NarrativeContractError('scoped task clauses exceed per-task cap')
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
                assert_no_physical_paths(claim)
                typed = _claim_from_dict(claim)
                if len(typed.text) > 280:
                    raise NarrativeContractError('summary claim text exceeds 280 characters')
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


@dataclass(frozen=True)
class ScopedClaimBinding:
    task_key: str
    basis_ids: tuple[str, ...]
    support_ids: tuple[str, ...]
    context_ids: tuple[str, ...]
    semantic_status: str = "not_evaluated"


@dataclass(frozen=True)
class ScopedModelView:
    plan: SummaryTaskPlan
    _spans: Mapping[str, EvidenceSpan]
    _source_keys: Mapping[str, str]
    _parts: Mapping[str, Mapping[str, str]]
    # A repair may display only a subset of source-admitted tasks. The complete
    # source plan remains available, including unsupported and duplicate scopes.
    visible_keys: frozenset[str] | None = None
    _admission: Mapping[str, Mapping[str, str]] | None = None
    _cards: Mapping[str, SourceCard] | None = None

    @property
    def admitted_task_keys(self) -> frozenset[str]:
        return frozenset(task.key for task in self.plan.tasks if self._admission is None
                         or self._admission[task.key]['status'] == 'admitted')

    @property
    def model_tasks(self) -> tuple[SourceSummaryTask, ...]:
        allowed = self.admitted_task_keys
        return tuple(task for task in self.plan.tasks if task.key in allowed
                     and (self.visible_keys is None or task.key in self.visible_keys))

    def to_binding(self) -> dict[str, Any]:
        """Program-owned exact identity; local keys never replace source IDs."""
        return {"schema_version": SCOPED_VIEW_SCHEMA, "source_plan": self.plan.to_binding(),
                "source_keys": dict(self._source_keys),
                "task_parts": {key: dict(parts) for key, parts in self._parts.items()},
                "source_admission": {key: dict(value) for key, value in (self._admission or {}).items()}}

    @property
    def binding_sha256(self) -> str:
        return canonical_json_hash(self.to_binding())

    def to_model_dict(self) -> dict[str, Any]:
        visible = self.model_tasks
        counts = Counter(sid for task in visible for sid in task.member_ids)

        def source_role(span):
            role = span.structured_value.get("source_role", "unknown")
            return role if isinstance(role, str) else "unknown"

        def frequent(values, fallback):
            return Counter(values).most_common(1)[0][0] if values else fallback

        visible_ids = [sid for sid in self.plan.evidence_order if counts[sid] > 0]
        fragment_defaults = {
            "source_role": frequent([source_role(self._spans[sid]) for sid in visible_ids], "unknown"),
            "quality_flags": list(frequent([self._spans[sid].quality_flags for sid in visible_ids], ())),
        }
        task_defaults = {
            "kind": frequent([task.kind for task in visible], "standalone"),
            "section_role": frequent([task.section_role for task in visible], "unknown"),
            "topics": list(frequent([task.topics for task in visible], ())),
            "support_parts": "all_parts", "context_parts": [],
        }

        def without_defaults(value, defaults):
            return {key: item for key, item in value.items() if key not in defaults or item != defaults[key]}

        def body(sid):
            span = self._spans[sid]
            return without_defaults({"source_key": self._source_keys[sid], "text": span.raw_text,
                    "source_role": source_role(span), "quality_flags": list(span.quality_flags)}, fragment_defaults)

        shared = [body(sid) for sid in self.plan.evidence_order if counts[sid] > 1]
        tasks = []
        for task in visible:
            parts = self._parts[task.key]
            support = [key for key, sid in parts.items() if sid in task.support_ids]
            tasks.append(without_defaults({
                "key": task.key, "kind": task.kind, "section_role": task.section_role,
                # Machine selection reason codes stay in the causal binding;
                # the model receives observed business topics, not diagnostics.
                "topics": list(task.topics),
                "support_parts": "all_parts" if support == list(parts) else support,
                "context_parts": [key for key, sid in parts.items() if sid in task.context_ids],
                "parts": [{"key": key, **({"shared_ref": self._source_keys[sid]}
                            if counts[sid] > 1 else body(sid))} for key, sid in parts.items()],
            }, task_defaults))
            hint = self._cards[task.key].reading_hint() if self._cards is not None else {}
            if hint:
                tasks[-1]['reading'] = hint
        return {"schema_version": SCOPED_VIEW_SCHEMA, "scope": "selected_source_tasks_only",
                "max_claims": self.plan.max_claims, "available_task_count": len(tasks),
                "fragment_defaults": fragment_defaults, "task_defaults": task_defaults,
                "shared_fragments": shared, "tasks": tasks}

    def resolve_basis(self, task_key: object, part_keys: object) -> ScopedClaimBinding:
        if not isinstance(task_key, str) or task_key not in self._parts:
            raise ValueError("scoped draft references an unknown source task")
        if task_key not in self.admitted_task_keys:
            raise ValueError("scoped draft references unavailable or duplicate source support")
        if (not isinstance(part_keys, list) or not part_keys
                or any(not isinstance(key, str) for key in part_keys)
                or len(part_keys) != len(set(part_keys))):
            raise ValueError("scoped draft requires unique task-local factual basis parts")
        parts = self._parts[task_key]
        task = next(task for task in self.plan.tasks if task.key == task_key)
        if any(key not in parts or parts[key] not in task.support_ids for key in part_keys):
            raise ValueError("scoped basis cannot borrow another task or context-only facts")
        selected = {parts[key] for key in part_keys}
        # Preserve the existing native scope closure; selecting a local basis
        # does not silently remove its source-owned qualifiers or QA context.
        return ScopedClaimBinding(task_key, tuple(sid for sid in task.support_ids if sid in selected),
                                  task.support_ids, task.context_ids)


def compile_scoped_model_view(selected: NarrativeSelectResult, *, max_claims: int) -> ScopedModelView:
    """Compile a transient view of this pinned selection, with no extra IO."""
    return compile_scoped_material_view(selected.evidence_spans,selected.reading_context,max_claims=max_claims)


def compile_scoped_material_view(evidence_spans, reading_context, *, max_claims: int) -> ScopedModelView:
    """The same compiler for an already validated selection or public bundle."""
    plan = build_summary_task_plan(evidence_spans,reading_context=reading_context,max_claims=max_claims)
    known = {span.span_id: span for span in evidence_spans}
    cards = tuple(source_cards(plan, known))
    admission = source_task_admission(cards)
    return ScopedModelView(plan,
        MappingProxyType(known),
        MappingProxyType({sid: "s" + str(i) for i, sid in enumerate(plan.evidence_order, 1)}),
        MappingProxyType({task.key: MappingProxyType({"p" + str(i): sid
            for i, sid in enumerate(task.member_ids, 1)}) for task in plan.tasks}),
        _admission=MappingProxyType({key: MappingProxyType(value) for key, value in admission.items()}),
        _cards=MappingProxyType({card.task.key: card for card in cards}))
