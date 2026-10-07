"""Retired-evidence pruning — retired write maintenance (G3-CWP-MAINT).

The verified-manifest authorisation ladder, frozen-plan apply, pending
receipts and batched ``evidence_spans`` deletes were the destructive half of
the archive → manifest → prune chain; the chain is retired together with the
second destructive permission flow.  Only the import-compatible entry point
remains: it raises the unified
:class:`~.maintenance_retirement.RetiredMaintenanceError` for EVERY call
shape (dry-run, ``--apply``, with or without ``now``, with a frozen plan)
BEFORE taking the operation lock, scanning manifests or opening the catalog.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .maintenance_retirement import RetiredMaintenanceError

RETENTION_DAYS = 90

__all__ = ["RETENTION_DAYS", "prune_retired_evidence"]


def prune_retired_evidence(
    config: Any,
    archive_root: Path | str,
    *,
    apply: bool = False,
    retention_days: int = RETENTION_DAYS,
    now: datetime | None = None,
    plan: Any = None,
) -> None:
    """Retired: always raises before any lock, manifest scan or delete."""
    raise RetiredMaintenanceError("prune-retired-evidence")
