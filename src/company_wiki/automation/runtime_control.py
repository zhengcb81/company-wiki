"""Short, fail-closed control boundary shared by legacy and automation workers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from company_wiki.source_catalog.lock import CatalogOperationLock

from .models import RuntimeGate, RuntimeState
from .store import AutomationStore


class RuntimeInterlockError(RuntimeError):
    """Raised when the legacy worker state cannot prove safe automation startup."""


class LegacyWorkerControl(Protocol):
    def interlock_state(self) -> dict[str, object]: ...

    def persist_pause_intent(self) -> dict[str, object]: ...

    def persist_automation_interlock(self, enabled: bool) -> dict[str, object]: ...

    def stop(self, **kwargs: Any) -> dict[str, object]: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_paused_legacy_state(state: dict[str, object]) -> None:
    if state.get("control_valid") is not True:
        raise RuntimeInterlockError("legacy worker control is missing or invalid")
    if state.get("desired_state") != "paused":
        raise RuntimeInterlockError("legacy worker must be persistently paused")
    if state.get("runtime_state") != "stopped":
        raise RuntimeInterlockError("legacy worker runtime must be stopped")


@dataclass(frozen=True)
class PauseResult:
    gate: RuntimeGate
    legacy: dict[str, object]


class AutomationWorkerController:
    """Linearize pause/enable intent without exposing a production start command."""

    def __init__(
        self,
        *,
        store: AutomationStore,
        catalog_dir: Path,
        legacy_controller: LegacyWorkerControl,
        timestamp: Callable[[], str] = _utc_now,
    ) -> None:
        self._store = store
        self._catalog_dir = catalog_dir
        self._legacy = legacy_controller
        self._timestamp = timestamp

    def enable(self) -> RuntimeGate:
        with CatalogOperationLock(
            self._catalog_dir,
            operation="automation-worker-enable",
        ):
            legacy_state = self._legacy.interlock_state()
            _require_paused_legacy_state(legacy_state)
            gate = self._store.read_runtime_gate()
            marker = legacy_state.get("automation_enabled")
            if gate.desired_state is RuntimeState.ENABLED:
                if marker is True:
                    return gate
                raise RuntimeInterlockError(
                    "automation gate is enabled without the legacy interlock"
                )
            if marker is not False:
                raise RuntimeInterlockError(
                    "legacy automation interlock is set while the gate is paused"
                )
            self._legacy.persist_automation_interlock(True)
            try:
                return self._store.set_runtime_gate(
                    RuntimeState.ENABLED,
                    updated_at=self._timestamp(),
                )
            except Exception:
                self._legacy.persist_automation_interlock(False)
                raise

    def pause(
        self,
        *,
        graceful_timeout_seconds: float = 5.0,
        force: bool = True,
    ) -> PauseResult:
        gate: RuntimeGate | None = None
        failure: Exception | None = None
        with CatalogOperationLock(
            self._catalog_dir,
            operation="automation-worker-pause",
        ):
            try:
                gate = self._store.set_runtime_gate(
                    RuntimeState.PAUSED,
                    updated_at=self._timestamp(),
                )
            except Exception as exc:
                failure = exc
            try:
                self._legacy.persist_pause_intent()
            except Exception as exc:
                if failure is None:
                    failure = exc
            try:
                self._legacy.persist_automation_interlock(False)
            except Exception as exc:
                if failure is None:
                    failure = exc
        legacy = self._legacy.stop(
            graceful_timeout_seconds=graceful_timeout_seconds,
            force=force,
        )
        if failure is not None:
            raise RuntimeInterlockError("failed to persist the complete pause boundary") from failure
        if gate is None:
            raise RuntimeInterlockError("runtime gate pause did not return a state")
        return PauseResult(gate=gate, legacy=legacy)


__all__ = [
    "AutomationWorkerController",
    "LegacyWorkerControl",
    "PauseResult",
    "RuntimeInterlockError",
]
