"""Unified retirement signal for legacy maintenance write entries (G3-CWP-MAINT).

The old write-maintenance backends — ``focus-cleanup`` (preview/apply and its
restore paths), ``archive-retired-evidence``, ``prune-retired-evidence``,
``duplicate-preview``/``duplicate-recycle`` plus the recycle-bin helper and
duplicate-journal writes — are permanently retired.  Calling any of them must
raise :class:`RetiredMaintenanceError` BEFORE any Store, operation lock, file
or journal is touched, for every historical call shape (missing ``now``,
unknown confirmation tokens, dry-run or ``--apply``).

The message states the retirement and points at the read-only inventory; it
never suggests re-signing, confirmation tokens or backups.  Consumers
(however the public CLI is wired by its owner) map this exception — and its
``operation`` attribute — to a named non-zero result.
"""

from __future__ import annotations

RETIRED_OPERATION_CODE = "MAINTENANCE_OPERATION_RETIRED"

__all__ = ["RETIRED_OPERATION_CODE", "RetiredMaintenanceError"]


class RetiredMaintenanceError(RuntimeError):
    """A retired maintenance write entry was called.

    Attributes:
        code: always ``"MAINTENANCE_OPERATION_RETIRED"`` (also a class
            attribute, readable without an instance).
        operation: the retired entry point, named the way the CLI names it
            (for example ``"focus-cleanup"`` or ``"prune-retired-evidence"``).
    """

    code = RETIRED_OPERATION_CODE

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"maintenance operation retired: {operation} "
            f"({RETIRED_OPERATION_CODE}); the legacy write entry is "
            "permanently retired — use the read-only inventory "
            "(list_groups / inventory_dropbox) and historical journal reads "
            "instead"
        )
