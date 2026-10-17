"""Bounded, fair, recoverable geometry-request planning for one parse round.

Pure in-call state only: no DB, files, threads, task stores, tokens or expiry.
Consumes the fixed ``du-geometry-policy/1`` data interface (compiled by the
POLICY card) and ROOT-bound windows; never re-interprets heading words, never
calls ``_match_rule`` / ``find_tables`` / ``TextPage``, never creates evidence
or body locators, and never resets the caller's work budget.
"""
from __future__ import annotations

from .contracts import (
    DEMAND_CLASSES,
    DISCOVER_VALUES,
    EVIDENCE_VALUES,
    FINE_VALUES,
    NAVIGATION_VALUES,
    SCHEMA_ADMISSION,
    SCHEMA_PLAN,
    SCHEMA_POLICY,
    SCHEMA_RUN_SUMMARY,
    SCHEMA_STATE,
)
from .planner import (
    admit_geometry_request,
    new_admission_state,
    plan_geometry_requests,
    summarize_admission_state,
)

__all__ = [
    "DEMAND_CLASSES",
    "DISCOVER_VALUES",
    "EVIDENCE_VALUES",
    "FINE_VALUES",
    "NAVIGATION_VALUES",
    "SCHEMA_ADMISSION",
    "SCHEMA_PLAN",
    "SCHEMA_POLICY",
    "SCHEMA_RUN_SUMMARY",
    "SCHEMA_STATE",
    "admit_geometry_request",
    "new_admission_state",
    "plan_geometry_requests",
    "summarize_admission_state",
]
