"""One local presentation of source-owned summary tasks; no model calls.

Shared original fragments remain a graph. Every fragment body is defined once
and all other uses are references. This compiler reduces global alias lookup;
neither a legal task nor a legal basis proves a paraphrase semantically true.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from company_wiki.document_understanding.summary_tasks import SummaryTaskPlan, build_summary_task_plan
from company_wiki.source_contract import EvidenceSpan

from .models import canonical_json, canonical_json_hash
from .narrative_contracts import NarrativeSelectResult


SCOPED_VIEW_SCHEMA = "source-scoped-model-view/1"
SCOPED_MODEL_PROJECTION_VERSION = 'reading-model-input/4'
SCOPED_PROMPT_VERSION = 'reading-source-scoped/4.0.0'
SCOPED_REQUEST_SCHEMA = 'narrative-model-request/5'
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
    'do not output them. Emit at most twenty clauses TOTAL across all tasks, each at most '
    '280 characters. Retain distinct important business updates within the configured output '
    'budget; omit a task rather than invent support. Do not output reasoning, Markdown, '
    'research conclusions, valuation, ratings or paths. Valid local citations do not prove '
    'that rewritten prose is true.'
)


def scoped_response_schema() -> dict[str, Any]:
    """One finite clause schema, not one copy per task."""
    return {'type': 'object', 'required': ['drafts_by_task'], 'additionalProperties': False,
        'properties': {'drafts_by_task': {'type': 'object', 'additionalProperties': {
            'type': 'array', 'maxItems': 20, 'items': {
                'type': 'object', 'required': ['text', 'basis_parts', 'modality'],
                'additionalProperties': False, 'properties': {
                    'text': {'type': 'string', 'minLength': 1, 'maxLength': 280},
                    'basis_parts': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                    'items': {'type': 'string', 'minLength': 1}},
                    'modality': {'enum': ['actual', 'planned', 'forecast', 'question', 'negation', 'uncertain']},
                }}}}}}


def scoped_boundary_identity(boundary) -> dict[str, Any]:
    from company_wiki.document_understanding import summary_tasks
    from company_wiki.source_catalog import narrative_evidence
    from company_wiki import narrative_subject
    from . import models, narrative_contracts, narrative_model, narrative_model_runtime

    dependencies = {}
    for name, module in {
            'runtime': narrative_model_runtime, 'scoped_protocol': __import__(__name__, fromlist=['']),
            'source_task_plan': summary_tasks, 'role_quality_owner': narrative_evidence,
            'legacy_utilities': narrative_model, 'canonical_contracts': narrative_contracts,
            'canonical_encoding': models, 'subject_contracts': narrative_subject,
        }.items():
        filename = module.__file__
        if filename is None:
            raise narrative_model.ModelResponseError('READING_MODEL_IMPLEMENTATION_UNAVAILABLE')
        dependencies[name] = hashlib.sha256(Path(filename).read_bytes()
            .replace(b'\r\n', b'\n').replace(b'\r', b'\n')).hexdigest()
    return {'schema_version': 'reading-model-boundary/1',
        'reading_projection_version': boundary.reading_projection_version,
        'prompt_version': boundary.prompt_version, 'request_schema': boundary.request_schema,
        'decoder_version': boundary.decoder_version,
        'instruction_sha256': hashlib.sha256(SCOPED_INSTRUCTION.encode()).hexdigest(),
        'response_schema_sha256': canonical_json_hash(scoped_response_schema()),
        'decoder_sha256': canonical_json_hash(dependencies), 'implementation_dependencies': dependencies}


def _scoped_output_plan(task_count: int, max_output_tokens: int | None = None) -> dict[str, Any]:
    from .narrative_model import ModelResponseError
    if max_output_tokens is not None and (type(max_output_tokens) is not int or max_output_tokens <= 0):
        raise ModelResponseError('model output budget must be a positive integer')
    target = min(20, max(1, task_count))
    if max_output_tokens is not None:
        target = min(target, max(1, (max_output_tokens - 256) // 320))
    return {'max_claims': 20, 'target_claim_count': target, 'target_text_chars': 240,
        'configured_output_tokens': max_output_tokens, 'coverage': 'selected_source_tasks_only',
        'planning': 'compact_target_not_token_estimate'}


from .narrative_model import NarrativeModelRequest as _LegacyModelRequest  # noqa: E402


@dataclass(frozen=True)
class ScopedModelRequest(_LegacyModelRequest):
    """Actual HTTP base type, with this explicit protocol's output-budget owner."""
    def with_output_budget(self, max_output_tokens: int) -> _LegacyModelRequest:
        from .narrative_model import ModelResponseError
        try:
            envelope = json.loads(self.data_json)
            if envelope['schema_version'] != SCOPED_REQUEST_SCHEMA:
                raise ModelResponseError('MODEL_REQUEST_INVALID')
            plan = _scoped_output_plan(envelope['material']['available_task_count'], max_output_tokens)
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelResponseError('MODEL_REQUEST_INVALID') from exc
        if envelope.get('output_plan') == plan:
            return self
        envelope['output_plan'] = plan
        return ScopedModelRequest(self.prompt_version, self.instruction, canonical_json(envelope),
            canonical_json_hash({'selected_input_sha256': self.input_sha256, 'output_plan': plan}))


