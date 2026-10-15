"""DU4-STATE operating-relation detection (source-oriented, in-memory only).

Public entry point per docs/plans/du4-state-2026-10-15/INTERFACES.md:

* :func:`detect_operating_relations` — bounded operating assertion relations
  (actor / object / predicate / qualifier refs over original unit offsets,
  with polarity, stage, attribution and modality kept apart).

This package owns no persistence, budget, identity or routing state: callers
pass the shared :class:`WorkBudget` instance and keep their own source roles,
locators and QA closures untouched. Output is diagnostic source meaning only —
never a score, a selection decision or an investment conclusion.
"""

from __future__ import annotations

from .relations import (
    OBSERVATION_SCHEMA,
    RELATIONS_SCHEMA,
    detect_operating_relations,
)

__all__ = [
    "OBSERVATION_SCHEMA",
    "RELATIONS_SCHEMA",
    "detect_operating_relations",
]
