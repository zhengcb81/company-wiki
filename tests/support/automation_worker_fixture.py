"""Spawn-safe deterministic runtime used by automation multiprocessing tests."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from company_wiki.automation.models import HandlerMetrics, HandlerOutcome, HandlerResult
from company_wiki.automation.registry import HandlerSpec, create_default_registry
from company_wiki.automation.worker import HandlerExecutor
from company_wiki.automation.worker_process import WorkerProcessSpec, WorkerRuntime


class FakeModelClient:
    """Identity-only model object proving model clients are child-local."""


def _write_marker(trace_dir: Path, phase: str, job_id: str, worker_id: str) -> None:
    payload = {
        "phase": phase,
        "job_id": job_id,
        "worker_id": worker_id,
        "pid": os.getpid(),
        "monotonic_ns": time.monotonic_ns(),
    }
    path = trace_dir / f"{phase}--{job_id}--{os.getpid()}--{time.monotonic_ns()}.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def create_runtime(spec: WorkerProcessSpec) -> WorkerRuntime:
    """Create all state inside the spawned child; nothing is inherited."""

    options = json.loads(spec.runtime_options_json)
    trace_dir = Path(options["trace_dir"])
    trace_dir.mkdir(parents=True, exist_ok=True)
    delay_by_job = options.get("delay_by_job", {})
    print_bytes = int(options.get("print_bytes", 0))
    block_phase_by_job = options.get("block_phase_by_job", {})

    registry = create_default_registry()
    registry.register(
        HandlerSpec(
            job_type="test.compute",
            handler_version="1.0.0",
            input_schema="test-input/1",
            result_schema="test-result/1",
            effect_class="artifact_only",
            allowed_paths=(),
            network=False,
            llm=False,
            default_max_attempts=3,
            retryable_errors=("LEASE_LOST",),
            human_errors=(),
            terminal_errors=(),
        )
    )
    registry.register(
        HandlerSpec(
            job_type="test.model",
            handler_version="1.0.0",
            input_schema="test-input/1",
            result_schema="test-result/1",
            effect_class="artifact_only",
            allowed_paths=(),
            network=False,
            llm=True,
            default_max_attempts=3,
            retryable_errors=("LEASE_LOST",),
            human_errors=(),
            terminal_errors=(),
        )
    )
    executor = HandlerExecutor()

    def handler(context) -> HandlerResult:
        job_id = context.job.job_id
        _write_marker(trace_dir, "handler_started", job_id, spec.worker_id)
        if block_phase_by_job.get(job_id) == "handler_started":
            while True:
                time.sleep(0.05)
        if print_bytes:
            print("x" * print_bytes, flush=True)
        delay = float(delay_by_job.get(job_id, 0.0))
        if delay:
            time.sleep(delay)
        _write_marker(trace_dir, "handler_finished", job_id, spec.worker_id)
        return HandlerResult(
            outcome=HandlerOutcome.SUCCEEDED,
            result={"worker_id": spec.worker_id, "pid": os.getpid()},
            artifacts=(),
            effects=(),
            metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
            error=None,
        )

    for job_type in spec.allowed_job_types:
        executor.register(job_type, handler)

    def lifecycle(phase: str, claimed) -> None:
        job_id = claimed.job.job_id
        _write_marker(trace_dir, phase, job_id, spec.worker_id)
        if block_phase_by_job.get(job_id) == phase:
            while True:
                time.sleep(0.05)

    runtime_record = {
        "worker_id": spec.worker_id,
        "role": spec.role,
        "pid": os.getpid(),
        "has_model_client": spec.role in {"model", "mixed"},
    }
    (trace_dir / f"runtime--{spec.worker_id}.json").write_text(
        json.dumps(runtime_record, sort_keys=True), encoding="utf-8"
    )
    return WorkerRuntime(
        registry=registry,
        executor=executor,
        model_client=FakeModelClient() if spec.role in {"model", "mixed"} else None,
        lifecycle_callback=lifecycle,
    )