def build_scoped_request(selected: NarrativeSelectResult) -> ScopedModelRequest:
    from . import narrative_model as legacy
    if selected.reading_context is None:
        raise legacy.ModelResponseError('READING_MODEL_CONTEXT_UNAVAILABLE')
    view = compile_scoped_model_view(selected, max_claims=20)
    if not view.plan.tasks or selected.source_metadata.language not in {'zh', 'en', 'mixed'}:
        raise legacy.ModelResponseError('SUMMARY_INPUT_UNAVAILABLE')
    aliases = ['r' + str(i) for i in range(1, len(selected.reading_context['groups']) + 1)]
    strategy = legacy._reading_model_context(selected.reading_context, aliases,
                                             version=SCOPED_MODEL_PROJECTION_VERSION)
    strategy.pop('groups')
    envelope = {'schema_version': SCOPED_REQUEST_SCHEMA,
        'subject' if selected.subject.kind == 'official_json' else 'source': {
            'language': selected.source_metadata.language, 'title': selected.source_metadata.title,
            'document_kind': selected.source_metadata.document_kind},
        'material': view.to_model_dict(), 'reading_strategy': strategy,
        'output_plan': _scoped_output_plan(len(view.plan.tasks)),
        'response_schema': scoped_response_schema()}
    data_json = canonical_json(envelope)
    return ScopedModelRequest(SCOPED_PROMPT_VERSION, SCOPED_INSTRUCTION, data_json,
        canonical_json_hash({'prompt_version': SCOPED_PROMPT_VERSION, 'instruction': SCOPED_INSTRUCTION,
            'data_json': data_json, 'task_binding': view.to_binding(), 'subject': selected.subject.to_dict(),
            'selection': selected.selection.to_dict()}))


