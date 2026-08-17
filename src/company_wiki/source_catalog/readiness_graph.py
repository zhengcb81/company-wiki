"""ZR-303: unified safety/identity/artifact/semantic readiness decision graph.

Composes the ZR-301 eight-stage readiness evaluator with the ZR-302
prompt-injection guard into ONE machine decision graph:

- safety uses the guard's cache evaluation (hit -> satisfied; ignored /
  expired / tampered / absent -> blocker with a next action — never a
  faked green);
- the other seven stages come from ``evaluate_source_readiness``
  (unknown never counts as satisfied);
- every blocker carries a next action (the decision graph has no dead
  ends);
- the same inputs always produce the same decision (pure, stateless).

Shadow only: reads exclusively through the zero-write ``CatalogReader``
(plus the guard's store-compatible reads); no catalog writes, no
production wiring (production entrypoints land in later cards).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .prompt_injection_guard import ReviewEvaluation, evaluate_review
from .reader import CatalogReader
from .source_lifecycle import (
    ConsumerRequirements,
    SourceReadiness,
    evaluate_source_readiness,
)

READINESS_GRAPH_SCHEMA_VERSION = "1.0"
READINESS_GRAPH_SCHEMA = "readiness-graph-1.0"

# Safety guard cache_state -> (graph verdict, next action).  hit is the
# only satisfied path; every other state is a blocker with a concrete
# next action — not_reviewed is never faked green.
_SAFETY_MAP: dict[str, tuple[str, str]] = {
    "hit": ("satisfied", ""),
    "ignored": ("unsatisfied", "re-scan with the current ruleset and record a new review receipt"),
    "expired": ("unsatisfied", "re-review the source (previous receipt is past its TTL)"),
    "tampered": ("unsatisfied", "verify source bytes and re-run the prompt-injection review"),
    "absent": ("unknown", "run the prompt-injection scanner and record a review receipt"),
}

# Blocker -> next action for the seven non-safety stages (from ZR-301).
_STAGE_NEXT_ACTIONS: dict[str, str] = {
    "identity": "record a verified identity assertion",
    "resolution": "resolve/bind the source to a document",
    "freshness": "record published_date evidence",
    "acquisition": "acquire/restore the source bytes",
    "artifact": "produce a valid artifact",
    "semantic": "parse/verify content (BR phase)",
    "consumer": "resolve the source_status blocker",
}


@dataclass(frozen=True)
class ReadinessBlocker:
    """One unsatisfied/unknown stage with the action to unblock it."""

    stage: str
    reason: str
    next_action: str


@dataclass(frozen=True)
class ReadinessDecision:
    """The unified decision for one source under one consumer's
    requirements: ready + every blocker + the safety cache state."""

    source_id: str
    requirements: ConsumerRequirements
    ready: bool = False
    blockers: tuple[ReadinessBlocker, ...] = ()
    safety_cache_state: str | None = None
    stages: tuple[Any, ...] = ()


def _safety_verdict(
    reader: CatalogReader, source_id: str, *, policy_hash: str, source_sha256: str, now: str, ttl_seconds: float
) -> tuple[str, str, str]:
    """(graph verdict, cache_state, next_action) for the safety stage.

    The guard's receipt store is keyed by document_id, so resolve the
    source's document first; a source with no bound document is absent.
    """
    row = reader.fetchone(
        "SELECT document_id FROM documents WHERE primary_source_id=? LIMIT 1",
        (source_id,),
    )
    if row is None:
        return "unknown", "absent", _SAFETY_MAP["absent"][1]
    document_id = str(row["document_id"])
    evaluation: ReviewEvaluation = evaluate_review(
        reader,
        document_id,
        source_sha256=source_sha256,
        policy_hash=policy_hash,
        now=now,
        ttl_seconds=ttl_seconds,
    )
    verdict, next_action = _SAFETY_MAP[evaluation.cache_state]
    return verdict, evaluation.cache_state, next_action


def evaluate_readiness(
    reader: CatalogReader,
    source_id: str,
    *,
    policy_hash: str,
    source_sha256: str,
    now: str,
    ttl_seconds: float,
    requirements: ConsumerRequirements | None = None,
) -> ReadinessDecision:
    """Evaluate one source under one consumer's requirements.

    Composes ZR-301 (eight stages) with ZR-302 (safety guard): the safety
    stage verdict comes from the guard's cache evaluation; the other
    seven stages come from the readiness evaluator.  Deterministic: the
    same inputs produce the same decision.
    """
    if requirements is None:
        requirements = ConsumerRequirements()
    readiness: SourceReadiness = evaluate_source_readiness(
        reader, source_id, requirements=requirements
    )
    safety_verdict, safety_cache, safety_next = _safety_verdict(
        reader, source_id, policy_hash=policy_hash, source_sha256=source_sha256,
        now=now, ttl_seconds=ttl_seconds,
    )
    # Replace the ZR-301 safety verdict with the guard's verdict.
    stages: list[Any] = []
    blockers: list[ReadinessBlocker] = []
    required = set(requirements.required_stages)
    for verdict in readiness.stages:
        if verdict.stage == "safety":
            stage_verdict = safety_verdict
            reason = "safety receipt is not fresh/bound" if safety_verdict != "satisfied" else None
            next_action = safety_next
        else:
            stage_verdict = verdict.verdict
            reason = verdict.blocker
            next_action = _STAGE_NEXT_ACTIONS.get(verdict.stage, "resolve the stage blocker")
        stages.append(
            {
                "stage": verdict.stage,
                "verdict": stage_verdict,
                "blocker": reason,
                "next_action": next_action if stage_verdict != "satisfied" else None,
                "evidence": list(verdict.evidence),
            }
        )
        if verdict.stage in required and stage_verdict != "satisfied":
            blockers.append(
                ReadinessBlocker(
                    stage=verdict.stage,
                    reason=reason or "stage not satisfied",
                    next_action=next_action,
                )
            )
    return ReadinessDecision(
        source_id=source_id,
        requirements=requirements,
        ready=not blockers,
        blockers=tuple(blockers),
        safety_cache_state=safety_cache,
        stages=tuple(stages),
    )


__all__ = [
    "READINESS_GRAPH_SCHEMA",
    "READINESS_GRAPH_SCHEMA_VERSION",
    "ReadinessBlocker",
    "ReadinessDecision",
    "evaluate_readiness",
]
