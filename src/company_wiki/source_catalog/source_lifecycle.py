"""ZR-301: additive source-lifecycle readiness evaluation (shadow only).

The counterexample (phase-3 task plan): ``documents.source_status`` is a
single field (active / incomplete / quarantined / retired /
upstream_rejected) that masks different readiness gaps — a source can be
identity-verified but safety-unreviewed, or artifact-complete but
semantic-blocked.  This module builds the shadow-only, per-source readiness
evaluator:

- ``LIFECYCLE_SCHEMA``/``LIFECYCLE_SCHEMA_VERSION`` — a versioned assertion
  schema; unknown stages/reasons fail closed (reusing the ZR-101
  eight-stage taxonomy from ``observability``).
- ``ConsumerRequirements`` — the stages a consumer requires; unknown stages
  are rejected; empty requirements trivially pass.
- ``evaluate_source_readiness(reader, source_id, requirements)`` — reads
  ONLY through the zero-write ``CatalogReader`` and returns a
  ``SourceReadiness`` with a per-stage verdict, blocker and next action.
  ready == every required stage satisfied; ``unknown`` never counts as
  satisfied (fail closed: a source without a safety receipt is not green).

Shadow only: this module never writes the catalog, never touches
``source_status``, and is not wired into any production entrypoint (the
unified decision graph lands in ZR-303).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .observability import (
    CrossRepoStage,
    stage_sequence,
)
from .reader import CatalogReader

LIFECYCLE_SCHEMA_VERSION = "1.0"
LIFECYCLE_SCHEMA = "source-lifecycle-1.0"

VERDICTS = frozenset({"satisfied", "unsatisfied", "unknown"})

# source_status values that never satisfy the consumer stage.
_BLOCKED_SOURCE_STATUSES = frozenset({"quarantined", "retired", "upstream_rejected", "incomplete"})


@dataclass(frozen=True)
class ConsumerRequirements:
    """Stages a consumer requires before a source is ready.

    ``required_stages`` must be canonical stage names (fail closed on
    unknown); empty means no requirement (trivially ready).
    """

    required_stages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for stage in self.required_stages:
            if stage not in {s.value for s in CrossRepoStage}:
                raise ValueError(f"unknown required stage: {stage!r}")


@dataclass(frozen=True)
class StageVerdict:
    """One stage's readiness verdict with the reason evidence it used."""

    stage: str
    verdict: str  # satisfied | unsatisfied | unknown
    blocker: str | None = None
    next_action: str | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceReadiness:
    """Per-source readiness: stage verdicts + consumer-driven ready."""

    source_id: str
    requirements: ConsumerRequirements
    stages: tuple[StageVerdict, ...] = ()
    ready: bool = False
    missing_stages: tuple[str, ...] = ()

    def verdict_for(self, stage: str) -> StageVerdict | None:
        for verdict in self.stages:
            if verdict.stage == stage:
                return verdict
        return None


