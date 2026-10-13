"""Document-understanding upgrade: shared observation layer for three lanes.

The three lanes are independent pure packages:

* :mod:`company_wiki.document_understanding.profiles` — document routing and
  reading strategy (:func:`route_document`).
* :mod:`company_wiki.document_understanding.structure` — cross-page sections
  and semantic units (:func:`build_structure`).
* ``tools.document_understanding_benchmark`` — independent quality benchmark.

This module owns only what is genuinely shared: the projection from existing
parser units onto the frozen ``du-input/1`` observation, and the orchestration
that feeds one observation through routing and structure without either package
importing the other.

Nothing here opens a company directory, re-verifies a security identity, or
collects a human sign-off: the reading responsibility layer has already opened
and verified the original by the time these functions run.
"""

from __future__ import annotations

from .observation_adapter import build_observation

__all__ = ["build_observation"]
