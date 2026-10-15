"""One local presentation of source-owned summary tasks; no model calls.

Shared original fragments remain a graph. Every fragment body is defined once
and all other uses are references. This compiler reduces global alias lookup;
neither a legal task nor a legal basis proves a paraphrase semantically true.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from company_wiki.document_understanding.summary_tasks import SummaryTaskPlan, build_summary_task_plan
from company_wiki.source_contract import EvidenceSpan

from .models import canonical_json_hash
from .narrative_contracts import NarrativeSelectResult


SCOPED_VIEW_SCHEMA = "source-scoped-model-view/1"


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
