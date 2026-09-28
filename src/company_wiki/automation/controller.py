"""AUTO-5 Controller: observe and shadow modes for the automation control plane.

This module depends on the store, registry, policy, planner and event_sources.
It does not import the legacy scheduler, network, LLM or configuration modules.

- **observe**: reads events, plans jobs, returns what would be done (no side effects).
- **shadow**: reads events, plans jobs, creates jobs in the store (no handler execution).
"""

from __future__ import annotations

from dataclasses import dataclass

from .event_sources import EventSource
from .models import make_job_key
from .planner import PlannedDAG, PlannerError, plan_jobs
from .policy import PolicyConfig
from .registry import HandlerRegistry
from .scheduler import AutomationScheduler


@dataclass(frozen=True)
class ObserveResult:
    """Result of an observe cycle (read-only, no side effects)."""

    events_processed: int
    planned_dags: tuple[PlannedDAG, ...]
    jobs_already_exist: int
    jobs_would_create: int


@dataclass(frozen=True)
class ShadowResult:
    """Result of a shadow cycle (jobs created, no handler execution)."""

    events_processed: int
    jobs_created: int
    jobs_already_existed: int


class Controller:
    """Automation controller with observe and shadow modes."""

    def __init__(
        self,
        store,
        registry: HandlerRegistry,
        config: PolicyConfig | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._config = config or PolicyConfig()
        self._event_source = EventSource(store)
        self._scheduler = AutomationScheduler(store, registry, self._config)

    def observe(self) -> ObserveResult:
        """Read events, plan jobs, return what would be done (no side effects).

        This is a pure read-only operation.  It does not create jobs, write to
        the store, or execute any handlers.
        """
        events = self._event_source.get_all_events()
        planned_dags: list[PlannedDAG] = []
        already_exist = 0
        would_create = 0

        for event in events:
            try:
                dag = plan_jobs(event, self._registry, self._config)
            except PlannerError:
                continue  # skip events that can't be planned
            planned_dags.append(dag)
            for pj in dag.jobs:
                job_key = make_job_key(
                    pj.job_type, pj.subject_type, pj.subject_id,
                    pj.input_hash, pj.policy_version, pj.handler_version,
                )
                existing = self._store.get_job_by_key(job_key)
                if existing:
                    already_exist += 1
                else:
                    would_create += 1

        return ObserveResult(
            events_processed=len(events),
            planned_dags=tuple(planned_dags),
            jobs_already_exist=already_exist,
            jobs_would_create=would_create,
        )

    def shadow(self) -> ShadowResult:
        """Read events, plan jobs, create jobs in the store.

        Root jobs are created READY and dependent jobs PLANNED in one database
        transaction. No handlers are executed and no effects are generated.
        """
        events = self._event_source.get_all_events()
        created = 0
        already_existed = 0

        for event in events:
            try:
                result = self._scheduler.materialize_event(event)
            except PlannerError:
                continue
            created += result.jobs_created
            already_existed += result.jobs_existing

        return ShadowResult(
            events_processed=len(events),
            jobs_created=created,
            jobs_already_existed=already_existed,
        )


__all__ = ["Controller", "ObserveResult", "ShadowResult"]
