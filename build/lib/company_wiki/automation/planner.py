"""AUTO-3 Planner: pure function from Event to deterministic Job DAG.

This module depends only on the Python standard library, ``models``,
``registry`` and ``policy``.  The same event and policy version always produce
the same DAG — no randomness, no clock reads, no side effects.  The planner
returns ``PlannedJob`` descriptions; the caller (AUTO-4 worker) is responsible
for creating actual ``Job`` records in the store.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import Event, RiskClass
from .policy import PolicyConfig, compute_risk
from .registry import HandlerRegistry


class PlannerError(Exception):
    """Raised when the planner cannot produce a valid DAG."""


@dataclass(frozen=True)
class PlannedJob:
    """Description of a single job in the planned DAG."""

    temp_id: str
    job_type: str
    subject_type: str
    subject_id: str
    input_hash: str
    policy_version: str
    handler_version: str
    risk_class: RiskClass
    priority: int
    max_attempts: int


@dataclass(frozen=True)
class PlannedDAG:
    """A deterministic job DAG produced by the planner."""

    jobs: tuple[PlannedJob, ...]
    dependencies: tuple[tuple[str, str], ...]  # (job_temp_id, depends_on_temp_id)


def _make_temp_id(event_id: str, job_type: str) -> str:
    """Deterministic temporary ID for a planned job."""
    return hashlib.sha256(f"{event_id}:{job_type}".encode()).hexdigest()[:16]


def plan_jobs(
    event: Event,
    registry: HandlerRegistry,
    config: PolicyConfig | None = None,
) -> PlannedDAG:
    """Plan a deterministic job DAG for the given event.

    The same event always produces the same DAG (same temp_ids, same jobs,
    same dependencies).  Raises ``PlannerError`` for unknown event types or
    ``PolicyViolationError`` for policy violations.
    """
    if config is None:
        config = PolicyConfig()

    mapping = _EVENT_JOB_MAPPING.get(event.event_type)
    if mapping is None:
        raise PlannerError(f"unknown event type: {event.event_type}")

    jobs: list[PlannedJob] = []
    deps: list[tuple[str, str]] = []

    for entry in mapping:
        spec = registry.get(entry.job_type)
        risk = compute_risk(spec, fan_out=entry.fan_out,
                            schema_change=entry.schema_change, config=config)
        temp_id = _make_temp_id(event.event_id, entry.job_type)
        pj = PlannedJob(
            temp_id=temp_id,
            job_type=entry.job_type,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            input_hash=event.input_hash,
            policy_version=event.policy_version,
            handler_version=spec.handler_version,
            risk_class=risk,
            priority=entry.priority,
            max_attempts=spec.default_max_attempts,
        )
        jobs.append(pj)
        for dep_type in entry.depends_on:
            dep_temp_id = _make_temp_id(event.event_id, dep_type)
            deps.append((temp_id, dep_temp_id))

    return PlannedDAG(jobs=tuple(jobs), dependencies=tuple(deps))


# --------------------------------------------------------------------------- #
# Event → job mapping (frozen, deterministic).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _JobMappingEntry:
    job_type: str
    priority: int
    fan_out: int
    schema_change: bool
    depends_on: tuple[str, ...]


_EVENT_JOB_MAPPING: dict[str, tuple[_JobMappingEntry, ...]] = {
    "source.revision_registered": (
        _JobMappingEntry("source.normalize", priority=0, fan_out=1,
                         schema_change=False, depends_on=()),
        _JobMappingEntry("source.analyze", priority=0, fan_out=1,
                         schema_change=False, depends_on=("source.normalize",)),
    ),
    "analysis.proposal_ready": (
        _JobMappingEntry("analysis.validate", priority=0, fan_out=1,
                         schema_change=False, depends_on=()),
        _JobMappingEntry("analysis.review", priority=0, fan_out=1,
                         schema_change=False, depends_on=("analysis.validate",)),
    ),
    "gold.inputs_changed": (
        _JobMappingEntry("gold.refresh_packet", priority=0, fan_out=1,
                         schema_change=False, depends_on=()),
    ),
    "review.receipt_changed": (
        _JobMappingEntry("gold.validate_receipt", priority=0, fan_out=1,
                         schema_change=False, depends_on=()),
    ),
    "review.approved": (
        _JobMappingEntry("gold.promote_reviewed", priority=0, fan_out=1,
                         schema_change=False, depends_on=()),
    ),
    "timer.due": (
        _JobMappingEntry("timer.execute_step", priority=0, fan_out=1,
                         schema_change=False, depends_on=()),
    ),
}


__all__ = [
    "PlannedJob",
    "PlannedDAG",
    "PlannerError",
    "plan_jobs",
]
