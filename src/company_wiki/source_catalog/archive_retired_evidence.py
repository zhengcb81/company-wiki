"""Retired-evidence archiving — retired write maintenance (G3-CWP-MAINT).

The streaming gzip snapshot export, its verification/publish ladder and the
per-snapshot manifest writer were the destructive permission chain's first
half; the chain (archive → manifest → prune delete) is retired together.
Only the import-compatible entry point remains: it raises the unified
:class:`~.maintenance_retirement.RetiredMaintenanceError` for EVERY call
shape — the historical CLI passes no ``now``, tests pass ``now=...`` — and
does so BEFORE opening the catalog or creating any archive directory.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from .maintenance_retirement import RetiredMaintenanceError

__all__ = ["archive_retired_evidence"]


def archive_retired_evidence(
    database_path: Path | str,
    archive_root: Path | str,
    *,
    now: datetime | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    """Retired: always raises before touching the catalog or filesystem."""
    raise RetiredMaintenanceError("archive-retired-evidence")
