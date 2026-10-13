"""Document-understanding upgrade: shared observation layer for three lanes.

The three lanes are independent pure packages:

* :mod:`company_wiki.document_understanding.profiles` — document routing and
  reading strategy (:func:`route_document`, :func:`get_profile`,
  :func:`list_profiles`).
* :mod:`company_wiki.document_understanding.structure` — cross-page sections
  and semantic units (:func:`build_structure`).
* ``tools.document_understanding_benchmark`` — independent quality benchmark.

This module owns only what is genuinely shared:

* :func:`build_observation` — the projection from existing parser units onto the frozen
  ``du-input/1`` observation, including the Q&A shadow marking;
* :func:`understand_units` — the end-to-end chain that feeds one observation through
  routing, structure and package building without either package importing the other;
* :func:`build_dependency_packages` — the dependency-closed package view the flat
  candidate list cannot express;
* :func:`build_summary_input` — the profile-driven summary *request* (focus, evidence with
  provenance, budget accounting, honest unread list). It assembles what to ask and never
  calls a model, so the existing transport and budget stay authoritative.

Nothing here opens a company directory, re-verifies a security identity, or
collects a human sign-off: the reading responsibility layer has already opened
and verified the original by the time these functions run.
"""

from __future__ import annotations

from .observation_adapter import build_observation, is_selectable, selectable_unit_ids
from .orchestration import build_dependency_packages, package_units_for_prompt
from .pipeline import PIPELINE_SCHEMA_VERSION, understand_units
from .summary_input import SUMMARY_INPUT_SCHEMA_VERSION, build_summary_input

__all__ = [
    "PIPELINE_SCHEMA_VERSION",
    "SUMMARY_INPUT_SCHEMA_VERSION",
    "build_dependency_packages",
    "build_observation",
    "build_summary_input",
    "is_selectable",
    "package_units_for_prompt",
    "selectable_unit_ids",
    "understand_units",
]