def _verified_identity(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    rows = reader.fetchall(
        "SELECT evidence_basis, decision FROM source_metadata_assertions "
        "WHERE source_id=? AND decision='verified'",
        (source_id,),
    )
    evidence = tuple(str(row["evidence_basis"]) for row in rows)
    return bool(rows), evidence


def _resolution_hit(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    row = reader.fetchone(
        "SELECT source_status FROM documents WHERE primary_source_id=?",
        (source_id,),
    )
    if row is None:
        return False, ()
    return True, ("document_bound",)


def _freshness_ok(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    row = reader.fetchone(
        "SELECT published_date FROM documents WHERE primary_source_id=? "
        "AND published_date IS NOT NULL AND published_date != ''",
        (source_id,),
    )
    if row is None:
        return False, ()
    return True, (f"published_date={row['published_date']}",)


def _acquisition_ok(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    rows = reader.fetchall(
        "SELECT location_status FROM locations WHERE source_id=?",
        (source_id,),
    )
    active = [str(row["location_status"]) for row in rows if row["location_status"] == "active"]
    if active:
        return True, ("active_location",)
    if rows:
        return False, (str(rows[0]["location_status"]),)
    return False, ()


def _safety_receipt(reader: CatalogReader, source_id: str) -> dict | None:
    """The stored prompt-injection receipt dict, or None when absent or
    malformed (fail closed)."""
    from .prompt_injection import (
        PROMPT_INJECTION_REVIEW_KEY,
        PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
    )

    row = reader.fetchone(
        "SELECT metadata_json FROM documents WHERE primary_source_id=? LIMIT 1",
        (source_id,),
    )
    if row is None:
        return None
    import json

    try:
        metadata = json.loads(str(row["metadata_json"] or "{}"))
    except json.JSONDecodeError:
        return None
    if not isinstance(metadata, dict):
        return None
    receipt = metadata.get(PROMPT_INJECTION_REVIEW_KEY)
    if not isinstance(receipt, dict):
        return None
    if receipt.get("schema_version") != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
        return None
    return receipt


def _safety_reviewed(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    """Safety is satisfied ONLY by an explicit review receipt.

    No review record -> unknown (never green; the envelope reports absent
    receipts as ``not_reviewed``).  A receipt whose status is outside the
    stored enum (``not_detected``/``detected_and_ignored``) is malformed
    -> unknown (fail closed).  A valid receipt is satisfied.  The receipt
    lives in ``documents.metadata_json`` under the prompt-injection key
    (written by ``record_prompt_injection_review``).
    """
    from .prompt_injection import PROMPT_INJECTION_REVIEW_STATUSES

    receipt = _safety_receipt(reader, source_id)
    if receipt is None:
        return False, ()
    status = str(receipt.get("status") or "")
    if status not in PROMPT_INJECTION_REVIEW_STATUSES:
        return False, ()
    return True, (f"prompt_injection_status={status}",)


def _artifact_ok(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    row = reader.fetchone(
        "SELECT artifact_id, status FROM artifacts WHERE source_id=? "
        "AND status='completed' ORDER BY created_at DESC, artifact_id LIMIT 1",
        (source_id,),
    )
    if row is None:
        return False, ()
    return True, (f"artifact={row['artifact_id']}",)


def _semantic_ok(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    row = reader.fetchone(
        "SELECT parse_status FROM evidence_spans WHERE source_id=? "
        "AND parse_status='ok' LIMIT 1",
        (source_id,),
    )
    if row is None:
        return False, ()
    return True, ("parse_ok",)


def _consumer_ok(reader: CatalogReader, source_id: str) -> tuple[bool, tuple[str, ...]]:
    row = reader.fetchone(
        "SELECT source_status FROM documents WHERE primary_source_id=?",
        (source_id,),
    )
    if row is None:
        return False, ()
    status = str(row["source_status"] or "")
    if status in _BLOCKED_SOURCE_STATUSES:
        return False, (f"source_status={status}",)
    return True, (f"source_status={status}",)


# Stage -> (evaluator, unsatisfied blocker, next action).  Evaluators return
# (satisfied, evidence); no row evidence at all means UNKNOWN (fail closed).
_STAGE_EVALUATORS: dict[str, Any] = {
    "identity": (_verified_identity, "no verified identity assertion", "record verified identity assertion"),
    "resolution": (_resolution_hit, "source not bound to a document", "resolve/bind the source"),
    "freshness": (_freshness_ok, "no published_date evidence", "record published_date"),
    "acquisition": (_acquisition_ok, "no active location", "acquire/restore source bytes"),
    "safety": (_safety_reviewed, "safety receipt is not_reviewed or absent", "run prompt-injection review (ZR-302)"),
    "artifact": (_artifact_ok, "no completed artifact", "produce a valid artifact"),
    "semantic": (_semantic_ok, "no parse_ok evidence span", "parse/verify content (BR phase)"),
    "consumer": (_consumer_ok, "source_status is blocked", "resolve source_status blocker"),
}


def evaluate_source_readiness(
    reader: CatalogReader,
    source_id: str,
    requirements: ConsumerRequirements | None = None,
) -> SourceReadiness:
    """Evaluate the eight-stage readiness for one source (shadow, read-only).

    ``unknown`` (no evidence) NEVER counts as satisfied: a source without a
    safety receipt is not ready.  ready == every required stage satisfied.
    """
    if requirements is None:
        requirements = ConsumerRequirements()
    required = set(requirements.required_stages)
    verdicts: list[StageVerdict] = []
    missing: list[str] = []
    for stage in stage_sequence():
        name = stage.value
        evaluator, blocker, next_action = _STAGE_EVALUATORS[name]
        satisfied, evidence = evaluator(reader, source_id)
        if satisfied:
            verdict = "satisfied"
        elif evidence:
            verdict = "unsatisfied"
        else:
            verdict = "unknown"
        verdicts.append(
            StageVerdict(
                stage=name,
                verdict=verdict,
                blocker=None if verdict == "satisfied" else blocker,
                next_action=None if verdict == "satisfied" else next_action,
                evidence=evidence,
            )
        )
        if name in required and verdict != "satisfied":
            missing.append(name)
    return SourceReadiness(
        source_id=source_id,
        requirements=requirements,
        stages=tuple(verdicts),
        ready=not missing,
        missing_stages=tuple(missing),
    )


__all__ = [
    "ConsumerRequirements",
    "LIFECYCLE_SCHEMA",
    "LIFECYCLE_SCHEMA_VERSION",
    "SourceReadiness",
    "StageVerdict",
    "VERDICTS",
    "evaluate_source_readiness",
]
