"""Case/check ledger shared by the P4 tests and the receipt writer.

Tests record what they actually exercised.  A skip is recorded as ``skip`` with
a reason and is never promoted to ``pass``; ``not_evaluated`` stays
``not_evaluated``.
"""

from __future__ import annotations

import threading
from typing import Any

from . import constants as C


def case_name(request) -> str:  # noqa: ANN001 - pytest FixtureRequest
    """Contract case name for a test: its function name, params stripped.

    Tests call ``p4_case()`` (no argument) so the ledger name can never drift
    from the nodeid the session report derives.
    """
    return request.node.name.split("[", 1)[0]


class LedgerError(RuntimeError):
    """The lane's own bookkeeping contract was violated (a test bug, not a result)."""


class Case:
    """One named case with its per-check outcomes."""

    __slots__ = ("name", "status", "reason", "checks")

    def __init__(self, name: str, status: str = "skip", reason: str | None = None):
        if status not in C.CASE_STATUSES:
            raise LedgerError(f"unknown case status {status!r}")
        self.name = name
        self.status = status
        self.reason = reason
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, status: str, detail: dict[str, Any] | None = None):
        if status not in C.CHECK_STATUSES:
            raise LedgerError(f"unknown check status {status!r}")
        if status in {"not_applicable", "not_evaluated"} and not (
            detail or {}
        ).get("reason"):
            raise LedgerError(f"check {name!r} status {status!r} requires a reason")
        self.checks.append({"name": name, "status": status, "detail": dict(detail or {})})
        return status

    def settle(self, status: str, reason: str | None = None) -> str:
        if status not in C.CASE_STATUSES:
            raise LedgerError(f"unknown case status {status!r}")
        self.status = status
        self.reason = reason
        return status

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "reason": self.reason,
            "checks": self.checks,
        }


class Ledger:
    """Thread-safe ordered collection of cases for one pytest session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cases: list[Case] = []
        self._started = False

    def start(self) -> None:
        with self._lock:
            self._started = True

    def case(self, name: str) -> Case:
        with self._lock:
            existing = next((item for item in self._cases if item.name == name), None)
            if existing is not None:
                return existing
            created = Case(name)
            self._cases.append(created)
            return created

    def record(
        self, name: str, status: str, *, reason: str | None = None
    ) -> Case:
        case = self.case(name)
        case.settle(status, reason)
        return case

    def cases(self) -> list[Case]:
        with self._lock:
            return list(self._cases)

    def reset(self) -> None:
        with self._lock:
            self._cases.clear()
            self._started = False


LEDGER = Ledger()
