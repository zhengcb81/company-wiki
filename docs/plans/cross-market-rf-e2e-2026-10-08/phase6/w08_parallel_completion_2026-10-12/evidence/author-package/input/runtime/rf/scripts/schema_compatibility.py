"""Immutable (schema_version, engine_version, mode) compatibility registry.

Single source of truth for which engine versions may legitimately produce (or
validate) a forecast of a given schema, per mode:

* ``formal``   — a newly produced artifact for the current schema.  Only the
  current engine may emit it.
* ``output``   — validating an existing forecast output.  Each schema lists the
  CHANGELOG-documented engine versions that could have emitted it.
* ``snapshot`` — validating a frozen snapshot.  For legacy schemas the exact
  engine is bound by ``snapshot_id``; the registry still constrains it to the
  documented emit set so unknown engines fail closed.

Every row is derived from ``CHANGELOG.md``; do not add an engine here without a
CHANGELOG entry (Phase 6 B2 / F-10).
"""

from __future__ import annotations

from typing import Any

from contracts.constants import (
    DATED_CONTRIBUTION_SCHEMA_VERSION,
    PERIOD_EVIDENCE_SCHEMA_VERSION,
)
from revenue_core import ENGINE_VERSION, FORECAST_SCHEMA_VERSION, OPT_IN_SCHEMA_VERSION, require

# ---------------------------------------------------------------------------
# Emit matrix (schema_version -> set of engine versions that emitted it)
#
# CHANGELOG provenance:
#   schema 3.0 — engine 3.0.0             (v3.0.0)
#   schema 3.1 — engine 3.1.0             (v3.1.0)
#   schema 3.2 — engines 3.2.0/3.2.1      (v3.2.0/v3.2.1), later 3.3.0 read-only
#   schema 3.3 — engine 3.4.0             (v3.4.0)
#   schema 3.4 — engines 3.5.0..3.10.0    (introduced v3.5.0, current through v3.10.0)
#   schema 3.5 — engine 3.10.0            (Unreleased, pre-3.6)
#   schema 3.6 — engines 3.10.0/4.0.0     (v3.10.0, legacy read-only from v4.0.0)
#   schemas 3.7/3.8 — engines 4.1.0/4.1.1 (v4.1.1 source-clock/1; old semantics need pinned runtime)
#   schema 3.9 — engine 4.2.0/4.2.1       (M3-FLOW period_flow + role-aware triangulation;
#                                          never emitted by 4.1.x, fail-closed there)
#   schema 3.10 — engine 4.3.0            (W05-RF-FLOW dated consolidated contributions;
#                                          never emitted by 4.2.x, fail-closed there)
# ---------------------------------------------------------------------------
# The 4.2.1 history is pinned as literal versions: ENGINE_VERSION moves with
# each release and must never erase the documented emit matrix.
SCHEMA_EMIT_ENGINES: dict[str, frozenset[str]] = {
    "3.0": frozenset({"3.0.0"}),
    "3.1": frozenset({"3.1.0"}),
    "3.2": frozenset({"3.2.0", "3.2.1", "3.3.0"}),
    "3.3": frozenset({"3.4.0"}),
    "3.4": frozenset({"3.5.0", "3.6.0", "3.7.0", "3.8.0", "3.9.0", "3.10.0", "4.0.0"}),
    "3.5": frozenset({"3.10.0", "4.0.0"}),
    "3.6": frozenset({"3.10.0", "4.0.0"}),
    # 4.1.1/4.2.1 stay documented emitters after later engine bumps; the
    # current engine is always a legal emitter for the schemas it can produce.
    FORECAST_SCHEMA_VERSION: frozenset({"4.1.0", "4.1.1", "4.2.0", "4.2.1", ENGINE_VERSION}),
    OPT_IN_SCHEMA_VERSION: frozenset({"4.1.0", "4.1.1", "4.2.0", "4.2.1", ENGINE_VERSION}),
    PERIOD_EVIDENCE_SCHEMA_VERSION: frozenset({"4.2.0", "4.2.1", ENGINE_VERSION}),
    DATED_CONTRIBUTION_SCHEMA_VERSION: frozenset({"4.3.0", ENGINE_VERSION}),
}


# Additive schemas share the modern bound-input/output features. Keeping this
# set beside the emit registry avoids consumers equating "current default" with
# "the only schema that has these features". Legacy output semantics remain
# pinned to their existing documented branch checks.
BOUND_INPUT_SCHEMA_VERSIONS = frozenset({
    FORECAST_SCHEMA_VERSION, OPT_IN_SCHEMA_VERSION, PERIOD_EVIDENCE_SCHEMA_VERSION,
    DATED_CONTRIBUTION_SCHEMA_VERSION,
})


def requires_bound_input_schema(schema_version: str) -> bool:
    """Whether an artifact uses modern bound-input/output recomputation."""
    return schema_version in BOUND_INPUT_SCHEMA_VERSIONS


def supported_schema_versions() -> frozenset[str]:
    """Every schema version the registry understands (mirrors
    ``SUPPORTED_FORECAST_SCHEMA_VERSIONS``)."""
    return frozenset(SCHEMA_EMIT_ENGINES)


def validating_engine_allowed(
    schema_version: str, engine_version: Any, mode: str
) -> bool:
    """Whether *engine_version* may validate an artifact of *schema_version*.

    *mode*: ``"formal"`` (production), ``"output"`` (existing output),
    ``"snapshot"`` (frozen snapshot).  Unknown schemas and unknown engines fail
    closed in every mode.
    """
    if not isinstance(engine_version, str) or not engine_version.strip():
        return False
    emit = SCHEMA_EMIT_ENGINES.get(schema_version)
    if emit is None:
        return False
    if mode == "formal":
        # Only the current engine may produce new artifacts of any schema.
        return engine_version == ENGINE_VERSION
    return engine_version in emit


def require_validating_engine(
    schema_version: str, engine_version: Any, mode: str
) -> None:
    """Fail closed unless the (schema, engine, mode) triple is documented."""
    if not validating_engine_allowed(schema_version, engine_version, mode):
        require(
            False,
            f"{mode} (schema {schema_version}, engine {engine_version}) is not a "
            "documented compatibility pair",
        )
