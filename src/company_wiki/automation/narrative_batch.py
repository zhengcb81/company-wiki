"""One finite, scoped application over the existing AUTO task system."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import stat
import time
from typing import Any

from company_wiki._file_mutex import os_file_mutex

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.lock import CatalogOperationLock
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactNotVisibleError, NarrativeArtifactStore,
)
from company_wiki.source_catalog.narrative_language import detect_narrative_language
from company_wiki.source_catalog.source_reader import SourceVersionReader

from .models import Event, JobStatus, RuntimeState, canonical_json, canonical_json_hash
from .narrative_batch_request import NarrativeBatchRequest
from .narrative_contracts import (
    BUNDLE_MAX_BYTES, SELECT_RESULT_MAX_BYTES, SUMMARY_RESULT_MAX_BYTES,
    SourceRevisionEventPayload,
)
from .narrative_model import NARRATIVE_PROMPT_VERSION
from .narrative_projection import NarrativeEffectDispatcher
from .narrative_run_store import NarrativeRunStore, RunConflictError
from .narrative_source_guard import (
    NarrativeSourceGuardError,
    source_ref,
    validate_opened_source,
)
from .narrative_verify import EFFECT_TYPE
from .policy import PolicyConfig
from .registry import create_default_registry
from .scheduler import AutomationScheduler
from .store import AutomationStore
from .supervisor import AutomationSupervisor, SupervisorConfig, profile_slots
from .terminal_receipt_contracts import FinalArtifactPin
from .terminal_receipts import compact_terminal_narrative_jobs


@dataclass(frozen=True)
class BatchEvents:
    input_hash: str
    events: tuple[Event, ...]


class BatchPreparationDeadlineExceeded(TimeoutError):
    """The existing request time budget was spent before workers started."""


def _check_preparation_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise BatchPreparationDeadlineExceeded("BATCH_PREPARATION_DEADLINE_EXCEEDED")


def build_batch_events(request: NarrativeBatchRequest, reader: SourceVersionReader, *, now: str,
                       deadline: float | None = None) -> BatchEvents:
    """Bind current source facts and execution settings before materializing jobs."""
    _check_preparation_deadline(deadline)
    policy = reader.read_policy_sha256()
    payloads = []
    for ref in request.sources:
        _check_preparation_deadline(deadline)
        current = reader.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
        if asdict(current) != ref.to_dict():
            raise ValueError("SOURCE_REF_CHANGED")
        metadata = reader.describe_version(current)
        _check_preparation_deadline(deadline)
        kind = metadata["document_kind"]
        language = metadata.get("language")
        if language is None:
            opened = reader.open_version(
                current,
                purpose="narrative_derivation",
                expected_read_policy_sha256=policy,
            )
            _check_preparation_deadline(deadline)
            try:
                validate_opened_source(
                    current,
                    opened,
                    expected_read_policy_sha256=policy,
                )
            except NarrativeSourceGuardError as exc:
                if exc.code == "SOURCE_HASH_MISMATCH":
                    raise ValueError("SOURCE_LANGUAGE_SOURCE_MISMATCH") from exc
                raise
            language = detect_narrative_language(opened.data, current.mime_type)
            _check_preparation_deadline(deadline)
        payloads.append(SourceRevisionEventPayload.from_dict({
            "schema_version": "source-revision-event/2.0", "source_ref": ref.to_dict(),
            "expected_read_policy_sha256": policy,
            "source_metadata": {"source_class": "transcript" if kind == "investor_call_transcript" else "filing",
                                "title": metadata["title"], "document_kind": kind, "language": language},
        }))
    _check_preparation_deadline(deadline)
    input_hash = canonical_json_hash({"request_sha256": request.input_hash,
                                      "source_payloads": [payload.to_dict() for payload in payloads]})
    return BatchEvents(input_hash, tuple(Event(
        "narrative-batch-" + canonical_json_hash({"run": input_hash, "source": payload.source_ref.document_id}),
        "source.revision_registered", "source_revision", payload.source_ref.document_id,
        payload.input_hash, canonical_json(payload.to_dict()), "narrative-batch/1:" + input_hash, now, now,
    ) for payload in payloads))


@dataclass(frozen=True)
class StorageSnapshot:
    persistent_added_bytes: int
    scratch_bytes: int
    scratch_peak_bytes: int


def _tree_bytes(path: Path) -> int:
    try:
        info = path.stat()
    except FileNotFoundError:
        return 0
    if stat.S_ISREG(info.st_mode):
        return info.st_size
    total = 0
    for item in path.rglob("*"):
        try:
            info = item.stat()
        except FileNotFoundError:
            # SQLite sidecars and atomic object files may be reclaimed while
            # sampling. Their disappearance releases storage, not a run error.
            continue
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
    return total


class BatchStorageBudget:
    """Measure only application-owned storage, never a raw document tree."""

    def __init__(self, *, files: tuple[Path, ...], persistent_dirs: tuple[Path, ...],
                 scratch_dirs: tuple[Path, ...], max_persistent_bytes: int, max_scratch_bytes: int,
                 baseline: tuple[int, ...] | None = None):
        self.paths = files + persistent_dirs
        self.baseline = baseline if baseline is not None else tuple(_tree_bytes(path) for path in self.paths)
        if len(self.baseline) != len(self.paths) or any(type(size) is not int or size < 0 for size in self.baseline):
            raise ValueError("BATCH_STORAGE_BASELINE_INVALID")
        self.scratch_dirs = scratch_dirs
        self.max_persistent_bytes = max_persistent_bytes
        self.max_scratch_bytes = max_scratch_bytes
        self.peak = 0

    def snapshot(self) -> StorageSnapshot:
        added = sum(max(0, _tree_bytes(path) - size) for path, size in zip(self.paths, self.baseline))
        scratch = sum(_tree_bytes(path) for path in self.scratch_dirs)
        self.peak = max(self.peak, scratch)
        return StorageSnapshot(added, scratch, self.peak)

    def check(self) -> StorageSnapshot:
        result = self.snapshot()
        if result.persistent_added_bytes > self.max_persistent_bytes:
            raise ValueError("PERSISTENT_BYTES_EXCEEDED")
        if result.scratch_bytes > self.max_scratch_bytes:
            raise ValueError("SCRATCH_BYTES_EXCEEDED")
        return result


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _storage_guard(request, catalog, db_path, work_dir, input_hash):
    database_paths = (db_path, catalog.config.database_path)
    files = tuple(path for database in database_paths for path in (
        database, Path(str(database) + "-wal"), Path(str(database) + "-shm")))
    baseline_path = work_dir / "storage-baseline.json"
    baseline = None
    if baseline_path.exists():
        saved = json.loads(baseline_path.read_text(encoding="utf-8"))
        if saved.get("input_hash") != input_hash:
            raise ValueError("BATCH_WORK_DIRECTORY_CONFLICT")
        baseline = tuple(saved["sizes"])
    guard = BatchStorageBudget(files=files, persistent_dirs=(catalog.config.catalog_dir / "objects", work_dir),
        scratch_dirs=(), max_persistent_bytes=request.max_persistent_bytes,
        max_scratch_bytes=request.max_scratch_bytes, baseline=baseline)
    if baseline is None:
        baseline_path.write_text(canonical_json({"input_hash": input_hash, "sizes": list(guard.baseline)}), encoding="utf-8")
    return guard


class _BudgetedObjects(LocalNarrativeObjectStore):
    def __init__(self, root, guard, max_final_bytes):
        super().__init__(root)
        self.guard = guard
        self.max_final_bytes = max_final_bytes

    def put(self, data):
        if len(data) > self.max_final_bytes:
            raise ValueError("FINAL_BYTES_EXCEEDED")
        if len(data) > self.guard.max_scratch_bytes:
            raise ValueError("SCRATCH_BYTES_EXCEEDED")
        self.guard.check()
        # The object writer creates one temporary file containing exactly these
        # bytes and removes it in finally. PDF/text parsing uses memory only.
        self.guard.peak = max(self.guard.peak, len(data))
        return super().put(data)


def _preflight_storage(request):
    # All contracts are byte-bounded. Admit their worst case plus SQLite/WAL/log
    # overhead before any worker or HTTP starts; measured growth is checked too.
    per_source = SELECT_RESULT_MAX_BYTES + SUMMARY_RESULT_MAX_BYTES + 2 * BUNDLE_MAX_BYTES + 1024 ** 2
    reserve = len(request.sources) * per_source + len(profile_slots(request.profile)) * 262144 + 8 * 1024 ** 2
    if reserve > request.max_persistent_bytes:
        raise ValueError("PERSISTENT_BYTES_EXCEEDED")
    if request.max_final_bytes > request.max_scratch_bytes:
        raise ValueError("SCRATCH_BYTES_EXCEEDED")


def run_batch(request: NarrativeBatchRequest, *, project_root: Path, catalog_config_path: Path,
              db_path: Path, work_dir: Path) -> dict[str, Any]:
    """Run or resume this exact finite request; paid uncertainty stays reserved."""
    deadline = time.monotonic() + request.max_seconds
    project_root, catalog_config_path, db_path, work_dir = (
        path.resolve() for path in (project_root, catalog_config_path, db_path, work_dir))
    if not db_path.parent.is_dir():
        raise ValueError("AUTOMATION_DATABASE_PARENT_MISSING")
    _preflight_storage(request)
    _check_preparation_deadline(deadline)
    with os_file_mutex(db_path.with_name(db_path.name + ".batch-owner.lock"), timeout_seconds=0.2):
        _check_preparation_deadline(deadline)
        config = load_catalog_config(catalog_config_path, project_root=project_root)
        _check_preparation_deadline(deadline)
        catalog = SourceCatalog(config)
        try:
            return _run_owned(request, catalog, project_root, catalog_config_path, db_path, work_dir,
                              deadline=deadline)
        finally:
            catalog.close()


def _run_owned(request, catalog, project_root, config_path, db_path, work_dir, *, deadline):
    _check_preparation_deadline(deadline)
    reader = SourceVersionReader(catalog)
    binding = build_batch_events(request, reader, now=_now(), deadline=deadline)
    # Verify raw bytes before materializing anything, including a completed resume.
    for event in binding.events:
        _check_preparation_deadline(deadline)
        payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
        reader.open_version(source_ref(payload), purpose="narrative_derivation",
                            expected_read_policy_sha256=payload.expected_read_policy_sha256)
        _check_preparation_deadline(deadline)
    # This directory is dedicated to batch records/logs. It must not contain or
    # be an ancestor of raw/config/catalog/database paths being measured.
    protected = (project_root, catalog.config.catalog_dir, db_path, config_path) + tuple(root.path for root in catalog.config.roots)
    if any(path.resolve() == work_dir or work_dir in path.resolve().parents for path in protected):
        raise ValueError("BATCH_WORK_DIRECTORY_OVERLAPS_STORAGE")
    if work_dir.exists() and any(work_dir.iterdir()) and not (work_dir / "storage-baseline.json").exists():
        raise ValueError("BATCH_WORK_DIRECTORY_NOT_EMPTY")
    _check_preparation_deadline(deadline)
    work_dir.mkdir(parents=True, exist_ok=True)
    # Save the baseline before AUTO initialization/materialization grows files.
    guard = _storage_guard(request, catalog, db_path, work_dir, binding.input_hash)
    store = AutomationStore(db_path)
    runs = NarrativeRunStore(db_path)
    previous = runs.get_run(request.run_id)
    if previous is not None and previous.input_hash != binding.input_hash:
        raise RunConflictError("batch run input changed")
    gate = store.read_runtime_gate()
    if gate.desired_state is RuntimeState.ENABLED and previous is None:
        raise ValueError("AUTOMATION_RUNTIME_ALREADY_ENABLED")
    if previous is not None and store.has_running_jobs_outside_scope(previous.job_ids):
        raise ValueError("AUTOMATION_FOREIGN_WORKER_ACTIVE")
    status = "partial"
    generation = None
    supervisor = None
    try:
        if gate.desired_state is RuntimeState.ENABLED:
            # A surviving enabled gate can only be recovered by the run
            # durably recorded as its owner. Bind and fence it before AUTO
            # events/jobs can be written.
            with CatalogOperationLock(catalog.config.catalog_dir, operation="narrative-batch-start"):
                generation = runs.activate_run(
                    request.run_id, expected_generation=gate.control_generation, updated_at=_now(),
                ).control_generation

        scheduler = AutomationScheduler(store, create_default_registry(), PolicyConfig(allow_llm=True, allow_network=True))
        event_ids = {event.event_id for event in binding.events}
        for event in binding.events:
            stored = store.get_event(event.event_id)
            if stored is None:
                stored = store.put_event(event).value
            elif (stored.input_hash, stored.payload_json, stored.policy_version, stored.subject_id) != (
                    event.input_hash, event.payload_json, event.policy_version, event.subject_id):
                raise RunConflictError("batch event changed")
            scheduler.materialize_event(stored)
        job_ids = tuple(job.job_id for job in store.list_jobs(event_ids=tuple(event_ids)))
        run = runs.create_run(run_id=request.run_id, input_hash=binding.input_hash, job_ids=job_ids,
            model_id=request.model_options["model_id"], prompt_version=NARRATIVE_PROMPT_VERSION,
            pricing_version=request.pricing_version,
            input_micro_usd_per_million_tokens=request.input_micro_usd_per_million_tokens,
            output_micro_usd_per_million_tokens=request.output_micro_usd_per_million_tokens,
            max_tokens=request.max_tokens, max_micro_usd=request.max_micro_usd,
            max_output_bytes=min(len(request.sources) * request.max_final_bytes, request.max_persistent_bytes), created_at=_now())
        artifacts = NarrativeArtifactStore(catalog.store, _BudgetedObjects(catalog.config.catalog_dir, guard, request.max_final_bytes))
        dispatcher = NarrativeEffectDispatcher(store, artifacts, allowed_job_ids=run.job_ids)
        supervisor = AutomationSupervisor(SupervisorConfig(
            db_path=db_path, log_dir=work_dir / "logs", profile=request.profile,
            runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
            runtime_options_json=canonical_json({"project_root": str(project_root), "catalog_config_path": str(config_path),
                "run_id": run.run_id, "expected_run_input_hash": run.input_hash, "model": request.model_options,
                "max_final_bytes": request.max_final_bytes}),
            compute_job_types=("source.narrative_select", "source.narrative_verify"),
            model_job_types=("source.narrative_summarize",), allowed_job_ids=run.job_ids,
            heartbeat_interval_seconds=1, lease_seconds=15, idle_sleep_seconds=0.05,
            maintenance_interval_seconds=0.05, stop_grace_seconds=2, child_log_max_bytes=262144,
        ))
        if generation is None:
            with CatalogOperationLock(catalog.config.catalog_dir, operation="narrative-batch-start"):
                current = store.read_runtime_gate()
                generation = runs.activate_run(
                    request.run_id, expected_generation=current.control_generation, updated_at=_now(),
                ).control_generation
        terminal = {JobStatus.SUCCEEDED, JobStatus.DEAD_LETTER, JobStatus.BLOCKED_HUMAN, JobStatus.CANCELLED}
        current_jobs = store.list_jobs(job_ids=run.job_ids)
        if len(current_jobs) != len(run.job_ids):
            raise RunConflictError("batch run job disappeared")
        needs_workers = any(job.status not in terminal for job in current_jobs)
        if not run.blocked and needs_workers and time.monotonic() < deadline:
            supervisor.start()
        while time.monotonic() < deadline:
            current_gate = store.read_runtime_gate()
            if current_gate.desired_state is not RuntimeState.ENABLED or current_gate.control_generation != generation:
                status = "paused"
                break
            guard.check()
            if not run.blocked:
                supervisor.maintain()
                # Finished model attempts with no provider receipt may have
                # reached the provider. Reconcile their reserved bounds as
                # unknown without refunding them; repeat calls are idempotent.
                runs.settle_finished_attempt_reservations(run_id=run.run_id, settled_at=_now())
            # Do not prepare a file larger than the requested final byte cap.
            for effect_id in store.effect_ids_for_jobs(run.job_ids, effect_type=EFFECT_TYPE):
                effect = store.get_effect(effect_id)
                if effect.status.value in {"planned", "pending"}:
                    if len(canonical_json(store.result_for_effect(effect_id).to_dict()["result"]).encode("utf-8")) > request.max_final_bytes:
                        raise ValueError("FINAL_BYTES_EXCEEDED")
            now = _now()
            dispatcher.dispatch_next(worker_id="narrative-batch-projector", now=now,
                lease_until=(datetime.now(timezone.utc) + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                expected_generation=generation)
            dispatcher.reconcile_prepared(activated_at=now)
            jobs = store.list_jobs(job_ids=run.job_ids)
            if len(jobs) != len(run.job_ids):
                raise RunConflictError("batch run job disappeared")
            if all(job.status in terminal for job in jobs):
                status = "completed" if all(job.status is JobStatus.SUCCEEDED for job in jobs) else "failed"
                if any(job.last_error_code == "MODEL_BUDGET_DENIED" for job in jobs):
                    status = "budget_exhausted"
                break
            current_run = runs.get_run(run.run_id)
            if current_run is None:
                raise RunConflictError("batch run disappeared")
            if current_run.blocked:
                status = "budget_exhausted"
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        status = "paused"
    except ValueError as exc:
        if str(exc) not in {"PERSISTENT_BYTES_EXCEEDED", "SCRATCH_BYTES_EXCEEDED", "FINAL_BYTES_EXCEEDED"}:
            raise
        runs.block_run(run.run_id, error_code=str(exc), updated_at=_now())
        status = "storage_exhausted"
    finally:
        if supervisor is not None:
            supervisor.stop()
        if generation is not None:
            with CatalogOperationLock(catalog.config.catalog_dir, operation="narrative-batch-stop"):
                current = store.read_runtime_gate()
                if current.control_generation == generation:
                    store.set_runtime_gate(RuntimeState.PAUSED, updated_at=_now(), expected_generation=generation)
    documents = _final_documents(request, binding, store, runs, artifacts)
    if status == "completed" and any(document["status"] != "completed" for document in documents):
        status = "partial"
    budget = runs.budget_snapshot(run.run_id)
    storage = guard.snapshot()
    return {"schema_version": "narrative-batch-result/1", "run_id": run.run_id, "status": status,
        "documents": documents, "budget": {"tokens": budget.charged_tokens,
            "estimated_micro_usd": budget.charged_micro_usd, "unknown_reservations": budget.unknown_reservations,
            "unsettled_reservations": budget.unsettled_reservations},
        "storage": {"persistent_added_bytes": storage.persistent_added_bytes, "scratch_peak_bytes": storage.scratch_peak_bytes}}


def _final_documents(request, binding, store, runs, artifacts):
    documents = []
    all_jobs = store.list_jobs(event_ids=tuple(event.event_id for event in binding.events))
    for event in binding.events:
        ref = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json)).source_ref
        jobs = tuple(job for job in all_jobs if job.created_from_event_id == event.event_id)
        verify = next(job for job in jobs if job.job_type == "source.narrative_verify")
        effect_ids = store.effect_ids_for_jobs((verify.job_id,), effect_type=EFFECT_TYPE)
        artifact_ref = None
        document_status = verify.status.value
        if verify.status is JobStatus.SUCCEEDED and effect_ids:
            try:
                # Exact-by-effect metadata will also feed terminal compaction.
                version = artifacts.visible_version_for_effect(effect_ids[0])
                artifacts.read_exact(artifact_version_id=version.artifact_version_id, document_id=ref.document_id,
                    source_id=ref.source_id, source_sha256=ref.content_sha256,
                    expected_sha256=version.content_sha256, expected_size=version.byte_size)
                artifact_ref = {"artifact_version_id": version.artifact_version_id, "content_sha256": version.content_sha256,
                    "byte_size": version.byte_size, "document_id": ref.document_id, "source_id": ref.source_id,
                    "source_sha256": ref.content_sha256}
                document_status = "completed"
                summary = next(job for job in jobs if job.job_type == "source.narrative_summarize")
                for reservation in runs.reservations_for_run(request.run_id):
                    if reservation.job_id == summary.job_id and reservation.error_code is None:
                        runs.settle_output(run_id=request.run_id, attempt_id=reservation.attempt_id,
                            output_bytes=version.byte_size, output_sha256=version.content_sha256, settled_at=_now())
                compact_terminal_narrative_jobs(store, artifacts, job_ids=tuple(job.job_id for job in jobs),
                    final_artifact=FinalArtifactPin(version.effect_id, version.artifact_version_id,
                        version.content_sha256, version.byte_size, ref.document_id, ref.source_id, ref.content_sha256),
                    compacted_at=_now())
            except NarrativeArtifactNotVisibleError:
                document_status = "activation_pending"
        documents.append({"document_id": ref.document_id, "status": document_status, "artifact_ref": artifact_ref,
            "errors": [job.last_error_code for job in jobs if job.last_error_code]})
    return documents


__all__ = ["BatchEvents", "BatchStorageBudget", "StorageSnapshot", "build_batch_events", "run_batch"]
