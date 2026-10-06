"""N6-FOOTPRINT: read-only storage footprint scan of an explicit project root.

The package measures directory footprint from filesystem metadata only. It
never reads original content, never opens databases, never follows links out
of the root and never deletes, moves or hydrates anything.
"""

from __future__ import annotations

from .core import REPORT_SCHEMA

__all__ = ["REPORT_SCHEMA"]