def decode_scoped_draft(response, *, selected: NarrativeSelectResult) -> dict[str, Any]:
    """Recover whole local clauses, never repair IDs or authorize their prose."""
    from company_wiki.source_catalog.narrative_evidence import (
        SummaryValidationError, project_summary_claim_quality, summary_claim_type_for_roles,
        validate_summary_claim,
    )
    from . import narrative_model as legacy
    from .narrative_contracts import NarrativeContractError, _claim_from_dict, _claim_to_dict, assert_no_physical_paths
    if response.prompt_version != SCOPED_PROMPT_VERSION:
        raise legacy.ModelResponseError('model response prompt version differs from request')
    if selected.reading_context is None:
        raise legacy.ModelResponseError('READING_MODEL_CONTEXT_UNAVAILABLE')
    try:
        payload = json.loads(response.response_bytes.decode('utf-8'),
            object_pairs_hook=legacy._unique_object, parse_constant=legacy._invalid_json_number)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise legacy.ModelResponseError('model response is not strict UTF-8 JSON') from exc
    if not isinstance(payload, dict) or set(payload) != {'drafts_by_task'} or not isinstance(payload['drafts_by_task'], dict):
        raise legacy.ModelResponseError('model response must contain only drafts_by_task')
    tasks = payload['drafts_by_task']
    if any(not isinstance(rows, list) for rows in tasks.values()):
        raise NarrativeContractError('scoped task clauses must be arrays')
    count = sum(len(rows) for rows in tasks.values())
    if count > 20:
        raise NarrativeContractError('summary claims exceed twenty')
    view = compile_scoped_model_view(selected, max_claims=20)
    if set(tasks) - {task.key for task in view.plan.tasks}:
        raise legacy.ModelCitationError('scoped draft references an unknown source task')
    known = {span.span_id: span for span in selected.evidence_spans}
    retained = []
    first_error = None
    for task in view.plan.tasks:
        for ordinal, raw in enumerate(tasks.get(task.key, []), 1):
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
    return {**identity, 'language': selected.source_metadata.language,
            'claims': [_claim_to_dict(claim) for claim in claims], 'status': status}


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

    def to_binding(self) -> dict[str, Any]:
        """Program-owned exact identity; local keys never replace source IDs."""
        return {"schema_version": SCOPED_VIEW_SCHEMA, "source_plan": self.plan.to_binding(),
                "source_keys": dict(self._source_keys),
                "task_parts": {key: dict(parts) for key, parts in self._parts.items()}}

    @property
    def binding_sha256(self) -> str:
        return canonical_json_hash(self.to_binding())

    def to_model_dict(self) -> dict[str, Any]:
        counts = Counter(sid for task in self.plan.tasks for sid in task.member_ids)

        def source_role(span):
            role = span.structured_value.get("source_role", "unknown")
            return role if isinstance(role, str) else "unknown"

        def frequent(values, fallback):
            return Counter(values).most_common(1)[0][0] if values else fallback

        fragment_defaults = {
            "source_role": frequent([source_role(self._spans[sid]) for sid in self.plan.evidence_order], "unknown"),
            "quality_flags": list(frequent([self._spans[sid].quality_flags for sid in self.plan.evidence_order], ())),
        }
        task_defaults = {
            "kind": frequent([task.kind for task in self.plan.tasks], "standalone"),
            "section_role": frequent([task.section_role for task in self.plan.tasks], "unknown"),
            "topics": list(frequent([task.topics for task in self.plan.tasks], ())),
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
        for task in self.plan.tasks:
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
        return {"schema_version": SCOPED_VIEW_SCHEMA, "scope": "selected_source_tasks_only",
                "max_claims": self.plan.max_claims, "available_task_count": len(tasks),
                "fragment_defaults": fragment_defaults, "task_defaults": task_defaults,
                "shared_fragments": shared, "tasks": tasks}

    def resolve_basis(self, task_key: object, part_keys: object) -> ScopedClaimBinding:
        if not isinstance(task_key, str) or task_key not in self._parts:
            raise ValueError("scoped draft references an unknown source task")
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
    plan = build_summary_task_plan(selected.evidence_spans,
                                   reading_context=selected.reading_context, max_claims=max_claims)
    return ScopedModelView(plan,
        MappingProxyType({span.span_id: span for span in selected.evidence_spans}),
        MappingProxyType({sid: "s" + str(i) for i, sid in enumerate(plan.evidence_order, 1)}),
        MappingProxyType({task.key: MappingProxyType({"p" + str(i): sid
            for i, sid in enumerate(task.member_ids, 1)}) for task in plan.tasks}))
