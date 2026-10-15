"""Source-owned, reference-only tasks for one selected-material summary.

The shared reader already owns selection, native groups and QA support views.
This module carries those decisions to the model boundary; it never ranks or
parses prose, invents referents, calls a model, or reads another source. Task
keys are local display addresses. Canonical span IDs remain their identity.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from company_wiki.source_contract import EvidenceSpan


SUMMARY_TASK_PLAN_SCHEMA = "source-summary-task-plan/1"


@dataclass(frozen=True)
class SourceSummaryTask:
    key: str
    source_id: str
    origin_group_id: str | None
    member_ids: tuple[str, ...]
    support_ids: tuple[str, ...]
    context_ids: tuple[str, ...]
    kind: str
    section_role: str
    topics: tuple[str, ...]
    selection_reasons: tuple[str, ...]
    support_roles: tuple[str, ...]

    def to_binding(self) -> dict[str, Any]:
        return {name: list(value) if isinstance(value, tuple) else value
                for name in self.__dataclass_fields__
                for value in (getattr(self, name),)}


@dataclass(frozen=True)
class SummaryTaskPlan:
    tasks: tuple[SourceSummaryTask, ...]
    evidence_order: tuple[str, ...]
    max_claims: int

    def to_binding(self) -> dict[str, Any]:
        """Finite causal mapping, without a second copy of original prose."""
        return {"schema_version": SUMMARY_TASK_PLAN_SCHEMA,
                "evidence_order": list(self.evidence_order), "max_claims": self.max_claims,
                "tasks": [task.to_binding() for task in self.tasks]}

    @property
    def binding_sha256(self) -> str:
        return sha256(json.dumps(self.to_binding(), ensure_ascii=False,
                                 sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def coverage(self, emitted_task_keys: Sequence[str]) -> dict[str, Any]:
        """Observe emitted source scopes; absence is not a business conclusion.

        A concise summary may emit fewer tasks than were supplied. This is an
        observation, not permission to run, and not semantic verification.
        """
        known = {task.key for task in self.tasks}
        emitted = set(emitted_task_keys)
        if emitted - known:
            raise ValueError("summary coverage references an unknown source task")
        return {"scope": "selected_source_tasks_only", "max_claims": self.max_claims,
                "available_task_count": len(self.tasks), "emitted_task_count": len(emitted),
                "not_emitted_task_keys": [task.key for task in self.tasks if task.key not in emitted],
                "source_task_coverage_complete": len(emitted) == len(self.tasks),
                "semantic_status": "not_evaluated"}


def build_summary_task_plan(
    evidence_spans: Sequence[EvidenceSpan], *, reading_context: Mapping[str, Any] | None,
    max_claims: int,
) -> SummaryTaskPlan:
    """Carry existing source groups/views into finite local summary tasks.

    `max_claims` comes from the caller's existing model contract; this module
    neither chooses a second paid budget nor truncates the source to fit it.
    Source intents below are observed metadata, never newly inferred facts.
    """
    if type(max_claims) is not int or max_claims <= 0:
        raise ValueError("source summary requires the actual positive claim limit")
    if any(not isinstance(span, EvidenceSpan) for span in evidence_spans):
        raise TypeError("source summary tasks require canonical EvidenceSpan objects")
    order = tuple(span.span_id for span in evidence_spans)
    known = {span.span_id: span for span in evidence_spans}
    if len(order) != len(known):
        raise ValueError("source summary has duplicate canonical spans")
    positions = {sid: index for index, sid in enumerate(order)}
    tasks: list[SourceSummaryTask] = []
    grouped: set[str] = set()

    def ids(value, *, allow_empty=False):
        if (not isinstance(value, (tuple, list)) or not value and not allow_empty
                or any(not isinstance(sid, str) or sid not in known for sid in value)
                or len(value) != len(set(value))):
            raise ValueError("source task requires unique existing native members")
        if [positions[sid] for sid in value] != sorted(positions[sid] for sid in value):
            raise ValueError("source task must retain canonical source selection order")
        return tuple(value)

    def observed_values(support, field):
        result: list[str] = []
        for sid in support:
            value = known[sid].structured_value.get(field, ())
            if isinstance(value, (tuple, list)):
                result.extend(item for item in value if isinstance(item, str))
        return tuple(dict.fromkeys(result))

    def register(members, support, context, origin, kind, role):
        if not isinstance(kind, str) or not isinstance(role, str):
            raise ValueError("source task labels must be immutable native strings")
        parents = {known[sid].source_id for sid in members}
        if len(parents) != 1:
            raise ValueError("source summary task cannot cross original parents")
        if (set(support).intersection(context)
                or set(support).union(context) != set(members)):
            raise ValueError("source support/context must partition the native group")
        roles = (known[sid].structured_value.get("source_role", "unknown") for sid in support)
        support_roles = tuple(dict.fromkeys(role if isinstance(role, str) else "unknown" for role in roles))
        tasks.append(SourceSummaryTask(
            "t" + str(len(tasks) + 1), next(iter(parents)), origin, members, support, context,
            kind, role, observed_values(support, "topics"),
            observed_values(support, "selection_reasons"),
            support_roles,
        ))

    if reading_context is not None:
        if reading_context.get("schema_version") not in {"du-production-reading/1", "du-production-reading/2"}:
            raise ValueError("source summary requires a known native reading context")
        for group in reading_context.get("groups", ()):
            members = ids(group["evidence_ids"])
            origin = group["group_id"]
            if not isinstance(origin, str) or not origin:
                raise ValueError("source summary task requires its actual origin group")
            views = (group["citation_views"] if reading_context["schema_version"] == "du-production-reading/2"
                     else ({"support_evidence_ids": members, "context_evidence_ids": ()},))
            if not isinstance(views, (tuple, list)) or not 1 <= len(views) <= 2:
                raise ValueError("source summary requires the existing finite citation views")
            for view in views:
                support = ids(view["support_evidence_ids"])
                context = ids(view["context_evidence_ids"], allow_empty=True)
                register(members, support, context, origin, group["kind"], group["section_role"])
            grouped.update(members)
    for sid in order:
        if sid not in grouped:
            register((sid,), (sid,), (), None, "standalone", "unknown")
    return SummaryTaskPlan(tuple(tasks), order, max_claims)
