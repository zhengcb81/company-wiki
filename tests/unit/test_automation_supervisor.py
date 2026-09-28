"""RED-first contracts for process topology, role isolation and bounded logs."""

from __future__ import annotations

from pathlib import Path

import pytest


def _modules():
    from company_wiki.automation import supervisor, worker_process

    return supervisor, worker_process


def test_profiles_have_exactly_one_model_slot_and_bounded_total_workers() -> None:
    supervisor, _ = _modules()

    assert [(slot.role, slot.ordinal) for slot in supervisor.profile_slots("P1")] == [
        ("mixed", 1)
    ]
    assert [(slot.role, slot.ordinal) for slot in supervisor.profile_slots("P2")] == [
        ("compute", 1),
        ("model", 1),
    ]
    assert [(slot.role, slot.ordinal) for slot in supervisor.profile_slots("P4")] == [
        ("compute", 1),
        ("compute", 2),
        ("compute", 3),
        ("model", 1),
    ]
    for profile in ("P1", "P2", "P4"):
        slots = supervisor.profile_slots(profile)
        assert sum(slot.role in {"model", "mixed"} for slot in slots) == 1
        assert len(slots) == int(profile[1:])


def test_compute_runtime_rejects_model_client_and_model_job_types() -> None:
    _, worker_process = _modules()
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.worker import HandlerExecutor

    runtime = worker_process.WorkerRuntime(
        registry=create_default_registry(),
        executor=HandlerExecutor(),
        model_client=object(),
    )
    with pytest.raises(ValueError, match="compute.*model client"):
        worker_process.validate_runtime(
            runtime, role="compute", allowed_job_types=("source.normalize",)
        )

    runtime = worker_process.WorkerRuntime(
        registry=create_default_registry(), executor=HandlerExecutor()
    )
    with pytest.raises(ValueError, match="compute.*LLM"):
        worker_process.validate_runtime(
            runtime, role="compute", allowed_job_types=("source.analyze",)
        )


def test_model_runtime_rejects_compute_job_types() -> None:
    _, worker_process = _modules()
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.worker import HandlerExecutor

    runtime = worker_process.WorkerRuntime(
        registry=create_default_registry(),
        executor=HandlerExecutor(),
        model_client=object(),
    )
    with pytest.raises(ValueError, match="model.*non-LLM"):
        worker_process.validate_runtime(
            runtime, role="model", allowed_job_types=("source.normalize",)
        )


def test_bounded_log_writer_never_exceeds_cap(tmp_path: Path) -> None:
    _, worker_process = _modules()
    path = tmp_path / "worker.stdout.log"
    writer = worker_process.BoundedLogWriter(path, max_bytes=64)

    writer.write("a" * 40)
    writer.write("b" * 80)
    writer.flush()

    assert path.stat().st_size == 64
    assert path.read_bytes() == b"b" * 64


def test_bounded_log_writer_preserves_bounded_tail_across_worker_restart(
    tmp_path: Path,
) -> None:
    _, worker_process = _modules()
    path = tmp_path / "worker.stderr.log"
    first = worker_process.BoundedLogWriter(path, max_bytes=32)
    first.write("first-crash\n")

    restarted = worker_process.BoundedLogWriter(path, max_bytes=32)
    restarted.write("second-start\n")

    assert path.read_text(encoding="utf-8") == "first-crash\nsecond-start\n"

