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
  ``du-input/1`` observation;
* :func:`understand_units` — the end-to-end chain that feeds one observation through
  routing, structure and package building without either package importing the other;
* :func:`build_dependency_packages` — the dependency-closed package view the flat
  candidate list cannot express.

Nothing here opens a company directory, re-verifies a security identity, or
collects a human sign-off: the reading responsibility layer has already opened
and verified the original by the time these functions run.
"""

from __future__ import annotations

from .observation_adapter import build_observation
from .orchestration import build_dependency_packages, package_units_for_prompt
from .pipeline import PIPELINE_SCHEMA_VERSION, understand_units

__all__ = [
    "PIPELINE_SCHEMA_VERSION",
    "build_dependency_packages",
    "build_observation",
    "package_units_for_prompt",
    "understand_units",
]
