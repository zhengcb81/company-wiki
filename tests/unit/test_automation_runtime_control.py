"""E2 runtime interlock and fail-closed gate contracts."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest


NOW = "2026-09-28T11:00:00Z"
LATER = "2026-09-28T11:01:00Z"


class _FakeLegacyController:
    def __init__(
        self,
        *,
        valid: bool = True,
        desired_state: str = "paused",
        runtime_state: str = "stopped",
    ) -> None:
        self.valid = valid
        self.desired_state = desired_state
        self.runtime_state = runtime_state
        self.persisted: list[str] = []
        self.automation_enabled = False
        self.stop_calls = 0

    def interlock_state(self) -> dict[str, object]:
        return {
            "control_valid": self.valid,
            "desired_state": self.desired_state,
            "runtime_state": self.runtime_state,
            "automation_enabled": self.automation_enabled,
        }

    def persist_pause_intent(self) -> dict[str, object]:
        self.persisted.append("paused")
        self.desired_state = "paused"
        self.valid = True
        return self.interlock_state()

    def stop(self, **_kwargs) -> dict[str, object]:
        self.stop_calls += 1
        self.runtime_state = "stopped"
        return self.interlock_state()

    def persist_automation_interlock(self, enabled: bool) -> dict[str, object]:
        self.automation_enabled = enabled
        return self.interlock_state()


def _store(tmp_path: Path):
    from company_wiki.automation.store import AutomationStore

    tmp_path.mkdir(parents=True, exist_ok=True)
    return AutomationStore(tmp_path / "automation.db")


def _controller(store, tmp_path: Path, legacy: _FakeLegacyController):
    from company_wiki.automation.runtime_control import AutomationWorkerController

    return AutomationWorkerController(
        store=store,
        catalog_dir=tmp_path / "catalog",
        legacy_controller=legacy,
        timestamp=lambda: NOW,
    )


def _ready_job(store) -> None:
    from company_wiki.automation.models import (
        Event,
        Job,
        JobStatus,
        RiskClass,
        canonical_json,
        make_job_key,
    )

    input_hash = hashlib.sha256(b"e2-gate-job").hexdigest()
    store.put_event(
        Event(
            event_id="evt-e2-gate",
            event_type="source.revision_registered",
            subject_type="source",
            subject_id="src-e2",
            input_hash=input_hash,
            payload_json=canonical_json({"source_id": "src-e2"}),
            policy_version="v1",
            occurred_at=NOW,
            observed_at=NOW,
        )
    )
    job_key = make_job_key("source.normalize", "source", "src-e2", input_hash, "v1", "1.0.0")
    store.put_job(
        Job(
            job_id="job-e2-gate",
            job_key=job_key,
            job_type="source.normalize",
            subject_type="source",
            subject_id="src-e2",
            input_hash=input_hash,
            policy_version="v1",
            handler_version="1.0.0",
            risk_class=RiskClass.LOW,
            status=JobStatus.READY,
            priority=0,
            not_before=NOW,
            max_attempts=2,
            created_from_event_id="evt-e2-gate",
            created_at=NOW,
            updated_at=NOW,
            last_error_code=None,
            last_error_detail=None,
        )
    )


def _claim(store, generation: int):
    return store.claim_next_ready(
        worker_id="worker-e2",
        attempt_id="attempt-e2-gate",
        lease_token="lease-e2-gate",
        now=NOW,
        lease_until=LATER,
        expected_generation=generation,
    )


def test_enable_requires_valid_paused_stopped_legacy_interlock(tmp_path: Path) -> None:
    from company_wiki.automation.models import RuntimeState
    from company_wiki.automation.runtime_control import RuntimeInterlockError

    for legacy in (
        _FakeLegacyController(valid=False),
        _FakeLegacyController(desired_state="enabled"),
        _FakeLegacyController(runtime_state="running"),
    ):
        store = _store(tmp_path / str(id(legacy)))
        with pytest.raises(RuntimeInterlockError):
            _controller(store, tmp_path / str(id(legacy)), legacy).enable()
        assert store.read_runtime_gate().desired_state is RuntimeState.PAUSED


def test_enable_then_pause_updates_gate_under_lock_and_stops_legacy(
    tmp_path: Path,
) -> None:
    from company_wiki.automation.models import RuntimeState

    store = _store(tmp_path)
    legacy = _FakeLegacyController()
    controller = _controller(store, tmp_path, legacy)

    enabled = controller.enable()
    assert legacy.automation_enabled is True
    paused = controller.pause(graceful_timeout_seconds=0, force=False)

    assert enabled.desired_state is RuntimeState.ENABLED
    assert paused.gate.desired_state is RuntimeState.PAUSED
    assert paused.gate.control_generation == enabled.control_generation + 1
    assert legacy.persisted == ["paused"]
    assert legacy.automation_enabled is False
    assert legacy.stop_calls == 1
    assert not (tmp_path / "catalog" / "operation.lock").exists()


def test_enable_is_idempotent_when_both_interlock_layers_are_enabled(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    legacy = _FakeLegacyController()
    controller = _controller(store, tmp_path, legacy)

    first = controller.enable()
    second = controller.enable()

    assert second == first
    assert legacy.automation_enabled is True


@pytest.mark.parametrize("corruption", ["missing", "invalid"])
def test_claim_fails_closed_when_runtime_gate_is_missing_or_corrupt(
    tmp_path: Path,
    corruption: str,
) -> None:
    from company_wiki.automation.models import RuntimeState
    from company_wiki.automation.store import RuntimeGateClosedError

    store = _store(tmp_path)
    _ready_job(store)
    gate = store.set_runtime_gate(RuntimeState.ENABLED, updated_at=NOW)
    connection = sqlite3.connect(store.db_path)
    try:
        if corruption == "missing":
            connection.execute("DELETE FROM runtime_gate WHERE singleton_id = 1")
        else:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute(
                "UPDATE runtime_gate SET desired_state = 'invalid' WHERE singleton_id = 1"
            )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeGateClosedError):
        _claim(store, gate.control_generation)
