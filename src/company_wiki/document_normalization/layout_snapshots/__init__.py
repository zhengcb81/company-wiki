"""Real layout snapshot -> existing unit metadata (DU3-GEOMETRY).

Public product API (frozen DU3/1 wire):

    project_layout_snapshot(snapshot, units, *, limits=None) -> dict

It consumes an in-memory ``du-layout-snapshot/1`` mapping and already-read
``du-input/1`` units and returns a ``du-layout-projection/1`` patch
(``unit_metadata`` + coverage/diagnostics/feature version).  It performs no file
or network I/O, calls no model or OCR backend, never rewrites a unit id/text/
locator/role and never creates an EvidenceSpan.

The projection only *binds* real, already-extracted fine geometry (words / cells /
font runs) to existing units and preserves each element's own real bbox plus its
native-index / char-range basis.  It infers no column lane, section / continuation
relation or header/footnote dependence: that remains the shared ``layout_hints``
responsibility.  A whole row/block/table bbox is never copied into a fine cell;
``row_cells`` strings alone are not fine geometry; identical text in different
blocks is never merged; an NFC/trim range that cannot be strictly aligned is
reported ``unknown`` without touching the unit text; an unknown coordinate frame
is reported partial and a physical size is never guessed.
"""

from __future__ import annotations

from .contract import FEATURE_VERSION, PROJECTION_SCHEMA, SNAPSHOT_SCHEMA
from .identity import DEFAULT_LIMITS, WorkBudget, WorkBudgetExceeded, resolve_limits
from .projection import PARTIAL_CODES, project_layout_snapshot

__all__ = [
    "DEFAULT_LIMITS",
    "FEATURE_VERSION",
    "PARTIAL_CODES",
    "PROJECTION_SCHEMA",
    "SNAPSHOT_SCHEMA",
    "WorkBudget",
    "WorkBudgetExceeded",
    "project_layout_snapshot",
    "resolve_limits",
]
