"""Deterministic DAG materialization and readiness scheduling."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Event, Job, JobStatus, MaterializedDAG, make_job_key
from .planner import PlannedDAG, plan_jobs
from .policy import PolicyConfig
from .registry import HandlerRegistry
from .store import AutomationStore, DAGPutResult


def materialize_plan(event: Event, plan: PlannedDAG) -> MaterializedDAG:
    """Convert a pure plan into immutable jobs with explicit initial states."""

    dependent_ids = {child for child, _parent in plan.dependencies}
    jobs = tuple(
        Job(
            job_id=planned.temp_id,
            job_key=make_job_key(
                planned.job_type,
                planned.subject_type,
                planned.subject_id,
                planned.input_hash,
                planned.policy_version,
                planned.handler_version,
            ),
            job_type=planned.job_type,
            subject_type=planned.subject_type,
            subject_id=planned.subject_id,
            input_hash=planned.input_hash,
            policy_version=planned.policy_version,
            handler_version=planned.handler_version,
            risk_class=planned.risk_class,
            status=(
                JobStatus.PLANNED
                if planned.temp_id in dependent_ids
                else JobStatus.READY
            ),
            priority=planned.priority,
            not_before=event.observed_at,
            max_attempts=planned.max_attempts,
            created_from_event_id=event.event_id,
            created_at=event.observed_at,
            updated_at=event.observed_at,
            last_error_code=None,
            last_error_detail=None,
        )
        for planned in plan.jobs
    )
    return MaterializedDAG(jobs=jobs, dependencies=plan.dependencies)


@dataclass(frozen=True)
class RefreshResult:
    promoted_job_ids: tuple[str, ...]


class AutomationScheduler:
    """Application layer between pure planning and atomic persistence."""

    def __init__(
        self,
        store: AutomationStore,
        registry: HandlerRegistry,
        config: PolicyConfig | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._config = config or PolicyConfig()

    def plan_event(self, event: Event) -> PlannedDAG:
        return plan_jobs(event, self._registry, self._config)

    def materialize_event(self, event: Event) -> DAGPutResult:
        plan = self.plan_event(event)
        return self._store.materialize_dag(event, materialize_plan(event, plan))

    def refresh_ready(self, *, now: str) -> RefreshResult:
        return RefreshResult(promoted_job_ids=self._store.promote_ready_jobs(now=now))


__all__ = [
    "AutomationScheduler",
    "RefreshResult",
    "materialize_plan",
]
