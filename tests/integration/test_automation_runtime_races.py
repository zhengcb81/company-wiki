"""E2 race contract for pause generation versus an in-flight completion."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from threading import Barrier, Thread

import pytest


NOW = "2026-09-28T12:00:00Z"
LATER = "2026-09-28T12:01:00Z"


class _Legacy:
    def __init__(self) -> None:
        self.desired_state = "paused"
        self.runtime_state = "stopped"
        self.automation_enabled = False

    def interlock_state(self):
        return {
            "control_valid": True,
            "desired_state": self.desired_state,
            "runtime_state": self.runtime_state,
            "automation_enabled": self.automation_enabled,
        }

    def persist_pause_intent(self):
        self.desired_state = "paused"
        return self.interlock_state()

    def stop(self, **_kwargs):
        self.runtime_state = "stopped"
        return self.interlock_state()

    def persist_automation_interlock(self, enabled):
        self.automation_enabled = enabled
        return self.interlock_state()


def _successful_result():
    from company_wiki.automation.models import (
        HandlerMetrics,
        HandlerOutcome,
        HandlerResult,
    )

    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result={"ok": True},
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )


def test_pause_and_finish_have_one_linearized_outcome(tmp_path: Path) -> None:
    from company_wiki.automation.models import (
        Event,
        Job,
        JobStatus,
        RiskClass,
        RuntimeState,
        canonical_json,
        make_job_key,
    )
    from company_wiki.automation.runtime_control import AutomationWorkerController
    from company_wiki.automation.store import (
        AutomationStore,
        RuntimeGateClosedError,
        RuntimeGenerationError,
    )

    store = AutomationStore(tmp_path / "automation.db")
    legacy = _Legacy()
    controller = AutomationWorkerController(
        store=store,
        catalog_dir=tmp_path / "catalog",
        legacy_controller=legacy,
        timestamp=lambda: NOW,
    )
    gate = controller.enable()
    input_hash = hashlib.sha256(b"e2-race-job").hexdigest()
    store.put_event(
        Event(
            event_id="evt-e2-race",
            event_type="source.revision_registered",
            subject_type="source",
            subject_id="src-e2-race",
            input_hash=input_hash,
            payload_json=canonical_json({"source_id": "src-e2-race"}),
            policy_version="v1",
            occurred_at=NOW,
            observed_at=NOW,
        )
    )
    store.put_job(
        Job(
            job_id="job-e2-race",
            job_key=make_job_key(
                "source.normalize", "source", "src-e2-race", input_hash, "v1", "1.0.0"
            ),
            job_type="source.normalize",
            subject_type="source",
            subject_id="src-e2-race",
            input_hash=input_hash,
            policy_version="v1",
            handler_version="1.0.0",
            risk_class=RiskClass.LOW,
            status=JobStatus.READY,
            priority=0,
            not_before=NOW,
            max_attempts=2,
            created_from_event_id="evt-e2-race",
            created_at=NOW,
            updated_at=NOW,
            last_error_code=None,
            last_error_detail=None,
        )
    )
    claim = store.claim_next_ready(
        worker_id="worker-e2",
        attempt_id="attempt-e2-race",
        lease_token="lease-e2-race",
        now=NOW,
        lease_until=LATER,
        expected_generation=gate.control_generation,
    )
    assert claim is not None

    barrier = Barrier(3)
    outcomes: list[str] = []

    def pause() -> None:
        barrier.wait()
        controller.pause(graceful_timeout_seconds=0, force=False)
        outcomes.append("paused")

    def finish() -> None:
        barrier.wait()
        try:
            store.finish_attempt(
                attempt_id=claim.attempt.attempt_id,
                lease_token=claim.attempt.lease_token,
                runtime_generation=claim.attempt.runtime_generation,
                finished_at=NOW,
                result=_successful_result(),
            )
        except (RuntimeGateClosedError, RuntimeGenerationError):
            outcomes.append("finish_fenced")
        else:
            outcomes.append("finish_committed")

    threads = [Thread(target=pause), Thread(target=finish)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()

    assert "paused" in outcomes
    assert len({"finish_fenced", "finish_committed"}.intersection(outcomes)) == 1
    assert store.read_runtime_gate().desired_state is RuntimeState.PAUSED
    assert legacy.automation_enabled is False
    job = store.get_job(claim.job.job_id)
    assert job is not None
    if "finish_committed" in outcomes:
        assert job.status is JobStatus.SUCCEEDED
    else:
        assert job.status is JobStatus.RUNNING
    assert not (tmp_path / "catalog" / "operation.lock").exists()


def test_real_legacy_controller_and_automation_gate_are_mutually_exclusive(
    tmp_path: Path,
) -> None:
    from company_wiki.automation.models import RuntimeState
    from company_wiki.automation.runtime_control import AutomationWorkerController
    from company_wiki.automation.store import AutomationStore
    from company_wiki.source_catalog.control import WorkerController

    project = tmp_path / "project"
    config = project / "config" / "source_catalog.yaml"
    worker_config = project / "config" / "source_catalog_worker.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    worker_config.write_text("schema_version: '1.0'\n", encoding="utf-8")
    catalog_dir = project / ".source_catalog"
    legacy = WorkerController(
        catalog_dir=catalog_dir,
        project_root=project,
        config_path=config,
        worker_config_path=worker_config,
        python_executable=Path(sys.executable),
        process_identity=lambda _pid: None,
        terminate_process=lambda _expected: False,
        process_inventory_provider=lambda: {},
        sleeper=lambda _seconds: None,
    )
    legacy.persist_pause_intent()
    store = AutomationStore(tmp_path / "automation.db")
    controller = AutomationWorkerController(
        store=store,
        catalog_dir=catalog_dir,
        legacy_controller=legacy,
        timestamp=lambda: NOW,
    )

    enabled = controller.enable()
    assert enabled.desired_state is RuntimeState.ENABLED
    assert legacy.interlock_state()["automation_enabled"] is True
    with pytest.raises(RuntimeError, match="automation worker"):
        legacy.resume(wait_seconds=0)

    paused = controller.pause(graceful_timeout_seconds=0, force=False)
    assert paused.gate.desired_state is RuntimeState.PAUSED
    assert legacy.interlock_state() == {
        "automation_enabled": False,
        "control_valid": True,
        "desired_state": "paused",
        "runtime_state": "stopped",
    }
