"""Spawn-safe narrative runtime used by the real-sample E6 acceptance test."""

from __future__ import annotations

import json
import time
from pathlib import Path

from company_wiki.automation.narrative_runtime import (
    NarrativeRuntimeDependencies,
    register_narrative_handlers,
)
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.worker import HandlerExecutor
from company_wiki.automation.worker_process import WorkerProcessSpec, WorkerRuntime
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader

from .narrative_model_fixture import ReplayNarrativeModel


class _DelayedReplayNarrativeModel:
    """Return deterministic local results while giving P2 overlap real work time."""

    def __init__(self, delay_seconds: float) -> None:
        self._delegate = ReplayNarrativeModel()
        self._delay_seconds = delay_seconds

    def generate(self, request):
        response = self._delegate.generate(request)
        if self._delay_seconds:
            time.sleep(self._delay_seconds)
        return response


def _catalog_config(project_root: Path) -> CatalogConfig:
    companies = project_root / "companies"
    return CatalogConfig(
        project_root=project_root,
        catalog_dir=project_root / "catalog",
        roots=(
            RootSpec(
                "company_raw",
                companies,
                "company_raw",
                priority=10,
                adapter_id="company_raw_v1",
                read_only=False,
                reusable_for_filing=True,
                canonical_write_target="companies",
            ),
        ),
        reusable_root_kinds=("company_raw",),
    )


def _write_lifecycle(trace_dir: Path, phase: str, claimed, spec) -> None:
    if phase not in {"claimed", "before_finish"}:
        return
    attempt_no = claimed.attempt.attempt_no
    payload = {
        "phase": phase,
        "job_id": claimed.job.job_id,
        "job_type": claimed.job.job_type,
        "source_id": claimed.job.subject_id,
        "attempt_no": attempt_no,
        "worker_id": spec.worker_id,
        "role": spec.role,
        "monotonic_ns": time.monotonic_ns(),
    }
    path = trace_dir / (
        f"{phase}--{claimed.job.job_id}--{attempt_no}--{spec.worker_id}.json"
    )
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_model_call(trace_dir: Path, request) -> None:
    envelope = json.loads(request.data_json)
    source_id = str(envelope["source"]["source_id"])
    path = trace_dir / f"model-call--{time.monotonic_ns()}.json"
    path.write_text(
        json.dumps(
            {
                "source_id": source_id,
                "monotonic_ns": time.monotonic_ns(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def create_runtime(spec: WorkerProcessSpec) -> WorkerRuntime:
    """Build catalog, source reader, model and handlers inside each child process."""

    options = json.loads(spec.runtime_options_json)
    project_root = Path(options["project_root"])
    trace_dir = Path(options["trace_dir"])
    trace_dir.mkdir(parents=True, exist_ok=True)
    block_phase_by_job = options.get("block_phase_by_job", {})
    release_file_by_job = options.get("release_file_by_job", {})

    catalog = SourceCatalog(_catalog_config(project_root))
    reader = SourceVersionReader(catalog)
    model = (
        _DelayedReplayNarrativeModel(
            float(options.get("model_delay_seconds", 0.0))
        )
        if spec.role in {"model", "mixed"}
        else None
    )
    if model is not None:
        original_generate = model.generate

        def generate_and_record(request):
            _write_model_call(trace_dir, request)
            return original_generate(request)

        model.generate = generate_and_record
    registry = create_default_registry()
    executor = HandlerExecutor()
    register_narrative_handlers(
        executor,
        NarrativeRuntimeDependencies(reader=reader, model=model),
    )

    def lifecycle(phase, claimed) -> None:
        _write_lifecycle(trace_dir, phase, claimed, spec)
        if block_phase_by_job.get(claimed.job.job_id) != phase:
            return
        release_file = release_file_by_job.get(claimed.job.job_id)
        if release_file is None:
            while True:
                time.sleep(0.05)
        while not Path(release_file).exists():
            time.sleep(0.05)

    return WorkerRuntime(
        registry=registry,
        executor=executor,
        model_client=model,
        lifecycle_callback=lifecycle,
    )
