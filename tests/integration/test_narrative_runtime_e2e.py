from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
from threading import Event as ThreadEvent, Thread
from datetime import datetime, timedelta, timezone
import time
from typing import Callable
import uuid

import pytest

from company_wiki.automation.models import (
    Event,
    HandlerOutcome,
    HandlerResult,
    JobStatus,
    RuntimeState,
    canonical_json,
    canonical_json_hash,
    make_effect_key,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeBundle,
    NarrativeSelectResult,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import (
    ModelRateLimitError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
)
from company_wiki.automation.narrative_runtime import (
    NarrativeRuntimeDependencies,
    register_narrative_handlers,
)
from company_wiki.automation.narrative_verify import EFFECT_TYPE, NarrativeVerifyHandler
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.narrative_projection import (
    NarrativeBundleReader,
    NarrativeEffectDispatcher,
)
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.supervisor import AutomationSupervisor, SupervisorConfig
from company_wiki.automation.worker import HandlerExecutor, Worker
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.lock import CatalogOperationLock
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactStore,
)
from company_wiki.source_catalog.narrative_evidence import (
    verify_pdf_evidence_spans_bytes,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.transcript_text_extract import (
    extract_transcript_material,
)
from support.narrative_model_fixture import ReplayNarrativeModel


T0 = "2026-09-28T22:00:00Z"
T1 = "2026-09-28T22:01:00Z"


def _ack_outbox_then_exit_process(
    db_path: str,
    outbox_id: str,
    lease_token: str,
    runtime_generation: int,
    verified_at: str,
    actual_after_hash: str,
) -> None:
    store = AutomationStore(Path(db_path))
    store.ack_outbox(
        outbox_id=outbox_id,
        lease_token=lease_token,
        runtime_generation=runtime_generation,
        verified_at=verified_at,
        actual_after_hash=actual_after_hash,
    )
    # Model the real crash window: durable AUTO ACK has committed; no process
    # remains to run the short catalog activation step.
    os._exit(0)


def _sha(value: bytes | str) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _pdf_bytes(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def _sidecar(
    data: bytes,
    *,
    title: str,
    document_kind: str,
    provider_document_id: str,
    language: str = "en",
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": document_kind,
        "fiscal_year": 2026,
        "period_end": "2026-06-30",
        "filing_date": "2026-08-01",
        "provider": "fixture",
        "provider_document_id": provider_document_id,
        "content_sha256": _sha(data),
        "source_url": f"https://fixtures.invalid/sources/{provider_document_id}",
        "source_title": title,
        "language": language,
        "retrieved_at": "2026-08-02T00:00:00Z",
        "collector_name": "narrative_runtime_fixture",
        "collector_version": "1.0.0",
    }
    if overrides:
        payload.update(overrides)
    payload["content_sha256"] = _sha(data)
    return payload


def _write_source(
    root: Path,
    *,
    name: str,
    data: bytes,
    title: str,
    document_kind: str,
    entity_name: str = "Acme",
    sidecar_overrides: dict[str, object] | None = None,
) -> Path:
    directory = root / entity_name
    if document_kind == "investor_call_transcript":
        directory = directory / "raw" / "investor_relations" / "transcripts"
    elif document_kind == "annual_report":
        directory = directory / "raw" / "financial_reports" / "annual"
    elif document_kind in {"prospectus", "equity_offering_prospectus"}:
        directory = directory / "raw" / "prospectus"
    else:
        directory = directory / "raw" / "investor_relations"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(data)
    path.with_name(path.name + ".source.json").write_text(
        json.dumps(
            _sidecar(
                data,
                title=title,
                document_kind=document_kind,
                provider_document_id=name,
                language=str((sidecar_overrides or {}).get("language", "en")),
                overrides=sidecar_overrides,
            ),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _new_catalog(run_root: Path, sources: list[dict[str, object]]) -> tuple[
    SourceCatalog,
    SourceVersionReader,
    dict[str, tuple[bytes, object]],
]:
    companies = run_root / "companies"
    by_sha: dict[str, bytes] = {}
    for source in sources:
        data = source["data"]
        assert isinstance(data, bytes)
        path = _write_source(
            companies,
            name=str(source["name"]),
            data=data,
            title=str(source["title"]),
            document_kind=str(source["document_kind"]),
            entity_name=str(source.get("entity_name", "Acme")),
            sidecar_overrides=(
                source.get("sidecar_overrides")
                if isinstance(source.get("sidecar_overrides"), dict)
                else None
            ),
        )
        by_sha[_sha(data)] = path.read_bytes()
    config = CatalogConfig(
        project_root=run_root,
        catalog_dir=run_root / "catalog",
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
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        reader = SourceVersionReader(catalog)
        result: dict[str, tuple[bytes, object]] = {}
        for digest, data in by_sha.items():
            row = catalog.reader.fetchone(
                """SELECT d.document_id, d.primary_source_id AS source_id
                     FROM documents d JOIN sources s ON s.source_id=d.primary_source_id
                    WHERE d.source_status='active' AND s.content_sha256=?""",
                (digest,),
            )
            assert row is not None
            ref = reader.query_ref(row["document_id"], row["source_id"], digest)
            result[digest] = (data, ref)
        return catalog, reader, result
    except BaseException:
        catalog.close()
        raise


def _event(
    reader: SourceVersionReader,
    ref,
    *,
    event_id: str,
) -> Event:
    metadata = reader.describe_version(ref)
    transcript = metadata["document_kind"] == "investor_call_transcript"
    expected_mime = "text/plain" if transcript else "application/pdf"
    assert ref.mime_type == expected_mime, (
        metadata.get("title"),
        metadata.get("document_kind"),
        ref.mime_type,
        expected_mime,
    )
    payload = {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": ref.schema_version,
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
        },
        "expected_read_policy_sha256": reader.read_policy_sha256(),
        "source_metadata": {
            "source_class": "transcript" if transcript else "filing",
            "title": metadata["title"],
            "document_kind": metadata["document_kind"],
            "language": metadata["language"],
        },
    }
    parsed = SourceRevisionEventPayload.from_dict(payload)
    return Event(
        event_id=event_id,
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id=ref.document_id,
        input_hash=parsed.input_hash,
        payload_json=canonical_json(payload),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )


class FixedClock:
    def __init__(self, value: str = T1) -> None:
        self.value = value

    def now(self) -> str:
        return self.value


class SequentialIDs:
    def __init__(self) -> None:
        self._value = 0

    def new_id(self) -> str:
        self._value += 1
        return f"runtime-e2e-{self._value:04d}"


class FailingModel:
    def __init__(self, error_factory: Callable[[], Exception]) -> None:
        self.calls: list[NarrativeModelRequest] = []
        self._error_factory = error_factory

    def generate(self, request: NarrativeModelRequest) -> NarrativeModelResponse:
        self.calls.append(request)
        raise self._error_factory()


class LostResponseOnceModel:
    """Simulate a provider accepting the first request before its reply is lost."""

    def __init__(self) -> None:
        self.calls: list[NarrativeModelRequest] = []
        self._delegate = ReplayNarrativeModel()

    def generate(self, request: NarrativeModelRequest) -> NarrativeModelResponse:
        self.calls.append(request)
        if len(self.calls) == 1:
            raise ModelTimeoutError("provider accepted request; response was lost")
        return self._delegate.generate(request)


def _wait_for_e7_condition(predicate: Callable[[], bool], *, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.03)
    raise AssertionError("E7 condition was not reached before the timeout")


def _e7_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _runtime(
    run_root: Path,
    reader: SourceVersionReader,
    model,
    *,
    clock: FixedClock | None = None,
) -> tuple[AutomationStore, AutomationScheduler, Worker]:
    state_dir = run_root / "automation"
    state_dir.mkdir()
    store = AutomationStore(state_dir / "automation.db")
    store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
    registry = create_default_registry()
    scheduler = AutomationScheduler(
        store,
        registry,
        PolicyConfig(allow_llm=True, allow_network=True),
    )
    executor = HandlerExecutor()
    register_narrative_handlers(
        executor,
        NarrativeRuntimeDependencies(
            reader=reader,
            model=model,
        ),
    )
    worker = Worker(
        store,
        registry,
        executor,
        clock=clock or FixedClock(),
        id_gen=SequentialIDs(),
        lease_seconds=60,
        worker_id="narrative-runtime-e2e",
        allowed_job_types=(
            "source.narrative_select",
            "source.narrative_summarize",
            "source.narrative_verify",
        ),
    )
    return store, scheduler, worker


def _drain(worker: Worker, scheduler: AutomationScheduler, limit: int = 32) -> int:
    processed = 0
    for _ in range(limit):
        scheduler.refresh_ready(now=T1)
        if not worker.process_one():
            break
        processed += 1
    return processed


def _attempt_result(store: AutomationStore, job_id: str) -> HandlerResult:
    attempts = store.list_attempts(job_id)
    assert attempts and attempts[-1].result_json is not None
    return HandlerResult.from_dict(json.loads(attempts[-1].result_json))


def _run_root(tmp_path: Path, name: str) -> tuple[Path, tuple[str, ...]]:
    baseline = tuple(sorted(path.name for path in tmp_path.iterdir()))
    root = tmp_path / name
    assert root.parent.resolve() == tmp_path.resolve()
    assert root.name.startswith("m3-e4-runtime-")
    root.mkdir()
    return root, baseline


def _cleanup(
    tmp_path: Path,
    run_root: Path,
    baseline: tuple[str, ...],
    catalog: SourceCatalog | None,
) -> None:
    if catalog is not None:
        catalog.close()
    if run_root.exists():
        assert run_root.resolve().parent == tmp_path.resolve()
        assert run_root.name.startswith("m3-e4-runtime-")
        shutil.rmtree(run_root)
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == baseline


def test_runtime_e2e_three_sources_are_idempotent_and_leave_only_pending_effects(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-success")
    catalog = None
    try:
        annual = _pdf_bytes(
            "Company launched a new product and expanded overseas capacity for customers."
        )
        low_value = _pdf_bytes("This policy describes meeting administration procedures.")
        transcript = (
            b"Full Conference Call Transcript\n"
            b"CEO: We launched a new product and expanded overseas capacity.\n"
            b"Questions & Answers\n"
            b"Analyst: Is commercial launch on schedule?\n"
        )
        sources = [
            {
                "name": "annual.pdf",
                "data": annual,
                "title": "ACME annual report",
                "document_kind": "annual_report",
            },
            {
                "name": "ir-policy.pdf",
                "data": low_value,
                "title": "投资者关系管理办法（2025年8月）.pdf",
                "document_kind": "ir_policy",
            },
            {
                "name": "call.txt",
                "data": transcript,
                "title": "ACME Q2 earnings call",
                "document_kind": "investor_call_transcript",
            },
        ]
        catalog, reader, indexed = _new_catalog(run_root, sources)
        raw_hashes = {digest: _sha(data) for digest, (data, _ref) in indexed.items()}
        artifacts_before = catalog.reader.fetchone("SELECT COUNT(*) AS count FROM artifacts")
        assert artifacts_before is not None
        model = ReplayNarrativeModel()
        store, scheduler, worker = _runtime(run_root, reader, model)
        events = [
            _event(
                reader,
                ref,
                event_id=f"event-runtime-{index}",
            )
            for index, (_data, ref) in enumerate(indexed.values(), start=1)
        ]
        for event in events:
            store.put_event(event)
            created = scheduler.materialize_event(event)
            assert (created.jobs_created, created.dependencies_created) == (3, 3)

        processed = _drain(worker, scheduler)
        assert processed == 9, [
            (job.job_type, job.status.value, job.last_error_code, job.last_error_detail)
            for job in store.list_jobs()
        ]
        assert len(model.calls) == 2
        jobs = store.list_jobs()
        assert sum(job.status is JobStatus.SUCCEEDED for job in jobs) == 6
        assert sum(job.status is JobStatus.VERIFYING for job in jobs) == 3
        verify_jobs = [job for job in jobs if job.job_type == "source.narrative_verify"]
        bundles = []
        for job in verify_jobs:
            result = _attempt_result(store, job.job_id)
            assert result.outcome is HandlerOutcome.SUCCEEDED
            bundles.append(NarrativeBundle.from_dict(result.result))
            assert len(store.list_effects(job.job_id)) == 1
        assert {bundle.quality_status for bundle in bundles} == {
            "verified",
            "skipped_no_narrative",
        }
        assert len(store.list_outbox_entries(status="pending")) == 3
        for event in events:
            replayed = scheduler.materialize_event(event)
            assert (replayed.jobs_created, replayed.dependencies_created) == (0, 0)
            assert (replayed.jobs_existing, replayed.dependencies_existing) == (3, 3)
        assert _drain(worker, scheduler) == 0
        assert len(store.list_outbox_entries(status="pending")) == 3
        artifacts_after = catalog.reader.fetchone("SELECT COUNT(*) AS count FROM artifacts")
        assert artifacts_after == artifacts_before
        assert {
            digest: _sha(data) for digest, (data, _ref) in indexed.items()
        } == raw_hashes
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


def test_runtime_e2e_dispatches_and_recovers_pathless_bundle_versions(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-publish")
    catalog = None
    try:
        annual = _pdf_bytes(
            "Company launched a new product and expanded overseas capacity for customers."
        )
        transcript = (
            b"Full Conference Call Transcript\n"
            b"CEO: We launched a new product and expanded overseas capacity.\n"
            b"Questions & Answers\n"
        )
        sources = [
            {
                "name": "annual.pdf",
                "data": annual,
                "title": "ACME annual report",
                "document_kind": "annual_report",
            },
            {
                "name": "call.txt",
                "data": transcript,
                "title": "ACME Q2 earnings call",
                "document_kind": "investor_call_transcript",
            },
        ]
        catalog, source_reader, indexed = _new_catalog(run_root, sources)
        raw_hashes_before = {
            digest: _sha(data) for digest, (data, _ref) in indexed.items()
        }
        store, scheduler, worker = _runtime(
            run_root, source_reader, ReplayNarrativeModel()
        )
        events = [
            _event(source_reader, ref, event_id=f"event-publish-{index}")
            for index, (_data, ref) in enumerate(indexed.values(), start=1)
        ]
        for event in events:
            store.put_event(event)
            scheduler.materialize_event(event)
        assert _drain(worker, scheduler) == 6

        artifacts = NarrativeArtifactStore(
            catalog.store,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(store, artifacts)
        generation = store.read_runtime_gate().control_generation

        ack_finished = ThreadEvent()
        allow_activation = ThreadEvent()
        order: list[str] = []
        original_ack = store.ack_outbox
        original_activate = artifacts.activate

        def ack_then_hold(**kwargs):
            result = original_ack(**kwargs)
            ack_finished.set()
            if not allow_activation.wait(timeout=10):
                raise AssertionError("test did not release activation")
            return result

        def activate_then_record(effect_id: str, **kwargs):
            result = original_activate(effect_id, **kwargs)
            order.append("visible")
            return result

        store.ack_outbox = ack_then_hold
        artifacts.activate = activate_then_record
        dispatched = []
        dispatch_thread = Thread(
            target=lambda: dispatched.append(
                dispatcher.dispatch_next(
                    worker_id="narrative-projector-e2e",
                    now="2026-09-28T22:02:00Z",
                    lease_until="2026-09-28T22:03:00Z",
                    expected_generation=generation,
                )
            )
        )
        dispatch_thread.start()
        try:
            assert ack_finished.wait(timeout=10)
            with CatalogOperationLock(
                catalog.config.catalog_dir,
                operation="test-pause-after-ack-before-activation",
            ):
                store.set_runtime_gate(
                    RuntimeState.PAUSED, updated_at="2026-09-28T22:02:20Z"
                )
                order.append("paused")
            allow_activation.set()
            dispatch_thread.join(timeout=10)
        finally:
            allow_activation.set()
            dispatch_thread.join(timeout=10)
            store.ack_outbox = original_ack
            artifacts.activate = original_activate

        assert not dispatch_thread.is_alive()
        assert dispatched and dispatched[0].status == "activation_pending"
        assert order == ["paused"]
        first = dispatched[0]
        first_effect = store.get_effect(first.effect_id)
        assert first_effect is not None
        assert first_effect.status.value == "verified"
        assert dispatcher.reconcile_prepared(
            activated_at="2026-09-28T22:02:25Z"
        ) == ()
        store.set_runtime_gate(
            RuntimeState.ENABLED, updated_at="2026-09-28T22:02:30Z"
        )
        generation = store.read_runtime_gate().control_generation
        assert dispatcher.reconcile_prepared(
            activated_at="2026-09-28T22:02:35Z"
        ) == (first.effect_id,)

        # Reconstruct the durable crash point: catalog prepared and AUTO ACKed,
        # process exits before the short catalog activation transaction.
        second_lease = store.claim_next_outbox(
            worker_id="narrative-projector-recovery",
            lease_token="recovery-lease",
            now="2026-09-28T22:02:00Z",
            lease_until="2026-09-28T22:03:00Z",
            expected_generation=generation,
            allowed_effect_types=(EFFECT_TYPE,),
        )
        assert second_lease is not None
        second_effect = store.get_effect(second_lease.effect_id)
        assert second_effect is not None
        result = store.result_for_effect(second_effect.effect_id)
        bundle = NarrativeBundle.from_dict(dict(result.result))
        bundle_bytes = canonical_json(bundle.to_dict()).encode("utf-8")
        artifacts.prepare(dispatcher._draft(second_effect, bundle), bundle_bytes)
        store.ack_outbox(
            outbox_id=second_lease.outbox_id,
            lease_token=second_lease.lease_token,
            runtime_generation=generation,
            verified_at="2026-09-28T22:02:30Z",
            actual_after_hash=canonical_json_hash(bundle.to_dict()),
        )
        prepared = artifacts.prepared_effects()
        assert [version.effect_id for version in prepared] == [
            second_effect.effect_id
        ]

        recovered = dispatcher.reconcile_prepared(
            activated_at="2026-09-28T22:02:40Z"
        )
        assert recovered == (second_effect.effect_id,)
        assert store.get_job(second_effect.job_id).status is JobStatus.SUCCEEDED

        pathless_reader = NarrativeBundleReader(artifacts)
        all_versions = []
        for effect in (first_effect, second_effect):
            result = store.result_for_effect(effect.effect_id)
            expected = NarrativeBundle.from_dict(dict(result.result))
            loaded = pathless_reader.read(
                document_id=expected.source_ref.document_id,
                source_id=expected.source_ref.source_id,
                source_sha256=expected.source_ref.content_sha256,
            )
            assert loaded.bundle.to_dict() == expected.to_dict()
            assert loaded.artifact.object_key.startswith("objects/sha256/")
            assert not hasattr(loaded, "path")
            all_versions.append(loaded)
        assert {
            item.bundle.source_metadata.document_kind for item in all_versions
        } == {"annual_report", "investor_call_transcript"}
        assert {
            digest: _sha(data) for digest, (data, _ref) in indexed.items()
        } == raw_hashes_before
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


def test_prepared_legacy_publication_recovers_without_rebinding_its_work_key(
    tmp_path: Path, monkeypatch,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-legacy-prepared")
    catalog = None
    try:
        sources = [{"name": "annual.pdf", "data": _pdf_bytes(
            "Acme launched a new product and expanded overseas sales in 2026."),
            "title": "ACME annual report", "document_kind": "annual_report"}]
        catalog, reader, indexed = _new_catalog(run_root, sources)
        originals = {path: path.read_bytes() for path in (run_root / "companies").rglob("*") if path.is_file()}
        store, scheduler, worker = _runtime(run_root, reader, ReplayNarrativeModel())
        _data, ref = next(iter(indexed.values()))
        event = _event(reader, ref, event_id="legacy-effect-before-upgrade")
        store.put_event(event)
        scheduler.materialize_event(event)
        current_effect = NarrativeVerifyHandler._effect

        def legacy_effect(context, bundle):
            effect = current_effect(context, bundle)
            key = make_effect_key(effect.effect_type, effect.target,
                                  canonical_json_hash(bundle.to_dict()), bundle.versions.bundle_producer)
            return replace(effect, effect_id="eff-" + key[:32], effect_key=key)

        # Simulate the previous producer finishing its work before an upgrade.
        with monkeypatch.context() as old_producer:
            old_producer.setattr(NarrativeVerifyHandler, "_effect", staticmethod(legacy_effect))
            assert _drain(worker, scheduler) == 3
        artifacts = NarrativeArtifactStore(catalog.store, LocalNarrativeObjectStore(catalog.config.catalog_dir))
        dispatcher = NarrativeEffectDispatcher(store, artifacts)
        effect_id = store.list_outbox_entries(status="pending")[0]["effect_id"]
        effect, bundle, payload = dispatcher._prepare_effect(effect_id)
        legacy_work_key = canonical_json_hash({
            "schema_version": "narrative-work-key/1.0", "document_id": ref.document_id,
            "source_id": ref.source_id, "source_sha256": ref.content_sha256,
            "artifact_role": "narrative_bundle", "producer_name": "company_wiki.narrative_bundle",
            "producer_version": bundle.versions.bundle_producer,
            "policy_sha256": bundle.expected_read_policy_sha256,
        })
        prepared = artifacts.prepare(replace(dispatcher._draft(effect, bundle), work_key=legacy_work_key), payload)
        assert prepared.status == "prepared"
        recovered = dispatcher.dispatch_next(
            worker_id="new-projector-after-upgrade", now=T1,
            lease_until="2026-09-28T22:05:00Z",
            expected_generation=store.read_runtime_gate().control_generation,
        )
        assert recovered.status == "visible" and recovered.artifact_version_id == prepared.artifact_version_id
        version, content = artifacts.read_exact(
            artifact_version_id=prepared.artifact_version_id, document_id=ref.document_id,
            source_id=ref.source_id, source_sha256=ref.content_sha256,
            expected_sha256=prepared.content_sha256, expected_size=prepared.byte_size,
        )
        assert version.work_key == legacy_work_key and content == payload
        assert store.list_outbox_entries(status="pending") == ()
        assert all(path.read_bytes() == data for path, data in originals.items())
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


@pytest.mark.parametrize("crash_round", [1, 2, 3])
def test_e7_r07_acknowledged_projection_recovers_after_projector_process_exit(
    tmp_path: Path, crash_round: int
) -> None:
    run_root, baseline = _run_root(
        tmp_path, f"m3-e4-runtime-e7-r07-process-crash-{crash_round}"
    )
    catalog = None
    child = None
    try:
        source_bytes = _pdf_bytes(
            "Acme launched a new product and expanded overseas sales in 2026."
        )
        sources = [
            {
                "name": "annual.pdf",
                "data": source_bytes,
                "title": "ACME annual report 2026",
                "document_kind": "annual_report",
            }
        ]
        catalog, reader, indexed = _new_catalog(run_root, sources)
        raw_hashes_before = {
            path: _sha(path.read_bytes())
            for path in (run_root / "companies").rglob("*")
            if path.is_file()
        }
        store, scheduler, worker = _runtime(
            run_root, reader, ReplayNarrativeModel()
        )
        _data, ref = next(iter(indexed.values()))
        event = _event(
            reader,
            ref,
            event_id=f"event-e7-r07-process-{crash_round}",
        )
        store.put_event(event)
        created = scheduler.materialize_event(event)
        assert (created.jobs_created, created.dependencies_created) == (3, 3)
        assert _drain(worker, scheduler) == 3
        assert len(store.list_outbox_entries(status="pending")) == 1

        artifacts = NarrativeArtifactStore(
            catalog.store,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(store, artifacts)
        generation = store.read_runtime_gate().control_generation
        lease = store.claim_next_outbox(
            worker_id=f"e7-r07-crash-projector-{crash_round}",
            lease_token=f"e7-r07-crash-lease-{crash_round}",
            now="2026-09-28T22:03:00Z",
            lease_until="2026-09-28T22:04:00Z",
            expected_generation=generation,
            allowed_effect_types=(EFFECT_TYPE,),
        )
        assert lease is not None
        effect, bundle, payload = dispatcher._prepare_effect(lease.effect_id)
        prepared = artifacts.prepare(dispatcher._draft(effect, bundle), payload)
        assert prepared.status == "prepared"

        context = multiprocessing.get_context("spawn")
        child = context.Process(
            target=_ack_outbox_then_exit_process,
            args=(
                str(store.db_path),
                lease.outbox_id,
                lease.lease_token,
                lease.runtime_generation,
                "2026-09-28T22:03:05Z",
                prepared.content_sha256,
            ),
        )
        child.start()
        child.join(timeout=20)
        assert not child.is_alive()
        assert child.exitcode == 0
        child = None

        recovered_effect = store.get_effect(effect.effect_id)
        assert recovered_effect is not None
        assert recovered_effect.status.value == "verified"
        assert store.list_outbox_entries(status="pending") == ()
        assert dispatcher.reconcile_prepared(
            activated_at="2026-09-28T22:03:10Z"
        ) == (effect.effect_id,)

        loaded = NarrativeBundleReader(artifacts).read(
            document_id=ref.document_id,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
        )
        assert loaded.bundle.to_dict() == bundle.to_dict()
        visible = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count, COUNT(DISTINCT work_key) AS work_keys "
            "FROM narrative_artifact_versions WHERE status='visible'"
        )
        assert visible is not None
        assert (int(visible["count"]), int(visible["work_keys"])) == (1, 1)
        assert {
            path: _sha(path.read_bytes())
            for path in raw_hashes_before
        } == raw_hashes_before
    finally:
        if child is not None and child.is_alive():
            child.terminate()
            child.join(timeout=5)
        _cleanup(tmp_path, run_root, baseline, catalog)


def test_e7_r08_catalog_lock_keeps_acknowledged_bundle_recoverable(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-e7-r08-catalog-lock")
    catalog = None
    try:
        source_bytes = _pdf_bytes(
            "Acme launched a new business line and expanded overseas sales in 2026."
        )
        catalog, reader, indexed = _new_catalog(
            run_root,
            [
                {
                    "name": "annual.pdf",
                    "data": source_bytes,
                    "title": "ACME annual report 2026",
                    "document_kind": "annual_report",
                }
            ],
        )
        raw_hashes_before = {
            path: _sha(path.read_bytes())
            for path in (run_root / "companies").rglob("*")
            if path.is_file()
        }
        store, scheduler, worker = _runtime(
            run_root, reader, ReplayNarrativeModel()
        )
        _data, ref = next(iter(indexed.values()))
        event = _event(reader, ref, event_id="event-e7-r08-catalog-lock")
        store.put_event(event)
        created = scheduler.materialize_event(event)
        assert (created.jobs_created, created.dependencies_created) == (3, 3)
        assert _drain(worker, scheduler) == 3
        assert len(store.list_outbox_entries(status="pending")) == 1

        artifacts = NarrativeArtifactStore(
            catalog.store,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(store, artifacts)
        generation = store.read_runtime_gate().control_generation
        with CatalogOperationLock(
            catalog.config.catalog_dir,
            operation="test-e7-r08-held-catalog-lock",
        ):
            receipt = dispatcher.dispatch_next(
                worker_id="e7-r08-catalog-projector",
                now="2026-09-28T22:02:00Z",
                lease_until="2026-09-28T22:03:00Z",
                expected_generation=generation,
            )
            assert receipt.status == "activation_pending"
            assert receipt.effect_id is not None
            effect = store.get_effect(receipt.effect_id)
            assert effect is not None
            assert effect.status.value == "verified"
            assert store.list_outbox_entries(status="pending") == ()
            prepared = artifacts.prepared_effects()
            assert [item.effect_id for item in prepared] == [receipt.effect_id]
            visible = catalog.reader.fetchone(
                "SELECT COUNT(*) AS count FROM narrative_artifact_versions "
                "WHERE status='visible'"
            )
            assert visible is not None
            assert int(visible["count"]) == 0

        assert not (catalog.config.catalog_dir / "operation.lock").exists()
        assert dispatcher.reconcile_prepared(
            activated_at="2026-09-28T22:03:00Z"
        ) == (receipt.effect_id,)
        loaded = NarrativeBundleReader(artifacts).read(
            document_id=ref.document_id,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
        )
        assert loaded.bundle.source_ref.content_sha256 == ref.content_sha256
        visible_after = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count, COUNT(DISTINCT work_key) AS work_keys "
            "FROM narrative_artifact_versions WHERE status='visible'"
        )
        assert visible_after is not None
        assert (int(visible_after["count"]), int(visible_after["work_keys"])) == (
            1,
            1,
        )
        assert {
            path: _sha(path.read_bytes()) for path in raw_hashes_before
        } == raw_hashes_before
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


@pytest.mark.parametrize(
    ("error_factory", "expected_code"),
    [
        (lambda: ModelRateLimitError("429"), "MODEL_RATE_LIMIT"),
        (lambda: ModelTimeoutError("timeout"), "MODEL_TIMEOUT"),
    ],
)
def test_runtime_e2e_model_transient_stops_before_verify_effect(
    tmp_path: Path,
    error_factory: Callable[[], Exception],
    expected_code: str,
) -> None:
    run_root, baseline = _run_root(tmp_path, f"m3-e4-runtime-{expected_code.lower()}")
    catalog = None
    try:
        data = _pdf_bytes("Company launched a new product for overseas customers.")
        catalog, reader, indexed = _new_catalog(
            run_root,
            [
                {
                    "name": "annual.pdf",
                    "data": data,
                    "title": "ACME annual report",
                    "document_kind": "annual_report",
                }
            ],
        )
        model = FailingModel(error_factory)
        store, scheduler, worker = _runtime(run_root, reader, model)
        ref = next(iter(indexed.values()))[1]
        event = _event(reader, ref, event_id="event-transient")
        store.put_event(event)
        scheduler.materialize_event(event)

        assert _drain(worker, scheduler) == 2
        jobs = {job.job_type: job for job in store.list_jobs()}
        assert jobs["source.narrative_select"].status is JobStatus.SUCCEEDED
        assert jobs["source.narrative_summarize"].status is JobStatus.RETRY_WAIT
        assert jobs["source.narrative_summarize"].last_error_code == expected_code
        assert jobs["source.narrative_verify"].status is JobStatus.PLANNED
        assert len(model.calls) == 1
        assert store.list_outbox_entries() == ()
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


def test_runtime_e2e_read_identity_fails_automatically_and_transcript_needs_no_receipt(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-auto-checks")
    catalog = None
    try:
        annual = _pdf_bytes("Company launched a new product for overseas customers.")
        transcript = (
            b"Full Conference Call Transcript\n"
            b"CEO: We launched a new product and expanded overseas capacity.\n"
        )
        catalog, reader, indexed = _new_catalog(
            run_root,
            [
                {
                    "name": "annual.pdf",
                    "data": annual,
                    "title": "ACME annual report",
                    "document_kind": "annual_report",
                },
                {
                    "name": "call.txt",
                    "data": transcript,
                    "title": "ACME earnings call",
                    "document_kind": "investor_call_transcript",
                },
            ],
        )
        model = ReplayNarrativeModel()
        store, scheduler, worker = _runtime(run_root, reader, model)
        refs = {data: ref for data, ref in indexed.values()}
        refused = _event(
            reader,
            refs[annual],
            event_id="event-read-policy-mismatch",
        )
        refused_payload = json.loads(refused.payload_json)
        refused_payload["expected_read_policy_sha256"] = _sha("wrong-read-policy")
        refused_parsed = SourceRevisionEventPayload.from_dict(refused_payload)
        refused = Event(
            **{
                **refused.to_dict(),
                "input_hash": refused_parsed.input_hash,
                "payload_json": canonical_json(refused_payload),
            }
        )
        transcript_event = _event(
            reader,
            refs[transcript],
            event_id="event-transcript-no-review",
        )
        for event in (refused, transcript_event):
            store.put_event(event)
            scheduler.materialize_event(event)

        processed = _drain(worker, scheduler)
        assert processed == 4, [
            (job.job_type, job.status.value, job.last_error_code, job.last_error_detail)
            for job in store.list_jobs()
        ]
        jobs = store.list_jobs()
        refused_select = next(
            job
            for job in jobs
            if job.created_from_event_id == refused.event_id
            and job.job_type == "source.narrative_select"
        )
        transcript_verify = next(
            job
            for job in jobs
            if job.created_from_event_id == transcript_event.event_id
            and job.job_type == "source.narrative_verify"
        )
        assert refused_select.status is JobStatus.DEAD_LETTER
        assert refused_select.last_error_code == "POLICY_DENIED"
        assert transcript_verify.status is JobStatus.VERIFYING
        assert store.list_outbox_entries(status="pending")
        assert len(model.calls) == 1
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


_E6_REAL_SAMPLES = (
    {
        "sample_id": "P01",
        "relative_path": "中微公司/raw/financial_reports/中微公司：2025年年度报告.pdf",
        "name": "中微公司：2025年年度报告.pdf",
        "entity_name": "中微公司",
        "title": "中微公司：2025年年度报告.pdf",
        "document_kind": "annual_report",
        "language": "zh",
        "sha256": "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
        "sidecar_overrides": {
            "canonical_entity_id": "e6-entity-zhongwei",
            "display_name": "中微公司",
            "market": "CN",
            "security_id": "688012.SH",
        },
    },
    {
        "sample_id": "P04",
        "relative_path": "中微公司/raw/prospectus/中微公司：首次公开发行股票并在科创板上市招股说明书.pdf",
        "name": "中微公司：首次公开发行股票并在科创板上市招股说明书.pdf",
        "entity_name": "中微公司",
        "title": "中微公司：首次公开发行股票并在科创板上市招股说明书.pdf",
        "document_kind": "prospectus",
        "language": "zh",
        "sha256": "19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67",
        "sidecar_overrides": {
            "canonical_entity_id": "e6-entity-zhongwei",
            "display_name": "中微公司",
            "market": "CN",
            "security_id": "688012.SH",
        },
    },
    {
        "sample_id": "P07",
        "relative_path": "万润股份/raw/research/万润股份：投资者关系活动记录表20260515.pdf",
        "name": "万润股份：投资者关系活动记录表20260515.pdf",
        "entity_name": "万润股份",
        "title": "万润股份：投资者关系活动记录表20260515.pdf",
        "document_kind": "investor_relations",
        "language": "zh",
        "sha256": "221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7",
        "sidecar_overrides": {
            "canonical_entity_id": "e6-entity-wanrun",
            "display_name": "万润股份",
            "market": "CN",
            "security_id": "002643.SZ",
        },
    },
    {
        "sample_id": "T01",
        "relative_path": "MSFT/MSFT_Q4_2026_earnings_call.txt",
        "name": "MSFT_Q4_2026_earnings_call.txt",
        "entity_name": "MSFT",
        "title": "Microsoft Q4 2026 earnings call transcript",
        "document_kind": "investor_call_transcript",
        "language": "en",
        "sha256": "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a",
        "sidecar_overrides": {
            "canonical_entity_id": "e6-entity-msft",
            "display_name": "Microsoft",
            "market": "US",
            "security_id": "MSFT",
        },
    },
)


def _e6_project_root() -> Path:
    configured_root = os.environ.get("COMPANY_WIKI_E6_PROJECT_ROOT")
    return (
        Path(configured_root).resolve()
        if configured_root
        else Path(__file__).resolve().parents[2]
    )


def _e6_source_paths() -> tuple[Path, dict[str, Path]]:
    project_root = _e6_project_root()
    companies_root = Path(
        os.environ.get(
            "COMPANY_WIKI_E6_COMPANIES_ROOT", str(project_root / "companies")
        )
    )
    transcripts_root = Path(
        os.environ.get(
            "EARNINGS_TRANSCRIPTS_E6_ROOT",
            str(
                project_root.parent
                / "earnings-transcripts"
                / "earnings-transcripts"
                / "transcripts"
            ),
        )
    )
    paths = {
        sample["sample_id"]: (
            transcripts_root / str(sample["relative_path"])
            if sample["sample_id"] == "T01"
            else companies_root / str(sample["relative_path"])
        )
        for sample in _E6_REAL_SAMPLES
    }
    return companies_root, paths


def _e6_production_fingerprint() -> dict[str, tuple[object, ...] | None]:
    project_root = _e6_project_root()
    catalog_dir = project_root / ".source_catalog"
    paths = (
        catalog_dir / "catalog.sqlite3",
        catalog_dir / "runtime_policy.json",
        catalog_dir / "worker_control.json",
        project_root / "config" / "source_catalog.yaml",
        project_root / "config" / "source_catalog_worker.yaml",
    )
    result: dict[str, tuple[object, ...] | None] = {}
    for path in paths:
        if not path.is_file():
            result[str(path)] = None
            continue
        stat = path.stat()
        if path.name == "catalog.sqlite3":
            # The production catalog is multi-gigabyte. Its immutable file
            # identity is checked with metadata; the E6 runtime never opens it.
            result[str(path)] = (stat.st_size, stat.st_mtime_ns)
        else:
            result[str(path)] = (stat.st_size, _sha(path.read_bytes()))
    return result


def _wait_for_e6_verification_jobs(
    supervisor: AutomationSupervisor,
    store: AutomationStore,
    job_ids: tuple[str, ...],
    *,
    timeout_seconds: float = 300.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    expected_verifying = sum(
        1
        for job_id in job_ids
        if (job := store.get_job(job_id)) is not None
        and job.job_type == "source.narrative_verify"
    )
    while time.monotonic() < deadline:
        supervisor.maintain()
        jobs = tuple(store.get_job(job_id) for job_id in job_ids)
        if all(job is not None for job in jobs):
            statuses = tuple(job.status for job in jobs if job is not None)
            if any(
                status
                in {
                    JobStatus.DEAD_LETTER,
                    JobStatus.BLOCKED_HUMAN,
                    JobStatus.CANCELLED,
                }
                for status in statuses
            ):
                raise AssertionError(
                    "E6 worker reached an unexpected terminal status: "
                    f"{[(job.job_type, job.status.value, job.last_error_code, job.last_error_detail) for job in jobs if job]}"
                )
            ready = all(
                status in {JobStatus.SUCCEEDED, JobStatus.VERIFYING}
                for status in statuses
            )
            verifying = sum(status is JobStatus.VERIFYING for status in statuses)
            if ready and verifying == expected_verifying:
                return
        time.sleep(0.05)
    raise TimeoutError("E6 verify jobs did not reach the outbox boundary")


def _e6_process_rss_bytes(pid: int) -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        open_process = kernel.OpenProcess
        open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        open_process.restype = ctypes.c_void_p
        close_handle = kernel.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_memory = psapi.GetProcessMemoryInfo
        get_memory.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        )
        get_memory.restype = wintypes.BOOL
        handle = open_process(0x0400 | 0x0010, False, pid)
        if not handle:
            return 0
        try:
            return (
                int(counters.WorkingSetSize)
                if get_memory(handle, ctypes.byref(counters), counters.cb)
                else 0
            )
        finally:
            close_handle(handle)

    status = Path(os.sep) / "proc" / str(pid) / "status"
    if not status.is_file():
        return 0
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return 0


def _e6_sample_supervisor_rss(
    supervisor: AutomationSupervisor,
    stop: ThreadEvent,
    peak_values: list[int],
) -> None:
    peak = 0
    while not stop.is_set():
        pids = {os.getpid()}
        pids.update(
            child.pid
            for child in supervisor.children()
            if child.alive and child.pid is not None
        )
        peak = max(peak, sum(_e6_process_rss_bytes(pid) for pid in pids))
        stop.wait(0.05)
    peak_values.append(peak)


def _e6_percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _e6_max_concurrency(intervals: list[tuple[int, int]]) -> int:
    events = sorted(
        [(start, 1) for start, _end in intervals]
        + [(end, -1) for _start, end in intervals],
        key=lambda event: (event[0], event[1]),
    )
    active = 0
    maximum = 0
    for _time_ns, delta in events:
        active += delta
        maximum = max(maximum, active)
    return maximum


def _e6_run_profile(
    run_root: Path,
    *,
    profile: str,
    copied_samples: dict[str, tuple[dict[str, object], bytes, Path]],
) -> dict[str, object]:
    profile_started = time.perf_counter()
    profile_root = run_root / profile
    sources: list[dict[str, object]] = []
    source_by_digest: dict[str, dict[str, object]] = {}
    for sample_id, (sample, data, _copied_path) in copied_samples.items():
        source = {
            "name": sample["name"],
            "data": data,
            "title": sample["title"],
            "document_kind": sample["document_kind"],
            "entity_name": sample["entity_name"],
            "language": sample["language"],
            "sidecar_overrides": {
                **sample["sidecar_overrides"],
                "language": sample["language"],
            },
            "sample_id": sample_id,
        }
        sources.append(source)
        source_by_digest[_sha(data)] = source

    policy = _pdf_bytes(
        "This policy describes investor meeting administration and record retention."
    )
    skip_source = {
        "name": "投资者关系管理办法（2025年8月）.pdf",
        "data": policy,
        "title": "投资者关系管理办法（2025年8月）.pdf",
        "document_kind": "ir_policy",
        "entity_name": "中微公司",
        "sidecar_overrides": {
            "canonical_entity_id": "e6-entity-zhongwei",
            "display_name": "中微公司",
            "market": "CN",
            "security_id": "688012.SH",
            "language": "zh",
        },
        "language": "zh",
        "sample_id": "SKIP",
    }
    sources.append(skip_source)
    source_by_digest[_sha(policy)] = skip_source

    catalog: SourceCatalog | None = None
    try:
        catalog, reader, indexed = _new_catalog(profile_root, sources)
        initial_artifacts = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count FROM artifacts"
        )
        assert initial_artifacts is not None
        initial_artifact_count = int(initial_artifacts["count"])

        automation_root = profile_root / "automation"
        automation_root.mkdir(parents=True)
        store = AutomationStore(automation_root / "automation.db")
        store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
        scheduler = AutomationScheduler(
            store,
            create_default_registry(),
            # The production handler declares network capability. The E6
            # fixture injects a deterministic local replay model and no
            # network client, but the policy must still admit that handler.
            PolicyConfig(allow_llm=True, allow_network=True),
        )
        events = []
        source_by_document: dict[str, dict[str, object]] = {}
        for index, (digest, (_data, ref)) in enumerate(indexed.items(), start=1):
            source = source_by_digest[digest]
            event = _event(reader, ref, event_id=f"event-e6-{profile}-{index}")
            events.append(event)
            source_by_document[ref.document_id] = source
            store.put_event(event)
            created = scheduler.materialize_event(event)
            assert (created.jobs_created, created.dependencies_created) == (3, 3)

        jobs = store.list_jobs()
        assert len(jobs) == 15
        job_ids = tuple(job.job_id for job in jobs)
        queued_at_ns = {job_id: time.monotonic_ns() for job_id in job_ids}
        config = SupervisorConfig(
            db_path=automation_root / "automation.db",
            log_dir=profile_root / "process-logs",
            profile=profile,
            runtime_factory_path=(
                "support.narrative_runtime_worker_fixture:create_runtime"
            ),
            runtime_options_json=json.dumps(
                {
                    "project_root": str(profile_root),
                    "trace_dir": str(profile_root / "trace"),
                    "model_delay_seconds": 0.8,
                },
                sort_keys=True,
            ),
            compute_job_types=(
                "source.narrative_select",
                "source.narrative_verify",
            ),
            model_job_types=("source.narrative_summarize",),
            lease_seconds=30.0,
            heartbeat_interval_seconds=1.0,
            idle_sleep_seconds=0.03,
            maintenance_interval_seconds=0.05,
            stop_grace_seconds=2.0,
            child_log_max_bytes=65_536,
        )

        supervisor = AutomationSupervisor(config)
        stop_sampling = ThreadEvent()
        peak_rss_values: list[int] = []
        sampler = Thread(
            target=_e6_sample_supervisor_rss,
            args=(supervisor, stop_sampling, peak_rss_values),
            daemon=True,
        )
        try:
            supervisor.start()
            sampler.start()
            parent_job_ids = tuple(
                job.job_id
                for job in jobs
                if job.job_type != "source.narrative_verify"
            )
            supervisor.wait_for_terminal(parent_job_ids, timeout_seconds=300.0)
            _wait_for_e6_verification_jobs(
                supervisor, store, job_ids, timeout_seconds=120.0
            )
        finally:
            supervisor.stop()
            stop_sampling.set()
            if sampler.ident is not None:
                sampler.join(timeout=3)

        current_jobs = store.list_jobs()
        assert len(current_jobs) == 15
        assert sum(job.status is JobStatus.VERIFYING for job in current_jobs) == 5
        assert sum(job.status is JobStatus.SUCCEEDED for job in current_jobs) == 10
        assert len(store.list_outbox_entries(status="pending")) == 5

        trace_dir = profile_root / "trace"
        claimed = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in trace_dir.glob("claimed--*.json")
        ]
        before_finish = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in trace_dir.glob("before_finish--*.json")
        ]
        starts_by_job = {item["job_id"]: item for item in claimed}
        finishes_by_job = {item["job_id"]: item for item in before_finish}
        assert len(starts_by_job) == len(current_jobs)
        assert len(finishes_by_job) == len(current_jobs)
        intervals = []
        for job in current_jobs:
            start = starts_by_job[job.job_id]
            finish = finishes_by_job[job.job_id]
            assert finish["monotonic_ns"] > start["monotonic_ns"]
            assert start["source_id"] == finish["source_id"] == job.subject_id
            intervals.append(
                (
                    start["monotonic_ns"],
                    finish["monotonic_ns"],
                    start["source_id"],
                    start["role"],
                    job.job_type,
                    job.job_id,
                )
            )
        handler_run_ms = [
            (finish - start) / 1_000_000
            for start, finish, *_metadata in intervals
        ]
        queue_wait_ms = [
            (int(starts_by_job[job_id]["monotonic_ns"]) - queued_at_ns[job_id])
            / 1_000_000
            for job_id in job_ids
        ]

        by_source_type = {
            (item[2], item[4]): item for item in intervals
        }
        for source_id in source_by_document:
            selected = by_source_type[(source_id, "source.narrative_select")]
            summarized = by_source_type[(source_id, "source.narrative_summarize")]
            verified = by_source_type[(source_id, "source.narrative_verify")]
            assert summarized[0] >= selected[1]
            assert verified[0] >= summarized[1]

        if profile == "P1":
            ordered = sorted(intervals)
            assert all(
                current[0] >= previous[1]
                for previous, current in zip(ordered, ordered[1:])
            )
        else:
            overlap = any(
                left[3] != right[3]
                and {left[3], right[3]} == {"compute", "model"}
                and left[2] != right[2]
                and max(left[0], right[0]) < min(left[1], right[1])
                for index, left in enumerate(intervals)
                for right in intervals[index + 1 :]
            )
            assert overlap, "P2 did not overlap compute and model work across sources"

        call_records = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in trace_dir.glob("model-call--*.json")
        ]
        assert len(call_records) == 4
        expected_model_source_ids = {
            ref.source_id
            for digest, (_data, ref) in indexed.items()
            if source_by_digest[digest]["sample_id"] != "SKIP"
        }
        assert {item["source_id"] for item in call_records} == expected_model_source_ids

        artifact_store = NarrativeArtifactStore(
            catalog.store,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(store, artifact_store)
        generation = store.read_runtime_gate().control_generation
        dispatch_now = datetime.now(timezone.utc)
        dispatch_at = dispatch_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        dispatch_lease_until = (dispatch_now + timedelta(minutes=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        for _ in range(6):
            receipt = dispatcher.dispatch_next(
                worker_id=f"e6-projector-{profile.lower()}",
                now=dispatch_at,
                lease_until=dispatch_lease_until,
                expected_generation=generation,
            )
            if receipt.status == "empty":
                break
            assert receipt.status == "visible", receipt
        assert store.list_outbox_entries(status="pending") == ()
        assert all(
            job.status is JobStatus.SUCCEEDED for job in store.list_jobs()
        )

        bundle_reader = NarrativeBundleReader(artifact_store)
        bundles_by_source_id = {}
        real_object_bytes = 0
        skip_size = None
        for document_id, source in source_by_document.items():
            source_job = next(
                job
                for job in current_jobs
                if job.subject_id == document_id
                and job.job_type == "source.narrative_select"
            )
            selection_result = NarrativeSelectResult.from_dict(
                _attempt_result(store, source_job.job_id).result
            )
            assert selection_result.encoded_size <= 1_048_576
            assert selection_result.source_metadata.language == source["language"]

            summary_job = next(
                job
                for job in current_jobs
                if job.subject_id == document_id
                and job.job_type == "source.narrative_summarize"
            )
            summary_result = _attempt_result(store, summary_job.job_id)
            summary_payload = json.loads(
                json.dumps(summary_result.result, default=lambda value: dict(value))
            )
            assert len(canonical_json(summary_payload).encode("utf-8")) <= 65_536
            assert summary_result.result["translate"] is False

            verify_job = next(
                job
                for job in current_jobs
                if job.subject_id == document_id
                and job.job_type == "source.narrative_verify"
            )
            handler_result = _attempt_result(store, verify_job.job_id)
            assert handler_result.outcome is HandlerOutcome.SUCCEEDED
            expected_bundle = NarrativeBundle.from_dict(handler_result.result)
            loaded = bundle_reader.read(
                document_id=expected_bundle.source_ref.document_id,
                source_id=expected_bundle.source_ref.source_id,
                source_sha256=expected_bundle.source_ref.content_sha256,
            )
            assert loaded.bundle.to_dict() == expected_bundle.to_dict()
            assert loaded.artifact.status == "visible"
            assert loaded.bundle.encoded_size <= 1_310_720
            bundles_by_source_id[expected_bundle.source_ref.source_id] = (
                source,
                loaded,
            )

            if source["sample_id"] == "SKIP":
                skip_size = loaded.artifact.byte_size
                assert expected_bundle.quality_status == "skipped_no_narrative"
                assert expected_bundle.selection.coverage_complete is True
                assert expected_bundle.evidence_spans == ()
                assert expected_bundle.summary.status == "summary_not_needed"
                assert loaded.artifact.byte_size <= 16_384
                assert expected_bundle.source_ref.source_id not in {
                    item["source_id"] for item in call_records
                }
                continue

            sample_id = str(source["sample_id"])
            selected_topics = {
                topic
                for span in expected_bundle.evidence_spans
                for topic in span.structured_value.get("topics", ())
            }
            required_topics = {
                "P01": {
                    "new_business", "products_rd", "capacity_projects",
                    "orders_customers", "core_business", "industry_dynamics",
                },
                "P04": {
                    "new_business", "products_rd", "capacity_projects",
                    "orders_customers", "core_business", "overseas",
                },
            }.get(sample_id, set())
            assert required_topics <= selected_topics, (
                sample_id, sorted(required_topics - selected_topics)
            )
            sample_caps = {"P01": 96, "P04": 160}
            if sample_id in sample_caps:
                assert len(expected_bundle.evidence_spans) <= sample_caps[sample_id]

            expected_quality_status = (
                "needs_review"
                if expected_bundle.summary.draft is not None
                and expected_bundle.summary.draft.status == "needs_review"
                else "verified"
            )
            assert expected_bundle.quality_status == expected_quality_status
            assert expected_bundle.evidence_spans
            real_object_bytes += loaded.artifact.byte_size
            raw = next(
                data
                for digest, (data, ref) in indexed.items()
                if ref.source_id == expected_bundle.source_ref.source_id
            )
            if source["document_kind"] == "investor_call_transcript":
                material = extract_transcript_material(raw, mime_type="text/plain")
                verified_ids, failed_ids = verify_transcript_evidence_spans(
                    material.text_utf8,
                    source_id=expected_bundle.source_ref.source_id,
                    source_sha256=expected_bundle.source_ref.content_sha256,
                    evidence_spans=expected_bundle.evidence_spans,
                    language=str(source["language"]),
                )
            else:
                verified_ids, failed_ids = verify_pdf_evidence_spans_bytes(
                    raw,
                    source_id=expected_bundle.source_ref.source_id,
                    source_sha256=expected_bundle.source_ref.content_sha256,
                    evidence_spans=expected_bundle.evidence_spans,
                )
            assert set(verified_ids) == {
                span.span_id for span in expected_bundle.evidence_spans
            }
            assert failed_ids == ()

        assert skip_size is not None and skip_size <= 16_384
        real_raw_bytes = sum(
            len(data)
            for sample_id, (_sample, data, _path) in copied_samples.items()
        )
        real_artifact_bytes_by_sample = {
            str(source["sample_id"]): loaded.artifact.byte_size
            for source, loaded in bundles_by_source_id.values()
            if source["sample_id"] != "SKIP"
        }
        raw_bytes_by_sample = {
            sample_id: len(data)
            for sample_id, (_sample, data, _path) in copied_samples.items()
        }
        assert real_object_bytes / real_raw_bytes <= 0.03, (
            f"real narrative artifact ratio={real_object_bytes}/{real_raw_bytes}; "
            f"artifact_bytes={real_artifact_bytes_by_sample}; "
            f"raw_bytes={raw_bytes_by_sample}"
        )

        visible = catalog.reader.fetchone(
            """SELECT COUNT(*) AS count, COUNT(DISTINCT work_key) AS work_keys
                 FROM narrative_artifact_versions WHERE status='visible'"""
        )
        assert visible is not None
        assert int(visible["count"]) == 5
        assert int(visible["work_keys"]) == 5
        duplicated = catalog.reader.fetchone(
            """SELECT COUNT(*) AS count FROM (
                   SELECT work_key FROM narrative_artifact_versions
                    WHERE status='visible' GROUP BY work_key HAVING COUNT(*) > 1
               )"""
        )
        assert duplicated is not None and int(duplicated["count"]) == 0
        object_paths = tuple(
            (profile_root / "catalog" / "objects" / "sha256").rglob("*.json")
        )
        assert len(object_paths) == 5
        assert sum(path.stat().st_size for path in object_paths) == sum(
            int(loaded.artifact.byte_size)
            for _source, loaded in bundles_by_source_id.values()
        )
        assert not tuple(
            path
            for path in profile_root.rglob("*")
            if path.is_file() and path.name.lower() in {"normalized.md", "summary.md"}
        )
        artifact_count_after = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count FROM artifacts"
        )
        assert artifact_count_after is not None
        assert int(artifact_count_after["count"]) == initial_artifact_count

        for event in events:
            replayed = scheduler.materialize_event(event)
            assert (replayed.jobs_created, replayed.dependencies_created) == (0, 0)
        visible_before_repeat = int(visible["count"])
        supervisor = AutomationSupervisor(config)
        try:
            supervisor.start()
            supervisor.wait_for_terminal(tuple(job.job_id for job in store.list_jobs()), timeout_seconds=10.0)
        finally:
            supervisor.stop()
        visible_after_repeat = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count FROM narrative_artifact_versions WHERE status='visible'"
        )
        assert visible_after_repeat is not None
        assert int(visible_after_repeat["count"]) == visible_before_repeat
        assert len(tuple(trace_dir.glob("model-call--*.json"))) == 4
        all_attempts = [
            attempt
            for job_id in job_ids
            for attempt in store.list_attempts(job_id)
        ]
        database_path = automation_root / "automation.db"
        wal_path = Path(f"{database_path}-wal")
        wall_seconds = time.perf_counter() - profile_started
        peak_rss_bytes = max(peak_rss_values, default=0)
        assert peak_rss_bytes > 0
        return {
            "profile": profile,
            "raw_bytes": real_raw_bytes,
            "object_bytes": real_object_bytes,
            "skip_bytes": skip_size,
            "visible_count": int(visible["count"]),
            "model_calls": len(call_records),
            "intervals": intervals,
            "wall_seconds": round(wall_seconds, 3),
            "narrative_documents_per_hour": round(
                len(call_records) * 3600 / wall_seconds, 1
            ),
            "p95_queue_wait_ms": round(_e6_percentile95(queue_wait_ms), 1),
            "p95_handler_ms": round(_e6_percentile95(handler_run_ms), 1),
            "max_concurrency": _e6_max_concurrency(
                [(start, finish) for start, finish, *_metadata in intervals]
            ),
            "peak_process_tree_rss_bytes": peak_rss_bytes,
            "automation_db_bytes": database_path.stat().st_size,
            "automation_wal_bytes": wal_path.stat().st_size if wal_path.exists() else 0,
            "retry_count": max(0, len(all_attempts) - len(job_ids)),
            "sqlite_busy_errors": sum(
                1
                for attempt in all_attempts
                if attempt.error_code
                and any(
                    token in attempt.error_code.upper()
                    for token in ("BUSY", "LOCKED")
                )
            ),
            "sqlite_busy_p95_ms": None,
            "catalog_lock_wait_ms": None,
        }
    finally:
        if catalog is not None:
            catalog.close()


def test_e6_real_samples_run_isolated_p1_p2_and_restore_test_root(
    tmp_path: Path,
) -> None:
    if os.environ.get("COMPANY_WIKI_RUN_E6") != "1":
        pytest.skip("set COMPANY_WIKI_RUN_E6=1 to run the real-sample E6 gate")

    test_base = Path(
        os.environ.get("COMPANY_WIKI_E6_TEST_BASE", str(tmp_path))
    ).resolve()
    assert test_base.is_dir(), "the dedicated E6 test root must already exist"
    initial_test_root_entries = set(test_base.iterdir())

    companies_root, sample_paths = _e6_source_paths()
    transcript_root = sample_paths["T01"].parent
    assert companies_root.is_dir()
    assert transcript_root.is_dir()
    production_hashes: dict[Path, str] = {}
    copied_samples: dict[str, tuple[dict[str, object], bytes, Path]] = {}
    input_files: dict[str, bytes] = {}
    for sample in _E6_REAL_SAMPLES:
        sample_id = str(sample["sample_id"])
        source_path = sample_paths[sample_id]
        assert source_path.is_file(), f"missing frozen E6 source: {source_path}"
        data = source_path.read_bytes()
        assert len(data) > 0
        assert _sha(data) == sample["sha256"], f"frozen SHA changed for {sample_id}"
        production_hashes[source_path] = _sha(data)
        input_files[sample_id] = data

    production_fingerprint = _e6_production_fingerprint()
    run_root = test_base / f"m3-e2e-{uuid.uuid4().hex}"
    assert run_root.parent.resolve() == test_base.resolve()
    assert run_root.name.startswith("m3-e2e-")
    assert not run_root.exists()


    run_root.mkdir()
    try:
        input_root = run_root / "input"
        input_root.mkdir()
        for sample in _E6_REAL_SAMPLES:
            sample_id = str(sample["sample_id"])
            copied_path = input_root / sample_id / str(sample["name"])
            copied_path.parent.mkdir(parents=True)
            copied_path.write_bytes(input_files[sample_id])
            copied = copied_path.read_bytes()
            assert _sha(copied) == sample["sha256"]
            copied_samples[sample_id] = (sample, copied, copied_path)

        profile_results: dict[str, dict[str, object]] = {}
        for profile in ("P1", "P2"):
            profile_results[profile] = _e6_run_profile(
                run_root,
                profile=profile,
                copied_samples=copied_samples,
            )
        assert profile_results["P1"]["visible_count"] == 5
        assert profile_results["P2"]["visible_count"] == 5
        assert profile_results["P1"]["model_calls"] == 4
        assert profile_results["P2"]["model_calls"] == 4
        assert profile_results["P1"]["object_bytes"] / profile_results["P1"]["raw_bytes"] <= 0.03
        assert profile_results["P2"]["object_bytes"] / profile_results["P2"]["raw_bytes"] <= 0.03
        metric_keys = (
            "wall_seconds",
            "narrative_documents_per_hour",
            "p95_queue_wait_ms",
            "p95_handler_ms",
            "max_concurrency",
            "peak_process_tree_rss_bytes",
            "automation_db_bytes",
            "automation_wal_bytes",
            "raw_bytes",
            "object_bytes",
            "skip_bytes",
            "visible_count",
            "model_calls",
            "retry_count",
            "sqlite_busy_errors",
            "sqlite_busy_p95_ms",
            "catalog_lock_wait_ms",
        )
        print(
            "E6_REAL_PROFILE_RECEIPT "
            + json.dumps(
                {
                    profile: {
                        key: result[key]
                        for key in metric_keys
                    }
                    for profile, result in profile_results.items()
                },
                sort_keys=True,
            )
        )
    finally:
        if run_root.exists():
            assert run_root.resolve().parent == test_base.resolve()
            assert run_root.name.startswith("m3-e2e-")
            shutil.rmtree(run_root)
        assert not run_root.exists()
        assert {
            path: _sha(path.read_bytes()) for path in production_hashes
        } == production_hashes
        assert _e6_production_fingerprint() == production_fingerprint
        assert set(test_base.iterdir()) == initial_test_root_entries

    assert not run_root.exists()


def test_e7_r09_lost_model_response_retries_without_duplicate_visible_bundle(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(
        tmp_path, "m3-e4-runtime-e7-lost-response"
    )
    catalog = None
    try:
        source_bytes = _pdf_bytes(
            "Acme launched a new product for overseas customers in 2026."
        )
        catalog, reader, indexed = _new_catalog(
            run_root,
            [
                {
                    "name": "annual.pdf",
                    "data": source_bytes,
                    "title": "Acme annual report",
                    "document_kind": "annual_report",
                }
            ],
        )
        model = LostResponseOnceModel()
        clock = FixedClock()
        store, scheduler, worker = _runtime(
            run_root, reader, model, clock=clock
        )
        ref = next(iter(indexed.values()))[1]
        event = _event(reader, ref, event_id="event-e7-lost-response")
        store.put_event(event)
        created = scheduler.materialize_event(event)
        assert (created.jobs_created, created.dependencies_created) == (3, 3)

        processed = _drain(worker, scheduler)
        assert processed == 2, [
            (job.job_type, job.status.value, job.last_error_code)
            for job in store.list_jobs()
        ]
        jobs = {job.job_type: job for job in store.list_jobs()}
        assert jobs["source.narrative_select"].status is JobStatus.SUCCEEDED
        assert jobs["source.narrative_summarize"].status is JobStatus.RETRY_WAIT
        assert jobs["source.narrative_verify"].status is JobStatus.PLANNED
        assert len(model.calls) == 1
        assert store.list_outbox_entries() == ()
        assert not tuple(
            (run_root / "catalog" / "objects" / "sha256").rglob("*.json")
        )

        retry_time = "2026-09-28T22:20:00Z"
        clock.value = retry_time
        scheduler.refresh_ready(now=retry_time)
        assert (
            store.get_job(jobs["source.narrative_summarize"].job_id).status
            is JobStatus.READY
        )
        assert _drain(worker, scheduler) == 2

        jobs = {job.job_type: job for job in store.list_jobs()}
        summarize_attempts = store.list_attempts(
            jobs["source.narrative_summarize"].job_id
        )
        assert len(summarize_attempts) == 2
        assert summarize_attempts[0].error_code == "MODEL_TIMEOUT"
        assert summarize_attempts[1].outcome is HandlerOutcome.SUCCEEDED
        assert jobs["source.narrative_summarize"].status is JobStatus.SUCCEEDED
        assert jobs["source.narrative_verify"].status is JobStatus.VERIFYING
        assert len(model.calls) == 2
        assert len(store.list_outbox_entries(status="pending")) == 1

        artifact_store = NarrativeArtifactStore(
            catalog.store,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(store, artifact_store)
        dispatch_now = datetime.now(timezone.utc)
        receipt = dispatcher.dispatch_next(
            worker_id="e7-lost-response-projector",
            now=dispatch_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            lease_until=(dispatch_now + timedelta(minutes=2)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            expected_generation=store.read_runtime_gate().control_generation,
        )
        assert receipt.status == "visible"
        assert store.list_outbox_entries(status="pending") == ()
        loaded = NarrativeBundleReader(artifact_store).read(
            document_id=ref.document_id,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
        )
        assert loaded.bundle.source_ref.content_sha256 == _sha(source_bytes)
        visible = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count, COUNT(DISTINCT work_key) AS work_keys "
            "FROM narrative_artifact_versions WHERE status='visible'"
        )
        assert visible is not None
        assert (int(visible["count"]), int(visible["work_keys"])) == (1, 1)
        assert len(
            tuple((run_root / "catalog" / "objects" / "sha256").rglob("*.json"))
        ) == 1
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


def test_e7_r11_100_narrative_jobs_recover_after_worker_restart_without_duplicates(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(
        tmp_path, "m3-e4-runtime-e7-r11-100job-restart"
    )
    catalog = None
    first_supervisor = None
    recovery_supervisor = None
    try:
        sources = [
            {
                "name": f"annual-{index:02d}.pdf",
                "data": _pdf_bytes(
                    f"Acme new product {index:02d} advanced export sales and overseas "
                    f"capacity for industrial customers during 2026."
                ),
                "title": f"Acme annual report 2026 #{index:02d}",
                "document_kind": "annual_report",
            }
            for index in range(34)
        ]
        catalog, reader, indexed = _new_catalog(run_root, sources)
        raw_file_hashes = {
            path: _sha(path.read_bytes())
            for path in (run_root / "companies").rglob("*")
            if path.is_file()
        }
        initial_artifacts = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count FROM artifacts"
        )
        assert initial_artifacts is not None

        automation_root = run_root / "automation"
        automation_root.mkdir()
        store = AutomationStore(automation_root / "automation.db")
        store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
        scheduler = AutomationScheduler(
            store,
            create_default_registry(),
            PolicyConfig(allow_llm=True, allow_network=True),
        )
        events = [
            _event(reader, ref, event_id=f"event-e7-r11-{index:02d}")
            for index, (_data, ref) in enumerate(indexed.values())
        ]
        for event in events:
            store.put_event(event)
            created = scheduler.materialize_event(event)
            assert (created.jobs_created, created.dependencies_created) == (3, 3)

        jobs = store.list_jobs()
        assert len(jobs) == 102
        job_ids = tuple(job.job_id for job in jobs)
        target_source_id = events[0].subject_id
        target_job = next(
            job
            for job in jobs
            if job.subject_id == target_source_id
            and job.job_type == "source.narrative_select"
        )
        trace_dir = run_root / "trace"

        def config(*, block_target: bool) -> SupervisorConfig:
            options: dict[str, object] = {
                "project_root": str(run_root),
                "trace_dir": str(trace_dir),
                "model_delay_seconds": 0.02,
            }
            if block_target:
                options["block_phase_by_job"] = {
                    target_job.job_id: "before_finish"
                }
            return SupervisorConfig(
                db_path=automation_root / "automation.db",
                log_dir=run_root / "process-logs",
                profile="P4",
                runtime_factory_path=(
                    "support.narrative_runtime_worker_fixture:create_runtime"
                ),
                runtime_options_json=json.dumps(options, sort_keys=True),
                compute_job_types=(
                    "source.narrative_select",
                    "source.narrative_verify",
                ),
                model_job_types=("source.narrative_summarize",),
                lease_seconds=3.0,
                heartbeat_interval_seconds=0.5,
                idle_sleep_seconds=0.03,
                maintenance_interval_seconds=0.05,
                stop_grace_seconds=10.0,
                child_log_max_bytes=65_536,
            )

        first_supervisor = AutomationSupervisor(config(block_target=True))
        first_supervisor.start()
        try:
            _wait_for_e7_condition(
                lambda: bool(
                    tuple(
                        trace_dir.glob(
                            f"before_finish--{target_job.job_id}--1--*.json"
                        )
                    )
                ),
                timeout=60,
            )
            marker = json.loads(
                next(
                    trace_dir.glob(
                        f"before_finish--{target_job.job_id}--1--*.json"
                    )
                ).read_text(encoding="utf-8")
            )
            first_supervisor.terminate_worker(str(marker["worker_id"]))
        finally:
            first_supervisor.stop()

        interrupted = store.list_attempts(target_job.job_id)
        assert len(interrupted) == 1
        assert interrupted[0].finished_at is None
        _wait_for_e7_condition(
            lambda: store.list_attempts(target_job.job_id)[0].lease_until < _e7_now(),
            timeout=10,
        )

        recovery_supervisor = AutomationSupervisor(config(block_target=False))
        recovery_supervisor.start()
        try:
            parent_job_ids = tuple(
                job.job_id
                for job in jobs
                if job.job_type != "source.narrative_verify"
            )
            recovery_supervisor.wait_for_terminal(
                parent_job_ids, timeout_seconds=240.0
            )
            _wait_for_e6_verification_jobs(
                recovery_supervisor, store, job_ids, timeout_seconds=120.0
            )
        finally:
            recovery_supervisor.stop()

        current_jobs = store.list_jobs()
        assert len(current_jobs) == 102
        assert sum(job.status is JobStatus.SUCCEEDED for job in current_jobs) == 68
        assert sum(job.status is JobStatus.VERIFYING for job in current_jobs) == 34
        assert len(store.list_outbox_entries(status="pending")) == 34
        for job in current_jobs:
            attempts = store.list_attempts(job.job_id)
            assert len(attempts) == (2 if job.job_id == target_job.job_id else 1)
            if job.job_id == target_job.job_id:
                assert attempts[0].error_code == "LEASE_EXPIRED"
                assert attempts[1].outcome is HandlerOutcome.SUCCEEDED
            else:
                assert attempts[0].outcome is HandlerOutcome.SUCCEEDED

        model_calls = tuple((trace_dir).glob("model-call--*.json"))
        assert len(model_calls) == 34
        artifact_store = NarrativeArtifactStore(
            catalog.store,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(store, artifact_store)
        dispatch_now = datetime.now(timezone.utc)
        for _ in range(35):
            receipt = dispatcher.dispatch_next(
                worker_id="e7-r11-projector",
                now=dispatch_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                lease_until=(dispatch_now + timedelta(minutes=2)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                expected_generation=store.read_runtime_gate().control_generation,
            )
            if receipt.status == "empty":
                break
            assert receipt.status == "visible"

        assert store.list_outbox_entries(status="pending") == ()
        visible = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count, COUNT(DISTINCT work_key) AS work_keys "
            "FROM narrative_artifact_versions WHERE status='visible'"
        )
        assert visible is not None
        assert (int(visible["count"]), int(visible["work_keys"])) == (34, 34)
        object_paths = tuple(
            (run_root / "catalog" / "objects" / "sha256").rglob("*.json")
        )
        assert len(object_paths) == 34
        assert {
            path: _sha(path.read_bytes()) for path in raw_file_hashes
        } == raw_file_hashes
        artifacts_after = catalog.reader.fetchone(
            "SELECT COUNT(*) AS count FROM artifacts"
        )
        assert artifacts_after == initial_artifacts
    finally:
        if first_supervisor is not None:
            first_supervisor.stop()
        if recovery_supervisor is not None:
            recovery_supervisor.stop()
        _cleanup(tmp_path, run_root, baseline, catalog)
